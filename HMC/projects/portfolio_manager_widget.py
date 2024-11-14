from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                           QPushButton, QLabel, QComboBox, QListWidget,
                           QGroupBox, QGridLayout, QGraphicsView, QGraphicsScene)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPen, QPainterPath
import logging
from pathlib import Path

from typing import Dict, List, Optional

class PortfolioManagerWidget(QWidget):
    """High-level project portfolio management widget"""
    
    project_selected = pyqtSignal(str, str)  # (vault_name, project_name)
    
    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.project_manager = cccore.project_manager
        self.current_vault = None
        self.current_project = None
        self.dashboard = None
        self.setup_ui()
        self.setup_connections()
        self.refresh_vaults()

    def setup_ui(self):
        """Setup the main UI layout"""
        layout = QVBoxLayout(self)
        
        # Top section: Vault and Project Selection
        selection_layout = self._setup_selection_panel()
        layout.addLayout(selection_layout)
        
        # Main content area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Project list and actions
        left_panel = self._setup_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Project overview/dashboard
        right_panel = self._setup_right_panel()
        splitter.addWidget(right_panel)
        
        layout.addWidget(splitter)

    def _setup_selection_panel(self):
        """Setup vault and project selection controls"""
        layout = QHBoxLayout()
        
        # Vault selector
        vault_layout = QHBoxLayout()
        self.vault_selector = QComboBox()
        vault_layout.addWidget(QLabel("Vault:"))
        vault_layout.addWidget(self.vault_selector)
        layout.addLayout(vault_layout)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.settings_btn = QPushButton("Settings")
        actions_layout.addWidget(self.refresh_btn)
        actions_layout.addWidget(self.settings_btn)
        layout.addLayout(actions_layout)
        
        return layout

    def _setup_left_panel(self):
        """Setup project list and management controls"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Project list
        self.project_list = QListWidget()
        layout.addWidget(QLabel("Projects:"))
        layout.addWidget(self.project_list)
        
        # Project actions
        actions = QGroupBox("Project Actions")
        actions_layout = QGridLayout()
        
        # Create action buttons
        self.add_btn = QPushButton("Add Project")
        self.remove_btn = QPushButton("Remove")
        self.open_btn = QPushButton("Open")
        self.config_btn = QPushButton("Configure")
        
        # Add buttons to grid
        actions_layout.addWidget(self.add_btn, 0, 0)
        actions_layout.addWidget(self.remove_btn, 0, 1)
        actions_layout.addWidget(self.open_btn, 1, 0)
        actions_layout.addWidget(self.config_btn, 1, 1)
        
        actions.setLayout(actions_layout)
        layout.addWidget(actions)
        
        return widget

    def _setup_right_panel(self):
        """Setup project overview and metrics panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Portfolio metrics
        metrics_group = QGroupBox("Portfolio Overview")
        metrics_layout = QGridLayout()
        
        self.total_projects = QLabel("Total Projects: 0")
        self.active_projects = QLabel("Active Projects: 0")
        self.resource_usage = QLabel("Resource Usage: 0%")
        
        metrics_layout.addWidget(self.total_projects, 0, 0)
        metrics_layout.addWidget(self.active_projects, 0, 1)
        metrics_layout.addWidget(self.resource_usage, 1, 0)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Project dashboard area
        self.dashboard_container = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_container)
        layout.addWidget(self.dashboard_container)
        
        return widget

    def setup_connections(self):
        """Setup signal/slot connections"""
        self.vault_selector.currentTextChanged.connect(self.on_vault_changed)
        self.project_list.itemSelectionChanged.connect(self.on_project_selected)
        
        self.refresh_btn.clicked.connect(self.refresh_all)
        self.add_btn.clicked.connect(self.add_project)
        self.remove_btn.clicked.connect(self.remove_project)
        self.open_btn.clicked.connect(self.open_selected_project)
        self.config_btn.clicked.connect(self.configure_selected_project)

    def refresh_all(self):
        """Refresh all data"""
        self.refresh_vaults()
        self.refresh_projects()
        self.update_metrics()
        if self.dashboard:
            self.dashboard.refresh_dashboard()

    def refresh_vaults(self):
        """Refresh vault list"""
        try:
            current = self.vault_selector.currentText()
            self.vault_selector.clear()
            
            vaults = self.cccore.vault_manager.get_vault_names()
            self.vault_selector.addItems(vaults)
            
            # Restore previous selection if available
            index = self.vault_selector.findText(current)
            if index >= 0:
                self.vault_selector.setCurrentIndex(index)
                
        except Exception as e:
            logging.error(f"Error refreshing vaults: {e}")

    def refresh_projects(self):
        """Refresh project list for current vault"""
        try:
            self.project_list.clear()
            if self.current_vault:
                projects = self.cccore.vault_manager.get_projects(self.current_vault)
                self.project_list.addItems(projects)
                self.update_metrics()
        except Exception as e:
            logging.error(f"Error refreshing projects: {e}")

    def update_metrics(self):
        """Update portfolio metrics"""
        try:
            if not self.current_vault:
                return
                
            projects = self.cccore.vault_manager.get_projects(self.current_vault)
            total = len(projects)
            active = sum(1 for p in projects if self.project_manager.is_project_active(p))
            
            self.total_projects.setText(f"Total Projects: {total}")
            self.active_projects.setText(f"Active Projects: {active}")
            self.resource_usage.setText(
                f"Resource Usage: {active/total*100:.1f}%" if total else "Resource Usage: 0%"
            )
            
        except Exception as e:
            logging.error(f"Error updating metrics: {e}") 