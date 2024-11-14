from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                           QPushButton, QLabel, QMessageBox, QInputDialog,
                           QFileDialog, QListWidget, QSplitter, QGroupBox, QGridLayout, QGraphicsView, QGraphicsScene)
from PyQt6.QtCore import pyqtSignal, Qt
from pathlib import Path
import logging

from .project_progress_widget import ProjectProgressWidget

class ProjectManagerWidget(QWidget):
    """Unified project management widget"""
    project_selected = pyqtSignal(str, str)  # (vault_name, project_name)
    
    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.project_manager = cccore.project_manager
        self.setup_ui()
        self.setup_connections()
        self.refresh_projects()

    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Vault selector
        vault_layout = QHBoxLayout()
        self.vault_selector = QComboBox()
        self.vault_selector.addItems(self.cccore.vault_manager.get_vault_names())
        vault_layout.addWidget(QLabel("Vault:"))
        vault_layout.addWidget(self.vault_selector)
        layout.addLayout(vault_layout)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Project list and controls
        left_widget = self._setup_left_panel()
        splitter.addWidget(left_widget)
        
        # Right side: Project overview
        right_widget = self._setup_right_panel()
        splitter.addWidget(right_widget)
        
        layout.addWidget(splitter)

    def _setup_left_panel(self):
        """Setup left panel with project list and controls"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Project list
        self.project_list = QListWidget()
        layout.addWidget(QLabel("Projects:"))
        layout.addWidget(self.project_list)
        
        # Project management buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Project")
        self.remove_button = QPushButton("Remove Project")
        self.rename_button = QPushButton("Rename Project")
        self.open_button = QPushButton("Open Project")
        
        for button in [self.add_button, self.remove_button, 
                      self.rename_button, self.open_button]:
            button_layout.addWidget(button)
        layout.addLayout(button_layout)
        
        # Project actions
        action_layout = QHBoxLayout()
        self.configure_button = QPushButton("Configure")
        self.build_button = QPushButton("Build")
        self.run_button = QPushButton("Run")
        self.dashboard_button = QPushButton("Dashboard")
        
        for button in [self.configure_button, self.build_button,
                      self.run_button, self.dashboard_button]:
            action_layout.addWidget(button)
        layout.addLayout(action_layout)
        
        return widget

    def _setup_right_panel(self):
        """Setup right panel with project overview"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Portfolio metrics
        metrics_group = QGroupBox("Portfolio Overview")
        metrics_layout = QGridLayout(metrics_group)
        
        self.total_projects = QLabel("Total Projects: 0")
        self.active_projects = QLabel("Active Projects: 0")
        self.resource_usage = QLabel("Resource Usage: 0%")
        
        metrics_layout.addWidget(self.total_projects, 0, 0)
        metrics_layout.addWidget(self.active_projects, 0, 1)
        metrics_layout.addWidget(self.resource_usage, 1, 0)
        
        layout.addWidget(metrics_group)
        
        # Progress widget
        self.progress_widget = ProjectProgressWidget(self.project_manager)
        layout.addWidget(self.progress_widget)
        
        # Dependencies view
        self.dep_view = QGraphicsView()
        self.dep_scene = QGraphicsScene()
        self.dep_view.setScene(self.dep_scene)
        layout.addWidget(QLabel("Project Dependencies:"))
        layout.addWidget(self.dep_view)
        
        return widget

    def setup_connections(self):
        """Setup signal/slot connections"""
        self.vault_selector.currentTextChanged.connect(self.on_vault_changed)
        self.project_list.itemDoubleClicked.connect(self.open_selected_project)
        
        self.add_button.clicked.connect(self.show_add_project_dialog)
        self.remove_button.clicked.connect(self.remove_project)
        self.rename_button.clicked.connect(self.show_rename_dialog)
        self.open_button.clicked.connect(self.open_selected_project)
        
        self.configure_button.clicked.connect(self.configure_project)
        self.build_button.clicked.connect(self.build_project)
        self.run_button.clicked.connect(self.run_project)
        self.dashboard_button.clicked.connect(self.show_dashboard)

    def refresh_projects(self):
        """Refresh the projects list and metrics"""
        self.project_list.clear()
        vault_name = self.vault_selector.currentText()
        if vault_name:
            projects = self.cccore.vault_manager.get_projects(vault_name)
            self.project_list.addItems(projects)
            self._update_portfolio_metrics()
            self._update_dependency_view()

    def _update_portfolio_metrics(self):
        """Update portfolio metrics display"""
        try:
            vault_name = self.vault_selector.currentText()
            projects = self.cccore.vault_manager.get_projects(vault_name)
            
            total = len(projects)
            active = sum(1 for p in projects if self.project_manager.is_project_active(p))
            
            self.total_projects.setText(f"Total Projects: {total}")
            self.active_projects.setText(f"Active Projects: {active}")
            self.resource_usage.setText(f"Resource Usage: {active/total*100:.1f}%" if total else "Resource Usage: 0%")
            
        except Exception as e:
            logging.error(f"Error updating portfolio metrics: {e}")

    def _update_dependency_view(self):
        """Update project dependencies visualization"""
        try:
            self.dep_scene.clear()
            # Add dependency visualization logic here
            # This could show project dependencies as a graph
        except Exception as e:
            logging.error(f"Error updating dependency view: {e}")