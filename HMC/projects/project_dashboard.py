from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                            QTextEdit, QPushButton, QLabel, QScrollArea,
                            QSplitter, QFrame, QTableWidget, QTableWidgetItem, QTreeWidget)
from PyQt6.QtCore import Qt
from GUX.markdown_viewer import MarkdownViewer
from GUX.widgets.task_checklist_manager import TaskChecklistManager
import os
from datetime import datetime
from typing import Dict, List
from GUX.widgets.file_outline_widget import FileOutlineWidget
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPen, QPainterPath
from HMC.symbol_manager import CodeSymbol, SymbolManager
from pathlib import Path
from typing import Dict, List
from GUX.dialogs.project_dialogs import ProjectConfig

class ProjectDashboard(QWidget):
    def __init__(self, cccore, project_config: ProjectConfig):
        super().__init__()
        self.cccore = cccore
        self.project_config = project_config
        self.setup_ui()
        
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
        
        # Main Content Area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Project Overview and Tasks
        left_tabs = QTabWidget()
        
        # Overview Tab
        self.overview_widget = QWidget()
        overview_layout = QVBoxLayout(self.overview_widget)
        
        # Project Stats
        stats_layout = QHBoxLayout()
        self.file_count_label = QLabel("Files: 0")
        self.task_count_label = QLabel("Tasks: 0")
        self.note_count_label = QLabel("Notes: 0")
        stats_layout.addWidget(self.file_count_label)
        stats_layout.addWidget(self.task_count_label)
        stats_layout.addWidget(self.note_count_label)
        overview_layout.addLayout(stats_layout)
        
        # Recent Activity
        self.recent_activity = QTextEdit()
        self.recent_activity.setReadOnly(True)
        overview_layout.addWidget(QLabel("Recent Activity:"))
        overview_layout.addWidget(self.recent_activity)
        
        left_tabs.addTab(self.overview_widget, "Overview")
        
        # Tasks Tab with TaskChecklistManager
        self.task_manager = TaskChecklistManager(self.cccore.project_manager)
        left_tabs.addTab(self.task_manager, "Tasks")
        
        # Add Project Outline tab
        self.project_outline = ProjectOutlineTab()
        left_tabs.addTab(self.project_outline, "Project Outline")
        
        splitter.addWidget(left_tabs)
        
        # Right side: Notes with Markdown support
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        left_layout = QHBoxLayout()
        layout.addLayout(left_layout)

        # Notes Header
        notes_header = QHBoxLayout()
        notes_header.addWidget(QLabel("Project Notes"))
        self.new_note_btn = QPushButton("New Note")
        self.new_note_btn.clicked.connect(self.create_new_note)
        notes_header.addWidget(self.new_note_btn)
        right_layout.addLayout(notes_header)
        
        # Notes area using MarkdownViewer
        self.notes_viewer = MarkdownViewer(None)  # We'll set the vault path later
        right_layout.addWidget(self.notes_viewer)
        
        splitter.addWidget(right_widget)
        
        # Set initial splitter sizes (50-50 split)
        splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])
        
        layout.addWidget(splitter)
        
        # Set minimum size for the dashboard
        self.setMinimumSize(1000, 600)
        
        # Add Risks Section
        risks_header = QHBoxLayout()
        risks_label = QLabel("Project Risks")
        risks_label.setStyleSheet("font-weight: bold;")
        self.add_risk_btn = QPushButton("Add Risk")
        self.add_risk_btn.clicked.connect(self.add_project_risk)
        risks_header.addWidget(risks_label)
        risks_header.addWidget(self.add_risk_btn)
        left_layout.addLayout(risks_header)
        
        # Risk table
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(4)
        self.risk_table.setHorizontalHeaderLabels(["Priority", "Description", "Status", "Owner"])
        left_layout.addWidget(self.risk_table)
        
        # Add system overview tab
        self.add_system_tab()
        
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
        
    def update_project_info(self):
        """Update dashboard with current project info"""
        self.project_title.setText(self.project_config.name)
        
        # Update metrics
        coverage = self.project_config.get_setting('tracking', 'metrics', 'test_coverage_target')
        complexity = self.project_config.get_setting('tracking', 'metrics', 'max_complexity')
        
        self.metrics_table.setItem(0, 1, QTableWidgetItem(str(coverage)))
        self.metrics_table.setItem(1, 1, QTableWidgetItem(str(complexity)))
        
        # Update symbols outline
        symbols = self.project_config.get_setting('tracking', 'symbols', default={})
        self.outline_tree.populate_project_outline(symbols)
        
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
    
    def update_recent_activity(self):
        """Update the recent activity feed"""
        project = self.cccore.project_manager.get_current_project()
        if not project:
            return
            
        activity = []
        
        # Add recent file changes
        for file_path in self.cccore.editor_manager.get_open_files():
            modified_time = os.path.getmtime(file_path)
            activity.append({
                'type': 'file',
                'path': file_path,
                'time': modified_time,
                'text': f"Modified: {os.path.basename(file_path)}"
            })
        
        # Add recent tasks
        for task in self.task_manager.get_recent_tasks():
            activity.append({
                'type': 'task',
                'time': task.updated_at.timestamp(),
                'text': f"Task: {task.text}"
            })
        
        # Sort by time and display
        activity.sort(key=lambda x: x['time'], reverse=True)
        self.recent_activity.setText("\n".join(item['text'] for item in activity[:10]))
        
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
    