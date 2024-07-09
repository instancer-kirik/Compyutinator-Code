from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QInputDialog, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt
import os
import subprocess

class ActionPadWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Action Pad", self)
        self.layout.addWidget(self.label)

        self.add_button = QPushButton("Add Button", self)
        self.add_button.clicked.connect(self.add_action_button)
        self.layout.addWidget(self.add_button)

        self.action_list = QListWidget(self)
        self.layout.addWidget(self.action_list)

    def add_action_button(self):
        button_name, ok = QInputDialog.getText(self, "New Action Button", "Enter button name:")
        if ok and button_name:
            action_button = QPushButton(button_name, self)
            action_button.clicked.connect(lambda: self.execute_action(button_name))
            list_item = QListWidgetItem()
            self.action_list.addItem(list_item)
            self.action_list.setItemWidget(list_item, action_button)

    def execute_action(self, button_name):
        action_command, ok = QInputDialog.getText(self, "Execute Action", f"Enter command for {button_name}:")
        if ok and action_command:
            try:
                subprocess.Popen(action_command, shell=True)
            except Exception as e:
                print(f"Failed to execute command: {e}")
