from pathlib import Path
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.expiry_times: Dict[str, datetime] = {}
        
    def set(self, key: str, value: Any, expires_in: Optional[timedelta] = None):
        """Store value in cache with optional expiration"""
        try:
            cache_file = self.cache_dir / f"{key}.json"
            with open(cache_file, 'w') as f:
                json.dump(value, f)
            
            self.memory_cache[key] = value
            if expires_in:
                self.expiry_times[key] = datetime.now() + expires_in
                
        except Exception as e:
            logger.error(f"Cache write error for {key}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value from cache"""
        try:
            # Check expiry
            if key in self.expiry_times:
                if datetime.now() > self.expiry_times[key]:
                    self.delete(key)
                    return default

            # Try memory cache first
            if key in self.memory_cache:
                return self.memory_cache[key]

            # Try file cache
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    value = json.load(f)
                self.memory_cache[key] = value
                return value

        except Exception as e:
            logger.error(f"Cache read error for {key}: {e}")

        return default

    def delete(self, key: str):
        """Remove item from cache"""
        try:
            if key in self.memory_cache:
                del self.memory_cache[key]
            if key in self.expiry_times:
                del self.expiry_times[key]
                
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                cache_file.unlink()
                
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")

    def clear(self):
        """Clear all cached data"""
        try:
            self.memory_cache.clear()
            self.expiry_times.clear()
            for file in self.cache_dir.glob("*.json"):
                file.unlink()
        except Exception as e:
            logger.error(f"Cache clear error: {e}") 