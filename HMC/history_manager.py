from PyQt6.QtWidgets import QListWidget
import logging
from typing import List

class HistoryManager:
    def __init__(self, max_history_length: int = 50):
        self.history: List[str] = []
        self.max_history_length = max_history_length
        self.history_widget = QListWidget()
        
    def update_history(self, path: str):
        """Update history with new path"""
        if path in self.history:
            self.history.remove(path)
        self.history.insert(0, path)
        if len(self.history) > self.max_history_length:
            self.history.pop()

        self.history_widget.clear()
        for item in self.history:
            self.history_widget.addItem(item)
            
    def get_history_widget(self) -> QListWidget:
        """Get the history widget for display"""
        return self.history_widget
        
    def clear_history(self):
        """Clear all history"""
        self.history.clear()
        self.history_widget.clear() 