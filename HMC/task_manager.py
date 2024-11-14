from PyQt6.QtWidgets import QWidget
from abc import ABC, abstractmethod

class TaskManagerMixin(ABC):
    """Abstract base class for task management functionality"""
    @abstractmethod
    def add_task(self, parent_index=None):
        """Add a new task"""
        pass
        
    @abstractmethod
    def filter_row(self, index, parent_visible=True):
        """Filter task rows"""
        pass
        
    @abstractmethod
    def setup_auto_save(self):
        """Setup auto-save functionality"""
        pass

    @abstractmethod
    def update_status_panel(self):
        """Update status panel"""
        pass

    @abstractmethod
    def apply_filters(self):
        """Apply filters to tasks"""
        pass

class TaskManagerBase(QWidget):
    """Base class for task management functionality"""
    def __init__(self):
        super().__init__()
        self.preferences = {
            'auto_save_interval': 300,  # 5 minutes
            'expand_new_tasks': True,
            'show_status_panel': True,
            'show_filter_panel': True,
            'sort_by': None,
            'sort_order': 'ascending',
            'theme': 'system'
        }

    def add_task(self, parent_index=None):
        """Add a new task"""
        raise NotImplementedError
        
    def filter_row(self, index, parent_visible=True):
        """Filter task rows"""
        raise NotImplementedError
        
    def setup_auto_save(self):
        """Setup auto-save functionality"""
        raise NotImplementedError

    def update_status_panel(self):
        """Update status panel"""
        raise NotImplementedError

    def apply_filters(self):
        """Apply filters to tasks"""
        raise NotImplementedError