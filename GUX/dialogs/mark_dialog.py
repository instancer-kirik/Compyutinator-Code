from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QTextEdit, QComboBox, QSpinBox,
                            QPushButton, QDateTimeEdit, QCheckBox, 
                            QListWidget, QListWidgetItem, QFileDialog)
from PyQt6.QtCore import Qt, QDateTime
from pathlib import Path
from typing import Optional, List
from HMC.mark_manager import Mark, MarkType
import logging

class MarkDialog(QDialog):
    """Base dialog for adding/editing marks"""
    def __init__(self, mark_manager, parent=None, mark: Optional[Mark] = None):
        super().__init__(parent)
        self.mark_manager = mark_manager
        self.mark = mark
        self.setMinimumWidth(500)
        self.setup_ui()
        if mark:
            self.load_mark_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Type Selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        for mark_type in MarkType:
            self.type_combo.addItem(f"{mark_type.value} {mark_type.name}", mark_type)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMinimumHeight(100)
        layout.addWidget(self.desc_edit)
        
        # Priority
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("Priority:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 5)
        self.priority_spin.setSpecialValueText("No Priority")
        priority_layout.addWidget(self.priority_spin)
        layout.addLayout(priority_layout)
        
        # Due Date
        due_layout = QHBoxLayout()
        self.has_due_date = QCheckBox("Due Date:")
        due_layout.addWidget(self.has_due_date)
        self.due_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.due_date.setEnabled(False)
        self.has_due_date.toggled.connect(self.due_date.setEnabled)
        due_layout.addWidget(self.due_date)
        layout.addLayout(due_layout)
        
        # Recurring
        recurring_layout = QHBoxLayout()
        self.recurring_check = QCheckBox("Recurring:")
        recurring_layout.addWidget(self.recurring_check)
        self.recurring_interval = QComboBox()
        self.recurring_interval.addItems(["daily", "weekly", "monthly"])
        self.recurring_interval.setEnabled(False)
        self.recurring_check.toggled.connect(self.recurring_interval.setEnabled)
        recurring_layout.addWidget(self.recurring_interval)
        layout.addLayout(recurring_layout)
        
        # Tags
        tags_layout = QVBoxLayout()
        tags_layout.addWidget(QLabel("Tags:"))
        self.tags_list = QListWidget()
        self.tags_list.setMaximumHeight(100)
        tags_layout.addWidget(self.tags_list)
        
        tags_input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tag and press Add")
        tags_input_layout.addWidget(self.tag_input)
        
        add_tag_btn = QPushButton("Add Tag")
        add_tag_btn.clicked.connect(self.add_tag)
        tags_input_layout.addWidget(add_tag_btn)
        
        tags_layout.addLayout(tags_input_layout)
        layout.addLayout(tags_layout)
        
        # Related Files
        files_layout = QVBoxLayout()
        files_layout.addWidget(QLabel("Related Files:"))
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(100)
        files_layout.addWidget(self.files_list)
        
        add_file_btn = QPushButton("Add File")
        add_file_btn.clicked.connect(self.add_file)
        files_layout.addWidget(add_file_btn)
        layout.addLayout(files_layout)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def add_tag(self):
        """Add tag to the list"""
        tag = self.tag_input.text().strip()
        if tag and tag not in self.get_tags():
            self.tags_list.addItem(tag)
            self.tag_input.clear()

    def add_file(self):
        """Add file to related files"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.files_list.addItem(file_path)

    def get_tags(self) -> List[str]:
        """Get all tags from list"""
        return [self.tags_list.item(i).text() 
                for i in range(self.tags_list.count())]

    def get_files(self) -> List[Path]:
        """Get all related files"""
        return [Path(self.files_list.item(i).text()) 
                for i in range(self.files_list.count())]

    def load_mark_data(self):
        """Load existing mark data into fields"""
        self.type_combo.setCurrentText(f"{self.mark.type.value} {self.mark.type.name}")
        self.title_edit.setText(self.mark.title)
        self.desc_edit.setText(self.mark.description)
        self.priority_spin.setValue(self.mark.priority)
        
        if self.mark.due_date:
            self.has_due_date.setChecked(True)
            self.due_date.setDateTime(self.mark.due_date)
            
        if self.mark.recurring:
            self.recurring_check.setChecked(True)
            self.recurring_interval.setCurrentText(self.mark.recurring_interval)
            
        for tag in self.mark.tags:
            self.tags_list.addItem(tag)
            
        for file_path in self.mark.related_files:
            self.files_list.addItem(str(file_path))

    def get_mark_data(self) -> dict:
        """Get data for creating/updating mark"""
        return {
            'type': self.type_combo.currentData(),
            'title': self.title_edit.text(),
            'description': self.desc_edit.toPlainText(),
            'priority': self.priority_spin.value(),
            'due_date': self.due_date.dateTime().toPyDateTime() if self.has_due_date.isChecked() else None,
            'recurring': self.recurring_check.isChecked(),
            'recurring_interval': self.recurring_interval.currentText() if self.recurring_check.isChecked() else None,
            'tags': self.get_tags(),
            'related_files': self.get_files()
        }

class AddMarkDialog(MarkDialog):
    """Dialog for adding new marks"""
    def __init__(self, mark_manager, parent=None):
        super().__init__(mark_manager, parent)
        self.setWindowTitle("Add New Mark")

class EditMarkDialog(MarkDialog):
    """Dialog for editing existing marks"""
    def __init__(self, mark: Mark, mark_manager, parent=None):
        super().__init__(mark_manager, parent, mark)
        self.setWindowTitle("Edit Mark")
        
        # Add complete button for existing marks
        complete_btn = QPushButton("Complete Mark")
        complete_btn.clicked.connect(self.complete_mark)
        self.layout().insertWidget(self.layout().count() - 1, complete_btn)

    def complete_mark(self):
        """Complete the mark"""
        try:
            self.mark_manager.complete_mark(self.mark.id)
            self.accept()
        except Exception as e:
            logging.error(f"Error completing mark: {e}") 