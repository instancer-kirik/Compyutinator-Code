from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                            QTextEdit, QPushButton, QLabel, QScrollArea,
                            QSplitter, QFrame, QTableWidget, QTableWidgetItem, QTreeWidget, QListWidget)
from PyQt6.QtCore import Qt
from GUX.markdown_viewer import MarkdownViewer
from GUX.widgets.task_checklist_manager import TaskChecklistManager
import os
from datetime import datetime
from typing import Dict, List, Any
from GUX.widgets.file_outline_widget import FileOutlineWidget
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPen, QPainterPath
from HMC.symbol_manager import CodeSymbol, SymbolManager
from pathlib import Path
from typing import Dict, List
from GUX.dialogs.project_dialogs import ProjectConfig
from GUX.widgets.project_src_widget import ProjectSourceWidget
import logging

from typing import Optional
from HMC.projects.project import Project  # Updated import
from HMC.projects.project_config import ProjectConfig
from riskkit.enums import ProjectType
    
class ProjectDashboard(QWidget):
    def __init__(self, cccore, project_name: str):
        super().__init__()
        self.cccore = cccore
        self.project_name = project_name
        self.project: Optional[Project] = None
        self.load_project()
        self.setup_ui()
        
    def load_project(self):
        """Load project configuration"""
        try:
            if not self.project_name:
                logging.warning("No project name provided")
                return
            
            project = self.cccore.vault_manager.get_project(self.project_name)
            if not project:
                logging.warning(f"No project found with name: {self.project_name}")
                return
            
            self.project = project
            self.project_title.setText(self.project.name)
            
        except Exception as e:
            logging.error(f"Error loading project: {e}")
            
    def update_metrics_table(self):
        """Update metrics table with current project data"""
        try:
            if not self.project_config:
                return
                
            metrics = self.project_config.get_setting('tracking', 'metrics', {})
            self.metrics_table.setRowCount(len(metrics))
            
            for i, (key, value) in enumerate(metrics.items()):
                self.metrics_table.setItem(i, 0, QTableWidgetItem(key))
                self.metrics_table.setItem(i, 1, QTableWidgetItem(str(value)))
                
        except Exception as e:
            logging.error(f"Error updating metrics table: {e}")
            
    def get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent project activity"""
        try:
            if not self.project_config:
                return []
                
            # Get activity from project tracking
            activity = self.project_config.get_setting('tracking', 'activity', [])
            return sorted(activity, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]
            
        except Exception as e:
            logging.error(f"Error getting recent activity: {e}")
            return []
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.setWindowTitle("Dashboard")
        
        # Project Header
        header_layout = QHBoxLayout()
        self.project_title = QLabel("No Project Selected")
        self.project_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.project_title)
        
        # Project Actions
        actions_layout = QHBoxLayout()
        self.add_note_btn = QPushButton("Add Note")
        self.add_note_btn.clicked.connect(self.create_new_note)
        self.add_task_btn = QPushButton("Add Task")
        self.add_task_btn.clicked.connect(self.add_project_task)
        actions_layout.addWidget(self.add_note_btn)
        actions_layout.addWidget(self.add_task_btn)
        
        header_layout.addLayout(actions_layout)
        layout.addLayout(header_layout)
        
        # Initialize tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Add all tabs
        self.add_overview_tab()
        self.add_system_tab()
        self.add_tasks_tab()
        self.add_notes_tab()
        self.add_risks_tab()
        self.add_outline_tab()
        self.add_activity_tab()
        
        # Project Stats
        stats_layout = QHBoxLayout()
        self.file_count_label = QLabel("Files: 0")
        self.task_count_label = QLabel("Tasks: 0")
        self.note_count_label = QLabel("Notes: 0")
        stats_layout.addWidget(self.file_count_label)
        stats_layout.addWidget(self.task_count_label)
        stats_layout.addWidget(self.note_count_label)
        layout.addLayout(stats_layout)
        
        # Recent Activity
        self.recent_activity = QTextEdit()
        self.recent_activity.setReadOnly(True)
        layout.addWidget(QLabel("Recent Activity:"))
        layout.addWidget(self.recent_activity)
        
    def add_overview_tab(self):
        """Add overview dashboard tab"""
        overview_tab = QWidget()
        layout = QVBoxLayout(overview_tab)
        
        # Project metrics
        self.metrics_table = QTableWidget(3, 2)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.metrics_table.setItem(0, 0, QTableWidgetItem("Test Coverage"))
        self.metrics_table.setItem(1, 0, QTableWidgetItem("Code Complexity"))
        self.metrics_table.setItem(2, 0, QTableWidgetItem("Build Status"))
        layout.addWidget(self.metrics_table)
        
        self.tab_widget.addTab(overview_tab, "Overview")

    def add_system_tab(self):
        """Add system monitoring tab"""
        system_tab = QWidget()
        layout = QVBoxLayout(system_tab)
        
        # Add system info tree
        self.system_tree = QTreeWidget()
        self.system_tree.setHeaderLabels(["Component", "Value", "Status"])
        layout.addWidget(self.system_tree)
        
        # Add refresh button
        refresh_btn = QPushButton("Refresh System Info")
        refresh_btn.clicked.connect(self.update_system_info)
        layout.addWidget(refresh_btn)
        
        self.tab_widget.addTab(system_tab, "System")
        
    def add_tasks_tab(self):
        """Add tasks management tab"""
        tasks_tab = QWidget()
        layout = QVBoxLayout(tasks_tab)
        
        # Initialize task manager with proper dependencies
        self.task_manager = TaskChecklistManager(
            project_manager=self.cccore.project_manager,
            risk_manager=self.cccore.risk_manager
        )
        layout.addWidget(self.task_manager)
        
        self.tab_widget.addTab(tasks_tab, "Tasks")

    def add_notes_tab(self):
        """Add notes management tab"""
        notes_tab = QWidget()
        layout = QVBoxLayout(notes_tab)
        
        # Notes viewer
        self.notes_viewer = MarkdownViewer(vault_path=self.cccore.vault_manager.current_vault.path)
        layout.addWidget(self.notes_viewer)
        
        # Notes controls
        controls = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_most_recent_note)
        controls.addWidget(refresh_btn)
        layout.addLayout(controls)
        
        self.tab_widget.addTab(notes_tab, "Notes")

    def add_risks_tab(self):
        """Add risk management tab"""
        risks_tab = QWidget()
        layout = QVBoxLayout(risks_tab)
        
        # Risk table
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(4)
        self.risk_table.setHorizontalHeaderLabels(["Priority", "Description", "Status", "Owner"])
        layout.addWidget(self.risk_table)
        
        # Risk controls
        controls = QHBoxLayout()
        add_risk_btn = QPushButton("Add Risk")
        add_risk_btn.clicked.connect(self.add_project_risk)
        controls.addWidget(add_risk_btn)
        layout.addLayout(controls)
        
        self.tab_widget.addTab(risks_tab, "Risks")

    def add_outline_tab(self):
        """Add project outline tab"""
        self.outline_tab = ProjectOutlineTab()
        self.tab_widget.addTab(self.outline_tab, "Project Outline")

    def add_activity_tab(self):
        """Add activity tracking tab"""
        activity_tab = QWidget()
        layout = QVBoxLayout(activity_tab)
        
        self.activity_list = QListWidget()
        layout.addWidget(self.activity_list)
        
        # Activity controls
        controls = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_recent_activity)
        controls.addWidget(refresh_btn)
        layout.addLayout(controls)
        
        self.tab_widget.addTab(activity_tab, "Activity")
        
    def update_project_info(self):
        """Update project information display"""
        try:
            if not self.project:
                return
                
            # Update metrics
            self.update_metrics_table()
            
            # Update activity
            activity = self.get_recent_activity()
            self.update_activity_list(activity)
            
            # Update technical metrics
            self.update_technical_metrics()
            
        except Exception as e:
            logging.error(f"Error updating project info: {e}")
    
    def create_new_note(self):
        """Create a new markdown note"""
        project = self.cccore.project_manager.get_current_project()
        if not project:
            return
            
        project_path = self.cccore.project_manager.get_project_path(project)
        notes_path = os.path.join(project_path, "notes")
        
        # Create a new note file with template
        note_name = f"note_{len(os.listdir(notes_path))}.md"
        note_path = os.path.join(notes_path, note_name)
        
        template = f"""# Project Note

## {project} - {datetime.now().strftime('%Y-%m-%d')}

### Summary


### Details


### Action Items
- [ ] 

### Related
- Tasks: 
- Files: 
"""
        
        with open(note_path, 'w') as f:
            f.write(template)
        
        # Open the note in the editor
        self.cccore.editor_manager.open_file(note_path)
        
    def add_project_task(self):
        """Add a new task through the task manager"""
        self.task_manager.add_task()
        
    def load_most_recent_note(self):
        """Load the most recent note into the viewer"""
        project = self.cccore.project_manager.get_current_project()
        if not project:
            return
            
        project_path = self.cccore.project_manager.get_project_path(project)
        notes_path = os.path.join(project_path, "notes")
        
        if not os.path.exists(notes_path):
            return
            
        notes = sorted(
            [f for f in os.listdir(notes_path) if f.endswith('.md')],
            key=lambda x: os.path.getmtime(os.path.join(notes_path, x)),
            reverse=True
        )
        
        if notes:
            latest_note = os.path.join(notes_path, notes[0])
            self.notes_viewer.load_markdown(latest_note)
    
    def update_dashboard(self, project_data):
        """Update dashboard with project information"""
        try:
            from HMC.project_manager import Project
            
            if isinstance(project_data, dict):
                self.project = Project(
                    name=project_data['name'],
                    path=project_data['path'],
                    project_type=project_data.get('type', 'local'),
                    created_at=project_data.get('created_at'),
                    updated_at=project_data.get('updated_at')
                )
            elif isinstance(project_data, Project):
                self.project = project_data
            else:
                logging.error(f"Invalid project data type: {type(project_data)}")
                return
            
            # Update all sections
            self.update_system_info()
            self.update_risk_section()
            self.update_task_section()
            self.update_recent_activity()
            
        except Exception as e:
            logging.error(f"Error refreshing dashboard: {e}")
            logging.debug(f"Project data: {project_data}")

    def update_recent_activity(self):
        """Update recent activity list"""
        try:
            if not hasattr(self, 'project') or not self.project:
                logging.warning("No project set for activity update")
                return
            
            activity = []
            
            # Add modified files
            if hasattr(self.cccore, 'file_manager'):
                recent_files = self.cccore.file_manager.get_recent_files(self.project.path)
                for file_path in recent_files:
                    activity.append({
                        'type': 'file',
                        'time': os.path.getmtime(file_path),
                        'text': f"Modified: {os.path.basename(file_path)}"
                    })
            
            # Add recent tasks
            if hasattr(self, 'task_manager'):
                for task in self.task_manager.get_recent_tasks():
                    activity.append({
                        'type': 'task',
                        'time': task.updated_at.timestamp() if hasattr(task, 'updated_at') else 0,
                        'text': f"Task: {task.text if hasattr(task, 'text') else str(task)}"
                    })
            
            # Sort and display
            activity.sort(key=lambda x: x['time'], reverse=True)
            if hasattr(self, 'activity_list'):
                self.activity_list.clear()
                for item in activity[:10]:
                    self.activity_list.addItem(item['text'])
                    
        except Exception as e:
            logging.error(f"Error refreshing activity: {e}")
            logging.debug(f"Project: {getattr(self, 'project', None)}")
        
    def update_risk_section(self):
        """Update the risk table with current project risks"""
        if not self.cccore.risk_manager:
            return
            
        project = self.cccore.project_manager.get_current_project()
        if not project:
            return
            
        risks = self.cccore.risk_manager.get_project_risks(project.id)
        self.risk_table.setRowCount(len(risks))
        
        for i, risk in enumerate(risks):
            self.risk_table.setItem(i, 0, QTableWidgetItem(risk.priority))
            self.risk_table.setItem(i, 1, QTableWidgetItem(risk.description))
            self.risk_table.setItem(i, 2, QTableWidgetItem(risk.status))
            self.risk_table.setItem(i, 3, QTableWidgetItem(risk.owner or ""))
    
    def on_symbol_selected(self, symbol: CodeSymbol, file_path: Path):
        """Handle symbol selection"""
        # You could implement navigation to the symbol in an editor
        # or show symbol details in a separate panel
        pass
    
    def add_project_risk(self):
        """Add a new risk to the project"""
        try:
            if not self.cccore.risk_manager:
                logging.warning("Risk manager not available")
                return
            
            project = self.cccore.project_manager.get_current_project()
            if not project:
                logging.warning("No project selected")
                return
            
            # Show risk creation dialog
            self.cccore.widget_manager.show_risk_dialog(project.id)
            
            # Update risk table after adding
            self.update_risk_section()
            
        except Exception as e:
            logging.error(f"Error adding project risk: {e}")
    
    def update_system_info(self):
        """Update system information display"""
        try:
            if not self.project_config:
                logging.warning("No project configuration available")
                return
            
            # Get system info from project config
            system_info = self.project_config.system_info
            
            # Update system info display
            if hasattr(self, 'system_info_view'):
                markdown_content = system_info.to_markdown()
                self.system_info_view.set_markdown(markdown_content)
            
            # Update technical metrics
            if self.cccore and hasattr(self, 'technical_metrics'):
                metrics = self.cccore.technical_analyzer.analyze_project(self.project_config.name)
                self.update_technical_metrics(metrics)
            
        except Exception as e:
            logging.error(f"Error updating system info: {e}")

    def update_technical_metrics(self, metrics: Dict[str, Any]):
        """Update technical metrics display"""
        try:
            if hasattr(self, 'technical_metrics'):
                # Format metrics for display
                formatted_metrics = [
                    f"**Dependencies:** {len(metrics.get('dependencies', []))}",
                    f"**Entry Points:** {len(metrics.get('entry_points', []))}",
                    f"**Structure:**\n" + "\n".join(
                        f"- {k}: {len(v.get('symbols', []))} symbols"
                        for k, v in metrics.get('structure', {}).items()
                    )
                ]
                
                self.technical_metrics.setText("\n".join(formatted_metrics))
            
        except Exception as e:
            logging.error(f"Error updating technical metrics: {e}")
    
class ProjectOutlineTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        
        # Left side: Tree view of files and symbols
        self.outline_tree = FileOutlineWidget()
        
        # Right side: Reference visualization
        self.ref_view = QGraphicsView()
        self.ref_scene = QGraphicsScene()
        self.ref_view.setScene(self.ref_scene)
        
        # Add zoom controls
        zoom_layout = QHBoxLayout()
        self.zoom_in_btn = QPushButton("+")
        self.zoom_out_btn = QPushButton("-")
        self.zoom_in_btn.clicked.connect(lambda: self.ref_view.scale(1.2, 1.2))
        self.zoom_out_btn.clicked.connect(lambda: self.ref_view.scale(0.8, 0.8))
        zoom_layout.addWidget(self.zoom_in_btn)
        zoom_layout.addWidget(self.zoom_out_btn)
        
        right_layout = QVBoxLayout()
        right_layout.addLayout(zoom_layout)
        right_layout.addWidget(self.ref_view)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.outline_tree)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        layout.addWidget(splitter)
        
    def update_outline(self, project_name: str, symbol_manager: SymbolManager):
        """Update both the tree and reference visualization"""
        # Get symbols from symbol manager
        vault_symbols = symbol_manager.vault_symbols.get(project_name, {})
        
        # Update tree view
        self.outline_tree.populate_project_outline(vault_symbols)
        
        # Update reference visualization
        self.update_references(vault_symbols)
        
    def update_references(self, symbols_map: Dict[Path, List[CodeSymbol]]):
        """Update the reference visualization"""
        self.ref_scene.clear()
        
        # Create nodes for each symbol
        nodes = {}
        y_pos = 0
        x_pos = 0
        last_file = None
        
        for file_path, symbols in symbols_map.items():
            if file_path != last_file:
                y_pos = 0
                x_pos += 200
                last_file = file_path
                
            for symbol in symbols:
                node = self.ref_scene.addEllipse(x_pos, y_pos, 10, 10)
                node.setToolTip(f"{symbol.name} ({symbol.type})\n{file_path.name}")
                nodes[f"{file_path}:{symbol.name}"] = node
                y_pos += 30
        
        # Draw connections based on parent-child relationships
        for file_path, symbols in symbols_map.items():
            for symbol in symbols:
                if symbol.parent:
                    parent_key = f"{file_path}:{symbol.parent.name}"
                    symbol_key = f"{file_path}:{symbol.name}"
                    
                    if parent_key in nodes and symbol_key in nodes:
                        start = nodes[parent_key].sceneBoundingRect().center()
                        end = nodes[symbol_key].sceneBoundingRect().center()
                        
                        path = QPainterPath()
                        path.moveTo(start)
                        path.lineTo(end)
                        
                        self.ref_scene.addPath(path, QPen(Qt.GlobalColor.blue))
        
        # Fit the view to all items
        self.ref_view.fitInView(self.ref_scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    