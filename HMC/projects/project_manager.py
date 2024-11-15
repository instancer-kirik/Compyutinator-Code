import os
import json
import logging

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, 
                             QInputDialog, QMessageBox, QFileDialog, QDialog, QLabel, QLineEdit, QFormLayout, QProgressBar, QStackedWidget)
from PyQt6.QtCore import Qt, QObject
import re
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
import sys
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialogButtonBox
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Union
from pathlib import Path
from GUX.widgets.project_dashboard import ProjectDashboard
from GUX.dialogs.project_dialogs import ProjectCreationDialog, ProjectConfigDialog
from HMC.projects.project_structure import PROJECT_DIRECTORIES
from HMC.system_analyzer import SystemInfo
from HMC.projects.project_config import ProjectConfig
import uuid
from HMC.projects.project_types import ProjectType
from HMC.symbol_manager import CodeSymbol
from HMC.projects.project import Project
from HMC.projects.project_registry import ProjectRegistry

class ProjectManager(QObject):
    project_changed = pyqtSignal(str)
    project_updated = pyqtSignal(object)
    
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.config_manager = cccore.config_manager
        self.registry = ProjectRegistry(self.config_manager.config_dir / "projects.json")
        self.projects: Dict[str, ProjectConfig] = {}
        self.current_project: Optional[Project] = None
        self.recent_projects: List[str] = []
        self.max_recent_projects = 10
        self.build_manager = cccore.build_manager
        self._load_projects()

    def set_current_project(self, project_name: str) -> bool:
        """Set current project and update recent projects"""
        try:
            if not project_name or project_name not in self.projects:
                return False
            
            project_config = self.get_project(project_name)
            if not project_config:
                return False
            
            # Create Project instance from config
            self.current_project = Project.from_config(project_config)
            self.current_project.cccore = self.cccore  # Set cccore reference
            
            # Update recent projects
            if project_name in self.recent_projects:
                self.recent_projects.remove(project_name)
            self.recent_projects.insert(0, project_name)
            self.recent_projects = self.recent_projects[:self.max_recent_projects]
            
            # Save to settings
            self.config_manager.set_value("recent_projects", self.recent_projects)
            
            # Emit signals
            self.project_changed.emit(project_name)
            self.project_updated.emit(self.current_project)
            
            logging.info(f"Current project set to: {project_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error setting current project: {e}")
            return False

    def get_project(self, project_name: str) -> Optional[ProjectConfig]:
        """Get project configuration by name"""
        return self.projects.get(project_name)

    def create_local_project(self, name: str, path: str, **kwargs) -> bool:
        """Create a new local project"""
        try:
            project_config = ProjectConfig(
                name=name,
                path=Path(path),
                project_type=ProjectType.LOCAL,
                **kwargs
            )
            
            if project_config.save():
                self.projects[name] = project_config
                return True
            return False
            
        except Exception as e:
            logging.error(f"Error creating local project: {e}")
            return False

    def load_project(self, project_path: str) -> Optional[ProjectConfig]:
        """Load project from path"""
        try:
            config = ProjectConfig.load(project_path)
            if config:
                self.projects[config.name] = config
                return config
            return None
            
        except Exception as e:
            logging.error(f"Error loading project: {e}")
            return None

    def update_project_symbols(self, project_name: str):
        """Update symbols for project"""
        project = self.get_project(project_name)
        if not project:
            return
            
        symbols = {}
        project_path = Path(project.path)
        
        for root, _, files in os.walk(project_path):
            for file in files:
                file_path = Path(root) / file
                if self._is_code_file(file_path):
                    symbols[file_path] = self._parse_file_symbols(file_path)
                    
        project.update_setting('tracking', 'symbols', value=symbols)
        project.save()

    def setup_self_as_default(self):
        """Set up the BigLinks project itself as the default project"""
        try:
            # Get the root directory of the BigLinks project
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            project_name = "BigLinks"
            
            project_data = {
                'name': project_name,
                'path': current_dir,
                'type': ProjectType.LOCAL.value,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'description': "BigLinks Development Project",
                'status': "active"
            }
            
            self.projects[project_name] = project_data
            self.save_projects()
            self.set_default_project(project_name)
            self.set_current_project(project_name)
            
            logging.info(f"Set up {project_name} as default project at {current_dir}")
            
        except Exception as e:
            logging.error(f"Error setting up default project: {e}")

    def load_default_project(self):
        """Load the default project if one exists"""
        try:
            # First try to load from settings
            default_project = self.config_manager.get_value("default_project")
            if default_project and default_project in self.projects:
                self.set_current_project(default_project)
                return True
                
            # Then try to load from config file
            config_path = os.path.expanduser("~/.config/biglinks/default_project.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    project_data = json.load(f)
                    
                if 'path' in project_data and os.path.exists(project_data['path']):
                    project_name = project_data.get('name') or os.path.basename(project_data['path'])
                    if self.load_project_from_folder(project_data['path'], project_name):
                        return True
                        
            # If no default project exists, set up self as default
            if not self.projects:
                self.setup_self_as_default()
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"Error loading default project: {e}")
            return False

    def set_default_project(self, project_name: str):
        """Set a project as the default"""
        try:
            if project_name not in self.projects:
                raise ValueError(f"Project {project_name} not found")
            
            # Save to settings
            self.config_manager.set_value("default_project", project_name)
            
            # Also save to config file for persistence
            config_dir = os.path.expanduser("~/.config/biglinks")
            os.makedirs(config_dir, exist_ok=True)
            
            project_data = {
                'path': self.projects[project_name]['path'],
                'name': project_name
            }
            
            with open(os.path.join(config_dir, 'default_project.json'), 'w') as f:
                json.dump(project_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logging.error(f"Error setting default project: {e}")
            return False
    def _load_projects(self):
        """Load projects from registry"""
        try:
            if self.registry.load():
                self.projects = {
                    name: ProjectConfig.from_dict(config) 
                    for name, config in self.registry.projects.items()
                }
                if self.registry.active_project:
                    self.set_current_project(self.registry.active_project)
        except Exception as e:
            logging.error(f"Error loading projects: {e}")

    def load_projects(self):
        """Load saved projects from disk"""
        try:
            config_dir = os.path.expanduser("~/.config/biglinks")
            projects_file = os.path.join(config_dir, "projects.json")
            
            if os.path.exists(projects_file):
                with open(projects_file, 'r') as f:
                    saved_projects = json.load(f)
                    
                self.projects = {
                    data['name']: Project.from_dict(data)
                    for data in saved_projects
                }
        except Exception as e:
            logging.error(f"Error loading projects: {e}")
      
    def load_current_project(self):
        """Load the last active or default project"""
        try:
            # Try recent projects first
            for project_name in self.recent_projects:
                if project_name in self.projects:
                    self.set_current_project(project_name)
                    return True
            
            # Try default project
            default_project = self.config_manager.get_value("default_project")
            if default_project and default_project in self.projects:
                self.set_current_project(default_project)
                return True
            
            # Fall back to first available project
            if self.projects:
                first_project = next(iter(self.projects))
                self.set_current_project(first_project)
                return True
                
            logging.warning("No projects available to load")
            return False
            
        except Exception as e:
            logging.error(f"Error loading current project: {e}")
            return False

    def get_current_project(self) -> Optional[ProjectConfig]:
        """Get current project configuration"""
        return self.current_project

    def get_project_technical_flow(self, project_name: str) -> Dict[str, Any]:
        """Generate technical flow overview of the project"""
        project = self.get_project(project_name)
        if not project:
            return {}
            
        return project.get_technical_flow()  # Move logic to ProjectConfig class

    def configure_build(self):
        """Fix: Method should use cccore.main_window"""
        current_project = self.get_current_project()
        if current_project:
            build_command, ok = QInputDialog.getText(
                self.cccore.main_window,  # Change: Use main_window
                "Configure Build", 
                "Enter build command:",
                text=self.build_manager.build_configs.get(current_project, {}).get('build_command', '')
            )
            if ok:
                self.build_manager.set_build_command(current_project, build_command)
                QMessageBox.information(
                    self.cccore.main_window,  # Change: Use main_window
                    "Build Configuration", 
                    f"Build command set for project: {current_project}"
                )
        else:
            QMessageBox.warning(
                self.cccore.main_window,  # Change: Use main_window
                "Error", 
                "No active project to configure"
            )


    def show_rename_dialog(self):
        """Add: Separate UI method for renaming"""
        projects = list(self.projects.keys())
        if not projects:
            QMessageBox.warning(self.cccore.main_window, "Error", "No projects to rename")
            return

        old_name, ok = QInputDialog.getItem(
            self.cccore.main_window, 
            "Rename Project", 
            "Select project to rename:", 
            projects, 0, False
        )
        if ok and old_name:
            new_name, ok = QInputDialog.getText(
                self.cccore.main_window, 
                "Rename Project", 
                "Enter new project name:"
            )
            if ok and new_name:
                if self.rename_project(old_name, new_name):
                    QMessageBox.information(
                        self.cccore.main_window,
                        "Project Renamed",
                        f"Renamed project from '{old_name}' to '{new_name}'"
                    )
                else:
                    QMessageBox.warning(
                        self.cccore.main_window,
                        "Error",
                        "Failed to rename project. New name may already exist."
                    )

    def update_project_symbols(self, project_name: str):
        """Update symbols for all code files in a project"""
        project = self.get_project(project_name)
        if not project:
            return
        
        project_path = Path(project.path)
        if not project_path.exists():
            return
            
        for root, _, files in os.walk(project_path):
            for file in files:
                file_path = Path(root) / file
                if self._is_code_file(file_path):
                    self._parse_file_symbols(file_path, project)
    
    def _is_code_file(self, file_path: Path) -> bool:
        """Check if file is a code file based on project settings"""
        try:
            project = self.get_current_project()
            if not project:
                return False
                
            extensions = project.attributes.development.get('file_extensions', ['.py', '.js', '.cpp'])
            return file_path.suffix in extensions
        except Exception as e:
            logging.error(f"Error checking code file: {e}")
            return False
    
    def _parse_file_symbols(self, content: str, file_path: Path) -> List[CodeSymbol]:
        """Parse a file's content for code symbols and their references"""
        try:
            symbols = []
            lines = content.splitlines()
            current_class = None
            symbol_stack = []
            
            for i, line in enumerate(lines):
                try:
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
                        
                except Exception as e:
                    logging.warning(f"Error parsing line {i+1} in {file_path}: {e}")
                    continue
                    
            return symbols
            
        except Exception as e:
            logging.error(f"Error parsing file {file_path}: {e}")
            return []
    
    def get_file_symbols(self, file_path: Path) -> List[CodeSymbol]:
        """Get symbols for a file, either from cache or by parsing"""
        if hasattr(self, 'symbol_manager'):
            return self.symbol_manager.get_file_symbols(file_path)
        return []

    def create_project(self, name: str, path: Path, project_type: ProjectType = ProjectType.LOCAL) -> Optional[Project]:
        """Create a new project"""
        try:
            project = Project.create(
                name=name,
                path=path,
                project_type=project_type
            )
            
            self.projects[name] = project
            self.save_projects()
            return project
            
        except Exception as e:
            logging.error(f"Error creating project: {e}")
            return None

    def get_project(self, project_name: str) -> Optional[Project]:
        """Get project by name"""
        try:
            if not project_name:
                return None
            
            # Check if project exists in current vault
            if self.cccore.vault_manager.current_vault:
                return self.cccore.vault_manager.current_vault.get_project(project_name)
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting project: {e}")
            return None

    def get_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Get project configuration"""
        try:
            project_path = self.get_project_path(project_name)
            if not project_path:
                return None
                
            return ProjectConfig.load(project_path)
            
        except Exception as e:
            logging.error(f"Error loading project config: {e}")
            return None
            
    def update_project_config(self, project_name: str, updated_config: ProjectConfig) -> bool:
        """Update project configuration"""
        try:
            if project_name not in self.projects:
                return False
            
            self.projects[project_name] = updated_config
            return self.save_project_config(updated_config)
            
        except Exception as e:
            logging.error(f"Error updating project config: {e}")
            return False

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

    def create_resolvinator_project(self, vault_name: str, project_name: str, project_path: str, 
                                      language: Optional[str] = None, version: Optional[str] = None) -> bool:
        """Create a Resolvinator-type project"""
        try:
            metadata = {
                "language": language,
                "version": version,
                "domain": None,
                "target_audience": None
            }
            
            project = Project(
                name=project_name,
                path=project_path,
                project_type=ProjectType.RESOLVINATOR,
                description="",
                status="planning",
                risk_appetite="cautious",
                metadata=metadata,
                settings={
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
                        "review_period_days": 30,
                        "alert_channels": [],
                        "monitoring_intervals": {
                            "risk_review": "30d",
                            "dependency_check": "7d",
                            "security_scan": "14d"
                        }
                    }
                }
            )

            # Save Resolvinator config
            config_path = os.path.join(project_path, 'resolvinator_config.json')
            with open(config_path, 'w') as f:
                json.dump(project.to_dict(), f, indent=2)

            # Notify WebSocket if connected
            if self.ws_client and self.ws_client.auth_state.get("authenticated"):
                self.ws_client.send_message({
                    "topic": "project",
                    "event": "project:create",
                    "payload": project.to_dict()
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
        
        project_path = self.current_project.path
        config_file = os.path.join(project_path, self.project_config_filename)
        
        files = [config_file]  # Always include the config file
        for root, dirs, filenames in os.walk(project_path):
            for filename in filenames:
                if filename != self.project_config_filename:
                    files.append(os.path.join(root, filename))
        
        return files

    def save_projects(self):
        """Save all projects to disk"""
        try:
            projects_data = {}
            for name, project in self.projects.items():
                if isinstance(project, Project):
                    projects_data[name] = project.to_dict()
                elif isinstance(project, dict):
                    projects_data[name] = project
                
            config_dir = Path.home() / '.config' / 'biglinks'
            config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(config_dir / 'projects.json', 'w') as f:
                json.dump(projects_data, f, indent=2, default=str)
            return True
        except Exception as e:
            logging.error(f"Error saving projects: {e}")
            return False
    
    def save_current_project_state(self):
        current_project = self.get_current_project()
        if current_project:
            self.add_recent_project(current_project)
        
        open_files = self.cccore.editor_manager.get_open_files()
        self.cccore.config_manager.set_value(f"open_files_{current_project}", open_files)

    def add_project(self):
        """Add a new project or import an existing one"""
        try:
            dialog = ProjectCreationDialog(self.cccore)
            if dialog.exec():
                project_data = dialog.get_project_data()
                
                # Get current vault
                vault = self.cccore.vault_manager.get_current_vault()
                if not vault:
                    raise ValueError("No vault selected")
                    
                # Add project to vault
                success = vault.add_project(
                    project_data['name'],
                    project_data['path'],
                    project_type=project_data['type']
                )
                
                if success:
                    # Update UI
                    self.update_project_list()
                    
                    # Show dashboard
                    self.cccore.widget_manager.show_dashboard(project_data['name'])
                    
                    return True
                    
        except Exception as e:
            logging.error(f"Error adding project: {e}")
            QMessageBox.warning(self, "Error", f"Failed to add project: {str(e)}")
            
        return False

    def get_projects(self, vault_name: Optional[str] = None) -> List[Project]:
        """Get list of projects, optionally filtered by vault"""
        try:
            if vault_name is None:
                vault_name = self.cccore.vault_manager.current_vault.name
                
            projects = []
            vault_projects = self.cccore.vault_manager.get_projects(vault_name)
            
            for project_data in vault_projects:
                if isinstance(project_data, dict):
                    projects.append(Project.from_dict(project_data))
                elif isinstance(project_data, Project):
                    projects.append(project_data)
                else:
                    logging.warning(f"Skipping invalid project data: {project_data}")
                    
            return projects
            
        except Exception as e:
            logging.error(f"Error getting projects: {e}")
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
    
    def get_current_project(self) -> Optional[Project]:
        """Get current project object"""
        try:
            if isinstance(self.current_project, dict):
                # Convert dictionary to Project object
                return Project.from_dict(self.current_project)
            return self.current_project
        except Exception as e:
            logging.error(f"Error getting current project: {e}")
            return None

    def set_current_project(self, project_name: str) -> bool:
        """Set current project by name"""
        try:
            if project_name in self.projects:
                project_data = self.projects[project_name]
                if isinstance(project_data, dict):
                    self.current_project = Project.from_dict(project_data)
                else:
                    self.current_project = project_data
                return True
            return False
        except Exception as e:
            logging.error(f"Error setting project@project_manager: {e}")
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
        self.recent_projects = self.config_manager.get_value("recent_projects", [])
   
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

   
    def build_project(self, name: str) -> Tuple[bool, str]:
        """Build a project with specified name"""
        if name in self.projects:
            project_data = self.projects[name]
            build_command = project_data.get('build_command')
            
            if not build_command:
                return False, "No build command specified"
            
            try:
                # Start process and get process info
                process_info = self.process_manager.start_process(
                    command=build_command,
                    name=f"Build {name}",
                    cwd=project_data['path'],
                    capture_output=True
                )
                
                if process_info:
                    pid = process_info.get('pid')
                    return True, f"Build process started for '{name}' (PID: {pid})"
                return False, "Failed to start build process"
                
            except Exception as e:
                logging.error(f"Error building project: {e}")
                return False, str(e)
            
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
    
   
    def configure_run(self):
        """Configure run command for current project"""
        current_project = self.get_current_project()
        if not current_project:
            QMessageBox.warning(
                self.cccore.main_window,
                "Error",
                "No active project to configure"
            )
            return

        run_command, ok = QInputDialog.getText(
            self.cccore.main_window,
            "Configure Run",
            "Enter run command:",
            text=self.build_manager.build_configs.get(current_project, {}).get('run_command', '')
        )
        
        if ok:
            self.build_manager.set_run_command(current_project, run_command)
            QMessageBox.information(
                self.cccore.main_window,
                "Run Configuration",
                f"Run command set for project: {current_project}"
            )

    def load_project_state(self, project_name):
        open_files = self.config_manager.get_value(f"open_files_{project_name}", [])
        for file_path in open_files:
            self.editor_manager.open_file(file_path)

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
        # Assuming you have a reference to the main window or another QWidget
        parent_widget = self.cccore.main_window  # Replace with your actual main window reference
        dialog = QDialog(parent_widget)  # Pass a valid QWidget as the parent
        dialog.setWindowTitle("Project Settings")
        layout = QVBoxLayout(dialog)
        
        # Add project path label
        path_label = QLabel("Project Path:")
        layout.addWidget(path_label)

    def update_project_selector(self):
        self.project_selector.clear()
        self.project_selector.addItems(self.get_projects(self.cccore.vault_manager.get_current_vault()))
        self.project_selector.setCurrentText(self.get_current_project())
    def open_project(self):
        """Open the selected project"""
        project_name = self.project_selector.currentText()
        if project_name:
            try:
                self.cccore.project_manager.set_current_project(project_name)
                self.project_selected.emit(project_name)
                logging.info(f"Opened project: {project_name}")
            except Exception as e:
                logging.error(f"Error opening project: {e}")
                QMessageBox.warning(self, "Error", f"Failed to open project: {str(e)}")
    def open_project_by_folder(self):
        """Open a project by selecting a folder."""
        try:
            folder_path = QFileDialog.getExistingDirectory(self.cccore.main_window, "Select Project Folder")
            if folder_path:
                project_name = os.path.basename(folder_path)
                self.load_project_from_folder(folder_path, project_name)
        except Exception as e:
            logging.error(f"Error opening project by folder: {str(e)}")
            QMessageBox.warning(self.cccore.main_window, "Error", f"Could not open project: {str(e)}")

    def open_project_as_treeview(self):
        
        pass

    def find_file_in_current_project(self, file_name):
        if not self.current_project:
            return None
        
        project_path = self.current_project.path
        if not project_path:
            return None
        
        for root, dirs, files in os.walk(project_path):
            if file_name in files:
                return os.path.join(root, file_name)
        
        return None

    def get_relative_path_in_project(self, file_path):
        if not self.current_project:
            return file_path
        
        project_path = self.current_project.path
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
        project_path = current_project.path
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
        current_project = self.config_manager.get_value("current_project")
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
    
    def load_project_from_folder(self, folder_path: str, project_name: str) -> bool:
        """Load a project from a filesystem folder"""
        try:
            logging.debug(f"Attempting to load project from folder: {folder_path}")
            if not os.path.isdir(folder_path):
                logging.error(f"Invalid folder path: {folder_path}")
                return False
            
            # Create config from folder
            config = ProjectConfig.from_folder(folder_path, project_name)
            
            # Create Project instance
            project = Project(
                name=project_name,
                path=Path(folder_path),
                project_type=config.project_type,
                config=config
            )
            
            # Add to projects and save
            self.projects[project_name] = project
            self.save_projects()
            self.set_current_project(project_name)
            logging.info(f"Successfully loaded project from folder: {project_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error loading project from folder: {e}")
            return False

    def get_project_config(self, project_name: str) -> Optional[Dict]:
        """Get the configuration data for a given project."""
        return self.get_project_data(project_name)
    def get_project_vault(self, project_name: str) -> Optional[str]:
        """Get the vault name for a given project."""
        for vault in self.cccore.vault_manager.vaults.values():
            if vault.has_project(project_name):
                return vault.name
        return None

    def configure_project(self, project_name: str):
        """Show project configuration dialog"""
        project = self.get_project(project_name)
        if not project:
            return False
            
        dialog = ProjectConfigDialog(project.config, self.cccore.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_config = dialog.get_updated_config()
            return self.update_project_config(project_name, updated_config)
        return False

