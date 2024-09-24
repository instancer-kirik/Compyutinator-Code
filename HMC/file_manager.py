import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from GUX.radial_menu import RadialMenu
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QInputDialog 
import tempfile

class FileManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.window = cccore.widget_manager.main_window

    def new_document(self):
        editor = self.cccore.editor_manager.create_new_editor_tab(tempfile.NamedTemporaryFile().name, "")
        self.window.tab_widget.addTab(editor, "Untitled")

    def open_file(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self.window, "Open File")
        if file_path:
            with open(file_path, 'r') as file:
                content = file.read()
            editor = self.cccore.editor_manager.create_new_editor_tab(file_path, content)
            editor.setText(content)
            self.window.tab_widget.addTab(editor, os.path.basename(file_path))

    def save_file(self, editor):
        if not editor.file_path:
            return self.save_file_as(editor)
        with open(editor.file_path, 'w') as file:
            file.write(editor.text())
        return True

    def save_file_as(self, editor):
        file_path, _ = QFileDialog.getSaveFileName(self.window, "Save File")
        if file_path:
            editor.file_path = file_path
            return self.save_file(editor)
        return False

    def close_tab(self, index):
        editor = self.window.tab_widget.widget(index)
        if editor.isModified():
            reply = QMessageBox.question(self.window, "Save Changes?",
                                         "Do you want to save your changes?",
                                         QMessageBox.StandardButton.Save | 
                                         QMessageBox.StandardButton.Discard | 
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file(editor):
                    return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        self.window.tab_widget.removeTab(index)
        return True
    
    def create_fileset(self):
        name, ok = QInputDialog.getText(self.window, "Create Fileset", "Enter fileset name:")
        if ok and name:
            files, _ = QFileDialog.getOpenFileNames(self.window, "Select Files for Fileset")
            if files:
                if self.fileset_manager.create_fileset(name, files):
                    QMessageBox.information(self.window, "Success", f"Fileset '{name}' created successfully.")
                    self.update_fileset_dropdowns()
                else:
                    QMessageBox.warning(self.window, "Error", f"Fileset '{name}' already exists.")

    def open_fileset(self):
        filesets = self.fileset_manager.get_all_filesets()
        if not filesets:
            QMessageBox.information(self.window, "No Filesets", "No filesets available. Create one first.")
            return

        fileset_name, ok = QInputDialog.getItem(self.window, "Open Fileset", "Select a fileset:", filesets, 0, False)
        if ok and fileset_name:
            files = self.fileset_manager.get_fileset(fileset_name)
            for file_path in files:
                self.open_file(file_path)

    def update_fileset(self):
        filesets = self.fileset_manager.get_all_filesets()
        if not filesets:
            QMessageBox.information(self.window, "No Filesets", "No filesets available. Create one first.")
            return

        fileset_name, ok = QInputDialog.getItem(self.window, "Update Fileset", "Select a fileset to update:", filesets, 0, False)
        if ok and fileset_name:
            files, _ = QFileDialog.getOpenFileNames(self.window, "Select Files for Fileset")
            if files:
                if self.fileset_manager.update_fileset(fileset_name, files):
                    QMessageBox.information(self.window, "Success", f"Fileset '{fileset_name}' updated successfully.")
                    self.update_fileset_dropdowns()
                else:
                    QMessageBox.warning(self.window, "Error", f"Failed to update fileset '{fileset_name}'.")

    def delete_fileset(self):
        filesets = self.fileset_manager.get_all_filesets()
        if not filesets:
            QMessageBox.information(self.window, "No Filesets", "No filesets available to delete.")
            return

        fileset_name, ok = QInputDialog.getItem(self.window, "Delete Fileset", "Select a fileset to delete:", filesets, 0, False)
        if ok and fileset_name:
            confirm = QMessageBox.question(self.window, "Confirm Deletion", f"Are you sure you want to delete the fileset '{fileset_name}'?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                if self.fileset_manager.delete_fileset(fileset_name):
                    QMessageBox.information(self.window, "Success", f"Fileset '{fileset_name}' deleted successfully.")
                    self.update_fileset_dropdowns()
                else:
                    QMessageBox.warning(self.window, "Error", f"Failed to delete fileset '{fileset_name}'.")

    def open_workspace(self):
        workspaces = self.cccore.workspace_manager.get_all_workspaces()
        if not workspaces:
            QMessageBox.information(self.window, "No Workspaces", "No workspaces available. Create one first.")
            return

        workspace_name, ok = QInputDialog.getItem(self.window, "Open Workspace", "Select a workspace:", workspaces, 0, False)
        if ok and workspace_name:
            if self.cccore.workspace_manager.switch_workspace(workspace_name):
                vault_path = self.cccore.workspace_manager.get_workspace_vault(workspace_name)
                fileset = self.cccore.workspace_manager.get_workspace_fileset(workspace_name)
                
                # Open the vault directory in the file explorer
                self.cccore.widget_manager.file_explorer.set_root_path(vault_path)
                
                # Open the files from the fileset
                for file_path in fileset:
                    self.open_file(file_path)
                
                QMessageBox.information(self.window, "Success", f"Workspace '{workspace_name}' opened successfully.")
            else:
                QMessageBox.warning(self.window, "Error", f"Failed to open workspace '{workspace_name}'.")

    def create_workspace(self):
        name, ok = QInputDialog.getText(self.window, "Create Workspace", "Enter workspace name:")
        if ok and name:
            vault_path = QFileDialog.getExistingDirectory(self.window, "Select Vault Directory")
            if vault_path:
                filesets = self.fileset_manager.get_all_filesets()
                fileset_name, ok = QInputDialog.getItem(self.window, "Create Workspace", "Select a fileset (optional):", 
                                                        ["None"] + filesets, 0, False)
                if ok:
                    fileset_name = None if fileset_name == "None" else fileset_name
                    if self.cccore.workspace_manager.create_workspace(name, vault_path, fileset_name):
                        QMessageBox.information(self.window, "Success", f"Workspace '{name}' created successfully.")
                    else:
                        QMessageBox.warning(self.window, "Error", f"Workspace '{name}' already exists.")

    def show_radial_menu(self, pos):
        options = ["Code", "Markdown", "LaTeX", "Plain Text"]
        menu = RadialMenu(self.window)
        menu.set_options(options)
        menu.optionSelected.connect(self.handle_radial_selection)
        menu.show_at(pos)

    def handle_radial_selection(self, option):
        if option == "Code":
            self.insert_code_block()
        elif option == "Markdown":
            self.insert_markdown_block()
        elif option == "LaTeX":
            self.insert_latex_block()
        elif option == "Plain Text":
            self.insert_plain_text_block()

    def insert_code_block(self):
        current_editor = self.cccore.editor_manager.get_current_editor()
        if current_editor:
            current_editor.insertPlainText("```\n\n```")
            current_editor.moveCursor(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor)
            current_editor.moveCursor(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor)

    def insert_markdown_block(self):
        current_editor = self.cccore.editor_manager.get_current_editor()
        if current_editor:
            current_editor.insertPlainText("**Bold** *Italic* [Link](http://example.com)")

    def insert_latex_block(self):
        current_editor = self.cccore.editor_manager.get_current_editor()
        if current_editor:
            current_editor.insertPlainText("$$\n\n$$")
            current_editor.moveCursor(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor)

    def insert_plain_text_block(self):
        # Do nothing, as plain text is the default
        pass

    def update_fileset_dropdowns(self):
        # Update the fileset dropdown in all open CodeEditor instances
        for editor in self.cccore.editor_manager.get_all_editors():
            editor.update_fileset_dropdown()