from typing import Dict, List, Optional, Callable, Any
import httpx
import logging
from pathlib import Path
from datetime import datetime
from .schemas import RiskCreate, RiskUpdate
from .conflict import ConflictResolver
from .config import ApiConfig
from .cache import Cache
from .offline import OfflineQueue
from pydantic import ValidationError
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from DEV.websocket_client import WebSocketClient

logger = logging.getLogger(__name__)

class RiskkitClient:
    def __init__(self, config: ApiConfig):
        from DEV.websocket_client import WebSocketClient
        
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient()
        self.socket = WebSocketClient(
            base_url=config.socket_url,
            token=config.api_key,
            event_manager=None
        )
        self.cache = Cache(config.cache_dir)
        self.offline_queue = OfflineQueue(config.cache_dir)
        self._connected = False
        self.conflict_resolver = ConflictResolver()
        
    def subscribe_to_project(self, project_id: int):
        """Subscribe to project-specific events"""
        self.socket.subscribe_to_project(project_id)

    def subscribe_to_channel(self, channel: str, **kwargs):
        """Subscribe to a specific channel"""
        self.socket.subscribe_to_channel(channel, **kwargs)

    def subscribe_to_all_channels(self):
        """Subscribe to all available channels"""
        self.socket.subscribe_to_all_channels()

    def connect_signal(self, signal_name: str, callback: Callable):
        """Connect a callback to a WebSocket signal"""
        if hasattr(self.socket, signal_name):
            getattr(self.socket, signal_name).connect(callback)
        else:
            logger.warning(f"Unknown signal: {signal_name}")
        
    async def close(self):
        """Cleanup and close all connections"""
        try:
            # Close WebSocket connection
            if self.socket:
                self.socket.disconnect()
                await self.socket.wait_for_disconnected()
            
            # Close HTTP client
            if self.client:
                await self.client.aclose()
            
            # Save cache and offline queue
            if self.cache:
                self.cache.save()
            
            if self.offline_queue:
                self.offline_queue.save()
                
            self._connected = False
            logger.info("RiskkitClient closed successfully")
            
        except Exception as e:
            logger.error(f"Error during RiskkitClient cleanup: {e}")
            
    async def wait_for_disconnected(self):
        """Wait for WebSocket to disconnect"""
        if self.socket:
            await self.socket.wait_for_disconnected()
        
    def sync_close(self):
        """Synchronous cleanup"""
        try:
            if self.socket:
                self.socket.disconnect()
            if self.cache:
                self.cache.save()
            if self.offline_queue:
                self.offline_queue.save()
            self._connected = False
            logger.info("RiskkitClient closed successfully")
        except Exception as e:
            logger.error(f"Error during RiskkitClient cleanup: {e}")
        