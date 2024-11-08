from dataclasses import asdict
from typing import Optional, Dict, List
import json
from datetime import datetime
from GUX.widgets.task_checklist_manager import TaskCheckItem
from riskkit.enums import EventPriority

class TaskDataManager:
    """Manages task data persistence and state"""
    def __init__(self, parent):
        self.parent = parent
        self.current_file: Optional[str] = None
        self.unsaved_changes = False
        
    def save_state(self) -> Dict:
        """Get current state as dictionary"""
        return {
            "tasks": [self.parent.get_task_data(row) 
                     for row in range(self.parent.tree_model.rowCount())],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "preferences": self.parent.preferences
            }
        }
        
    def load_state(self, data: Dict) -> bool:
        """Load state from dictionary"""
        try:
            self.parent.tree_model.clear()
            for task_data in data["tasks"]:
                self.parent.add_task_to_tree(TaskCheckItem(**task_data))
            if "preferences" in data.get("metadata", {}):
                self.parent.preferences.update(data["metadata"]["preferences"])
            return True
        except Exception as e:
            self.parent.event_manager.broadcast_news(
                "Load Error",
                f"Failed to load state: {e}",
                EventPriority.HIGH
            )
            return False 