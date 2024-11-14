from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeView, QLabel,
    QLineEdit, QMessageBox, QFileDialog, QTextBrowser, QMenu, QMenuBar,
    QDialog, QFormLayout, QDateTimeEdit, QComboBox, QSpinBox, QGroupBox,
    QDialogButtonBox, QTextEdit, QWidget, QGridLayout, QToolBar
)
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QKeySequence, QShortcut, QAction
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
import logging
from riskkit.enums import (
    RiskPriority, RiskStatus, RiskProbability,
    ImpactSeverity, ImpactArea, ImpactTimeframe
)
from riskkit.event_manager import EventManager, EventPriority
from riskkit.client import RiskkitClient
from riskkit.data_mux import DataMux
import json
import os

@dataclass
class TaskCheckItem:
    text: str
    completed: bool = False
    category: str = ""  # e.g., "Integration", "Development", "Security", etc.
    priority: RiskPriority = RiskPriority.MEDIUM
    risk_level: RiskProbability = RiskProbability.POSSIBLE
    impact: ImpactSeverity = ImpactSeverity.MEDIUM
    impact_area: ImpactArea = ImpactArea.FUNCTIONALITY
    timeframe: ImpactTimeframe = ImpactTimeframe.SHORT_TERM
    assigned_to: str = ""
    due_date: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    related_tasks: List[str] = field(default_factory=list)
    related_risks: List[int] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

from HMC.task_manager import TaskManagerBase

class TaskChecklistManager(TaskManagerBase):
    """A comprehensive task and checklist management system"""
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
    
    def __init__(self, project_manager=None, risk_manager=None):
        super().__init__()
        self.project_manager = project_manager
        self.risk_manager = risk_manager
        self.event_manager = EventManager()
        self.data_mux = DataMux()
        self.tree_model = QStandardItemModel()
        self.setup_ui()
        self.setup_auto_save()

    def setup_ui(self):
        """Setup the UI components"""
        self.setWindowTitle("Task Checklist Manager")
        self.setGeometry(100, 100, 1000, 800)
        
        # Create main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Initialize UI components in order
        self._init_toolbar()
        self.setup_filter_panel()
        self.setup_tree_view()
        self.setup_status_panel()
        
        # Setup additional functionality
        self.setup_keyboard_shortcuts()
        self.setup_drag_drop()
        self.setup_user_preferences()
        self.setup_task_templates()
        self.setup_auto_save()

    def _init_toolbar(self):
        """Initialize the toolbar with common actions"""
        toolbar = QToolBar()
        
        # Add task action
        add_action = QAction("Add Task", self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self.add_task)
        toolbar.addAction(add_action)
        
        # Save action
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_checklist)
        toolbar.addAction(save_action)
        
        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_view)
        toolbar.addAction(refresh_action)
        
        self.layout.addWidget(toolbar)

    def setup_auto_save(self):
        """Setup auto-save functionality"""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.save_checklist)
        interval = self.preferences.get('auto_save_interval', 300) * 1000  # Convert to milliseconds
        self.auto_save_timer.start(interval)

    def refresh_view(self):
        """Refresh the task view and update all UI elements"""
        try:
            if self.project_manager:
                current_project = self.project_manager.get_current_project()
                if current_project:
                    self.load_tasks(current_project)
                    self.update_status_panel()
                    self.apply_filters()
        except Exception as e:
            logging.error(f"Error refreshing view: {e}")

    def load_tasks(self, project):
        """Load tasks from project"""
        try:
            self.tree_model.clear()
            self.tree_model.setHorizontalHeaderLabels([
                "Task", "Category", "Status", "Priority", 
                "Risk Level", "Impact", "Area", "Due Date"
            ])
            
            tasks = project.get_tasks()
            for task in tasks:
                self.add_task_to_tree(task)
                
        except Exception as e:
            logging.error(f"Error loading tasks: {e}")

    def new_checklist(self):
        """Create a new empty checklist"""
        try:
            self.tree_model.clear()
            self.tree_model.setHorizontalHeaderLabels([
                "Task", "Category", "Status", "Priority",
                "Risk Level", "Impact", "Area", "Due Date"
            ])
            self.current_file = None
            self.unsaved_changes = False
            self.update_status_panel()
            return True
        except Exception as e:
            self.event_manager.broadcast_news(
                "Checklist Error",
                f"Failed to create new checklist: {e}",
                EventPriority.HIGH
            )
            return False

    def add_task(self, parent_index=None):
        """Add a new task to the checklist"""
        dialog = TaskDialog(self)
        if dialog.exec():
            task_data = dialog.get_task_data()
            success = self.add_task_to_tree(task_data, parent_index)
            if success:
                self.unsaved_changes = True
                self.update_status_panel()
            return success
        return False

    def setup_tree_view(self):
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels([
            "Task", "Category", "Status", "Priority", 
            "Risk Level", "Impact", "Area", "Due Date"
        ])
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSortingEnabled(True)
        self.layout.addWidget(self.tree_view)

    def setup_status_panel(self):
        status_group = QGroupBox("Task Overview")
        status_layout = QGridLayout()

        # Status indicators
        self.total_tasks = QLabel("Total Tasks: 0")
        self.completed_tasks = QLabel("Completed: 0")
        self.high_priority_tasks = QLabel("High Priority: 0")
        self.overdue_tasks = QLabel("Overdue: 0")
        self.risk_score = QLabel("Risk Score: 0.0")
        self.completion_rate = QLabel("Completion Rate: 0%")

        status_layout.addWidget(self.total_tasks, 0, 0)
        status_layout.addWidget(self.completed_tasks, 0, 1)
        status_layout.addWidget(self.high_priority_tasks, 1, 0)
        status_layout.addWidget(self.overdue_tasks, 1, 1)
        status_layout.addWidget(self.risk_score, 2, 0)
        status_layout.addWidget(self.completion_rate, 2, 1)

        status_group.setLayout(status_layout)
        self.layout.addWidget(status_group)

    def show_context_menu(self, position):
        """Show context menu with advanced task management options"""
        menu = QMenu()
        index = self.tree_view.indexAt(position)
        
        # Add Task Actions
        add_menu = menu.addMenu("Add")
        add_menu.addAction("New Task", self.add_task)
        add_menu.addAction("New Subtask", lambda: self.add_task(parent_index=index))
        add_menu.addAction("From Template", self.add_from_template)
        
        if index.isValid():
            # Task Management
            menu.addSeparator()
            menu.addAction("Edit Task", lambda: self.edit_task(index))
            menu.addAction("Duplicate Task", lambda: self.duplicate_task(index))
            menu.addAction("Move Task", lambda: self.move_task(index))
            
            # Status Management
            status_menu = menu.addMenu("Set Status")
            status_menu.addAction("Not Started", lambda: self.set_task_status(index, "Not Started"))
            status_menu.addAction("In Progress", lambda: self.set_task_status(index, "In Progress"))
            status_menu.addAction("Completed", lambda: self.set_task_status(index, "Completed"))
            status_menu.addAction("Blocked", lambda: self.set_task_status(index, "Blocked"))
            status_menu.addAction("Deferred", lambda: self.set_task_status(index, "Deferred"))
            
            # Priority Management
            priority_menu = menu.addMenu("Set Priority")
            for priority in RiskPriority:
                priority_menu.addAction(
                    priority.name, 
                    lambda p=priority: self.set_task_priority(index, p)
                )
            
            # Assignment Management
            assign_menu = menu.addMenu("Assign To")
            if self.project_manager and hasattr(self.project_manager, 'team_members'):
                for member in self.project_manager.team_members:
                    assign_menu.addAction(
                        member.name, 
                        lambda m=member: self.assign_task(index, m)
                    )
            assign_menu.addSeparator()
            assign_menu.addAction("Other...", lambda: self.assign_task(index))
            
            # Links and References
            link_menu = menu.addMenu("Link")
            link_menu.addAction("Link to Risk", lambda: self.link_to_risk(index))
            link_menu.addAction("Link to Issue", lambda: self.link_to_issue(index))
            link_menu.addAction("Link to Document", lambda: self.link_to_document(index))
            link_menu.addAction("Add Reference", lambda: self.add_reference(index))
            
            # Task Analysis
            menu.addSeparator()
            menu.addAction("Show Dependencies", lambda: self.show_dependencies(index))
            menu.addAction("Show Impact Analysis", lambda: self.show_impact_analysis(index))
            menu.addAction("View History", lambda: self.view_task_history(index))
            
            # Export Options
            export_menu = menu.addMenu("Export")
            export_menu.addAction("Export as Markdown", lambda: self.export_task(index, "markdown"))
            export_menu.addAction("Export as JSON", lambda: self.export_task(index, "json"))
            export_menu.addAction("Export as PDF", lambda: self.export_task(index, "pdf"))
            
            # Task Removal
            menu.addSeparator()
            menu.addAction("Remove Task", lambda: self.remove_task(index))

        # Global Actions
        menu.addSeparator()
        menu.addAction("Expand All", self.tree_view.expandAll)
        menu.addAction("Collapse All", self.tree_view.collapseAll)
        menu.addAction("Refresh View", self.refresh_view)

        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions"""
        shortcuts = [
            (QKeySequence("Ctrl+N"), self.add_task),
            (QKeySequence("Ctrl+E"), lambda: self.edit_task(self.tree_view.currentIndex())),
            (QKeySequence("Delete"), lambda: self.remove_task(self.tree_view.currentIndex())),
            (QKeySequence("Ctrl+D"), lambda: self.duplicate_task(self.tree_view.currentIndex())),
            (QKeySequence("Ctrl+Space"), lambda: self.toggle_task_completion(self.tree_view.currentIndex())),
            (QKeySequence("Ctrl+F"), lambda: self.search_box.setFocus()),
            (QKeySequence("Ctrl+R"), self.refresh_view),
            (QKeySequence("Ctrl+S"), self.save_checklist),
            (QKeySequence("F5"), self.refresh_view),
        ]
        
        for shortcut, callback in shortcuts:
            QShortcut(shortcut, self).activated.connect(callback)

    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.tree_view.setDefaultDropAction(Qt.DropAction.MoveAction)

    def setup_user_preferences(self):
        """Setup user preferences for the checklist manager"""
        self.preferences = {
            'auto_save_interval': 300,  # seconds
            'show_completed_tasks': True,
            'default_view': 'tree',  # or 'list'
            'sort_by': 'priority',
            'sort_order': 'descending',
            'expand_new_tasks': True,
            'confirm_deletions': True,
            'show_status_panel': True,
            'show_filter_panel': True,
            'enable_animations': True,
            'theme': 'system'  # or 'light'/'dark'
        }
        
        # Load saved preferences
        if self.project_manager and hasattr(self.project_manager, 'config'):
            saved_prefs = self.project_manager.config.get('checklist_preferences', {})
            self.preferences.update(saved_prefs)

    def apply_user_preferences(self):
        """Apply user preferences to the UI"""
        # View preferences
        if not self.preferences['show_status_panel']:
            self.status_panel.hide()
        if not self.preferences['show_filter_panel']:
            self.filter_panel.hide()
            
        # Sort preferences
        if self.preferences['sort_by']:
            column = self.get_column_index(self.preferences['sort_by'])
            order = Qt.SortOrder.DescendingOrder if self.preferences['sort_order'] == 'descending' else Qt.SortOrder.AscendingOrder
            self.tree_view.sortByColumn(column, order)
            
        # Theme preferences
        if self.preferences['theme'] != 'system':
            self.apply_theme(self.preferences['theme'])

    def setup_task_templates(self):
        """Setup task templates"""
        try:
            self.templates = {}
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
            
            if not os.path.exists(template_dir):
                os.makedirs(template_dir)
                
            # Default templates
            default_templates = {
                'integration_testing': 'templates/integration_testing.md',
                'security_audit': 'templates/security_audit.md',
                'documentation': 'templates/documentation.md',
                'release': 'templates/release.md',
                'code_review': 'templates/code_review.md'
            }
            
            for name, path in default_templates.items():
                template_path = os.path.join(template_dir, path)
                if os.path.exists(template_path):
                    with open(template_path, 'r') as f:
                        self.templates[name] = f.read()
                else:
                    logging.warning(f"Template not found: {name}")
                
        except Exception as e:
            logging.error(f"Error setting up task templates: {e}")

    def load_template(self, template_name: str) -> List[TaskCheckItem]:
        """Load a task template from file or resources"""
        template_paths = [
            os.path.join(self.TEMPLATE_DIR, f"{template_name}_template.md"),
            os.path.join(self.TEMPLATE_DIR, f"{template_name}.md")
        ]
        
        for template_path in template_paths:
            try:
                if hasattr(self.project_manager, 'get_template'):
                    return self.project_manager.get_template(template_name)
                elif os.path.exists(template_path):
                    with open(template_path, 'r', encoding='utf-8') as f:
                        return self.parse_template(f.read())
            except Exception as e:
                logging.warning(f"Failed to load template {template_path}: {e}")
        
        logging.error(f"No valid template found for {template_name}")
        return []

    def parse_template(self, template_content: str) -> List[TaskCheckItem]:
        """Parse markdown template into task items"""
        tasks = []
        current_section = None
        current_task = None
        
        for line in template_content.split('\n'):
            if line.startswith('##'):
                current_section = line.strip('# ')
            elif line.startswith('- [ ]'):
                task_text = line[5:].strip()
                metadata = {}
                current_task = TaskCheckItem(
                    text=task_text,
                    category=current_section or "",
                    metadata=metadata
                )
                tasks.append(current_task)
            elif line.startswith('  - Priority:'):
                if current_task:
                    current_task.priority = RiskPriority[line.split(':')[1].strip().upper()]
            elif line.startswith('  - Impact:'):
                if current_task:
                    current_task.impact = ImpactSeverity[line.split(':')[1].strip().upper()]
            elif line.startswith('  - Area:'):
                if current_task:
                    current_task.impact_area = ImpactArea[line.split(':')[1].strip().upper()]
        
        return tasks

    def save_template(self, template_name: str, tasks: List[TaskCheckItem]) -> bool:
        """Save tasks as a template"""
        try:
            template_path = os.path.join(self.TEMPLATE_DIR, f"{template_name}_template.md")
            content = self.generate_template_content(tasks)
            
            os.makedirs(self.TEMPLATE_DIR, exist_ok=True)
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.templates['Custom'].append(template_name)
            return True
        except Exception as e:
            logging.error(f"Failed to save template {template_name}: {e}")
            return False

    def generate_template_content(self, tasks: List[TaskCheckItem]) -> str:
        """Generate markdown content from tasks"""
        content = ["# Task Template", "", "## Tasks", ""]
        
        for task in tasks:
            content.append(f"- [ ] {task.text}")
            content.append(f"  - Priority: {task.priority.name}")
            content.append(f"  - Impact: {task.impact.name}")
            content.append(f"  - Area: {task.impact_area.name}")
            if task.notes:
                content.append(f"  - Notes: {task.notes}")
            content.append("")
        
        return "\n".join(content)

    def update_status_panel(self):
        """Update status panel with current statistics"""
        total = self.tree_model.rowCount()
        completed = sum(1 for row in range(total) 
                       if self.tree_model.item(row, 2).text() == "Completed")
        high_priority = sum(1 for row in range(total) 
                           if self.tree_model.item(row, 3).text() in ["HIGH", "CRITICAL"])
        overdue = sum(1 for row in range(total) 
                     if self.is_task_overdue(row))
        
        self.total_tasks.setText(f"Total Tasks: {total}")
        self.completed_tasks.setText(f"Completed: {completed}")
        self.high_priority_tasks.setText(f"High Priority: {high_priority}")
        self.overdue_tasks.setText(f"Overdue: {overdue}")
        self.completion_rate.setText(f"Completion Rate: {(completed/total*100):.1f}%" if total else "0%")
        self.risk_score.setText(f"Risk Score: {self.calculate_risk_score():.2f}")

    def calculate_risk_score(self) -> float:
        """Calculate overall risk score for all tasks"""
        total = self.tree_model.rowCount()
        if not total:
            return 0.0
            
        risk_values = {
            RiskProbability.UNLIKELY.name: 1,
            RiskProbability.POSSIBLE.name: 2,
            RiskProbability.LIKELY.name: 3,
            RiskProbability.CERTAIN.name: 4
        }
        
        impact_values = {
            ImpactSeverity.LOW.name: 1,
            ImpactSeverity.MEDIUM.name: 2,
            ImpactSeverity.HIGH.name: 3,
            ImpactSeverity.CRITICAL.name: 4
        }
        
        total_score = 0
        for row in range(total):
            risk_level = self.tree_model.item(row, 4).text()
            impact = self.tree_model.item(row, 5).text()
            total_score += risk_values.get(risk_level, 0) * impact_values.get(impact, 0)
            
        return total_score / (total * 16)  # Normalize to 0-1 scale

    def save_checklist(self, filepath: Optional[str] = None):
        """Save checklist to file"""
        if not filepath:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Checklist", "", "Checklist Files (*.json);;All Files (*)"
            )
        
        if filepath:
            data = {
                "tasks": [self.get_task_data(row) for row in range(self.tree_model.rowCount())],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "preferences": self.preferences
                }
            }
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                self.event_manager.broadcast_news(
                    "Checklist Saved",
                    f"Checklist saved to {filepath}",
                    EventPriority.LOW
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save checklist: {e}")

    def setup_filter_panel(self):
        """Setup the filtering options panel"""
        filter_group = QGroupBox("Filters")
        filter_layout = QGridLayout()
        
        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Completed"])
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Status:"), 0, 0)
        filter_layout.addWidget(self.status_filter, 0, 1)
        
        # Priority filter
        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["All"] + [p.name for p in RiskPriority])
        self.priority_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Priority:"), 0, 2)
        filter_layout.addWidget(self.priority_filter, 0, 3)
        
        # Category filter
        self.category_filter = QComboBox()
        self.category_filter.addItems(["All", "Development", "Integration", "Security", "Documentation"])
        self.category_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Category:"), 1, 0)
        filter_layout.addWidget(self.category_filter, 1, 1)
        
        # Assigned to filter
        self.assigned_filter = QComboBox()
        self.assigned_filter.addItems(["All"])  # Will be populated with team members
        self.assigned_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Assigned To:"), 1, 2)
        filter_layout.addWidget(self.assigned_filter, 1, 3)
        
        filter_group.setLayout(filter_layout)
        self.layout.addWidget(filter_group)

    def apply_filters(self):
        """Apply all active filters to the task list"""
        try:
            status_filter = self.status_filter.currentText()
            priority_filter = self.priority_filter.currentText()
            category_filter = self.category_filter.currentText()
            assigned_filter = self.assigned_filter.currentText()
            
            for i in range(self.task_list.topLevelItemCount()):
                item = self.task_list.topLevelItem(i)
                task_data = self.get_task_data_from_item(item)
                
                # Check each filter condition
                show = True
                if status_filter != "All":
                    show = show and (
                        (status_filter == "Completed" and task_data.completed) or
                        (status_filter == "Active" and not task_data.completed)
                    )
                
                if priority_filter != "All":
                    show = show and (task_data.priority.name == priority_filter)
                    
                if category_filter != "All":
                    show = show and (task_data.category == category_filter)
                    
                if assigned_filter != "All":
                    show = show and (task_data.assigned_to == assigned_filter)
                    
                item.setHidden(not show)
                
        except Exception as e:
            logging.error(f"Error applying filters: {e}")

    def get_task_data_from_item(self, item) -> TaskCheckItem:
        """Extract task data from a QTreeWidgetItem"""
        return TaskCheckItem(
            text=item.text(0),
            completed=item.text(2) == "Completed",
            category=item.text(3),
            priority=RiskPriority[item.text(1)] if item.text(1) else RiskPriority.MEDIUM,
            assigned_to=item.text(4),
            due_date=datetime.strptime(item.text(5), "%Y-%m-%d") if item.text(5) else None
        )

class TaskDialog(QDialog):
    def __init__(self, parent=None, task_data=None):
        super().__init__(parent)
        self.task_data = task_data
        self.setup_ui()
        if task_data:
            self.load_task_data(task_data)

    def setup_ui(self):
        self.setWindowTitle("Task Details")
        layout = QFormLayout(self)

        # Basic Info
        self.text_input = QLineEdit()
        layout.addRow("Task:", self.text_input)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Integration", "Development", "Security", "Documentation"])
        layout.addRow("Category:", self.category_combo)

        # Priority and Risk
        self.priority_combo = QComboBox()
        self.priority_combo.addItems([p.name for p in RiskPriority])
        layout.addRow("Priority:", self.priority_combo)

        self.risk_combo = QComboBox()
        self.risk_combo.addItems([r.name for r in RiskProbability])
        layout.addRow("Risk Level:", self.risk_combo)

        # Impact
        self.impact_combo = QComboBox()
        self.impact_combo.addItems([i.name for i in ImpactSeverity])
        layout.addRow("Impact:", self.impact_combo)

        self.area_combo = QComboBox()
        self.area_combo.addItems([a.name for a in ImpactArea])
        layout.addRow("Impact Area:", self.area_combo)

        # Dates and Assignment
        self.due_date = QDateTimeEdit()
        self.due_date.setCalendarPopup(True)
        layout.addRow("Due Date:", self.due_date)

        self.assigned_to = QLineEdit()
        layout.addRow("Assigned To:", self.assigned_to)

        # Notes
        self.notes = QTextEdit()
        layout.addRow("Notes:", self.notes)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def get_task_data(self) -> TaskCheckItem:
        """Get task data from dialog fields"""
        return TaskCheckItem(
            text=self.text_input.text(),
            category=self.category_combo.currentText(),
            priority=RiskPriority[self.priority_combo.currentText()],
            risk_level=RiskProbability[self.risk_combo.currentText()],
            impact=ImpactSeverity[self.impact_combo.currentText()],
            impact_area=ImpactArea[self.area_combo.currentText()],
            assigned_to=self.assigned_to.text(),
            due_date=self.due_date.dateTime().toPyDateTime() if self.due_date.dateTime().isValid() else None,
            notes=self.notes.toPlainText()
        )

    def load_task_data(self, task: TaskCheckItem):
        """Load task data into dialog fields"""
        self.text_input.setText(task.text)
        self.category_combo.setCurrentText(task.category)
        self.priority_combo.setCurrentText(task.priority.name)
        self.risk_combo.setCurrentText(task.risk_level.name)
        self.impact_combo.setCurrentText(task.impact.name)
        self.area_combo.setCurrentText(task.impact_area.name)
        self.assigned_to.setText(task.assigned_to)
        if task.due_date:
            self.due_date.setDateTime(task.due_date)
        self.notes.setPlainText(task.notes)

    def get_task_data(self, row: int) -> TaskCheckItem:
        """Get task data from row"""
        item = self.tree_model.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def calculate_risk_score(self) -> float:
        """Calculate overall risk score"""
        total_score = 0
        total_tasks = self.tree_model.rowCount()
        
        if total_tasks == 0:
            return 0.0
        
        for row in range(total_tasks):
            task = self.get_task_data(row)
            if task:
                priority_score = {
                    RiskPriority.LOW: 1,
                    RiskPriority.MEDIUM: 2,
                    RiskPriority.HIGH: 3,
                    RiskPriority.CRITICAL: 4
                }.get(task.priority, 0)
                
                impact_score = {
                    ImpactSeverity.LOW: 1,
                    ImpactSeverity.MEDIUM: 2,
                    ImpactSeverity.HIGH: 3,
                    ImpactSeverity.CRITICAL: 4
                }.get(task.impact, 0)
                
                total_score += (priority_score * impact_score)
        
        return total_score / total_tasks

    def is_task_overdue(self, row: int) -> bool:
        """Check if task is overdue"""
        task = self.get_task_data(row)
        if task and task.due_date:
            return task.due_date < datetime.now()
        return False