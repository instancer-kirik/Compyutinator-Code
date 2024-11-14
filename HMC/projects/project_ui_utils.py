class ProjectUIUtils:
    """Common UI utilities for project management"""
    
    @staticmethod
    def show_rename_dialog(parent, project_manager, project_name):
        new_name, ok = QInputDialog.getText(
            parent,
            "Rename Project",
            "Enter new project name:",
            text=project_name
        )
        
        if ok and new_name:
            return project_manager.rename_project(project_name, new_name)
        return False

    @staticmethod
    def show_project_dialog(parent, project_manager):
        dialog = ProjectCreationDialog(parent)
        if dialog.exec():
            return dialog.get_project_data()
        return None

    @staticmethod
    def confirm_delete_project(parent, project_name):
        reply = QMessageBox.question(
            parent,
            "Delete Project",
            f"Are you sure you want to delete project '{project_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes 