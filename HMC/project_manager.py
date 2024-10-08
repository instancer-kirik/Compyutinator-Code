import os
import json
import logging
from .environment_manager import EnvironmentManager
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, 
                             QInputDialog, QMessageBox, QFileDialog, QDialog, QLabel, QLineEdit, QFormLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
import sys
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialogButtonBox
class ProjectConfigDialog(QDialog):
    def __init__(self, project_name, project_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configure Project: {project_name}")
        self.project_name = project_name
        self.project_data = project_data
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Project Name and Path (read-only)
        form_layout = QFormLayout()
        form_layout.addRow("Project Name:", QLabel(self.project_name))
        form_layout.addRow("Project Path:", QLabel(self.project_data.get('path', 'N/A')))
        layout.addLayout(form_layout)

        # Build Command
        self.build_command_edit = QLineEdit(self.project_data.get('build_command', ''))
        form_layout.addRow("Build Command:", self.build_command_edit)

        # Run Command
        self.run_command_edit = QLineEdit(self.project_data.get('run_command', ''))
        form_layout.addRow("Run Command:", self.run_command_edit)

        # Registered Scripts
        self.scripts_list = QListWidget()
        self.scripts_list.addItems(self.project_data.get('registered_scripts', []))
        form_layout.addRow("Registered Scripts:", self.scripts_list)

        # Add and Remove Script buttons
        script_buttons_layout = QHBoxLayout()
        self.add_script_button = QPushButton("Add Script")
        self.remove_script_button = QPushButton("Remove Script")
        script_buttons_layout.addWidget(self.add_script_button)
        script_buttons_layout.addWidget(self.remove_script_button)
        layout.addLayout(script_buttons_layout)

        self.add_script_button.clicked.connect(self.add_script)
        self.remove_script_button.clicked.connect(self.remove_script)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def add_script(self):
        script, ok = QInputDialog.getText(self, "Add Script", "Enter script name:")
        if ok and script:
            self.scripts_list.addItem(script)

    def remove_script(self):
        current_item = self.scripts_list.currentItem()
        if current_item:
            self.scripts_list.takeItem(self.scripts_list.row(current_item))

    def get_updated_data(self):
        return {
            'name': self.project_name,
            'path': self.project_data.get('path'),
            'build_command': self.build_command_edit.text(),
            'run_command': self.run_command_edit.text(),
            'registered_scripts': [self.scripts_list.item(i).text() for i in range(self.scripts_list.count())]
        }

class Project:
    def __init__(self, name, path, language, version):
        self.name = name
        self.path = path
        self.language = language
        self.version = version
        self.config_file = os.path.join(path, '.project_config.json')
        self.build_command = ""
        self.run_command = ""
        self.load_config()
        
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.build_command = config.get('build_command', "")
                self.run_command = config.get('run_command', "")
        else:
            self.save_config()

    def save_config(self):
        config = {
            'name': self.name,
            'language': self.language,
            'version': self.version,
            'build_command': self.build_command,
            'run_command': self.run_command
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def set_build_command(self, command):
        self.build_command = command
        self.save_config()

    def set_run_command(self, command):
        self.run_command = command
        self.save_config()

class ProjectManager:
    project_changed = pyqtSignal(str)
    def __init__(self, settings_manager, cccore):
        self.settings_manager = settings_manager
        self.cccore = cccore
        self.build_manager = cccore.build_manager
        self.process_manager = cccore.process_manager
        self.projects = {}
        self.current_project = None
        self.recent_projects = []
        self.max_recent_projects = 10
        self.env_manager = EnvironmentManager(self.settings_manager.get_value("environments_path", "./environments"))
        self.vaults = {}  # New attribute to store vaults
        self.project_selector = QComboBox()
       # self.load_projects()
        self.update_project_selector()
        logging.warning(f"Loaded projects: {self.projects}")
        self.project_config_filename = "project_config.json"

    def create_project(self, project_name, project_path):
        full_path = os.path.join(project_path, project_name)
        os.makedirs(full_path, exist_ok=True)
        config_path = os.path.join(full_path, self.project_config_filename)
        
        config = {
            "name": project_name,
            "path": full_path,
            "files": []
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        return full_path

    def load_project(self, project_path):
        config_path = os.path.join(project_path, self.project_config_filename)
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Project configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.current_project = config
        self.project_changed.emit(config)
        return config

    def get_project_files(self):
        if not self.current_project:
            return []
        
        project_path = self.current_project['path']
        config_file = os.path.join(project_path, self.project_config_filename)
        
        files = [config_file]  # Always include the config file
        for root, dirs, filenames in os.walk(project_path):
            for filename in filenames:
                if filename != self.project_config_filename:
                    files.append(os.path.join(root, filename))
        
        return files
    def save_projects(self):
        if isinstance(self.projects, dict):
            self.settings_manager.set_value("projects", self.projects)
        else:
            logging.error(f"Cannot save projects, invalid data: {self.projects}")
        self.settings_manager.set_value("current_project", self.current_project)
        self.settings_manager.set_value("recent_projects", self.recent_projects)
    
    def save_current_project_state(self):
        current_project = self.get_current_project()
        if current_project:
            self.add_recent_project(current_project)
        
        open_files = self.cccore.editor_manager.get_open_files()
        self.cccore.settings_manager.set_value(f"open_files_{current_project}", open_files)

    def add_project(self, vault_name, project_name, project_path):
        vault = self.cccore.vault_manager.get_vault(vault_name)
        if vault:
            return vault.add_project(project_name=project_name, project_path=project_path)
        return False

    def get_projects(self, vault_name):
        vault = self.cccore.vault_manager.get_vault(vault_name)
        if vault:
            return vault.get_project_names()
        return []

    def get_many_projects(self):
        many_projects = []
        for vault in self.cccore.vault_manager.vaults.values():
            many_projects.extend(vault.projects.keys())
        return many_projects

    def get_project_path(self, vault_name, project_name):
        vault = self.cccore.vault_manager.get_vault(vault_name)
        if vault:
            return vault.get_project_path(project_name)
        return None

    def set_current_project(self, vault_name, project_name):
        project_path = self.get_project_path(vault_name, project_name)
        if project_path:
            self.current_project = {
                'name': project_name,
                'path': project_path,
                'vault': vault_name
            }
            return True
        return False
    
    def remove_project(self, name):
        if name in self.projects:
            del self.projects[name]
            if self.current_project == name:
                self.current_project = None
            self.save_projects()
            return True
        return False

    def close_project(self):
        current_project = self.project_selector.currentText()
        if current_project:
            self.save_current_project_state()
            self.current_project = None
            QMessageBox.information(self, "Success", f"Project '{current_project}' closed successfully.")
        else:
            QMessageBox.warning(self, "Error", "No active project to close.")
    
    def rename_project(self, old_name, new_name):
        if old_name in self.projects and new_name not in self.projects:
            self.projects[new_name] = self.projects.pop(old_name)
            if self.current_project == old_name:
                self.current_project = new_name
            self.save_projects()
            return True
        return False

    def set_current_project(self, name):
        if name in self.projects:
            self.current_project = name
            self.add_recent_project(name)
            self.save_projects()
            return True
        return False

    # def get_projects(self):
    #     return list(self.projects.keys())

    def get_current_project(self):
        return self.current_project

    def get_project_path(self, name):
        logging.debug(f"Attempting to get path for project: {name}")
        logging.debug(f"Current projects: {self.projects}")
        if isinstance(self.projects, dict):
            project_data = self.projects.get(name, {})
            if isinstance(project_data, dict):
                path = project_data.get("path")
            elif isinstance(project_data, str):
                path = project_data
            else:
                logging.error(f"Invalid project data for {name}: {project_data}")
                path = None
        else:
            logging.error(f"self.projects is not a dictionary: {self.projects}")
            path = None
        logging.debug(f"Retrieved path: {path}")
        return path

    def get_project_environment(self, name):
        return self.env_manager.get_environment_path(name)

    def add_recent_project(self, project_name):
        if project_name in self.recent_projects:
            self.recent_projects.remove(project_name)
        self.recent_projects.insert(0, project_name)
        self.recent_projects = self.recent_projects[:self.max_recent_projects]  # Keep only the 10 most recent projects
        self.save_projects()

    def get_recent_projects(self):
        self.recent_projects = self.settings_manager.get_value("recent_projects", [])
   
        return self.recent_projects

    def switch_environment(self, project_name, env_name):
        if project_name in self.projects and self.env_manager.get_environment_path(env_name):
            self.projects[project_name]['environment'] = env_name
            self.save_projects()
            return True
        return False

    def switch_project(self, project_name):
        logging.warning(f"Attempting to switch to project: {project_name}")
        if not project_name:
            logging.warning("Attempted to switch to an empty project name")
            return False, "Empty project name"

        if project_name not in self.projects:
            logging.error(f"Project '{project_name}' does not exist")
            return False, "Project does not exist"

        project_path = self.get_project_path(project_name)
        if project_path is None:
            logging.error(f"Failed to get path for project: {project_name}")
            return False, "Failed to get project path"

        if self.set_current_project(project_name):
            self.add_recent_project(project_name)
            self.settings_manager.set_value("last_project", project_name)
            logging.warning(f"Successfully switched to project: {project_name}")
            return True, project_path
        else:
            logging.error(f"Failed to set current project to: {project_name}")
            return False, "Failed to set current project"

    def update_project_config(self, project_name, updated_data):
        project_path = self.get_project_path(project_name)
        if project_path:
            config_file = os.path.join(project_path, 'project_config.json')
            with open(config_file, 'w') as f:
                json.dump(updated_data, f, indent=4)
        else:
            logging.error(f"Project not found: {project_name}")

    def build_project(self, name):
        if name in self.projects:
            project_data = self.projects[name]
            build_command = project_data.get('build_command')
            nix_expression = project_data.get('nix_expression')
            if build_command:
                try:
                    if nix_expression:
                        command = f"nix-shell {nix_expression} --run '{build_command}'"
                    else:
                        command = build_command
                    
                    process_id = self.process_manager.start_process(command, f"Build {name}", cwd=project_data['path'], capture_output=True)
                    
                    if process_id:
                        return True, f"Build process started for '{name}' (PID: {process_id})"
                    else:
                        return False, "Failed to start build process"
                except Exception as e:
                    return False, str(e)
            else:
                return False, "No build command specified"
        return False, "Project not found"

    def run_project(self, name):
        if name in self.projects:
            project_data = self.projects[name]
            run_command = project_data.get('run_command')
            nix_expression = project_data.get('nix_expression')
            if run_command:
                try:
                    if nix_expression:
                        command = f"nix-shell {nix_expression} --run '{run_command}'"
                    else:
                        command = run_command
                    
                    process_id = self.process_manager.start_process(command, f"Run {name}", cwd=project_data['path'])
                    
                    if process_id:
                        return True, f"Project '{name}' is now running (PID: {process_id})"
                    else:
                        return False, "Failed to start run process"
                except Exception as e:
                    return False, str(e)
            else:
                return False, "No run command specified"
        return False, "Project not found"

    
    def configure_build(self):
        current_project = self.get_current_project()
        if current_project:
            build_command, ok = QInputDialog.getText(
                self, "Configure Build", "Enter build command:",
                text=self.build_manager.build_configs.get(current_project, {}).get('build_command', '')
            )
            if ok:
                self.build_manager.set_build_command(current_project, build_command)
                QMessageBox.information(self, "Build Configuration", f"Build command set for project: {current_project}")
            else:
                QMessageBox.warning(self, "Error", "No active project to configure")

    def configure_run(self):
        current_project = self.get_current_project()
        if current_project:
            run_command, ok = QInputDialog.getText(
                self, "Configure Run", "Enter run command:",
                text=self.build_manager.build_configs.get(current_project, {}).get('run_command', '')
            )
            if ok:
                self.build_manager.set_run_command(current_project, run_command)
                QMessageBox.information(self, "Run Configuration", f"Run command set for project: {current_project}")
        else:
            QMessageBox.warning(self, "Error", "No active project to configure")

    def load_project_state(self, project_name):
        open_files = self.settings_manager.get_value(f"open_files_{project_name}", [])
        for file_path in open_files:
            self.editor_manager.open_file(file_path)

    def rename_project(self):
        projects = self.get_projects()
        old_name, ok = QInputDialog.getItem(self, "Rename Project", "Select project to rename:", projects, 0, False)
        if ok and old_name:
            new_name, ok = QInputDialog.getText(self, "Rename Project", "Enter new project name:")
            if ok and new_name:
                if self.rename_project(old_name, new_name):
                    QMessageBox.information(self, "Project Renamed", f"Renamed project from '{old_name}' to '{new_name}'")
                    self.update_project_selector()
                else:
                    QMessageBox.warning(self, "Error", "Failed to rename project. New name may already exist.")

    def open_project(self):
        dialog = QDialog(self.cccore.main_window)
        dialog.setWindowTitle("Open Project")
        layout = QVBoxLayout(dialog)

        many_projects_widget = self.cccore.widget_manager.ManyProjectsManagerWidget(self.cccore)
        layout.addWidget(many_projects_widget)

        many_projects_widget.project_selected.connect(dialog.accept)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            vault_name = many_projects_widget.vault_selector.currentText()
            project_name = many_projects_widget.project_list.currentItem().text()
            self.switch_project(vault_name, project_name)
    
    def show_project_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Project Settings")
        layout = QVBoxLayout(dialog)
        
        # Add project path label
        path_label = QLabel("Project Path:")
        layout.addWidget(path_label)

    def update_project_selector(self):
        self.project_selector.clear()
        self.project_selector.addItems(self.get_projects(self.cccore.vault_manager.get_current_vault()))
        self.project_selector.setCurrentText(self.get_current_project())

    def open_project_as_treeview(self):
        
        pass

    def is_file_in_project_context(self, file_path):
        current_project = self.get_current_project()
        if not current_project:
            return True  # Allow opening files if no project is active
        project_path = os.path.dirname(current_project.path)
        return file_path.startswith(project_path) or "Daily Notes" in file_path

    def handle_file_not_in_context(self, file_path):
        # Implement logic to handle files not in the current project context
        # For example, you could add the file to the current project or create a new project
        pass

    def switch_project(self, vault_name, project_name):
        # Implement the logic to switch to the selected project
        # This might involve updating the current project in the cccore,
        # updating the UI, loading project files, etc.
        self.cccore.vault_manager.set_current_vault(vault_name)
        self.cccore.set_current_project(project_name)
        QMessageBox.information(self.cccore.main_window, "Project Opened", f"Opened project: {project_name} in vault: {vault_name}")

    def get_project_data(self, project_name):
        project_path = self.get_project_path(project_name)
        if project_path:
            config_file = os.path.join(project_path, 'project_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
        return {
            'name': project_name,
            'path': project_path,
            'build_command': '',
            'run_command': '',
            'registered_scripts': []
        }  # Return an empty dict if no data is found
    
        # Add project path input field
        # current_project = self.get_current_project()
        # if current_project:
        #     project_path = self.get_project_path(current_project)
        #     if project_path:
                
        #     else:
        #         QMessageBox.warning(self, "Error", "Failed to open project directory.")
        # else:
        #     QMessageBox.warning(self, "Error", "No active project to open.")
    
   

class ProjectManagerWidget(QWidget):
    def __init__(self, parent, cccore, window):
        super().__init__(parent)
        self.cccore = cccore
        self.window = window  # Store the specific window this widget is associated with
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Use the project selector from the main window
        button = QPushButton("Open Project")
        button.clicked.connect(self.open_project)
        layout.addWidget(button)

        # Project management buttons
        management_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Project")
        self.add_button.clicked.connect(self.add_project)
        management_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Project")
        self.remove_button.clicked.connect(self.remove_project)
        management_layout.addWidget(self.remove_button)

        self.rename_button = QPushButton("Rename Project")
        self.rename_button.clicked.connect(self.rename_project)
        management_layout.addWidget(self.rename_button)

        layout.addLayout(management_layout)

        # Project action buttons
        action_layout = QHBoxLayout()
        self.configure_button = QPushButton("Configure")
        self.configure_button.clicked.connect(self.configure_project)
        action_layout.addWidget(self.configure_button)

        self.build_button = QPushButton("Build")
        self.build_button.clicked.connect(self.build_project)
        action_layout.addWidget(self.build_button)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_project)
        action_layout.addWidget(self.run_button)

        layout.addLayout(action_layout)

        # Set the layout for the widget
        self.setLayout(layout)

    # def update_project_list(self):
    #     self.project_selector.clear()
    #     current_vault = self.window.get_current_vault()
    #     if current_vault:
    #         projects = self.cccore.vault_manager.get_projects(current_vault.name)
    #         self.project_selector.addItems(projects)
        
    def add_project(self):
        vault_name = self.cccore.vault_manager.get_current_vault().name
        if not vault_name:
            QMessageBox.warning(self, "Nope", "Please select a vault first.")
            return

        project_name, ok = QInputDialog.getText(self, "Add Project", "Enter project name:")
        if not ok or not project_name:
            return

        path = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if not path:
            return

        languages = ["Python", "C++", "JavaScript"]
        language, ok = QInputDialog.getItem(self, "Select Language", "Choose project main language:", 
                                            languages, 0, False)
        if not ok:
            return

        default_version = ""
        if language == "Python":
            default_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        version, ok = QInputDialog.getText(self, "Enter Version", "Enter language version:", 
                                           text=default_version)
        if not ok:
            return

        if self.cccore.vault_manager.add_project(vault_name=vault_name, project_name=project_name, project_path=path, language=language, version=version):
            self.cccore.widget_manager.ManyProjectsManagerWidget.update_project_list()
            QMessageBox.information(self, "Success", f"Project '{project_name}' added successfully.")
        else:
            QMessageBox.warning(self, "Error", f"Failed to add project '{project_name}'.")
    def remove_project(self):
        current_project = self.cccore.project_manager.get_current_project()
        if current_project:
            reply = QMessageBox.question(self, "Remove Project", f"Are you sure you want to remove the project '{current_project}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.cccore.project_manager.remove_project(current_project):
                    self.update_project_list()
                    QMessageBox.information(self, "Success", f"Project '{current_project}' removed successfully.")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to remove project '{current_project}'.")

    def rename_project(self):
        old_name = self.cccore.project_manager.get_current_project()
        if old_name:
            new_name, ok = QInputDialog.getText(self, "Rename Project", "Enter new project name:", text=old_name)
            if ok and new_name and new_name != old_name:
                if self.cccore.project_manager.rename_project(old_name, new_name):
                    self.update_project_list()
                    QMessageBox.information(self, "Success", f"Project renamed from '{old_name}' to '{new_name}'.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to rename project. New name may already exist.")

    def configure_project(self):
        current_project = self.cccore.project_manager.get_current_project()
        if current_project:
            project_data = self.cccore.project_manager.get_project_data(current_project)
            dialog = ProjectConfigDialog(current_project, project_data, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_config = dialog.get_config()
                self.cccore.project_manager.update_project_config(current_project, new_config)
                QMessageBox.information(self, "Success", f"Project '{current_project}' configuration updated.")

    def build_project(self):
        current_project = self.cccore.project_manager.get_current_project()
        if current_project:
            success, message = self.cccore.project_manager.build_project(current_project)
            if success:
                QMessageBox.information(self, "Build Success", message)
            else:
                QMessageBox.warning(self, "Build Error", message)

    def run_project(self):
        current_project = self.cccore.project_manager.get_current_project()
        if current_project:
            success, message = self.cccore.project_manager.run_project(current_project)
            if success:
                QMessageBox.information(self, "Run", message)
            else:
                QMessageBox.warning(self, "Run Error", message)

    def on_project_selected(self, project_name):
        if project_name:
            self.cccore.project_manager.set_current_project(project_name)
    def open_project(self):
        if self.cccore.widget_manager.projects_manager_widget:
            selected_project = self.cccore.widget_manager.projects_manager_widget.project_selector.currentText()
            if selected_project:
                self.switch_project(selected_project)
        else:
            QMessageBox.warning(self, "Error", "No project selector, open in main window.")

    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)
class ManyProjectsManagerWidget(QWidget):
    project_selected = pyqtSignal(str, str)  # Signal to emit (vault_name, project_name)

    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Vault selector
        self.vault_selector = QComboBox()
        self.vault_selector.currentTextChanged.connect(self.on_vault_changed)
        layout.addWidget(QLabel("Vault:"))
        layout.addWidget(self.vault_selector)

        # Project list
        self.project_list = QListWidget()
        layout.addWidget(QLabel("Projects:"))
        layout.addWidget(self.project_list)

        # Buttons
        button_layout = QHBoxLayout()
        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self.open_selected_project)
        button_layout.addWidget(self.open_button)
        self.add_button = QPushButton("Add Project")
        self.add_button.clicked.connect(self.add_project)
        self.remove_button = QPushButton("Remove Project")
        self.remove_button.clicked.connect(self.remove_project)
        self.rename_button = QPushButton("Rename Project")
        self.rename_button.clicked.connect(self.rename_project)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.rename_button)
        layout.addLayout(button_layout)

        self.update_vault_selector()

    def update_vault_selector(self):
        self.vault_selector.clear()
        self.vault_selector.addItems(self.cccore.vault_manager.get_vault_names())

    def on_vault_changed(self, vault_name):
        self.update_project_list(vault_name)

    def update_project_list(self, vault_name):
        self.project_list.clear()
        projects = self.cccore.vault_manager.get_projects(vault_name)
        self.project_list.addItems(projects)

    def open_selected_project(self):
        selected_project = self.project_list.currentItem()
        if selected_project:
            project_name = selected_project.text()
            vault_name = self.vault_selector.currentText()
            self.project_selected.emit(vault_name, project_name)
        else:
            QMessageBox.warning(self, "No Project Selected", "Please select a project to open.")

    def add_project(self):
        # Implementation similar to ProjectManagerWidget.add_project()
        pass

    def remove_project(self):
        # Implementation similar to ProjectManagerWidget.remove_project()
        pass

    def rename_project(self):
        # Implementation similar to ProjectManagerWidget.rename_project()
        pass