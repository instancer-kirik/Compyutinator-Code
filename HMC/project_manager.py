import os
import json
import logging
from .environment_manager import EnvironmentManager
from PyQt6.QtWidgets import QInputDialog, QMessageBox   
class ProjectManager:
    def __init__(self, settings_manager,cccore):
        self.settings_manager = settings_manager
        self.cccore = cccore
        self.build_manager = cccore.build_manager
        self.projects = {}
        self.current_project = None
        self.recent_projects = []
        self.env_manager = EnvironmentManager(self.settings_manager.get_value("environments_path", "./environments"))
        self.load_projects()

    def load_projects(self):
        projects_data = self.settings_manager.get_value("projects", {})
        if isinstance(projects_data, dict):
            self.projects = projects_data
        else:
            logging.error(f"Invalid projects data: {projects_data}")
            self.projects = {}
        self.current_project = self.settings_manager.get_value("current_project")
        self.recent_projects = self.settings_manager.get_value("recent_projects", [])
        logging.info(f"Loaded projects: {self.projects}")

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

    def add_project(self, name, path, language, version):
        if name not in self.projects:
            self.projects[name] = {"path": path, "language": language, "version": version}
            self.env_manager.create_environment(name, language, version)
            self.save_projects()
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

    def get_projects(self):
        return list(self.projects.keys())

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
        self.recent_projects = self.recent_projects[:10]  # Keep only the 10 most recent projects
        self.save_projects()

    def get_recent_projects(self):
        return self.recent_projects

    def switch_environment(self, project_name, env_name):
        if project_name in self.projects and self.env_manager.get_environment_path(env_name):
            self.projects[project_name]['environment'] = env_name
            self.save_projects()
            return True
        return False

    def switch_project(self, project_name):
        logging.info(f"Attempting to switch to project: {project_name}")
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
            logging.info(f"Successfully switched to project: {project_name}")
            return True, project_path
        else:
            logging.error(f"Failed to set current project to: {project_name}")
            return False, "Failed to set current project"
    def build_project(self):
        current_project = self.get_current_project()
        if current_project:
            if self.build_manager.build_project(current_project):
                QMessageBox.information(self,                                        "Build Project",
                                        f"Successfully built project: {current_project}")
            else:
                QMessageBox.warning(self,
                                    "Build Failed",
                                    f"Failed to build project: {current_project}")
        else:
            QMessageBox.warning(self, "Error", "No active project to build")

    def run_project(self):
        current_project = self.get_current_project()
        if current_project:
            if self.build_manager.run_project(current_project):
                QMessageBox.information(self, "Run Project", f"Started project: {current_project}")
            else:
                QMessageBox.warning(self, "Run Failed", f"Failed to run project: {current_project}")
        else:
            QMessageBox.warning(self, "Error", "No active project to run")

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
