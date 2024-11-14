import os
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QFileDialog

class ProjectManagerUI:
    """UI methods for project management"""
    
    @staticmethod
    def show_rename_dialog(parent, project_manager):
        """Show dialog for renaming a project"""
        projects = list(project_manager.projects.keys())
        if not projects:
            QMessageBox.warning(parent, "Error", "No projects to rename")
            return

        old_name, ok = QInputDialog.getItem(
            parent, 
            "Rename Project", 
            "Select project to rename:", 
            projects, 0, False
        )
        if ok and old_name:
            new_name, ok = QInputDialog.getText(
                parent, 
                "Rename Project", 
                "Enter new project name:"
            )
            if ok and new_name:
                if project_manager.rename_project(old_name, new_name):
                    QMessageBox.information(
                        parent,
                        "Project Renamed",
                        f"Renamed project from '{old_name}' to '{new_name}'"
                    )
                else:
                    QMessageBox.warning(
                        parent,
                        "Error",
                        "Failed to rename project. New name may already exist."
                    )

    @staticmethod
    def show_open_folder_dialog(parent, project_manager):
        """Show dialog for opening a project from folder"""
        folder_path = QFileDialog.getExistingDirectory(
            parent, 
            "Select Project Folder"
        )
        if folder_path:
            project_name = os.path.basename(folder_path)
            if project_manager.load_project_from_folder(folder_path, project_name):
                QMessageBox.information(
                    parent,
                    "Project Opened",
                    f"Opened project: {project_name} from folder: {folder_path}"
                )
            else:
                QMessageBox.warning(
                    parent,
                    "Error",
                    "Failed to open project from folder"
                ) 