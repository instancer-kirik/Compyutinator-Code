from PyQt6.QtWidgets import QWidget

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
        
    # Move common methods here
    def add_task(self, parent_index=None):
        """Base implementation"""
        pass
        
    def filter_row(self, index, parent_visible=True):
        """Base implementation"""
        pass
        
    def setup_auto_save(self):
        """Base implementation"""
        pass