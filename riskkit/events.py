from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

class SystemEvent(Enum):
    # System Events
    RESTART_REQUESTED = auto()
    SHUTDOWN_REQUESTED = auto()
    UPDATE_AVAILABLE = auto()
    UPDATE_STARTED = auto()
    UPDATE_COMPLETED = auto()
    
    # Maintenance Events
    MAINTENANCE_SCHEDULED = auto()
    MAINTENANCE_STARTED = auto()
    MAINTENANCE_ENDED = auto()
    
    # Network Events
    NETWORK_ERROR = auto()
    RECONNECTING = auto()
    CONNECTION_RESTORED = auto()
    
    # Data Events
    SYNC_STARTED = auto()
    SYNC_COMPLETED = auto()
    SYNC_FAILED = auto()
    DATA_CORRUPTED = auto()
    BACKUP_STARTED = auto()
    BACKUP_COMPLETED = auto()
    
    # Security Events
    SESSION_EXPIRED = auto()
    UNAUTHORIZED_ACCESS = auto()
    LOGIN_REQUIRED = auto()
    PASSWORD_EXPIRING = auto()
    
    # Resource Events
    RESOURCE_LOCKED = auto()
    RESOURCE_UNLOCKED = auto()
    RESOURCE_CONFLICT = auto()
    
    # Performance Events
    LOW_MEMORY = auto()
    HIGH_CPU_USAGE = auto()
    DISK_SPACE_LOW = auto()

class NotificationPriority(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

class NotificationType(Enum):
    SYSTEM = "system"
    SECURITY = "security"
    UPDATE = "update"
    NETWORK = "network"
    DATA = "data"
    USER = "user"
    NEWS = "news"

@dataclass
class Notification:
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    timestamp: datetime
    action: Optional[str] = None
    data: Optional[dict] = None
    expires_at: Optional[datetime] = None
    dismissed: bool = False 