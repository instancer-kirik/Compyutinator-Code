import os
import json
import logging
from .environment_manager import EnvironmentManager
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, 
                             QInputDialog, QMessageBox, QFileDialog, QDialog, QLabel, QLineEdit, QFormLayout, QProgressBar, QStackedWidget)
from PyQt6.QtCore import Qt
import re
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
import sys
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialogButtonBox
from .project_config import ProjectConfig
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from .project_dashboard import ProjectDashboard
from GUX.dialogs.project_dialogs import ProjectCreationDialog

class ProjectType(Enum):
    LOCAL = "local"
    RESOLVINATOR = "resolvinator"

@dataclass
class BaseProjectAttributes:
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    symbols: Dict[Path, List['CodeSymbol']] = None  # Path is now properly imported
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = {}

@dataclass
class CodeSymbol:
    name: str
    type: str  # 'class', 'function', 'method', 'variable'
    line: int
    column: int
    file_path: Path  # Path is now properly imported
    parent: Optional['CodeSymbol'] = None
    children: List['CodeSymbol'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

@dataclass
class LocalProjectAttributes(BaseProjectAttributes):
    build_command: Optional[str] = None
    run_command: Optional[str] = None
    registered_scripts: List[str] = None
    file_extensions: List[str] = None
    excluded_dirs: List[str] = None
    workspace_path: Optional[str] = None
    
    def __post_init__(self):
        self.registered_scripts = self.registered_scripts or []
        self.file_extensions = self.file_extensions or [".py", ".json", ".yml"]
        self.excluded_dirs = self.excluded_dirs or ["__pycache__", ".git", "venv"]

@dataclass
class ResolvinatorProjectAttributes(BaseProjectAttributes):
    risk_appetite: str = "cautious"  # Changed from float to str with default
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    status: str = "planning"  # Added default status
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.settings = self.settings or {
            "risk_matrix_config": {
                "probability_weights": {
                    "rare": 1,
                    "unlikely": 2,
                    "possible": 3,
                    "likely": 4,
                    "certain": 5
                },
                "impact_weights": {
                    "negligible": 1,
                    "minor": 2,
                    "moderate": 3,
                    "major": 4,
                    "severe": 5
                }
            },
            "notification_preferences": {
                "high_risk_threshold": 12,
                "review_period_days": 30
            }
        }

class Project:
    def __init__(self, project_type: ProjectType, **kwargs):
        self.project_type = project_type
        self.id = kwargs.get('id')
        self.path = kwargs.get('path')
        
        # Initialize appropriate attributes based on project type
        if project_type == ProjectType.LOCAL:
            self.attributes = LocalProjectAttributes(
                name=kwargs.get('name', ''),
                description=kwargs.get('description'),
                status=kwargs.get('status'),
                build_command=kwargs.get('build_command'),
                run_command=kwargs.get('run_command'),
                registered_scripts=kwargs.get('registered_scripts', []),
                file_extensions=kwargs.get('file_extensions', [".py", ".json", ".yml"]),
                excluded_dirs=kwargs.get('excluded_dirs', ["__pycache__", ".git", "venv"]),
                workspace_path=kwargs.get('workspace_path'),
                inserted_at=datetime.now(),
                updated_at=datetime.now()
            )
        else:
            self.attributes = ResolvinatorProjectAttributes(
                name=kwargs.get('name', ''),
                description=kwargs.get('description'),
                status=kwargs.get('status'),
                risk_appetite=kwargs.get('risk_appetite', 0.5),
                start_date=kwargs.get('start_date', datetime.now()),
                target_date=kwargs.get('target_date', datetime.now()),
                completion_date=kwargs.get('completion_date', datetime.now()),
                settings=kwargs.get('settings', {
                    "risk_matrix_config": {
                        "probability_weights": {
                            "rare": 1,
                            "unlikely": 2,
                            "possible": 3,
                            "likely": 4,
                            "certain": 5
                        },
                        "impact_weights": {
                            "negligible": 1,
                            "minor": 2,
                            "moderate": 3,
                            "major": 4,
                            "severe": 5
                        }
                    },
                    "notification_preferences": {
                        "high_risk_threshold": 12,
                        "review_period_days": 30
                    }
                }),
                inserted_at=datetime.now(),
                updated_at=datetime.now()
            )
        self.relationships = kwargs.get('relationships', {})
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary format"""
        if self.project_type == ProjectType.RESOLVINATOR:
            return {
                "id": self.id,
                "type": "project",
                "attributes": {
                    "name": self.attributes.name,
                    "description": self.attributes.description,
                    "status": self.attributes.status,
                    "risk_appetite": self.attributes.risk_appetite,
                    "start_date": self.attributes.start_date.isoformat() if self.attributes.start_date else None,
                    "target_date": self.attributes.target_date.isoformat() if self.attributes.target_date else None,
                    "completion_date": self.attributes.completion_date.isoformat() if self.attributes.completion_date else None,
                    "inserted_at": self.attributes.inserted_at.isoformat() if self.attributes.inserted_at else None,
                    "updated_at": self.attributes.updated_at.isoformat() if self.attributes.updated_at else None
                },
                "relationships": self.relationships
            }
        else:
            return {
                "name": self.attributes.name,
                "path": self.path,
                "type": "local"
            }

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

class ProjectManager:
    project_changed = pyqtSignal(str)
    project_progress_updated = pyqtSignal(str, float)  # New signal for progress updates
    def __init__(self, settings_manager, cccore):
        super().__init__()
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
        self.ws_client = None
        self.project_types = {
            "local": self.create_local_project,
            "resolvinator": self.create_resolvinator_project
        }
        self.lsp_manager = cccore.lsp_manager  # Use LSP for better symbol detection
       # self.load_projects()
        self.update_project_selector()
        logging.warning(f"Loaded projects: {self.projects}")
        self.project_config_filename = "project_config.json"
        self.load_current_project()  # Add this line to load the current project on initialization
        self.integration_testing_manager = None

        # Add new attributes for enhanced project tracking
        self.active_projects = {}  # Dictionary to track multiple active projects
        self.project_dashboards = {}  # Store dashboard instances
        self.project_progress = {}  # Track project completion progress
        
    def update_project_symbols(self, project_name: str):
        """Update symbols for all code files in a project"""
        project = self.projects.get(project_name)
        if not project:
            return
        
        project_path = Path(project.get('path', ''))
        if not project_path.exists():
            return
            
        for root, _, files in os.walk(project_path):
            for file in files:
                file_path = Path(root) / file
                if self._is_code_file(file_path):
                    self._parse_file_symbols(file_path, project)
    
    def _is_code_file(self, file_path: Path) -> bool:
        """Check if file is a code file based on project settings"""
        project = self.get_current_project()
        if not project:
            return False
            
        extensions = project.get('file_extensions', ['.py', '.js', '.cpp'])
        return file_path.suffix in extensions
    
    def _parse_file_symbols(self, content: str, file_path: Path) -> List[CodeSymbol]:
        """Parse a file's content for code symbols and their references"""
        symbols = []
        lines = content.splitlines()
        current_class = None
        symbol_stack = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            indent = len(line) - len(stripped)
            
            # Track scope using indentation
            while symbol_stack and symbol_stack[-1][1] >= indent:
                symbol_stack.pop()
            
            if stripped.startswith('class '):
                class_name = stripped[6:].split('(')[0].strip(':').strip()
                current_class = CodeSymbol(
                    name=class_name,
                    type='class',
                    line=i + 1,
                    column=indent,
                    file_path=file_path,
                    parent=symbol_stack[-1][0] if symbol_stack else None
                )
                symbols.append(current_class)
                symbol_stack.append((current_class, indent))
                
            elif stripped.startswith('def '):
                func_name = stripped[4:].split('(')[0].strip()
                method = CodeSymbol(
                    name=func_name,
                    type='method' if current_class else 'function',
                    line=i + 1,
                    column=indent,
                    file_path=file_path,
                    parent=symbol_stack[-1][0] if symbol_stack else None
                )
                if symbol_stack:
                    symbol_stack[-1][0].children.append(method)
                symbols.append(method)
                symbol_stack.append((method, indent))
                
            # Add reference tracking
            else:
                # Look for symbol references in the line
                for symbol in symbols:
                    if symbol.name in stripped:
                        # Add reference to both symbols
                        referenced_symbol = next((s for s in symbols if s.name in stripped), None)
                        if referenced_symbol and referenced_symbol != symbol:
                            if not hasattr(symbol, 'references'):
                                symbol.references = []
                            symbol.references.append(referenced_symbol)
        
        return symbols
    
    def get_file_symbols(self, file_path: Path) -> List[CodeSymbol]:
        """Get symbols for a file, either from cache or by parsing"""
        if hasattr(self, 'symbol_manager'):
            return self.symbol_manager.get_file_symbols(file_path)
        return []

    def create_project(self, vault_name: str, project_name: str, project_path: str, project_type: ProjectType, **kwargs) -> bool:
        """Create a new project of specified type"""
        try:
            if project_type == ProjectType.LOCAL:
                return self.create_local_project(
                    Project(
                        project_type=ProjectType.LOCAL,
                        name=project_name,
                        path=project_path,
                        description=kwargs.get('description', ''),
                        build_command=kwargs.get('build_command'),
                        run_command=kwargs.get('run_command'),
                        registered_scripts=kwargs.get('registered_scripts', []),
                        file_extensions=kwargs.get('file_extensions'),
                        excluded_dirs=kwargs.get('excluded_dirs'),
                        workspace_path=kwargs.get('workspace_path'),
                        inserted_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                )
            else:
                return self.create_resolvinator_project(
                    Project(
                        project_type=ProjectType.RESOLVINATOR,
                        name=project_name,
                        path=project_path,
                        description=kwargs.get('description', ''),
                        status='planning',
                        risk_appetite=kwargs.get('risk_appetite', 0.5),
                        start_date=datetime.now(),
                        settings=kwargs.get('settings'),
                        inserted_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                )
        except Exception as e:
            logging.error(f"Error creating project: {e}")
            return False
    
    def set_current_project(self, project: Project):
        """Set the current active project"""
        self.active_project = project
        
        # Subscribe to WebSocket updates if it's a Resolvinator project
        if (project.project_type == ProjectType.RESOLVINATOR and 
            self.ws_client and project.id):
            self.ws_client.subscribe_to_project(project.id)
            
        self.project_changed.emit(project.attributes.name)
        
    def handle_project_update(self, project_data: dict):
        """Handle project updates from WebSocket"""
        if not self.active_project:
            return
            
        if project_data.get('id') == self.active_project.id:
            # Update project attributes
            for key, value in project_data.get('attributes', {}).items():
                setattr(self.active_project.attributes, key, value)
            
            # Update relationships if included
            if 'relationships' in project_data:
                self.active_project.relationships = project_data['relationships']
                
            self.project_updated.emit(self.active_project)
            
    def get_project_risks(self, project_id: int) -> List[Dict]:
        """Get risks for a Resolvinator project"""
        if self.ws_client:
            return self.ws_client.get_project_risks(project_id)
        return []
        
    def create_local_project(self, project: Project) -> bool:
        """Create a local project with directory structure"""
        try:
            full_path = os.path.join(project.path, project.attributes.name)
            os.makedirs(full_path, exist_ok=True)
            
            # Save basic project config
            config_path = os.path.join(full_path, self.project_config_filename)
            config = project.to_dict()
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            project.path = full_path  # Update project path with full path
            return True
            
        except Exception as e:
            logging.error(f"Error creating local project structure: {e}")
            return False

    def create_resolvinator_project(self, vault_name: str, project_name: str, project_path: str, language: Optional[str] = None, version: Optional[str] = None) -> bool:
        """Create a Resolvinator-type project"""
        try:
            # Create project instance first
            project = Project(
                project_type=ProjectType.RESOLVINATOR,
                name=project_name,
                path=project_path,
                description="",
                status="planning",
                risk_appetite=0.5,
                start_date=datetime.now(),
                inserted_at=datetime.now(),
                updated_at=datetime.now()
            )

            # Create basic project structure
            success = self.create_local_project(project)
            if not success:
                return False

            # Add Resolvinator-specific configuration
            project_config = project.to_dict()
            project_config.update({
                "settings": {
                    "risk_matrix_config": {
                        "probability_weights": {
                            "rare": 1,
                            "unlikely": 2,
                            "possible": 3,
                            "likely": 4,
                            "certain": 5
                        },
                        "impact_weights": {
                            "negligible": 1,
                            "minor": 2,
                            "moderate": 3,
                            "major": 4,
                            "severe": 5
                        }
                    },
                    "notification_preferences": {
                        "high_risk_threshold": 12,
                        "review_period_days": 30
                    }
                },
                "language": language,
                "version": version
            })

            # Save Resolvinator config
            config_path = os.path.join(project_path, 'resolvinator_config.json')
            with open(config_path, 'w') as f:
                json.dump(project_config, f, indent=2)

            # Notify WebSocket if connected
            if self.ws_client and self.ws_client.auth_state.get("authenticated"):
                self.ws_client.send_message({
                    "topic": "project",
                    "event": "project:create",
                    "payload": project_config
                })

            return True

        except Exception as e:
            logging.error(f"Error creating Resolvinator project: {e}")
            return False

    def load_project(self, project_path: str) -> Optional[Project]:
        """Load project from path with proper error handling"""
        try:
            # Determine project type
            project_type = self.get_project_type(project_path)
            if not project_type:
                return None
                
            # Load config
            config_file = self.get_config_filename(project_type)
            config_path = os.path.join(project_path, config_file)
            
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                
            # Create appropriate project instance
            project = Project(
                project_type=ProjectType(project_type),
                path=project_path,
                **config_data
            )
            
            return project
            
        except Exception as e:
            logging.error(f"Error loading project: {e}")
            return None

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
    def add_project(self):
        """Enhanced add_project dialog with project type selection"""
        vault_name = self.cccore.vault_manager.get_current_vault().name
        if not vault_name:
            QMessageBox.warning(self, "Error", "Please select a vault first.")
            return

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Project")
        layout = QVBoxLayout(dialog)

        # Project type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Project Type:")
        type_combo = QComboBox()
        type_combo.addItems([t.value for t in ProjectType])
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)

        # Project details
        form_layout = QFormLayout()
        
        # Name input
        name_input = QLineEdit()
        form_layout.addRow("Project Name:", name_input)
        
        # Path input with browse button
        path_layout = QHBoxLayout()
        path_input = QLineEdit()
        browse_button = QPushButton("Browse")
        path_layout.addWidget(path_input)
        path_layout.addWidget(browse_button)
        form_layout.addRow("Project Path:", path_layout)
        
        # Language selection
        language_combo = QComboBox()
        language_combo.addItems(["Python", "JavaScript", "Java", "C++", "Other"])
        form_layout.addRow("Language:", language_combo)
        
        # Version input
        version_input = QLineEdit()
        version_input.setPlaceholderText("e.g., 1.0.0")
        form_layout.addRow("Version:", version_input)
        
        layout.addLayout(form_layout)

        def browse_path():
            path = QFileDialog.getExistingDirectory(dialog, "Select Project Directory")
            if path:
                path_input.setText(path)

        browse_button.clicked.connect(browse_path)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            project_type = ProjectType(type_combo.currentText())
            project_data = {
                "name": name_input.text(),
                "path": path_input.text(),
                "type": project_type.value,
                "language": language_combo.currentText(),
                "version": version_input.text()
            }
            
            success = self.create_project(
                vault_name=vault_name,
                project_name=project_data["name"],
                project_path=project_data["path"],
                project_type=project_type,
                **project_data
            )
            
            if success:
                QMessageBox.information(self, "Success", f"Project '{project_data['name']}' created successfully.")
                return True
            else:
                QMessageBox.warning(self, "Error", f"Failed to create project '{project_data['name']}'.")
                return False

    def get_projects(self, vault_name):
        vault = self.cccore.vault_manager.get_vault(vault_name)
        if vault:
            return vault.get_project_names()
        return []

    def get_many_projects(self):
        many_projects = []
        for vault in self.cccore.vault_manager.vaults.values():
            many_projects.extend(vault.get_project_names())
        return many_projects

    def get_project_type(self, project_name):
        """Get the type of a project"""
        project_path = self.get_project_path(project_name)
        if not project_path:
            return None

        config_path = os.path.join(project_path, 'resolvinator_config.json')
        if os.path.exists(config_path):
            return "resolvinator"
        return "local"

    def load_project_data(self, project_name):
        """Enhanced project data loading to handle both types"""
        project_type = self.get_project_type(project_name)
        project_path = self.get_project_path(project_name)
        
        if project_type == "resolvinator":
            config_path = os.path.join(project_path, 'resolvinator_config.json')
            try:
                with open(config_path, 'r') as f:
                    resolvinator_data = json.load(f)
                return {**self.get_project_data(project_name), **resolvinator_data}
            except Exception as e:
                logging.error(f"Error loading Resolvinator project data: {e}")
                return self.get_project_data(project_name)
        
        return self.get_project_data(project_name)
    
    def set_current_project(self, project: Project):
        """Set the current active project with proper state management"""
        try:
            # Save previous project state if exists
            if self.active_project:
                self.save_project_state(self.active_project.attributes.name)
            
            # Set new active project
            self.active_project = project
            
            # Load project state
            self.load_project_state(project.attributes.name)
            
            # Setup WebSocket if needed
            if (project.project_type == ProjectType.RESOLVINATOR and 
                self.ws_client and project.id):
                self.ws_client.subscribe_to_project(project.id)
                
            self.project_changed.emit(project.attributes.name)
            
        except Exception as e:
            logging.error(f"Error setting current project: {e}")
    
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

    def get_current_project(self):
        return self.current_project
   
    def get_project_path(self, project_name=None):
        if project_name is None:
            project_name = self.get_current_project()
        
        if project_name:
            for vault in self.cccore.vault_manager.vaults.values():
                project = vault.get_project(project_name)
                if project:
                    return project.path
        
        logging.warning(f"No path found for project: {project_name}")
        return None

   
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
        project_path = self.get_project_path(project_name)
        if not project_path:
            return False

        try:
            # Load project configuration
            config = ProjectConfig.load(project_path)
            if not config:
                logging.error(f"No configuration found for project: {project_name}")
                return False

            # Handle WebSocket subscription
            if self.current_project and self.current_project.websocket_enabled:
                self.ws_client.unsubscribe_from_project(self.current_project.name)

            self.current_project = config

            if config.websocket_enabled and self.ws_client:
                self.ws_client.subscribe_to_project(config.name)

            self.project_changed.emit(project_name)
            return True

        except Exception as e:
            logging.error(f"Error switching project: {e}")
            return False

    def update_project_config(self, project_name: str, updated_data: dict) -> bool:
        """Update project configuration with validation"""
        try:
            project_path = self.get_project_path(project_name)
            if not project_path:
                return False
                
            # Get current config
            config_file = self.get_config_filename(self.get_project_type(project_name))
            config_path = os.path.join(project_path, config_file)
            
            # Load existing config
            with open(config_path, 'r') as f:
                current_config = json.load(f)
                
            # Update config
            current_config.update(updated_data)
            
            # Validate config
            if not self.validate_project_config(current_config):
                return False
                
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(current_config, f, indent=4)
                
            return True
            
        except Exception as e:
            logging.error(f"Error updating project config: {e}")
            return False

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

    def find_file_in_current_project(self, file_name):
        if not self.current_project:
            return None
        
        project_path = self.current_project.get('path')
        if not project_path:
            return None
        
        for root, dirs, files in os.walk(project_path):
            if file_name in files:
                return os.path.join(root, file_name)
        
        return None

    def get_relative_path_in_project(self, file_path):
        if not self.current_project:
            return file_path
        
        project_path = self.current_project.get('path')
        if not project_path:
            return file_path
        
        try:
            return os.path.relpath(file_path, project_path)
        except ValueError:  # This occurs if the file is on a different drive than the project
            return file_path

    def is_file_in_project_context(self, file_path):
        current_project = self.get_current_project()
        if not current_project:
            return True  # Allow opening files if no project is active
        project_path = current_project.get('path')
        if not project_path:
            return True
        return os.path.commonpath([file_path, project_path]) == project_path or "Daily Notes" in file_path

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
            'registered_scripts': [],
            'file_extensions': ['.py', '.json', '.yml'],
            'excluded_dirs': ['__pycache__', '.git', 'venv'],
            'symbols': {},
            'status': None,
            'description': None,
            'inserted_at': datetime.now(),
            'updated_at': datetime.now(),
            'workspace_path': None,
            'risk_appetite': None,
            'settings': {
                'risk_matrix_config': {
                    'probability_weights': {
                        'rare': 1,
                        'unlikely': 2,
                        'possible': 3,
                        'likely': 4,
                        'certain': 5
                    },
                    'impact_weights': {
                        'negligible': 1,
                        'minor': 2,
                        'moderate': 3,
                        'major': 4,
                        'severe': 5
                    }
                }
            }
        }

    def load_current_project(self):
        current_project = self.settings_manager.get_value("current_project")
        if current_project:
            self.set_current_project(current_project)
        else:
            # If no current project is set, try to set the first available project
            projects = self.get_many_projects()
            if projects:
                self.set_current_project(projects[0])
    
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
        self.project_list = QListWidget()
        self.setup_ui()

    def refresh_projects(self):
        """Refresh the projects list"""
        self.project_list.clear()
        if hasattr(self.cccore, 'project_manager'):
            # Change get_all_projects to get_many_projects
            projects = self.cccore.project_manager.get_many_projects()
            for project in projects:
                self.project_list.addItem(project)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Vault selector
        self.vault_selector = QComboBox()
        self.vault_selector.currentTextChanged.connect(self.on_vault_changed)
        layout.addWidget(QLabel("Vault:"))
        layout.addWidget(self.vault_selector)

        # Project list
        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self.open_selected_project)  # Fixed connection
        layout.addWidget(self.project_list)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Project management buttons
        self.add_project_btn = QPushButton("Add Project")
        self.remove_project_btn = QPushButton("Remove Project")
        self.open_project_btn = QPushButton("Open Project")
        self.dashboard_btn = QPushButton("Project Dashboard")  # Add dashboard button
        
        # Connect signals
        self.add_project_btn.clicked.connect(self.show_project_dialog)
        self.remove_project_btn.clicked.connect(self.remove_project)
        self.open_project_btn.clicked.connect(self.open_selected_project)
        self.dashboard_btn.clicked.connect(self.show_dashboard)  # Connect dashboard button
        
        # Add buttons to layout
        button_layout.addWidget(self.add_project_btn)
        button_layout.addWidget(self.remove_project_btn)
        button_layout.addWidget(self.open_project_btn)
        button_layout.addWidget(self.dashboard_btn)
        
        layout.addLayout(button_layout)
        
        # Refresh project list
        self.refresh_projects()

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

    def show_project_dialog(self):
        """Show project creation dialog"""
        dialog = ProjectCreationDialog(self.cccore, self)
        if dialog.exec():
            self.update_project_list()

    def remove_project(self):
        """Remove the selected project"""
        current_item = self.project_list.currentItem()
        if current_item:
            project_name = current_item.text()
            self.cccore.project_manager.remove_project(project_name)
            self.update_project_list()

    def rename_project(self):
        # Implementation similar to ProjectManagerWidget.rename_project()
        pass

    def show_dashboard(self):
        """Show dashboard for selected project"""
        try:
            current_item = self.project_list.currentItem()
            if current_item:
                project_name = current_item.text()
                dashboard = ProjectDashboard(self.parent(), self.cccore)
                dashboard.update_project_info(project_name)
                
                # Add to tab widget
                if hasattr(self.cccore.widget_manager, 'tab_widget'):
                    tab_widget = self.cccore.widget_manager.tab_widget
                    tab_widget.addTab(dashboard, f"Dashboard - {project_name}")
                    tab_widget.setCurrentWidget(dashboard)
            else:
                QMessageBox.warning(self, "No Project", 
                                  "Please select a project first.")
        except Exception as e:
            logging.error(f"Error showing project dashboard: {e}")

    def initialize_integration_testing(self):
        """Initialize the integration testing manager for the current project"""
        from GUX.widgets.integration_test_op import IntegrationTestingManager
        self.integration_testing_manager = IntegrationTestingManager(self)
        return self.integration_testing_manager

    def get_integration_testing_manager(self):
        """Get or create the integration testing manager"""
        if not self.integration_testing_manager:
            self.initialize_integration_testing()
        return self.integration_testing_manager

    def switch_project(self, vault_name, project_name):
        # ... (existing code) ...
        
        # Update integration testing manager
        if self.integration_testing_manager:
            self.integration_testing_manager.load_project_checklist()

    def setup_menu(self):
        # Project Menu
        project_menu = self.menuBar().addMenu("&Project")
        
        # ... (existing project menu items) ...
        
        project_menu.addSeparator()
        
        # Add Dashboard action to Project menu
        dashboard_action = project_menu.addAction("&Dashboard")
        dashboard_action.triggered.connect(self.show_project_dashboard)
        
        # Testing submenu
        testing_menu = project_menu.addMenu("&Testing")
        
        integration_test_action = testing_menu.addAction("&Integration Testing")
        integration_test_action.triggered.connect(self.show_integration_testing)
        
        unit_test_action = testing_menu.addAction("&Unit Testing")
        unit_test_action.triggered.connect(self.show_unit_testing)
        
        testing_menu.addSeparator()
        
        test_report_action = testing_menu.addAction("Generate Test &Report")
        test_report_action.triggered.connect(self.generate_test_report)

    def show_integration_testing(self):
        if not hasattr(self, '_integration_testing_window'):
            self._integration_testing_window = self.get_integration_testing_manager()
        self._integration_testing_window.show()
        self._integration_testing_window.raise_()

    def show_unit_testing(self):
        # TODO: Implement unit testing window
        pass

    def generate_test_report(self):
        if hasattr(self, '_integration_testing_window'):
            self._integration_testing_window.generate_report()

    def show_project_dashboard(self):
        """Show the project dashboard for the current project"""
        if not hasattr(self, '_dashboard'):
            from .project_dashboard import ProjectDashboard
            self._dashboard = ProjectDashboard(self.cccore)
        
        current_project = self.get_current_project()
        if current_project:
            self._dashboard.update_project_info(current_project)
        
        self._dashboard.show()
        self._dashboard.raise_()

    def update_dashboard(self):
        """Update the dashboard if it's open"""
        if hasattr(self, '_dashboard') and self._dashboard.isVisible():
            current_project = self.get_current_project()
            if current_project:
                self._dashboard.update_project_info(current_project)

    def create_project_structure(self, project_name: str, project_type: str) -> bool:
        """Create a new project with enhanced structure"""
        try:
            project_path = self.get_project_path(project_name)
            
            # Create project directories
            directories = {
                'notes': 'Markdown notes',
                'tasks': 'Task tracking',
                'docs': 'Documentation',
                'assets': 'Project assets',
                'scripts': 'Project scripts',
                'config': 'Configuration files',
                'data': 'Project data',
                'stories': {
                    'personas': 'User persona definitions and profiles',
                    'journeys': 'User journey maps and flows',
                    'scenarios': 'Use case scenarios and stories',
                    'feedback': 'User feedback and testimonials'
                },
                'marketing': {
                    'images': {
                        'brand': 'Brand identity assets',
                        'screenshots': 'Product screenshots',
                        'social': 'Social media graphics',
                        'banners': 'Marketing banners'
                    },
                    'videos': {
                        'demos': 'Product demonstrations',
                        'tutorials': 'How-to guides',
                        'promos': 'Promotional content'
                    },
                    'copy': {
                        'descriptions': 'Product descriptions',
                        'taglines': 'Marketing taglines',
                        'press_releases': 'Press materials'
                    },
                    'presentations': {
                        'pitch_decks': 'Investor presentations',
                        'product_demos': 'Product demonstrations'
                    },
                    'research': {
                        'market_analysis': 'Market research data',
                        'user_personas': 'Target audience profiles',
                        'competitors': 'Competitor analysis'
                    },
                    'archetypes': {
                        'brand_archetypes': 'Brand personality definitions',
                        'user_archetypes': 'User personality profiles'
                    },
                    'charts': {
                        'metrics': 'Performance metrics',
                        'growth': 'Growth analytics',
                        'analytics': 'Usage statistics'
                    },
                    'assets': {
                        'logos': 'Brand logos',
                        'icons': 'UI/Brand icons',
                        'fonts': 'Brand typography'
                    },
                    'seo': {
                        'keywords': 'Keyword research and mapping',
                        'metadata': 'Meta descriptions and titles',
                        'analytics': 'SEO performance tracking',
                        'content': {
                            'snippets': 'Rich snippets and structured data',
                            'schemas': 'Schema.org markup templates',
                            'sitemap': 'XML sitemaps and URL structure'
                        },
                        'backlinks': 'Backlink strategy and tracking',
                        'competitors': 'Competitor SEO analysis',
                        'reports': 'SEO audit reports and metrics'
                    },
                },
                'requirements': {
                    'business': 'Business requirements and objectives',
                    'technical': 'Technical specifications and constraints',
                    'functional': 'Functional requirements and features',
                    'security': 'Security requirements and compliance',
                    'performance': 'Performance requirements and metrics',
                    'integrations': 'Third-party integration requirements'
                },
                'contacts': {
                    'team': 'Project team contacts and roles',
                    'stakeholders': 'Project stakeholder information',
                    'vendors': 'Third-party vendor contacts',
                    'clients': 'Client contact information',
                    'support': 'Support team contacts'
                },
                'meta': {
                    'roadmap': 'Project roadmap and milestones',
                    'budget': 'Budget tracking and forecasts',
                    'risks': 'Risk assessment and mitigation',
                    'decisions': 'Decision log and rationale',
                    'meetings': 'Meeting notes and action items',
                    'reviews': 'Project reviews and retrospectives'
                }
            }

            def create_directory_structure(base_path, structure, depth=0):
                if isinstance(structure, dict):
                    for name, content in structure.items():
                        dir_path = os.path.join(base_path, name)
                        os.makedirs(dir_path, exist_ok=True)
                        
                        # Create README for each directory
                        readme_content = f"# {name.title()}\n\n"
                        if isinstance(content, dict):
                            readme_content += "## Contents\n\n"
                            for subdir, desc in content.items():
                                readme_content += f"- **{subdir}**: {desc}\n"
                            create_directory_structure(dir_path, content, depth + 1)
                        else:
                            readme_content += f"{content}\n"
                        
                        with open(os.path.join(dir_path, 'README.md'), 'w') as f:
                            f.write(readme_content)

            # Create directory structure
            create_directory_structure(project_path, directories)
            readme_template = f"""# {project_name}

## Overview
Project Type: {project_type}
Created: {datetime.now().strftime('%Y-%m-%d')}

## Quick Links
- [Tasks](tasks/README.md) - Project tasks and milestones
- [Documentation](docs/README.md) - Technical documentation
- [Project Notes](notes/README.md) - Development notes and updates
- [Stories](stories/README.md) - User stories and scenarios
- [Marketing](marketing/README.md) - Brand and marketing assets
- [SEO](marketing/seo/README.md) - Search engine optimization

## Project Structure
{project_name}/
├── notes/          # Project notes and documentation
├── tasks/          # Task tracking and management
├── docs/           # Technical documentation
├── assets/         # Project assets and resources
├── scripts/        # Project scripts and tools
├── config/         # Configuration files
├── data/          # Project data files
├── stories/        # User stories and scenarios
│   ├── personas/   # User persona definitions
│   ├── journeys/   # User journey maps
│   └── scenarios/  # Use case scenarios
└── marketing/      # Marketing and brand assets
    ├── images/     # Visual assets
    │   ├── brand/  # Brand identity assets
    │   ├── social/ # Social media graphics
    │   └── promo/  # Promotional materials
    ├── copy/       # Marketing text and content
    ├── research/   # Market analysis and research
    ├── archetypes/ # Brand and user archetypes
    └── seo/        # Search engine optimization
        ├── keywords/     # Keyword research and mapping
        ├── metadata/     # Meta descriptions and titles
        ├── content/      # SEO content templates
        │   ├── snippets/ # Rich snippets
        │   └── schemas/  # Schema markup
        ├── analytics/    # SEO performance data
        └── reports/      # SEO audits and reports

## Brand Story
[Brief description of the project's purpose and vision]

## Target Audience
- Primary: [Describe primary user]
- Secondary: [Describe secondary user]

## SEO Strategy
### Keywords
- Primary: [Main keyword]
- Secondary: [Supporting keywords]
- Long-tail: [Specific phrases]

### Content Pillars
1. [Main topic area]
2. [Secondary topic area]
3. [Additional topic area]

### Technical SEO Checklist
- [ ] Configure meta descriptions
- [ ] Implement schema markup
- [ ] Setup XML sitemap
- [ ] Configure robots.txt
- [ ] Setup analytics tracking
- [ ] Mobile optimization
- [ ] Page speed optimization

## Getting Started
1. Review the project documentation in `docs/`
2. Check current tasks in `tasks/`
3. Understand user stories in `stories/`
4. Review brand guidelines in `marketing/brand/`
5. Configure SEO settings in `marketing/seo/`

## Development
- Language: [Primary language]
- Framework: [Main framework]
- Dependencies: [Key dependencies]

## Recent Updates
- Project created on {datetime.now().strftime('%Y-%m-%d')}

## Contributing
[Brief contribution guidelines]

## License
[License information]
"""

            # Create brand archetype template
            archetype_path = os.path.join(project_path, 'marketing/archetypes/brand_archetypes')
            archetype_template = """# Brand Archetypes

## Primary Archetype
- Name: 
- Characteristics:
- Values:
- Voice and Tone:
- Visual Elements:

## Secondary Archetypes
1. Name:
   - Purpose:
   - Traits:
   - Expression:

2. Name:
   - Purpose:
   - Traits:
   - Expression:

## Brand Personality Matrix
- Professional <-> Casual
- Traditional <-> Modern
- Serious <-> Playful
- Technical <-> Accessible

## Anti-Archetypes
- What we're not:
- Traits to avoid:
- Voice to avoid:

## Implementation Guidelines
- Communication Style:
- Visual Expression:
- Content Tone:
- Customer Interaction:
"""
            
            with open(os.path.join(archetype_path, 'brand_archetype_template.md'), 'w') as f:
                f.write(archetype_template)

            # Create SEO config file
            seo_config_template = """{
    "seo_config": {
        "site_name": "",
        "default_title_template": "%s | Your Brand",
        "default_description": "",
        "default_keywords": [],
        "social_media": {
            "twitter_card": "summary_large_image",
            "twitter_site": "@yourbrand",
            "og_type": "website",
            "og_site_name": "Your Brand"
        },
        "structured_data": {
            "organization": {
                "@type": "Organization",
                "name": "",
                "url": "",
                "logo": ""
            }
        },
        "tracking": {
            "google_analytics_id": "",
            "google_search_console": "",
            "bing_webmaster": ""
        }
    }
}
"""
            seo_config_path = os.path.join(project_path, 'marketing/seo/config.json')
            with open(seo_config_path, 'w') as f:
                f.write(seo_config_template)

            with open(os.path.join(project_path, 'project_readme.md'), 'w') as f:
                f.write(readme_template)
                
            requirements_template = """# Project Requirements

## Business Requirements
- [ ] Market analysis completed
- [ ] Business objectives defined
- [ ] Success metrics established
- [ ] Budget constraints identified
- [ ] Timeline requirements set

## Technical Requirements
### Infrastructure
- [ ] Hosting requirements
- [ ] Database requirements
- [ ] Security requirements
- [ ] Scalability needs
- [ ] Backup/recovery requirements

### Performance
- [ ] Load time targets
- [ ] Concurrent user expectations
- [ ] Resource usage limits
- [ ] Availability requirements
- [ ] Response time goals

### Integration Requirements
- [ ] Third-party services
- [ ] API requirements
- [ ] Data exchange formats
- [ ] Authentication methods
- [ ] Webhook requirements

## Compliance Requirements
- [ ] Data protection standards
- [ ] Industry regulations
- [ ] Security certifications
- [ ] Accessibility requirements
- [ ] Legal requirements

## Dependencies
- [ ] External systems
- [ ] Third-party libraries
- [ ] Development tools
- [ ] Testing tools
- [ ] Deployment requirements
"""

            contacts_template = """# Project Contacts

## Team Members
| Role | Name | Email | Phone | Time Zone |
|------|------|-------|-------|-----------|
| Project Manager | | | | |
| Tech Lead | | | | |
| Developer | | | | |
| Designer | | | | |

## Stakeholders
| Role | Organization | Name | Email | Priority |
|------|--------------|------|-------|----------|
| | | | | |

## Vendors
| Service | Company | Contact | Email | Contract # |
|---------|----------|---------|-------|------------|
| | | | | |

## Emergency Contacts
| Situation | Name | Role | Phone | Email |
|-----------|------|------|-------|-------|
| Technical Emergency | | | | |
| Security Incident | | | | |
| Service Outage | | | | |

## Communication Preferences
| Contact | Preferred Method | Best Time | Frequency |
|---------|-----------------|------------|-----------|
| | | | |
"""

        # Update README template with new sections
            readme_template = f"""# {project_name}

## Requirements Overview
- [Business Requirements](requirements/business/README.md)
- [Technical Requirements](requirements/technical/README.md)
- [Security Requirements](requirements/security/README.md)
- [Integration Requirements](requirements/integrations/README.md)

## Project Contacts
- [Team Directory](contacts/team/README.md)
- [Stakeholder Registry](contacts/stakeholders/README.md)
- [Vendor Contacts](contacts/vendors/README.md)

## Project Metadata
- [Project Roadmap](meta/roadmap/README.md)
- [Risk Register](meta/risks/README.md)
- [Decision Log](meta/decisions/README.md)
- [Meeting Notes](meta/meetings/README.md)

## Dependencies
### Required Services
- [List of required services]

### Development Dependencies
- [List of development tools]

### External Integrations
- [List of external integrations]

## Environment Setup
1. [Development environment setup steps]
2. [Testing environment configuration]
3. [Production deployment requirements]

## Monitoring & Metrics
- Performance Metrics
- User Analytics
- Error Tracking
- Usage Statistics

## Support & Maintenance
- Support Contact: [contact information]
- Bug Reporting Process: [process description]
- Update Schedule: [schedule information]
- Backup Strategy: [backup details]

"""

           
            # Create directory structure (using existing directories dict)
            create_directory_structure(project_path, directories)
            
            # Define and write templates
            templates = {
                'requirements/README.md': requirements_template,
                'contacts/README.md': contacts_template,
                'marketing/archetypes/brand_archetypes/brand_archetype_template.md': archetype_template,
                'marketing/seo/config.json': seo_config_template,
                'README.md': self.generate_readme_template(project_name, project_type)
            }

            # Write all templates
            for file_path, content in templates.items():
                full_path = os.path.join(project_path, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)

            return True

        except Exception as e:
            logging.error(f"Error creating project structure: {e}")
            return False

    def generate_readme_template(self, project_name: str, project_type: str) -> str:
        """Generate the main README template"""
        return f"""# {project_name}

## Overview
Project Type: {project_type}
Created: {datetime.now().strftime('%Y-%m-%d')}

## Quick Links
- [Tasks](tasks/README.md) - Project tasks and milestones
- [Documentation](docs/README.md) - Technical documentation
- [Project Notes](notes/README.md) - Development notes and updates
- [Stories](stories/README.md) - User stories and scenarios
- [Marketing](marketing/README.md) - Brand and marketing assets
- [SEO](marketing/seo/README.md) - Search engine optimization

## Project Structure
{project_name}/
├── notes/          # Project notes and documentation
├── tasks/          # Task tracking and management
├── docs/           # Technical documentation
├── assets/         # Project assets and resources
├── scripts/        # Project scripts and tools
├── config/         # Configuration files
├── data/          # Project data files
├── stories/        # User stories and scenarios
│   ├── personas/   # User persona definitions
│   ├── journeys/   # User journey maps
│   └── scenarios/  # Use case scenarios
└── marketing/      # Marketing and brand assets
    ├── images/     # Visual assets
    │   ├── brand/  # Brand identity assets
    │   ├── social/ # Social media graphics
    │   └── promo/  # Promotional materials
    ├── copy/       # Marketing text and content
    ├── research/   # Market analysis and research
    ├── archetypes/ # Brand and user archetypes
    └── seo/        # Search engine optimization
        ├── keywords/     # Keyword research and mapping
        ├── metadata/     # Meta descriptions and titles
        ├── content/      # SEO content templates
        │   ├── snippets/ # Rich snippets
        │   └── schemas/  # Schema markup
        ├── analytics/    # SEO performance data
        └── reports/      # SEO audits and reports

## Brand Story
[Brief description of the project's purpose and vision]

## Target Audience
- Primary: [Describe primary user]
- Secondary: [Describe secondary user]

## SEO Strategy
### Keywords
- Primary: [Main keyword]
- Secondary: [Supporting keywords]
- Long-tail: [Specific phrases]

### Content Pillars
1. [Main topic area]
2. [Secondary topic area]
3. [Additional topic area]

### Technical SEO Checklist
- [ ] Configure meta descriptions
- [ ] Implement schema markup
- [ ] Setup XML sitemap
- [ ] Configure robots.txt
- [ ] Setup analytics tracking
- [ ] Mobile optimization
- [ ] Page speed optimization

## Getting Started
1. Review the project documentation in `docs/`
2. Check current tasks in `tasks/`
3. Understand user stories in `stories/`
4. Review brand guidelines in `marketing/brand/`
5. Configure SEO settings in `marketing/seo/`

## Development
- Language: [Primary language]
- Framework: [Main framework]
- Dependencies: [Key dependencies]

## Recent Updates
- Project created on {datetime.now().strftime('%Y-%m-%d')}
"""

    def activate_project(self, project_name: str) -> bool:
        """Activate a project for tracking"""
        try:
            project_config = self.get_project_config(project_name)
            if not project_config:
                return False
                
            # Create or get dashboard
            if project_name not in self.project_dashboards:
                self.project_dashboards[project_name] = ProjectDashboard(self.cccore)
            
            # Update active projects tracking
            self.active_projects[project_name] = {
                'config': project_config,
                'activated_at': datetime.now(),
                'last_activity': datetime.now()
            }
            
            # Calculate initial progress
            self.update_project_progress(project_name)
            
            return True
            
        except Exception as e:
            logging.error(f"Error activating project: {e}")
            return False

    def update_project_progress(self, project_name: str):
        """Update project progress based on various metrics"""
        if project_name not in self.active_projects:
            return
            
        try:
            project = self.active_projects[project_name]
            dashboard = self.project_dashboards[project_name]
            
            # Calculate progress based on:
            # 1. Task completion
            task_progress = dashboard.task_manager.get_completion_rate()
            
            # 2. Documentation coverage
            doc_progress = self.calculate_documentation_coverage(project_name)
            
            # 3. Project milestones
            milestone_progress = self.calculate_milestone_progress(project_name)
            
            # Weighted average of different progress metrics
            total_progress = (
                task_progress * 0.4 +
                doc_progress * 0.3 +
                milestone_progress * 0.3
            )
            
            self.project_progress[project_name] = total_progress
            self.project_progress_updated.emit(project_name, total_progress)
            
        except Exception as e:
            logging.error(f"Error updating project progress: {e}")

    def calculate_documentation_coverage(self, project_name: str) -> float:
        """Calculate documentation coverage percentage"""
        try:
            project_path = self.get_project_path(project_name)
            docs_path = os.path.join(project_path, 'docs')
            notes_path = os.path.join(project_path, 'notes')
            
            # Count markdown files
            doc_files = len([f for f in os.listdir(docs_path) if f.endswith('.md')])
            note_files = len([f for f in os.listdir(notes_path) if f.endswith('.md')])
            
            # Simple metric: 1 doc per project feature (minimum 5)
            target_docs = max(5, len(self.get_project_features(project_name)))
            
            return min(1.0, (doc_files + note_files) / target_docs)
            
        except Exception:
            return 0.0

    def calculate_milestone_progress(self, project_name: str) -> float:
        """Calculate project milestone completion percentage"""
        try:
            project = self.active_projects[project_name]
            if not project['config'].target_date:
                return 0.0
                
            total_duration = (project['config'].target_date - project['config'].start_date).days
            elapsed_duration = (datetime.now() - project['config'].start_date).days
            
            return min(1.0, elapsed_duration / total_duration)
            
        except Exception:
            return 0.0

    def show_command_manager(self):
        """Show the command manager window"""
        if not hasattr(self, '_command_manager'):
            from GUX.widgets.command_manager import CommandManager
            self._command_manager = CommandManager(self.cccore)
        
        self._command_manager.show()
        self._command_manager.raise_()

    def setup_menu(self):
        # Project Menu
        project_menu = self.menuBar().addMenu("&Project")
        
        # ... (existing project menu items) ...
        
        project_menu.addSeparator()
        
        # Add Dashboard action to Project menu
        dashboard_action = project_menu.addAction("&Dashboard")
        dashboard_action.triggered.connect(self.show_project_dashboard)
        
        # Testing submenu
        testing_menu = project_menu.addMenu("&Testing")
        
        integration_test_action = testing_menu.addAction("&Integration Testing")
        integration_test_action.triggered.connect(self.show_integration_testing)
        
        unit_test_action = testing_menu.addAction("&Unit Testing")
        unit_test_action.triggered.connect(self.show_unit_testing)
        
        testing_menu.addSeparator()
        
        test_report_action = testing_menu.addAction("Generate Test &Report")
        test_report_action.triggered.connect(self.generate_test_report)

        # Add Command Manager to Tools menu
        tools_menu = self.menuBar().addMenu("&Tools")
        command_manager_action = tools_menu.addAction("&Command Manager")
        command_manager_action.triggered.connect(self.show_command_manager)

    def get_config_filename(self, project_type: ProjectType) -> str:
        """Get the appropriate config filename based on project type"""
        return 'resolvinator_config.json' if project_type == ProjectType.RESOLVINATOR else 'project_config.json'

    def get_project_technical_flow(self, project_name: str) -> Dict[str, Any]:
        """Generate a comprehensive technical flow overview of the project with Nix integration"""
        project_path = self.get_project_path(project_name)
        if not project_path:
            return {}
        
        flow_data = {
            'project_info': {
                'name': project_name,
                'type': self.get_project_type(project_name),
                'path': project_path,
                'vault_info': {
                    'name': self.cccore.vault_manager.current_vault.name if self.cccore.vault_manager.current_vault else None,
                    'path': str(self.cccore.vault_manager.get_current_vault_path())
                }
            },
            'structure': {},  # Code structure with symbols
            'dependencies': set(),  # Project dependencies
            'entry_points': [],  # Main entry points
            'relationships': [],  # Symbol relationships
            'environment': {
                'nix_enabled': bool(self.cccore.vault_manager.get_nix_store_path()),
                'nix_store_path': str(self.cccore.vault_manager.get_nix_store_path() or ''),
                'knowledge_graph': {
                    'tags': list(self.cccore.vault_manager.current_vault.get_all_tags()),
                    'references': list(self.cccore.vault_manager.current_vault.get_all_references()),
                    'backlinks': list(self.cccore.vault_manager.current_vault.get_all_backlinks())
                }
            }
        }

        # Analyze project files
        for root, _, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(os.path.join(root, file))
                    relative_path = file_path.relative_to(project_path)
                    
                    # Get or parse symbols
                    symbols = self.get_file_symbols(file_path)
                    if not symbols:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            symbols = self._parse_file_symbols(content, file_path)
                    
                    # Add to structure
                    flow_data['structure'][str(relative_path)] = {
                        'symbols': [
                            {
                                'name': sym.name,
                                'type': sym.type,
                                'line': sym.line,
                                'column': sym.column,
                                'parent': sym.parent.name if sym.parent else None,
                                'children': [child.name for child in sym.children]
                            }
                            for sym in symbols
                        ]
                    }
                    
                    # Extract dependencies
                    flow_data['dependencies'].update(self._extract_dependencies(content))
                    
                    # Identify entry points
                    if '__main__' in content or 'if __name__ == "__main__"' in content:
                        flow_data['entry_points'].append(str(relative_path))
        
        # Add file metadata from vault index
        if self.cccore.vault_manager.current_vault:
            vault = self.cccore.vault_manager.current_vault
            for file_path, file_info in vault.get_index().get('files', {}).items():
                if str(file_path).startswith(str(project_name)):
                    flow_data['structure'][file_path] = {
                        **flow_data['structure'].get(file_path, {}),
                        'metadata': {
                            'type': file_info['type'],
                            'size': file_info['size'],
                            'created': file_info['created'],
                            'modified': file_info['modified'],
                            'tags': file_info['tags'],
                            'links': file_info['links']
                        }
                    }
        
        # Add symbol relationships
        flow_data['relationships'] = self._analyze_symbol_relationships(flow_data['structure'])
        
        # Convert dependencies to list for JSON serialization
        flow_data['dependencies'] = list(flow_data['dependencies'])
        
        return flow_data

    def _parse_file_symbols(self, content: str, file_path: Path) -> List[CodeSymbol]:
        """Parse a file's content for code symbols"""
        symbols = []
        lines = content.splitlines()
        current_class = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            indent = len(line) - len(stripped)
            
            if stripped.startswith('class '):
                class_name = stripped[6:].split('(')[0].strip(':').strip()
                current_class = CodeSymbol(
                    name=class_name,
                    type='class',
                    line=i + 1,
                    column=indent,
                    file_path=file_path
                )
                symbols.append(current_class)
                
            elif stripped.startswith('def '):
                func_name = stripped[4:].split('(')[0].strip()
                method = CodeSymbol(
                    name=func_name,
                    type='method' if current_class else 'function',
                    line=i + 1,
                    column=indent,
                    file_path=file_path,
                    parent=current_class
                )
                if current_class:
                    current_class.children.append(method)
                symbols.append(method)
        
        return symbols

    def _extract_dependencies(self, content: str) -> set:
        """Extract Python dependencies from file content"""
        dependencies = set()
        import_pattern = r'^(?:from|import)\s+([a-zA-Z0-9_\.]+)'
        
        for line in content.splitlines():
            if match := re.match(import_pattern, line.strip()):
                # Get the base package name
                package = match.group(1).split('.')[0]
                if package not in ['__future__', 'typing']:  # Skip built-in modules
                    dependencies.add(package)
        
        return dependencies

    def _analyze_symbol_relationships(self, structure: Dict) -> List[Dict]:
        """Analyze relationships between symbols across files"""
        relationships = []
        symbol_map = {}
        
        # First pass: build symbol map
        for file_path, info in structure.items():
            for symbol in info.get('symbols', []):
                symbol_map[symbol['name']] = {
                    'file': file_path,
                    'type': symbol['type'],
                    'references': []
                }
        
        # Second pass: analyze references
        for file_path, info in structure.items():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for symbol_name in symbol_map:
                if symbol_name in content:
                    symbol_map[symbol_name]['references'].append(file_path)
        
        # Build relationships
        for symbol_name, info in symbol_map.items():
            if len(info['references']) > 1:  # Only include symbols with multiple references
                relationships.append({
                    'symbol': symbol_name,
                    'type': info['type'],
                    'defined_in': info['file'],
                    'referenced_in': info['references']
                })
        
        return relationships