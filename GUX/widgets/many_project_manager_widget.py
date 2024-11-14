import logging
from datetime import datetime
import os
from pathlib import Path
from typing import Dict, Any, List
import re
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QComboBox, QFileDialog, QLabel, QMessageBox
from PyQt6.QtCore import pyqtSignal
from GUX.dialogs.project_dialogs import ProjectCreationDialog
from GUX.widgets.project_dashboard import ProjectDashboard
from HMC.project_config import PROJECT_DIRECTORIES
from GUX.widgets.integration_test_op import IntegrationTestingManager
from HMC.symbol_manager import CodeSymbol, SymbolManager
from HMC.project_manager import ProjectType
from HMC.technical_analyzer import TechnicalAnalyzer
import json
class ManyProjectsManagerWidget(QWidget):
    project_selected = pyqtSignal(str, str)  # Signal to emit (vault_name, project_name)

    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.technical_analyzer = TechnicalAnalyzer(cccore)
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
                dashboard = self.cccore.widget_manager.show_dashboard(project_name)
                
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
        """Create initial project structure and templates"""
        try:
            project_path = self.get_project_path(project_name)
            
            def create_directory_structure(base_path, structure, depth=0):
                """Recursively create directory structure with READMEs"""
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
            create_directory_structure(project_path, PROJECT_DIRECTORIES)
            
            # Create templates
            templates = {
                'requirements/README.md': self._load_template('requirements.md'),
                'contacts/README.md': self._load_template('contacts.md'),
                'marketing/archetypes/brand_archetypes/template.md': self._load_template('brand_archetype.md'),
                'README.md': self._load_and_format_template(
                    'project_readme.md',
                    project_name=project_name,
                    project_type=project_type,
                    creation_date=datetime.now().strftime('%Y-%m-%d')
                )
            }
            
            # Write template files
            for file_path, content in templates.items():
                full_path = os.path.join(project_path, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
                    
            return True
            
        except Exception as e:
            logging.error(f"Error creating project structure: {e}")
            return False

    def _load_template(self, template_name: str) -> str:
        """Load a template file"""
        try:
            template_path = self.template_dir / template_name
            with open(template_path, 'r') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Error loading template {template_name}: {e}")
            return ""

    def _load_and_format_template(self, template_name: str, **kwargs) -> str:
        """Load and format a template with variables"""
        template = self._load_template(template_name)
        return template.format(**kwargs)

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
        """Get technical flow analysis for project"""
        return self.technical_analyzer.analyze_project(project_name)

    def open_project_by_folder(self):
        """Open a project by selecting a folder."""
        folder_path = QFileDialog.getExistingDirectory(self.cccore.main_window, "Select Project Folder")
        if folder_path:
            project_name = os.path.basename(folder_path)  # Use the folder name as the project name
            self.load_project_from_folder(folder_path, project_name)

    def load_project_from_folder(self, folder_path: str, project_name: str) -> bool:
        """Load a project from a filesystem folder"""
        try:
            if not os.path.isdir(folder_path):
                return False
                
            project_data = {
                'name': project_name,
                'path': folder_path,
                'type': ProjectType.LOCAL.value,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.projects[project_name] = project_data
            self.save_projects()
            self.set_current_project(project_name)
            return True
            
        except Exception as e:
            logging.error(f"Error loading project from folder: {e}")
            return False
    
    def load_default_project(self):
        """Load the default project if one exists"""
        try:
            default_path = os.path.expanduser("~/.config/biglinks/default_project.json")
            if os.path.exists(default_path):
                with open(default_path, 'r') as f:
                    project_data = json.load(f)
                    
                # Validate project data
                if 'path' in project_data and os.path.exists(project_data['path']):
                    project_name = os.path.basename(project_data['path'])
                    return self.load_project_from_folder(project_data['path'], project_name)
                else:
                    logging.warning("Default project path not found or invalid")
                    return False
            else:
                logging.info("No default project configuration found")
                return False
                
        except Exception as e:
            logging.error(f"Error loading default project: {e}")
            return False
    
    def set_default_project(self, project_name: str):
        """Set a project as the default"""
        try:
            if project_name not in self.projects:
                raise ValueError(f"Project {project_name} not found")
            
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
    