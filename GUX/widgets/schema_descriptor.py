from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeView,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDialog, QFormLayout,
    QTextEdit, QCheckBox, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from dataclasses import dataclass, field, fields, MISSING
from typing import Dict, List, Optional, Any, Type, get_type_hints
import inspect
import json
from pydantic import BaseModel, Field
import logging

class SchemaDescriptorWidget(QWidget):
    schema_updated = pyqtSignal(dict)  # Emitted when schema is modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_schema = None

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.load_button = QPushButton("Load Schema")
        self.load_button.clicked.connect(self.load_schema)
        toolbar.addWidget(self.load_button)
        
        self.save_button = QPushButton("Save Schema")
        self.save_button.clicked.connect(self.save_schema)
        toolbar.addWidget(self.save_button)
        
        self.generate_button = QPushButton("Generate Code")
        self.generate_button.clicked.connect(self.generate_code)
        toolbar.addWidget(self.generate_button)
        
        self.validate_button = QPushButton("Validate")
        self.validate_button.clicked.connect(self.validate_schema)
        toolbar.addWidget(self.validate_button)
        
        layout.addLayout(toolbar)
        
        # Schema Tree View
        self.tree_view = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree_view)
        
        # Preview Panel
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)

    def load_schema_from_class(self, cls: Type):
        """Load schema from a Python class (dataclass or Pydantic model)"""
        try:
            self.tree_model.clear()
            self.tree_model.setHorizontalHeaderLabels(["Field", "Type", "Required", "Default", "Description"])
            
            if inspect.isclass(cls):
                if hasattr(cls, '__dataclass_fields__'):  # Dataclass
                    for field_name, field_obj in cls.__dataclass_fields__.items():
                        self.add_field_to_tree(field_name, field_obj)
                elif issubclass(cls, BaseModel):  # Pydantic model
                    for field_name, field_obj in cls.model_fields.items():
                        self.add_field_to_tree(field_name, field_obj)
            
            self.current_schema = cls
            self.update_preview()
        except Exception as e:
            logging.error(f"Error loading schema: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load schema: {str(e)}")

    def add_field_to_tree(self, name: str, field_obj: Any):
        """Add a field to the tree view"""
        row = [
            QStandardItem(name),
            QStandardItem(str(field_obj.type)),
            QStandardItem(str(field_obj.default is MISSING)),
            QStandardItem(str(field_obj.default if field_obj.default is not MISSING else "")),
            QStandardItem(str(getattr(field_obj, "description", "")))
        ]
        self.tree_model.appendRow(row)

    def generate_code(self):
        """Generate Python code for the current schema"""
        if not self.current_schema:
            return
        
        try:
            code = []
            code.append("from dataclasses import dataclass, field")
            code.append("from typing import Optional, List, Dict, Any")
            code.append("from datetime import datetime")
            code.append("")
            
            # Generate dataclass code
            code.append("@dataclass")
            code.append(f"class {self.current_schema.__name__}:")
            
            for field_name, field_obj in self.current_schema.__dataclass_fields__.items():
                type_hint = field_obj.type
                default = field_obj.default
                
                if default is MISSING:
                    code.append(f"    {field_name}: {type_hint}")
                else:
                    code.append(f"    {field_name}: {type_hint} = {repr(default)}")
            
            self.preview.setText("\n".join(code))
        except Exception as e:
            logging.error(f"Error generating code: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate code: {str(e)}")

    def validate_schema(self):
        """Validate the current schema"""
        if not self.current_schema:
            return
        
        try:
            # Basic validation
            issues = []
            
            # Check for required fields
            for field_name, field_obj in self.current_schema.__dataclass_fields__.items():
                if field_obj.default is MISSING and field_obj.default_factory is MISSING:
                    # Check if type hints are properly defined
                    if not field_obj.type:
                        issues.append(f"Field '{field_name}' missing type hint")
            
            if issues:
                QMessageBox.warning(self, "Validation Issues", "\n".join(issues))
            else:
                QMessageBox.information(self, "Validation", "Schema is valid!")
        except Exception as e:
            logging.error(f"Error validating schema: {e}")
            QMessageBox.critical(self, "Error", f"Validation failed: {str(e)}")

    def show_context_menu(self, position):
        """Show context menu for tree items"""
        menu = QMenu()
        menu.addAction("Add Field", self.add_field)
        menu.addAction("Edit Field", self.edit_field)
        menu.addAction("Remove Field", self.remove_field)
        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def add_field(self):
        """Add a new field to the schema"""
        dialog = FieldDialog(self)
        if dialog.exec():
            field_data = dialog.get_field_data()
            self.add_field_to_tree(**field_data)
            self.update_preview()

    def edit_field(self):
        """Edit the selected field"""
        current_index = self.tree_view.currentIndex()
        if not current_index.isValid():
            return
            
        dialog = FieldDialog(self)
        dialog.set_field_data({
            "name": self.tree_model.item(current_index.row(), 0).text(),
            "type": self.tree_model.item(current_index.row(), 1).text(),
            "required": self.tree_model.item(current_index.row(), 2).text() == "True",
            "default": self.tree_model.item(current_index.row(), 3).text(),
            "description": self.tree_model.item(current_index.row(), 4).text()
        })
        
        if dialog.exec():
            field_data = dialog.get_field_data()
            for col, value in enumerate([
                field_data["name"],
                field_data["type"],
                str(field_data["required"]),
                field_data["default"],
                field_data["description"]
            ]):
                self.tree_model.item(current_index.row(), col).setText(value)
            self.update_preview()

    def remove_field(self):
        """Remove the selected field"""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            self.tree_model.removeRow(current_index.row())
            self.update_preview()

    def update_preview(self):
        """Update the preview panel with current schema"""
        try:
            preview_data = {
                self.tree_model.item(row, 0).text(): {
                    "type": self.tree_model.item(row, 1).text(),
                    "required": self.tree_model.item(row, 2).text() == "True",
                    "default": self.tree_model.item(row, 3).text(),
                    "description": self.tree_model.item(row, 4).text()
                }
                for row in range(self.tree_model.rowCount())
            }
            self.preview.setText(json.dumps(preview_data, indent=2))
        except Exception as e:
            logging.error(f"Error updating preview: {e}")
    def export_to_json(self) -> dict:
        """Export current schema to JSON format"""
        schema_data = {
            "module_name": self.current_schema.__name__,
            "table_name": self.current_schema.__name__.lower(),
            "class_name": self.current_schema.__name__,
            "fields": {}
        }
        
        for row in range(self.tree_model.rowCount()):
            field_name = self.tree_model.item(row, 0).text()
            schema_data["fields"][field_name] = {
                "type": self.tree_model.item(row, 1).text(),
                "required": self.tree_model.item(row, 2).text() == "True",
                "default": self.tree_model.item(row, 3).text(),
                "description": self.tree_model.item(row, 4).text()
            }
        
        return schema_data