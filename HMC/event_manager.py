from riskkit.event_manager import EventManager as RiskkitEventManager, SystemEvent, EventPriority
from PyQt6.QtCore import pyqtSignal
from enum import Enum

class AppEvent(Enum):
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"

class AppEventManager(RiskkitEventManager):
    # Application-specific signals
    project_event = pyqtSignal(AppEvent, dict)  # event_type, event_data
    build_event = pyqtSignal(AppEvent, str, dict)  # event_type, project_name, build_data
    run_event = pyqtSignal(AppEvent, str, dict)  # event_type, project_name, run_data
    
    def __init__(self):
        super().__init__()

    def broadcast_project_event(self, event_type: AppEvent, project_data: dict):
        """Broadcast project-related events"""
        self.project_event.emit(event_type, project_data)
        self.broadcast_news(
            f"Project {event_type.value}",
            f"Project '{project_data.get('name', '')}' was {event_type.value}",
            EventPriority.NORMAL
        )

    def broadcast_build_event(self, event_type: AppEvent, project_name: str, build_data: dict):
        """Broadcast build-related events"""
        self.build_event.emit(event_type, project_name, build_data)
        
        if event_type == AppEvent.BUILD_FAILED:
            priority = EventPriority.HIGH
        else:
            priority = EventPriority.NORMAL
            
        self.broadcast_news(
            f"Build {event_type.value}",
            f"Project '{project_name}' build {event_type.value}",
            priority
        )

    def broadcast_run_event(self, event_type: AppEvent, project_name: str, run_data: dict):
        """Broadcast run-related events"""
        self.run_event.emit(event_type, project_name, run_data)
        
        if event_type == AppEvent.RUN_FAILED:
            priority = EventPriority.HIGH
        else:
            priority = EventPriority.NORMAL
            
        self.broadcast_news(
            f"Run {event_type.value}",
            f"Project '{project_name}' run {event_type.value}",
            priority
        ) 