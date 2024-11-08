from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLineEdit, QListWidget, QLabel, QMessageBox
)
from .device_flows import DeviceFlow
from .device_manager import DeviceCommand

class FlowEditorDialog(QDialog):
    def __init__(self, parent=None, flow=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Flow")
        self.flow = flow
        self.available_commands = parent.parent().commands if parent else []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Flow name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Flow Name:"))
        self.name_edit = QLineEdit()
        if self.flow:
            self.name_edit.setText(self.flow.name)
        name_layout.addWidget(self.name_edit)
        
        # Command lists
        lists_layout = QHBoxLayout()
        
        # Available commands
        available_layout = QVBoxLayout()
        available_layout.addWidget(QLabel("Available Commands:"))
        self.available_list = QListWidget()
        for cmd in self.available_commands:
            self.available_list.addItem(cmd.name)
        available_layout.addWidget(self.available_list)
        
        # Buttons
        btn_layout = QVBoxLayout()
        add_btn = QPushButton("→")
        remove_btn = QPushButton("←")
        add_btn.clicked.connect(self.add_command)
        remove_btn.clicked.connect(self.remove_command)
        btn_layout.addStretch()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        
        # Selected commands
        selected_layout = QVBoxLayout()
        selected_layout.addWidget(QLabel("Flow Steps:"))
        self.selected_list = QListWidget()
        if self.flow:
            for step in self.flow.steps:
                self.selected_list.addItem(step.name)
        selected_layout.addWidget(self.selected_list)
        
        lists_layout.addLayout(available_layout)
        lists_layout.addLayout(btn_layout)
        lists_layout.addLayout(selected_layout)
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.save_flow)
        cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(save_btn)
        dialog_buttons.addWidget(cancel_btn)
        
        layout.addLayout(name_layout)
        layout.addLayout(lists_layout)
        layout.addLayout(dialog_buttons)
        self.setLayout(layout) 