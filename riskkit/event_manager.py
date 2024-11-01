from PyQt6.QtCore import QObject, pyqtSignal
from enum import Enum
from typing import Optional, Dict, Any
import logging

class SystemEvent(Enum):
    RESTART_REQUESTED = "restart_requested"
    SHUTDOWN_REQUESTED = "shutdown_requested"
    MAINTENANCE_STARTED = "maintenance_started"
    MAINTENANCE_ENDED = "maintenance_ended"
    NEWS_BROADCAST = "news_broadcast"
    ERROR_BROADCAST = "error_broadcast"

class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class EventManager(QObject):
    # System-wide signals
    system_event = pyqtSignal(SystemEvent, dict)  # event_type, event_data
    news_broadcast = pyqtSignal(str, str, EventPriority)  # title, message, priority
    operation_interrupted = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._active_operations: set = set()
        self._is_shutting_down = False

    def register_operation(self, operation_id: str):
        """Register an ongoing operation"""
        self._active_operations.add(operation_id)

    def unregister_operation(self, operation_id: str):
        """Mark an operation as completed"""
        self._active_operations.discard(operation_id)

    def has_active_operations(self) -> bool:
        """Check if there are any ongoing operations"""
        return len(self._active_operations) > 0

    def broadcast_news(self, title: str, message: str, priority: EventPriority = EventPriority.NORMAL):
        """Broadcast a news message to all components"""
        self.news_broadcast.emit(title, message, priority)
        logging.info(f"News broadcast: {title} - {message}")

    def request_restart(self, reason: str = "", force: bool = False):
        """Request application restart"""
        if self.has_active_operations() and not force:
            self.broadcast_news(
                "Restart Pending",
                "Please complete or cancel ongoing operations before restart",
                EventPriority.HIGH
            )
            return False
        
        self._is_shutting_down = True
        self.system_event.emit(SystemEvent.RESTART_REQUESTED, {"reason": reason})
        self.operation_interrupted.emit()
        return True

    def interrupt_operations(self):
        """Interrupt all ongoing operations"""
        if self._active_operations:
            self.operation_interrupted.emit()
            self._active_operations.clear() 