from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QInputDialog, QListWidget, QListWidgetItem, QHBoxLayout, QFormLayout, QDialogButtonBox, QMessageBox 
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
import os
import subprocess
from NITTY_GRITTY.database import DatabaseManager, UserAction

class ActionPadWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Action Pad", self)
        self.layout.addWidget(self.label)

        self.add_button = QPushButton("Add Button", self)
        self.add_button.clicked.connect(self.add_action_button)
        self.layout.addWidget(self.add_button)

        self.action_list = QListWidget(self)
        self.layout.addWidget(self.action_list)

        self.flash_label = QLabel("", self)
        self.flash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flash_label.setStyleSheet("color: yellow; background-color: black;")
        self.layout.addWidget(self.flash_label)
        self.flash_label.hide()  # Hide it initially

        self.populate_action_list()

    def populate_action_list(self):
        self.action_list.clear()  # Clear the existing items
        actions = self.db_manager.get_all_actions()
        for action in actions:
            self.add_action_to_list(action)

    def add_action_to_list(self, action):
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout()

        button = QPushButton(action.action_name)
        button.clicked.connect(lambda _, name=action.action_name: self.execute_action(name))

        count_label = QLabel(f"Count: {action.pressed_count or 0}")
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Create the hamburger menu button
        menu_button = QPushButton("☰")
        menu_button.setFixedWidth(30)  # Adjust the width as needed
        menu = QMenu()

        # Example actions for the menu
        edit_action = QAction("Edit", self)
        # Trigger edit action with the action's name
        edit_action.triggered.connect(lambda: self.edit_action(action.action_name))
        no_action = QAction("", self)
      #  edit_action.triggered.connect(lambda: self.edit_action(action))
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_action(action))
        
        menu.addAction(edit_action)
        menu.addAction(no_action)
        menu.addAction(delete_action)

        # Connect the button to the menu
        menu_button.setMenu(menu)

        # Add widgets to the layout
        layout.addWidget(button)
        layout.addWidget(count_label)
        layout.addWidget(menu_button)
        widget.setLayout(layout)

        item.setSizeHint(widget.sizeHint())
        self.action_list.addItem(item)
        self.action_list.setItemWidget(item, widget)

    def add_action_button(self):
        button_name, ok = QInputDialog.getText(self, "New Action Button", "Enter button name:")
        if ok and button_name:
            action_type = "button_click"  # Replace with desired action type
            action_data = ""  # Or provide default action data if needed

            # Store the action in the database without a command
            self.db_manager.store_action(button_name, action_type, action_data, None)

            # Retrieve the newly added action to get its details
            new_action = self.db_manager.get_action_by_name(button_name)

            # Add the action to the list
            self.add_action_to_list(new_action)

    def execute_action(self, action_name):
        """Executes a user action based on its name."""
        try:
            # Open a new session
            db = next(self.db_manager.get_db())
            
            # Fetch the action from the database
            action = db.query(UserAction).filter(UserAction.action_name == action_name).first()

            if action:
                print(f"Executing action: {action.command}")  # Replace with actual command execution

                # Increment the pressed_count for the action
                action.pressed_count = (action.pressed_count or 0) + 1
                db.commit()
            else:
                print(f"Action '{action_name}' not found in the database.")

        except Exception as e:
            print(f"Error executing action: {e}")
        
        finally:
            # Ensure the session is closed
            if 'db' in locals():
                db.close()

    def show_flash_message(self, message):
        """Displays a flash message for a brief period."""
        self.flash_label.setText(message)
        self.flash_label.show()

        # Set a timer to hide the flash message after 2 seconds
        QTimer.singleShot(2000, self.flash_label.hide)
    
    def edit_action(self, action_name):
        try:
            db = next(self.db_manager.get_db())
            action = db.query(UserAction).filter(UserAction.action_name == action_name).first()
            if action:
                dialog = EditActionDialog(action, self.db_manager)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.populate_action_list()  # Refresh the list to reflect changes
            else:
                QMessageBox.warning(self, "Error", f"Action '{action_name}' not found")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit action: {e}")
        finally:
            if 'db' in locals():
                db.close()

    def delete_action(self, action):
        # Implement deletion logic here
        print(f"Deleting action: {action.action_name}")
class EditActionDialog(QDialog):
    def __init__(self, action, db_manager, parent=None):
        super().__init__(parent)
        self.action = action
        self.db_manager = db_manager
        self.setWindowTitle("Edit Action")

        self.layout = QVBoxLayout()

        # Form layout to hold the input fields
        form_layout = QFormLayout()

        # action_name field
        self.action_name_edit = QLineEdit(self.action.action_name)
        form_layout.addRow("Action Name:", self.action_name_edit)

        # action_type field
        self.action_type_edit = QLineEdit(self.action.action_type)
        form_layout.addRow("Action Type:", self.action_type_edit)

        # action_data field
        self.action_data_edit = QLineEdit(self.action.action_data)
        form_layout.addRow("Action Data:", self.action_data_edit)

        # pressed_count field
        self.pressed_count_edit = QLineEdit(str(self.action.pressed_count))
        form_layout.addRow("Pressed Count:", self.pressed_count_edit)

        # command field
        self.command_edit = QLineEdit(self.action.command)
        form_layout.addRow("Command:", self.command_edit)

        self.layout.addLayout(form_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_changes)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

    def save_changes(self):
        try:
            new_name = self.action_name_edit.text()
            new_type = self.action_type_edit.text()
            new_data = self.action_data_edit.text()
            new_count = int(self.pressed_count_edit.text())
            new_command = self.command_edit.text()

            # Use the update_action method from db_manager
            if self.db_manager.update_action(
                self.action.action_name, 
                new_name, 
                new_type, 
                new_data, 
                new_count, 
                new_command
            ):
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to update action")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")