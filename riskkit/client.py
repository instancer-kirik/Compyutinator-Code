from typing import Dict, List, Optional, Callable, Any
import httpx
import asyncio
from phoenix_channel import PhoenixChannel
from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
import backoff
import logging
from pathlib import Path
from .schemas import RiskCreate, RiskUpdate, ResourceBase
from .conflict import ConflictResolver
from pydantic import ValidationError

logger = logging.getLogger(__name__)

@dataclass
class ApiConfig:
    base_url: str
    api_key: str
    org_id: str
    socket_url: Optional[str] = None
    cache_dir: Optional[Path] = None
    max_retries: int = 3
    offline_mode: bool = False

    def __post_init__(self):
        if not self.socket_url:
            self.socket_url = f"{self.base_url}/socket"
        if not self.cache_dir:
            self.cache_dir = Path.home() / ".riskkit" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

class Cache:
    def __init__(self, cache_dir: Path):
        self.db_path = cache_dir / "cache.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def get(self, key: str) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT data FROM cache WHERE key = ?", (key,)
                ).fetchone()
                return json.loads(result[0]) if result else None
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def set(self, key: str, data: Dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, data) VALUES (?, ?)",
                    (key, json.dumps(data))
                )
        except Exception as e:
            logger.error(f"Cache write error: {e}")

class OfflineQueue:
    def __init__(self, cache_dir: Path):
        self.queue_path = cache_dir / "offline_queue.json"
        self.queue: List[Dict] = self._load_queue()

    def _load_queue(self) -> List[Dict]:
        try:
            if self.queue_path.exists():
                return json.loads(self.queue_path.read_text())
        except Exception as e:
            logger.error(f"Failed to load offline queue: {e}")
        return []

    def _save_queue(self):
        try:
            self.queue_path.write_text(json.dumps(self.queue))
        except Exception as e:
            logger.error(f"Failed to save offline queue: {e}")

    def add(self, operation: Dict):
        self.queue.append(operation)
        self._save_queue()

    def get_pending(self) -> List[Dict]:
        return self.queue.copy()

    def clear(self):
        self.queue = []
        self._save_queue()

class RiskkitClient:
    def __init__(self, config: ApiConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient()
        self.socket = PhoenixChannel(config.socket_url)
        self._subscribers: Dict[str, List[Callable]] = {}
        self.cache = Cache(config.cache_dir)
        self.offline_queue = OfflineQueue(config.cache_dir)
        self._connected = False
        self._retry_task = None
        self.conflict_resolver = ConflictResolver()

    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPError, ConnectionError),
        max_tries=3
    )
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict:
        """Make HTTP request with retry logic"""
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            if e.response.status_code == 401:
                self._notify("auth:expired", {})
            raise

    async def connect(self):
        """Connect to Phoenix channels with retry logic"""
        if self.config.offline_mode:
            logger.info("Running in offline mode")
            return

        try:
            await self.socket.connect()
            await self._setup_channels()
            self._connected = True
            
            # Process offline queue if any
            await self._process_offline_queue()
            
            # Start retry task if not running
            if not self._retry_task:
                self._retry_task = asyncio.create_task(self._retry_connection())
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._connected = False

    async def _retry_connection(self):
        """Continuously retry connection when disconnected"""
        while True:
            if not self._connected:
                try:
                    await self.connect()
                except Exception as e:
                    logger.error(f"Retry connection failed: {e}")
            await asyncio.sleep(5)

    async def _process_offline_queue(self):
        """Process pending offline operations"""
        pending = self.offline_queue.get_pending()
        for operation in pending:
            try:
                await self._make_request(
                    operation["method"],
                    operation["url"],
                    json=operation["data"]
                )
            except Exception as e:
                logger.error(f"Failed to process offline operation: {e}")
                return
        self.offline_queue.clear()

    async def get_risks(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Fetch risks with offline support"""
        cache_key = f"risks:{json.dumps(filters or {})}"
        
        # Try to get from cache first
        cached = self.cache.get(cache_key)
        if cached and self.config.offline_mode:
            return cached

        try:
            data = await self._make_request(
                "GET",
                f"{self.config.base_url}/api/risks",
                params=filters
            )
            self.cache.set(cache_key, data)
            return data
        except Exception as e:
            if cached:
                logger.warning(f"Using cached risks due to error: {e}")
                return cached
            raise

    async def create_risk(self, risk_data: Dict) -> Dict:
        """Create risk with validation"""
        try:
            # Validate data against schema
            validated_data = RiskCreate(**risk_data).dict()
            
            if not self._connected or self.config.offline_mode:
                operation = {
                    "method": "POST",
                    "url": f"{self.config.base_url}/api/risks",
                    "data": {"risk": validated_data},
                    "timestamp": datetime.now().isoformat()
                }
                self.offline_queue.add(operation)
                return {"status": "queued", "data": validated_data}

            return await self._make_request(
                "POST",
                f"{self.config.base_url}/api/risks",
                json={"risk": validated_data}
            )
        except ValidationError as e:
            raise ValueError(f"Invalid risk data: {e.errors()}")

    async def update_risk(self, risk_id: int, risk_data: Dict) -> Dict:
        """Update risk with conflict resolution"""
        try:
            # Validate update data
            validated_data = RiskUpdate(**risk_data).dict()
            
            if not self._connected or self.config.offline_mode:
                # Store local version
                cache_key = f"risk:{risk_id}"
                self.cache.set(f"{cache_key}:local", validated_data)
                
                operation = {
                    "method": "PUT",
                    "url": f"{self.config.base_url}/api/risks/{risk_id}",
                    "data": {"risk": validated_data},
                    "timestamp": datetime.now().isoformat()
                }
                self.offline_queue.add(operation)
                return {"status": "queued", "data": validated_data}

            # Get current server version for comparison
            current = await self._make_request(
                "GET",
                f"{self.config.base_url}/api/risks/{risk_id}"
            )

            # Check for conflicts
            if current["version"] != validated_data["version"]:
                resolved = self.conflict_resolver.resolve(
                    validated_data,
                    current,
                    strategy="merge_fields"
                )
                
                if "_conflicts" in resolved:
                    return {
                        "status": "conflict",
                        "data": resolved,
                        "message": "Conflicts detected, manual resolution required"
                    }
                
                validated_data = resolved

            return await self._make_request(
                "PUT",
                f"{self.config.base_url}/api/risks/{risk_id}",
                json={"risk": validated_data}
            )
            
        except ValidationError as e:
            raise ValueError(f"Invalid risk data: {e.errors()}")

    # ... similar patterns for other methods ...

    async def close(self):
        """Clean up connections"""
        if self._retry_task:
            self._retry_task.cancel()
        await self.socket.disconnect()
        await self.client.aclose()
        