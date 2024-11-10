from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLineEdit, QTreeWidget, QTreeWidgetItem, QMenu,
                            QInputDialog, QMessageBox, QLabel, QComboBox,
                            QDialog, QFormLayout, QTextEdit, QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal
import json
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class CommandConfig:
    name: str
    command: str
    description: Optional[str] = None
    category: str = "General"
    environment: str = "Default"
    variables: Dict[str, str] = None
    last_used: Optional[datetime] = None
    success_count: int = 0
    fail_count: int = 0
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = {}
        if self.last_used is None:
            self.last_used = datetime.now()

BUILTIN_COMMANDS = {
    "install_nix": CommandConfig(
        name="Install Nix Package Manager",
        command="sh <(curl -L https://nixos.org/nix/install)",
        description="Installs the Nix package manager on your system. Nix is a powerful package manager that enables reproducible, declarative and reliable systems.",
        category="System Setup",
        environment="Default",
        variables={},
        success_count=0,
        fail_count=0
    ),
    "install_nix_daemon": CommandConfig(
        name="Install Nix (Multi-user)",
        command="sh <(curl -L https://nixos.org/nix/install) --daemon",
        description="Installs Nix in multi-user mode with daemon support. Recommended for most systems.",
        category="System Setup",
        environment="Default",
        variables={},
        success_count=0,
        fail_count=0
    ),
    "verify_nix": CommandConfig(
        name="Verify Nix Installation",
        command="nix-shell -p nix-info --run 'nix-info -m'",
        description="Displays detailed information about your Nix installation and system configuration.",
        category="System Setup",
        environment="Default",
        variables={},
        success_count=0,
        fail_count=0
    )
}

class CommandEditorDialog(QDialog):
    def __init__(self, command_data=None, parent=None):
        super().__init__(parent)
        self.command_data = command_data
        self.setup_ui()
        if command_data:
            self.load_command_data()

    def setup_ui(self):
        self.setWindowTitle("Command Editor")
        layout = QFormLayout(self)

        # Basic Info
        self.name_edit = QLineEdit()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems([
            "General", 
            "System Setup", 
            "Build", 
            "Test", 
            "Deploy", 
            "Database", 
            "Network"
        ])
        
        self.env_combo = QComboBox()
        self.env_combo.setEditable(True)
        self.env_combo.addItems(["Default", "Development", "Production", "Testing"])

        # Command with variables
        self.command_edit = QTextEdit()
        self.command_edit.setPlaceholderText("Enter command. Use ${var_name} for variables")

        # Variables section
        self.variables_widget = QWidget()
        self.variables_layout = QVBoxLayout(self.variables_widget)
        self.add_variable_btn = QPushButton("Add Variable")
        self.add_variable_btn.clicked.connect(self.add_variable_row)

        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)

        # Add all to layout
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Category:", self.category_combo)
        layout.addRow("Environment:", self.env_combo)
        layout.addRow("Command:", self.command_edit)
        layout.addRow("Variables:", self.variables_widget)
        layout.addRow("", self.add_variable_btn)
        layout.addRow("Description:", self.description_edit)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def add_variable_row(self, name="", value=""):
        row = QWidget()
        layout = QHBoxLayout(row)
        
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Variable name")
        value_edit = QLineEdit(value)
        value_edit.setPlaceholderText("Default value")
        delete_btn = QPushButton("×")
        
        layout.addWidget(name_edit)
        layout.addWidget(value_edit)
        layout.addWidget(delete_btn)
        
        self.variables_layout.addWidget(row)
        delete_btn.clicked.connect(lambda: row.deleteLater())

    def get_command_data(self) -> CommandConfig:
        variables = {}
        for i in range(self.variables_layout.count()):
            widget = self.variables_layout.itemAt(i).widget()
            if widget:
                layout = widget.layout()
                name = layout.itemAt(0).widget().text()
                value = layout.itemAt(1).widget().text()
                if name:
                    variables[name] = value

        return CommandConfig(
            name=self.name_edit.text(),
            command=self.command_edit.toPlainText(),
            description=self.description_edit.toPlainText(),
            category=self.category_combo.currentText(),
            environment=self.env_combo.currentText(),
            variables=variables
        )

    def load_command_data(self):
        self.name_edit.setText(self.command_data.name)
        self.category_combo.setCurrentText(self.command_data.category)
        self.env_combo.setCurrentText(self.command_data.environment)
        self.command_edit.setText(self.command_data.command)
        self.description_edit.setText(self.command_data.description or "")
        
        for name, value in self.command_data.variables.items():
            self.add_variable_row(name, value)

class CommandManager(QWidget):
    command_executed = pyqtSignal(str, bool)  # command, success

    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.commands: Dict[str, CommandConfig] = {}
        self.setup_ui()
        self.load_commands()
        self.add_builtin_commands()

    def add_builtin_commands(self):
        """Add built-in commands if they don't already exist"""
        for name, cmd in BUILTIN_COMMANDS.items():
            if name not in self.commands:
                self.commands[name] = cmd
        self.save_commands()
        self.refresh_tree()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.category_filter = QComboBox()
        self.category_filter.addItems([
            "All Categories", 
            "System Setup", 
            "General", 
            "Build", 
            "Test", 
            "Deploy"
        ])
        self.category_filter.currentTextChanged.connect(self.filter_commands)
        
        self.env_filter = QComboBox()
        self.env_filter.addItems(["All Environments", "Default", "Development", "Production"])
        self.env_filter.currentTextChanged.connect(self.filter_commands)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search commands...")
        self.search_box.textChanged.connect(self.filter_commands)
        
        toolbar.addWidget(QLabel("Category:"))
        toolbar.addWidget(self.category_filter)
        toolbar.addWidget(QLabel("Environment:"))
        toolbar.addWidget(self.env_filter)
        toolbar.addWidget(self.search_box)
        
        # Command Tree
        self.command_tree = QTreeWidget()
        self.command_tree.setHeaderLabels(["Name", "Description", "Last Used", "Success Rate"])
        self.command_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.command_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # Quick Run Area
        quick_run = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command or select from above...")
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self.run_command)
        
        quick_run.addWidget(self.command_input)
        quick_run.addWidget(self.run_btn)
        
        # Add all to main layout
        layout.addLayout(toolbar)
        layout.addWidget(self.command_tree)
        layout.addLayout(quick_run)

    def show_context_menu(self, position):
        item = self.command_tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        run_action = menu.addAction("Run")
        edit_action = menu.addAction("Edit")
        duplicate_action = menu.addAction("Duplicate")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec(self.command_tree.viewport().mapToGlobal(position))
        
        command_name = item.text(0)
        if action == run_action:
            self.run_saved_command(command_name)
        elif action == edit_action:
            self.edit_command(command_name)
        elif action == duplicate_action:
            self.duplicate_command(command_name)
        elif action == delete_action:
            self.delete_command(command_name)

    def run_command(self):
        command = self.command_input.text()
        if not command:
            return
            
        try:
            # Execute through cccore's process manager
            success = self.cccore.process_manager.run_command(command)
            self.command_executed.emit(command, success)
            
            if success:
                QMessageBox.information(self, "Success", "Command executed successfully")
            else:
                QMessageBox.warning(self, "Error", "Command execution failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error executing command: {str(e)}")

    def run_saved_command(self, command_name):
        command_config = self.commands.get(command_name)
        if not command_config:
            return
            
        # Replace variables
        command = command_config.command
        for var_name, var_value in command_config.variables.items():
            command = command.replace(f"${{{var_name}}}", var_value)
            
        self.command_input.setText(command)
        self.run_command()
        
        # Update stats
        command_config.last_used = datetime.now()
        self.save_commands()
        self.refresh_tree()

    def add_command(self):
        dialog = CommandEditorDialog(parent=self)
        if dialog.exec():
            command_data = dialog.get_command_data()
            self.commands[command_data.name] = command_data
            self.save_commands()
            self.refresh_tree()

    def edit_command(self, command_name):
        command_data = self.commands.get(command_name)
        if not command_data:
            return
            
        dialog = CommandEditorDialog(command_data, parent=self)
        if dialog.exec():
            updated_data = dialog.get_command_data()
            if command_name != updated_data.name:
                del self.commands[command_name]
            self.commands[updated_data.name] = updated_data
            self.save_commands()
            self.refresh_tree()

    def duplicate_command(self, command_name):
        command_data = self.commands.get(command_name)
        if not command_data:
            return
            
        new_name = f"{command_name} (copy)"
        new_command = CommandConfig(
            name=new_name,
            command=command_data.command,
            description=command_data.description,
            category=command_data.category,
            environment=command_data.environment,
            variables=dict(command_data.variables)
        )
        
        self.commands[new_name] = new_command
        self.save_commands()
        self.refresh_tree()

    def delete_command(self, command_name):
        reply = QMessageBox.question(
            self, "Delete Command",
            f"Are you sure you want to delete '{command_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.commands[command_name]
            self.save_commands()
            self.refresh_tree()

    def filter_commands(self):
        category = self.category_filter.currentText()
        environment = self.env_filter.currentText()
        search_text = self.search_box.text().lower()
        
        self.command_tree.clear()
        
        for command in self.commands.values():
            if (category == "All Categories" or command.category == category) and \
               (environment == "All Environments" or command.environment == environment) and \
               (search_text in command.name.lower() or search_text in command.description.lower()):
                
                success_rate = 0
                if command.success_count + command.fail_count > 0:
                    success_rate = (command.success_count / (command.success_count + command.fail_count)) * 100
                
                item = QTreeWidgetItem([
                    command.name,
                    command.description or "",
                    command.last_used.strftime("%Y-%m-%d %H:%M") if command.last_used else "",
                    f"{success_rate:.1f}%"
                ])
                
                self.command_tree.addTopLevelItem(item)

    def save_commands(self):
        try:
            commands_data = {
                name: {
                    "name": cmd.name,
                    "command": cmd.command,
                    "description": cmd.description,
                    "category": cmd.category,
                    "environment": cmd.environment,
                    "variables": cmd.variables,
                    "last_used": cmd.last_used.isoformat() if cmd.last_used else None,
                    "success_count": cmd.success_count,
                    "fail_count": cmd.fail_count
                }
                for name, cmd in self.commands.items()
            }
            
            config_path = os.path.join(self.cccore.config_dir, "commands.json")
            with open(config_path, 'w') as f:
                json.dump(commands_data, f, indent=2)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save commands: {str(e)}")

    def load_commands(self):
        try:
            config_path = os.path.join(self.cccore.config_dir, "commands.json")
            if not os.path.exists(config_path):
                return
                
            with open(config_path, 'r') as f:
                commands_data = json.load(f)
                
            self.commands = {}
            for name, data in commands_data.items():
                self.commands[name] = CommandConfig(
                    name=data["name"],
                    command=data["command"],
                    description=data["description"],
                    category=data["category"],
                    environment=data["environment"],
                    variables=data["variables"],
                    last_used=datetime.fromisoformat(data["last_used"]) if data["last_used"] else None,
                    success_count=data["success_count"],
                    fail_count=data["fail_count"]
                )
                
            self.refresh_tree()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load commands: {str(e)}")

    def refresh_tree(self):
        self.filter_commands()