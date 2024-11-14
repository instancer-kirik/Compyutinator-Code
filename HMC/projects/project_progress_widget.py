from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, 
                            QLabel, QFrame)
from PyQt6.QtCore import Qt
import math

class ProjectProgressWidget(QWidget):
    def __init__(self, project_manager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.setup_ui()
        
        # Connect to progress updates
        self.project_manager.project_progress_updated.connect(self.update_progress)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Progress bar with percentage
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
                margin: 0.5px;
            }
        """)
        
        self.progress_label = QLabel("0%")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        layout.addLayout(progress_layout)
        
        # Stats frame
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        stats_layout = QHBoxLayout(stats_frame)
        
        # Task completion
        self.task_label = QLabel("Tasks: 0/0")
        stats_layout.addWidget(self.task_label)
        
        # Documentation progress
        self.docs_label = QLabel("Docs: 0%")
        stats_layout.addWidget(self.docs_label)
        
        # Milestone progress
        self.milestone_label = QLabel("Milestones: 0%")
        stats_layout.addWidget(self.milestone_label)
        
        layout.addWidget(stats_frame)
        
    def update_progress(self, project_name: str, progress: float):
        """Update progress display with animation"""
        percentage = math.floor(progress * 100)
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(f"{percentage}%")
        
        # Update stats
        project = self.project_manager.active_projects[project_name]
        dashboard = self.project_manager.project_dashboards[project_name]
        
        task_total = dashboard.task_manager.tree_model.rowCount()
        task_completed = sum(1 for i in range(task_total) 
                           if dashboard.task_manager.is_task_completed(i))
        self.task_label.setText(f"Tasks: {task_completed}/{task_total}")
        
        doc_progress = self.project_manager.calculate_documentation_coverage(project_name)
        self.docs_label.setText(f"Docs: {math.floor(doc_progress * 100)}%")
        
        milestone_progress = self.project_manager.calculate_milestone_progress(project_name)
        self.milestone_label.setText(f"Milestones: {math.floor(milestone_progress * 100)}%") 