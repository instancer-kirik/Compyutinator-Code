from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
                           QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                           QGroupBox, QGridLayout, QTextEdit, QTreeWidget, QComboBox)
from PyQt6.QtCore import Qt
from GUX.widgets.task_checklist_manager import TaskChecklistManager
from GUX.markdown_viewer import MarkdownViewer
from HMC.risk_manager import RiskPriority, RiskStatus
from pathlib import Path
import logging
import traceback
from datetime import datetime
from .technical_analyzer import TechnicalAnalyzer
from GUX.widgets.stat_tracker import StatTrackerPanel
from HMC.risk_manager import RiskManager
from .system_analyzer import SystemInfo
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QListWidget
from GUX.widgets.project_dashboard import ProjectDashboard
from GUX.widgets.mark_board import MarkBoard
from typing import List, Dict

class Dashboard(QWidget):
    """High-level project overview dashboard"""
    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.project_name = None
        self.stat_tracker = StatTrackerPanel()
        self.technical_analyzer = TechnicalAnalyzer(cccore)
        self.activity_timer = QTimer()
        self.activity_timer.timeout.connect(self.refresh_activity)
        self.activity_timer.start(60000)  # Refresh every minute
        self.setup_ui()

    def setup_ui(self):
        """Setup the main dashboard UI"""
        try:
            layout = QVBoxLayout(self)
            
            # Header with project title and actions
            header = self._setup_header()
            layout.addLayout(header)
            
            # Project selector
            selector_layout = QHBoxLayout()
            self.project_selector = QComboBox()
            self.project_selector.currentTextChanged.connect(self.on_project_changed)
            selector_layout.addWidget(QLabel("Current Project:"))
            selector_layout.addWidget(self.project_selector)
            layout.addLayout(selector_layout)
            
            # Main content tabs
            self.tab_widget = QTabWidget()
            
            # Overview Tab
            self.tab_widget.addTab(self._setup_overview_tab(), "Overview")
            
            # Project Details Tab
            self.project_dashboard = ProjectDashboard(self.cccore, None)  # Initialize with no project
            self.tab_widget.addTab(self.project_dashboard, "Project Details")
            
            # Risk Overview Tab
            self.risk_overview = self._setup_risk_overview()
            self.tab_widget.addTab(self.risk_overview, "Risks")
            
            # Stats Tab
            self.tab_widget.addTab(self._setup_stats_tab(), "Statistics")
            
            # Activity & Events Tab
            self.activity_tab = self._setup_activity_tab()
            self.tab_widget.addTab(self.activity_tab, "Activity & Events")
            
            # Add Marks Tab
            self.mark_board = MarkBoard(self.cccore.mark_manager)
            self.tab_widget.addTab(self.mark_board, "Marks")
            
            layout.addWidget(self.tab_widget)
            
            # Initialize project list
            self.refresh_project_list()
            
        except Exception as e:
            logging.error(f"Error setting up dashboard UI: {e}")
            raise

    def _setup_header(self) -> QHBoxLayout:
        """Setup dashboard header"""
        header = QHBoxLayout()
        
        # Project title
        self.project_title = QLabel("Project Dashboard")
        self.project_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(self.project_title)
        
        # Action buttons
        actions = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_dashboard)
        actions.addWidget(refresh_btn)
        
        header.addLayout(actions)
        return header

    def _setup_overview_tab(self) -> QWidget:
        """Setup main overview tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Technical Analysis Section
        tech_group = QGroupBox("Technical Overview")
        tech_layout = QGridLayout()
        
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Value"])
        tech_layout.addWidget(self.metrics_table, 0, 0)
        
        tech_group.setLayout(tech_layout)
        layout.addWidget(tech_group)
        
        # System Info Section
        system_group = QGroupBox("System Information")
        system_layout = QVBoxLayout()
        self.system_tree = QTreeWidget()
        self.system_tree.setHeaderLabels(["Component", "Value", "Status"])
        system_layout.addWidget(self.system_tree)
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        return tab

    def _setup_stats_tab(self) -> QWidget:
        """Setup statistics tracking tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.stat_tracker.add_tracker("Files Modified", "#00ff00")
        self.stat_tracker.add_tracker("Tasks Completed", "#ff00ff")
        self.stat_tracker.add_tracker("Risks Mitigated", "#ffff00")
        self.stat_tracker.add_tracker("Build Success Rate", "#00ffff")
        
        layout.addWidget(self.stat_tracker)
        return tab

    def _setup_risk_overview(self) -> QWidget:
        """Setup risk overview section"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Risk summary table
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(4)
        self.risk_table.setHorizontalHeaderLabels(["Priority", "Description", "Status", "Owner"])
        layout.addWidget(self.risk_table)
        
        # View full risk manager button
        view_risks_btn = QPushButton("Open Risk Manager")
        view_risks_btn.clicked.connect(self.show_risk_manager)
        layout.addWidget(view_risks_btn)
        
        tab.setLayout(layout)
        return tab

    def _setup_activity_tab(self) -> QWidget:
        """Setup activity and events tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Recent Activity
        activity_widget = QWidget()
        activity_layout = QVBoxLayout(activity_widget)
        
        activity_header = QHBoxLayout()
        activity_header.addWidget(QLabel("Recent Activity"))
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_activity)
        activity_header.addWidget(refresh_btn)
        activity_layout.addLayout(activity_header)
        
        self.activity_list = QListWidget()
        activity_layout.addWidget(self.activity_list)
        
        # Right side: Project Events & News
        events_widget = QWidget()
        events_layout = QVBoxLayout(events_widget)
        
        # Upcoming Events
        events_group = QGroupBox("Upcoming Events")
        events_group_layout = QVBoxLayout()
        self.events_list = QListWidget()
        events_group_layout.addWidget(self.events_list)
        events_group.setLayout(events_group_layout)
        events_layout.addWidget(events_group)
        
        # Project News
        news_group = QGroupBox("Project News")
        news_group_layout = QVBoxLayout()
        self.news_list = QListWidget()
        news_group_layout.addWidget(self.news_list)
        news_group.setLayout(news_group_layout)
        events_layout.addWidget(news_group)
        
        splitter.addWidget(activity_widget)
        splitter.addWidget(events_widget)
        layout.addWidget(splitter)
        
        return tab

    def refresh_project_list(self):
        """Refresh the list of available projects"""
        try:
            current = self.project_selector.currentText()
            self.project_selector.clear()
            
            projects = self.cccore.project_manager.get_projects()
            for project in projects:
                self.project_selector.addItem(project.name)
                
            # Restore previous selection if still available
            index = self.project_selector.findText(current)
            if index >= 0:
                self.project_selector.setCurrentIndex(index)
                
        except Exception as e:
            logging.error(f"Error refreshing project list: {e}")

    def on_project_changed(self, project_name: str):
        """Handle project selection change"""
        try:
            if project_name:
                self.set_project(project_name)
        except Exception as e:
            logging.error(f"Error handling project change: {e}")

    def set_project(self, project_name: str):
        """Set the current project"""
        try:
            self.project_name = project_name
            project = self.cccore.project_manager.get_project(project_name)
            
            if not project:
                logging.error(f"Project not found: {project_name}")
                return
            
            # Update UI elements
            self.project_title.setText(f"Project Dashboard - {project_name}")
            
            # Update project dashboard
            if hasattr(self, 'project_dashboard'):
                self.project_dashboard.set_project(project)
            
            # Update mark board
            if hasattr(self, 'mark_board'):
                self.mark_board.set_project(project_name)
            
            # Refresh all dashboard data
            self.refresh_dashboard()
            
        except Exception as e:
            logging.error(f"Error setting project: @dashboard {e}")

    def refresh_dashboard(self):
        """Refresh all dashboard data"""
        try:
            if not self.project_name:
                return
            
            project = self.cccore.project_manager.get_project(self.project_name)
            if not project:
                return
            
            # Update technical metrics
            metrics = self.technical_analyzer.analyze_project(project)
            self.update_metrics_table(metrics)
            
            # Update system info
            system_info = SystemInfo.get_system_info()
            self.update_system_tree(system_info)
            
            # Update activity log
            activities = project.get_recent_activity()
            if hasattr(self, 'activity_list'):
                self.update_activity_log(activities)
            
            # Update risk overview
            if hasattr(self, 'risk_table'):
                self.update_risk_overview()
            
            # Update statistics
            if hasattr(self, 'stat_tracker'):
                self.update_stats(project)
            
        except Exception as e:
            logging.error(f"Error refreshing dashboard: {e}")

    def show_risk_manager(self):
        """Open the full risk manager"""
        self.cccore.widget_manager.show_widget('Risk Manager')

    def refresh_activity(self):
        """Refresh activity log"""
        if not self.project_name:
            return
        
        try:
            project = self.cccore.project_manager.get_project(self.project_name)
            if not project:
                return
            
            # Get recent activity from project
            activities = project.get_recent_activity()
            self.update_activity_log(activities)
            
        except Exception as e:
            logging.error(f"Error refreshing activity: {e}")

    def update_activity_log(self, activities: List[dict]):
        """Update activity log with new entries"""
        try:
            self.activity_list.clear()
            
            for activity in activities:
                timestamp = activity.get('timestamp', datetime.now())
                action = activity.get('action', '')
                details = activity.get('details', '')
                
                # Format the activity entry
                entry = f"{timestamp.strftime('%Y-%m-%d %H:%M')} - {action}"
                if details:
                    entry += f": {details}"
                    
                self.activity_list.addItem(entry)
                
        except Exception as e:
            logging.error(f"Error updating activity log: {e}")

    def update_risk_overview(self):
        """Update risk overview table"""
        try:
            risks = self.cccore.risk_manager.get_risks_for_project(self.project_name)
            
            self.risk_table.setRowCount(len(risks))
            for i, risk in enumerate(risks):
                self.risk_table.setItem(i, 0, QTableWidgetItem(str(risk.priority)))
                self.risk_table.setItem(i, 1, QTableWidgetItem(risk.description))
                self.risk_table.setItem(i, 2, QTableWidgetItem(risk.status))
                self.risk_table.setItem(i, 3, QTableWidgetItem(risk.owner))
                
        except Exception as e:
            logging.error(f"Error updating risk overview: {e}")

    def update_stats(self, project):
        """Update project statistics"""
        try:
            # Update stat trackers with project metrics
            self.stat_tracker.update_tracker(
                "Files Modified", 
                project.get_modified_files_count()
            )
            self.stat_tracker.update_tracker(
                "Tasks Completed", 
                project.get_completed_tasks_count()
            )
            self.stat_tracker.update_tracker(
                "Risks Mitigated", 
                project.get_mitigated_risks_count()
            )
            self.stat_tracker.update_tracker(
                "Build Success Rate", 
                project.get_build_success_rate()
            )
            
        except Exception as e:
            logging.error(f"Error updating statistics: {e}")