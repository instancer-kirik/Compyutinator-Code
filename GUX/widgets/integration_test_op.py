import sys
import json
import os
import markdown
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QLineEdit, QMessageBox, QFileDialog, QTextBrowser, QMenu,
    QDialog, QFormLayout, QDateTimeEdit, QComboBox, QSpinBox, QMenuBar,
    QGroupBox, QGridLayout
)
from PyQt6.QtCore import (
    Qt, QStringListModel, QAbstractItemModel, QModelIndex, 
    pyqtSignal, QMimeData, QTimer
)
from PyQt6.QtGui import QImage, QTextDocument, QKeySequence,QStandardItemModel, QStandardItem
from riskkit.enums import (
    RiskPriority, RiskStatus, RiskProbability,
    ImpactSeverity, ImpactArea, ImpactTimeframe
)
from riskkit.event_manager import EventManager, EventPriority
from riskkit.client import RiskkitClient
from riskkit.data_mux import DataMux

@dataclass
class Reference:
    type: str  # 'file', 'line', 'symbol', 'issue', 'comment'
    path: str
    line: Optional[int] = None
    column: Optional[int] = None
    signature: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChecklistItem:
    text: str
    completed: bool = False
    children: List['ChecklistItem'] = None
    due_date: Optional[datetime] = None
    priority: str = "Medium"
    notes: str = ""
    assigned_to: str = ""
    tags: List[str] = None
    references: List[Reference] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.tags is None:
            self.tags = []
        if self.references is None:
            self.references = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "completed": self.completed,
            "children": [child.to_dict() for child in self.children],
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "priority": self.priority,
            "notes": self.notes,
            "assigned_to": self.assigned_to,
            "tags": self.tags,
            "references": [
                {
                    "type": ref.type,
                    "path": ref.path,
                    "line": ref.line,
                    "column": ref.column,
                    "signature": ref.signature,
                    "description": ref.description,
                    "metadata": ref.metadata
                } for ref in self.references
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def add_reference(self, ref_type: str, path: str, **kwargs):
        """Add a reference to the checklist item"""
        self.references.append(Reference(type=ref_type, path=path, **kwargs))

    @classmethod
    def from_dict(cls, data: dict) -> 'ChecklistItem':
        children = [cls.from_dict(child) for child in data.get("children", [])]
        return cls(
            text=data["text"],
            completed=data["completed"],
            children=children,
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            priority=data.get("priority", "Medium"),
            notes=data.get("notes", ""),
            assigned_to=data.get("assigned_to", ""),
            tags=data.get("tags", []),
            references=[
                Reference(
                    type=ref["type"],
                    path=ref["path"],
                    line=ref.get("line"),
                    column=ref.get("column"),
                    signature=ref.get("signature"),
                    description=ref.get("description"),
                    metadata=ref.get("metadata", {})
                ) for ref in data.get("references", [])
            ],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )

class ChecklistItemDialog(QDialog):
    def __init__(self, item: Optional[ChecklistItem] = None, parent=None):
        super().__init__(parent)
        self.item = item or ChecklistItem("")
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Checklist Item Details")
        layout = QFormLayout(self)

        # Text input
        self.text_input = QLineEdit(self.item.text)
        layout.addRow("Text:", self.text_input)

        # Priority selector
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText(self.item.priority)
        layout.addRow("Priority:", self.priority_combo)

        # Due date
        self.due_date_edit = QDateTimeEdit()
        self.due_date_edit.setCalendarPopup(True)
        if self.item.due_date:
            self.due_date_edit.setDateTime(self.item.due_date)
        layout.addRow("Due Date:", self.due_date_edit)

        # Assigned to
        self.assigned_to_input = QLineEdit(self.item.assigned_to)
        layout.addRow("Assigned To:", self.assigned_to_input)

        # Tags
        self.tags_input = QLineEdit(",".join(self.item.tags))
        layout.addRow("Tags (comma-separated):", self.tags_input)

        # Notes
        self.notes_input = QLineEdit(self.item.notes)
        layout.addRow("Notes:", self.notes_input)
        tree_view = QTreeView()
        layout.addRow("Tree View:", tree_view)
        # Buttons
        buttons = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def get_item(self) -> ChecklistItem:
        self.item.text = self.text_input.text()
        self.item.priority = self.priority_combo.currentText()
        self.item.due_date = self.due_date_edit.dateTime().toPyDateTime()
        self.item.assigned_to = self.assigned_to_input.text()
        self.item.tags = [tag.strip() for tag in self.tags_input.text().split(",") if tag.strip()]
        self.item.notes = self.notes_input.text()
        self.item.updated_at = datetime.now()
        return self.item

class ChecklistTreeModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels(["Task", "Status", "Priority", "Due Date", "Assigned To"])

    def add_item(self, item: ChecklistItem, parent=None):
        row = []
        # Task
        task_item = QStandardItem(item.text)
        task_item.setCheckable(True)
        task_item.setCheckState(Qt.CheckState.Checked if item.completed else Qt.CheckState.Unchecked)
        row.append(task_item)
        
        # Status
        status_item = QStandardItem("Complete" if item.completed else "Pending")
        row.append(status_item)
        
        # Priority
        priority_item = QStandardItem(item.priority)
        row.append(priority_item)
        
        # Due Date
        due_date = item.due_date.strftime("%Y-%m-%d %H:%M") if item.due_date else ""
        due_date_item = QStandardItem(due_date)
        row.append(due_date_item)
        
        # Assigned To
        assigned_to_item = QStandardItem(item.assigned_to)
        row.append(assigned_to_item)

        if parent is None:
            self.appendRow(row)
        else:
            parent.appendRow(row)

        # Add children recursively
        for child in item.children:
            self.add_item(child, task_item)

        return task_item

class MarkdownViewer(QTextBrowser):
    def __init__(self, vault_path):
        super().__init__()
        self.vault_path = vault_path
        self.image_map = {}
        if self.vault_path:
            self.index_vault()

    def index_vault(self):
        if not self.vault_path:
            return
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    self.image_map[file] = os.path.join(root, file)

    def load_markdown(self, md_file):
        with open(md_file, 'r') as f:
            md_content = f.read()
        
        # Custom image syntax handling
        def image_handler(match):
            image_name = match.group(1)
            if image_name in self.image_map:
                return f'<img src="{self.image_map[image_name]}">'
            return match.group(0)

        md_content = re.sub(r'!\[\[(.*?)\]\]', image_handler, md_content)
        
        html_content = markdown.markdown(md_content)
        self.setHtml(html_content)

    def loadResource(self, type, name):
        if type == QTextDocument.ResourceType.ImageResource:
            image = QImage(name.toString())
            if not image.isNull():
                return image
        return super().loadResource(type, name)

    def set_vault_path(self, new_vault_path):
        self.vault_path = new_vault_path
        self.image_map = {}
        if self.vault_path:
            self.index_vault()

class IntegrationCheckItem:
    """Data class for integration test items"""
    name: str
    description: str = ""
    status: str = "Not Started"  # Not Started, In Progress, Failed, Passed
    priority: RiskPriority = RiskPriority.MEDIUM
    risk_level: RiskProbability = RiskProbability.POSSIBLE
    impact: ImpactSeverity = ImpactSeverity.MEDIUM
    impact_area: ImpactArea = ImpactArea.FUNCTIONALITY
    timeframe: ImpactTimeframe = ImpactTimeframe.SHORT_TERM
    assigned_to: str = ""
    due_date: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    related_tests: List[str] = field(default_factory=list)
    related_risks: List[int] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    test_results: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)

class IntegrationTestingManager(QWidget):
    def __init__(self, project_manager=None, risk_manager=None):
        super().__init__()
        self.project_manager = project_manager
        self.risk_manager = risk_manager
        self.event_manager = EventManager()
        self.data_mux = DataMux()
        
        self.setWindowTitle("Integration Testing Manager")
        self.setGeometry(100, 100, 1000, 800)

        # Initialize layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Initialize tree model and view
        self.setup_tree_view()
        
        # Setup UI components
        self.setup_menu()
        self.setup_toolbar()
        self.setup_status_panel()
        
        # Initialize auto-save
        self.setup_auto_save()

    def setup_tree_view(self):
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels([
            "Task", "Status", "Risk Level", "Impact",
            "Area", "Timeframe", "Assigned To", "Due Date"
        ])
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.tree_view)

    def setup_status_panel(self):
        status_group = QGroupBox("Integration Status")
        status_layout = QGridLayout()

        # Status indicators
        self.total_items = QLabel("Total Items: 0")
        self.completed_items = QLabel("Completed: 0")
        self.high_risk_items = QLabel("High Risk Items: 0")
        self.overdue_items = QLabel("Overdue: 0")
        self.risk_score = QLabel("Risk Score: 0.0")

        status_layout.addWidget(self.total_items, 0, 0)
        status_layout.addWidget(self.completed_items, 0, 1)
        status_layout.addWidget(self.high_risk_items, 1, 0)
        status_layout.addWidget(self.overdue_items, 1, 1)
        status_layout.addWidget(self.risk_score, 2, 0)

        status_group.setLayout(status_layout)
        self.layout.addWidget(status_group)

    def new_checklist(self):
        reply = QMessageBox.question(
            self, 'New Checklist',
            'Create new checklist? Unsaved changes will be lost.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.tree_model.clear()
            self.tree_model.setHorizontalHeaderLabels([
                "Task", "Status", "Risk Level", "Impact",
                "Area", "Timeframe", "Assigned To", "Due Date"
            ])
            self.checklist_path = None
            self.update_status_panel()

    def add_item(self):
        dialog = IntegrationItemDialog(self)
        if dialog.exec():
            item_data = dialog.get_item_data()
            self.add_item_to_tree(item_data)
            self.update_status_panel()
            
            # Check if risk level is high enough to create a risk
            if item_data.risk_level in [RiskProbability.LIKELY, RiskProbability.CERTAIN]:
                self.create_associated_risk(item_data)

    def create_associated_risk(self, item_data: IntegrationCheckItem):
        """Create a risk entry for high-risk integration items"""
        if self.risk_manager:
            risk_data = {
                "description": f"Integration Risk: {item_data.text}",
                "probability": item_data.risk_level.value,
                "impact": item_data.impact.value,
                "priority": RiskPriority.HIGH.value,
                "status": RiskStatus.OPEN.value,
                "mitigation": item_data.notes,
                "impact_area": item_data.impact_area.value,
                "timeframe": item_data.timeframe.value
            }
            self.risk_manager.create_risk(risk_data)
            self.event_manager.broadcast_news(
                "Integration Risk Created",
                f"New risk created for integration item: {item_data.text}",
                EventPriority.HIGH
            )

    def update_status_panel(self):
        """Update status panel with current statistics"""
        total = self.tree_model.rowCount()
        completed = sum(1 for row in range(total) 
                       if self.tree_model.item(row, 1).text() == "Completed")
        high_risk = sum(1 for row in range(total)
                       if self.tree_model.item(row, 2).text() 
                       in [RiskProbability.LIKELY.value, RiskProbability.CERTAIN.value])
        
        now = datetime.now()
        overdue = sum(1 for row in range(total)
                     if self.tree_model.item(row, 7).text() 
                     and datetime.fromisoformat(self.tree_model.item(row, 7).text()) < now)
        
        risk_score = self.calculate_risk_score()
        
        self.total_items.setText(f"Total Items: {total}")
        self.completed_items.setText(f"Completed: {completed}")
        self.high_risk_items.setText(f"High Risk Items: {high_risk}")
        self.overdue_items.setText(f"Overdue: {overdue}")
        self.risk_score.setText(f"Risk Score: {risk_score:.2f}")

    def calculate_risk_score(self) -> float:
        """Calculate overall risk score for the integration checklist"""
        total = self.tree_model.rowCount()
        if not total:
            return 0.0
            
        risk_values = {
            RiskProbability.UNLIKELY.value: 1,
            RiskProbability.POSSIBLE.value: 2,
            RiskProbability.LIKELY.value: 3,
            RiskProbability.CERTAIN.value: 4
        }
        
        impact_values = {
            ImpactSeverity.LOW.value: 1,
            ImpactSeverity.MEDIUM.value: 2,
            ImpactSeverity.HIGH.value: 3,
            ImpactSeverity.CRITICAL.value: 4
        }
        
        total_score = 0
        for row in range(total):
            risk_level = self.tree_model.item(row, 2).text()
            impact = self.tree_model.item(row, 3).text()
            total_score += risk_values.get(risk_level, 0) * impact_values.get(impact, 0)
            
        return total_score / (total * 16)  # Normalize to 0-1 scale

class IntegrationItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Add Integration Item")
        layout = QFormLayout(self)

        # Item text
        self.text_input = QLineEdit()
        layout.addRow("Item Text:", self.text_input)

        # Risk level
        self.risk_level_combo = QComboBox()
        self.risk_level_combo.addItems([
            RiskProbability.UNLIKELY.value,
            RiskProbability.POSSIBLE.value,
            RiskProbability.LIKELY.value,
            RiskProbability.CERTAIN.value
        ])
        layout.addRow("Risk Level:", self.risk_level_combo)

        # Impact
        self.impact_combo = QComboBox()
        self.impact_combo.addItems([
            ImpactSeverity.LOW.value,
            ImpactSeverity.MEDIUM.value,
            ImpactSeverity.HIGH.value,
            ImpactSeverity.CRITICAL.value
        ])
        layout.addRow("Impact:", self.impact_combo)

        # Impact area
        self.impact_area_combo = QComboBox()
        self.impact_area_combo.addItems([
            ImpactArea.FUNCTIONALITY.value,
            ImpactArea.SECURITY.value,
            ImpactArea.PERFORMANCE.value,
            ImpactArea.RELIABILITY.value
        ])
        layout.addRow("Impact Area:", self.impact_area_combo)

        # Timeframe
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems([
            ImpactTimeframe.SHORT_TERM.value,
            ImpactTimeframe.MEDIUM_TERM.value,
            ImpactTimeframe.LONG_TERM.value
        ])
        layout.addRow("Timeframe:", self.timeframe_combo)

        # Assigned to
        self.assigned_to_input = QLineEdit()
        layout.addRow("Assigned To:", self.assigned_to_input)

        # Due date
        self.due_date_edit = QDateTimeEdit()
        self.due_date_edit.setCalendarPopup(True)
        layout.addRow("Due Date:", self.due_date_edit)

        # Notes
        self.notes_input = QLineEdit()
        layout.addRow("Notes:", self.notes_input)

        # Dependencies
        self.dependencies_input = QLineEdit()
        layout.addRow("Dependencies (comma-separated):", self.dependencies_input)

        # Related risks
        self.related_risks_input = QLineEdit()
        layout.addRow("Related Risks (comma-separated):", self.related_risks_input)

        # Buttons
        buttons = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def get_item_data(self) -> IntegrationCheckItem:
        return IntegrationCheckItem(
            text=self.text_input.text(),
            risk_level=RiskProbability(self.risk_level_combo.currentText()),
            impact=ImpactSeverity(self.impact_combo.currentText()),
            impact_area=ImpactArea(self.impact_area_combo.currentText()),
            timeframe=ImpactTimeframe(self.timeframe_combo.currentText()),
            assigned_to=self.assigned_to_input.text(),
            due_date=self.due_date_edit.dateTime().toPyDateTime(),
            dependencies=[dep.strip() for dep in self.dependencies_input.text().split(',') if dep.strip()],
            related_risks=[int(risk.strip()) for risk in self.related_risks_input.text().split(',') if risk.strip()],
            notes=self.notes_input.text()
        )

class ReferenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Add Reference")
        layout = QFormLayout(self)

        # Reference type
        self.type_combo = QComboBox()
        self.type_combo.addItems(['file', 'line', 'symbol', 'issue', 'comment'])
        layout.addRow("Type:", self.type_combo)

        # Path
        self.path_input = QLineEdit()
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_path)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        layout.addRow("Path:", path_layout)

        # Line and column
        self.line_input = QSpinBox()
        self.line_input.setMinimum(1)
        self.line_input.setMaximum(999999)
        layout.addRow("Line:", self.line_input)

        self.column_input = QSpinBox()
        self.column_input.setMinimum(1)
        self.column_input.setMaximum(999)
        layout.addRow("Column:", self.column_input)

        # Signature
        self.signature_input = QLineEdit()
        layout.addRow("Signature:", self.signature_input)

        # Description
        self.description_input = QLineEdit()
        layout.addRow("Description:", self.description_input)

        # Buttons
        buttons = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def browse_path(self):
        if self.type_combo.currentText() == 'file':
            path, _ = QFileDialog.getOpenFileName(self, "Select File")
            if path:
                self.path_input.setText(path)

    def get_reference(self) -> Reference:
        return Reference(
            type=self.type_combo.currentText(),
            path=self.path_input.text(),
            line=self.line_input.value() if self.line_input.value() > 0 else None,
            column=self.column_input.value() if self.column_input.value() > 0 else None,
            signature=self.signature_input.text() or None,
            description=self.description_input.text() or None
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IntegrationTestingManager()
    window.show()
    sys.exit(app.exec())
