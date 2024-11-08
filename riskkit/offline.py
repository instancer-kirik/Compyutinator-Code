from pathlib import Path
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OfflineQueue:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.queue_file = queue_dir / "offline_queue.json"
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.queue: List[Dict] = self._load_queue()

    def _load_queue(self) -> List[Dict]:
        """Load queued operations from disk"""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load offline queue: {e}")
        return []

    def _save_queue(self):
        """Save queued operations to disk"""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump(self.queue, f)
        except Exception as e:
            logger.error(f"Failed to save offline queue: {e}")

    def add(self, operation: Dict):
        """Add operation to queue"""
        operation['timestamp'] = datetime.now().isoformat()
        self.queue.append(operation)
        self._save_queue()

    def get_pending(self) -> List[Dict]:
        """Get all pending operations"""
        return self.queue.copy()

    def remove(self, operation_id: str):
        """Remove operation from queue"""
        self.queue = [op for op in self.queue if op.get('id') != operation_id]
        self._save_queue()

    def clear(self):
        """Clear all pending operations"""
        self.queue.clear()
        self._save_queue() 