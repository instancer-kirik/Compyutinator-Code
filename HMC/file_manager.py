import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from GUX.radial_menu import RadialMenu
from PyQt6.QtGui import QTextCursor, QFileSystemModel 
from PyQt6.QtWidgets import QInputDialog 
from PyQt6.QtCore import QDir
import hashlib
import tempfile
import shutil
import logging
class FileManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.file_system_model = None

    def create_file_system_model(self):
        if self.file_system_model is None:
            self.file_system_model = QFileSystemModel()
            default_path = os.path.expanduser("~")  # Use user's home directory as default
            self.file_system_model.setRootPath(default_path)
        return self.file_system_model

    def update_explorer_views(self, file_explorer, vault_explorer):
        root_path = self.cccore.vault_manager.get_current_vault_path()
        if root_path and os.path.exists(root_path):
            self.file_system_model.setRootPath(root_path)
            vault_explorer.set_root_path(root_path)
            file_explorer.set_root_path(root_path)
        else:
            default_path = os.path.expanduser("~")
            self.file_system_model.setRootPath(default_path)
            file_explorer.set_root_path(default_path)
            vault_explorer.set_root_path(default_path)
    
    def update_explorer_views(self):
        root_path = self.mm.vault_manager.get_current_vault_path()
        if root_path and os.path.exists(root_path):
            self.file_system_model.setRootPath(root_path)
            self.vault_explorer.set_root_path(root_path)
            self.file_explorer.set_root_path(root_path)
        else:
            default_path = os.path.expanduser("~")
            self.file_system_model.setRootPath(default_path)
            self.file_explorer.set_root_path(default_path)
            self.vault_explorer.set_root_path(default_path)

    def new_document(self):
        editor = self.cccore.editor_manager.create_new_editor_tab(file_path=tempfile.NamedTemporaryFile().name,content="")
        self.cccore.current_window.tab_widget.addTab(editor, "Untitled")

    def open_file(self, file_path):
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            new_editor = self.cccore.editor_manager.create_new_editor_tab(file_path=file_path,content=content)
            if new_editor:
                self.cccore.editor_manager.set_current_editor(new_editor)
                logging.info(f"File opened successfully: {file_path}")
            else:
                logging.error(f"Failed to create new editor for file: {file_path}")
        except Exception as e:
            logging.error(f"Error opening file {file_path}: {str(e)}")
            QMessageBox.warning(None, "Error", f"Failed to open file: {file_path}\n\nError: {str(e)}")

    def save_file(self, editor=None):
        if editor is None:
            editor = self.cccore.editor_manager.current_editor
        if editor is None:
            return

        if editor.file_path.startswith("Untitled_"):
            return self.save_file_as(editor)

        try:
            with open(editor.file_path, 'w') as file:
                file.write(editor.text())
            editor.setModified(False)
            index = self.cccore.editor_manager.current_window.tab_widget.indexOf(editor)
            self.cccore.editor_manager.current_window.tab_widget.setTabText(index, os.path.basename(editor.file_path))
        except Exception as e:
            logging.error(f"Error saving file: {e}")
            QMessageBox.critical(self.cccore.current_window, "Error", f"Could not save file: {e}")
        self.cccore.vault_manager.update_knowledge_graph()

    def save_file_as(self, editor=None):
        if editor is None:
            editor = self.cccore.editor_manager.current_editor
        if editor is None:
            return

        path, _ = QFileDialog.getSaveFileName(self.cccore.current_window, "Save File As")
        if not path:
            return False

        editor.set_file_path(path)
        return self.save_file(editor)

    def close_tab(self, index):
        editor = self.cccore.editor_manager.current_window.tab_widget.widget(index)
        if editor.isModified():
            reply = QMessageBox.question(self.cccore.current_window, "Save Changes?",
                                         "Do you want to save your changes?",
                                         QMessageBox.StandardButton.Save | 
                                         QMessageBox.StandardButton.Discard | 
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file(editor):
                    return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        self.cccore.editor_manager.current_window.tab_widget.removeTab(index)
        return True
    
    def create_fileset(self):
        name, ok = QInputDialog.getText(self.cccore.editor_manager.current_window, "Create Fileset", "Enter fileset name:")
        if ok and name:
            files, _ = QFileDialog.getOpenFileNames(self.cccore.editor_manager.current_window, "Select Files for Fileset")
            if files:
                if self.cccore.vault_manager.create_fileset(name, files):
                    QMessageBox.information(self.cccore.editor_manager.current_window, "Success", f"Fileset '{name}' created successfully.")
                    self.update_fileset_dropdowns()
                else:
                    QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", f"Fileset '{name}' already exists.")

    def open_fileset(self):
        filesets = self.cccore.vault_manager.get_all_filesets()
        if not filesets:
            QMessageBox.information(self.cccore.editor_manager.current_window, "No Filesets", "No filesets available. Create one first.")
            return

        fileset_name, ok = QInputDialog.getItem(self.cccore.editor_manager.current_window, "Open Fileset", "Select a fileset:", filesets, 0, False)
        if ok and fileset_name:
            files = self.cccore.vault_manager.get_fileset(fileset_name)
            for file_path in files:
                self.open_file(file_path)

    def update_fileset(self):
        filesets = self.cccore.vault_manager.get_all_filesets()
        if not filesets:
            QMessageBox.information(self.cccore.editor_manager.current_window, "No Filesets", "No filesets available. Create one first.")
            return

        fileset_name, ok = QInputDialog.getItem(self.cccore.editor_manager.current_window, "Update Fileset", "Select a fileset to update:", filesets, 0, False)
        if ok and fileset_name:
            files, _ = QFileDialog.getOpenFileNames(self.cccore.editor_manager.current_window, "Select Files for Fileset")
            if files:
                if self.cccore.vault_manager.update_fileset(fileset_name, files):
                    QMessageBox.information(self.cccore.editor_manager.current_window, "Success", f"Fileset '{fileset_name}' updated successfully.")
                    self.update_fileset_dropdowns()
                else:
                    QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", f"Failed to update fileset '{fileset_name}'.")

    def delete_fileset(self):
        filesets = self.cccore.vault_manager.get_all_filesets()
        if not filesets:
            QMessageBox.information(self.cccore.editor_manager.current_window, "No Filesets", "No filesets available to delete.")
            return

        fileset_name, ok = QInputDialog.getItem(self.cccore.editor_manager.current_window, "Delete Fileset", "Select a fileset to delete:", filesets, 0, False)
        if ok and fileset_name:
            confirm = QMessageBox.question(self.cccore.editor_manager.current_window, "Confirm Deletion", f"Are you sure you want to delete the fileset '{fileset_name}'?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                if self.cccore.vault_manager.delete_fileset(fileset_name):
                    QMessageBox.information(self.cccore.editor_manager.current_window, "Success", f"Fileset '{fileset_name}' deleted successfully.")
                    self.update_fileset_dropdowns()
                else:
                    QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", f"Failed to delete fileset '{fileset_name}'.")

    def update_fileset_dropdowns(self):
        # Update the fileset dropdown in all open CodeEditor instances
        for editor in self.cccore.editor_manager.editors:
            editor.update_fileset_dropdown()

    def open_workspace(self):
        workspaces = self.cccore.workspace_manager.get_all_workspaces()
        if not workspaces:
            QMessageBox.information(self.cccore.editor_manager.current_window, "No Workspaces", "No workspaces available. Create one first.")
            return

        workspace_name, ok = QInputDialog.getItem(self.cccore.editor_manager.current_window, "Open Workspace", "Select a workspace:", workspaces, 0, False)
        if ok and workspace_name:
            if self.cccore.workspace_manager.switch_workspace(workspace_name):
                vault_path = self.cccore.workspace_manager.get_workspace_vault(workspace_name)
                fileset = self.cccore.workspace_manager.get_workspace_fileset(workspace_name)
                
                # Open the vault directory in the file explorer
                self.cccore.widget_manager.file_explorer.set_root_path(vault_path)
                
                # Open the files from the fileset
                for file_path in fileset:
                    self.open_file(file_path)
                
                QMessageBox.information(self.cccore.editor_manager.current_window, "Success", f"Workspace '{workspace_name}' opened successfully.")
            else:
                QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", f"Failed to open workspace '{workspace_name}'.")

    def create_workspace(self):
        name, ok = QInputDialog.getText(self.cccore.editor_manager.current_window, "Create Workspace", "Enter workspace name:")
        if ok and name:
            vault_path = QFileDialog.getExistingDirectory(self.cccore.editor_manager.current_window, "Select Vault Directory")
            if vault_path:
                filesets = self.cccore.vault_manager.get_all_filesets()
                fileset_name, ok = QInputDialog.getItem(self.cccore.editor_manager.current_window, "Create Workspace", "Select a fileset (optional):", 
                                                        ["None"] + filesets, 0, False)
                if ok:
                    fileset_name = None if fileset_name == "None" else fileset_name
                    if self.cccore.workspace_manager.create_workspace(name, vault_path, fileset_name):
                        QMessageBox.information(self.cccore.editor_manager.current_window, "Success", f"Workspace '{name}' created successfully.")
                    else:
                        QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", f"Workspace '{name}' already exists.")

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
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.insertPlainText("```\n\n```")
            current_editor.moveCursor(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor)
            current_editor.moveCursor(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor)

    def insert_markdown_block(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.insertPlainText("**Bold** *Italic* [Link](http://example.com)")

    def insert_latex_block(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.insertPlainText("$$\n\n$$")
            current_editor.moveCursor(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor)

    def insert_plain_text_block(self):
        # Do nothing, as plain text is the default
        pass

    def create_new_folder(self):
        current_path = self.cccore.widget_manager.file_explorer.current_path
        folder_name, ok = QInputDialog.getText(self.cccore.editor_manager.current_window, "Create New Folder", "Enter folder name:")
        if ok and folder_name:
            new_folder_path = os.path.join(current_path, folder_name)
            try:
                os.makedirs(new_folder_path)
                QMessageBox.information(self.cccore.editor_manager.current_window, "Success", f"Folder '{folder_name}' created successfully at {new_folder_path}.")
                self.cccore.widget_manager.file_explorer.refresh()
            except OSError as e:
                QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", f"Failed to create folder: {str(e)}")

    def rename_selected_item(self):
        selected_item = self.cccore.widget_manager.file_explorer.get_selected_item()
        if selected_item:
            old_name = os.path.basename(selected_item)
            new_name, ok = QInputDialog.getText(self.cccore.editor_manager.current_window, "Rename Item", "Enter new name:", text=old_name)
            if ok and new_name:
                old_path = selected_item
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                try:
                    os.rename(old_path, new_path)
                    QMessageBox.information(self.cccore.editor_manager.current_window, "Success", f"Item renamed from '{old_name}' to '{new_name}'.")
                    self.cccore.widget_manager.file_explorer.refresh()
                except OSError as e:
                    QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", f"Failed to rename item: {str(e)}")
        else:
            QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", "No item selected for renaming.")

    def delete_selected_item(self):
        selected_item = self.cccore.widget_manager.file_explorer.get_selected_item()
        if selected_item:
            item_name = os.path.basename(selected_item)
            confirm = QMessageBox.question(self.cccore.editor_manager.current_window, "Confirm Deletion", 
                                           f"Are you sure you want to delete '{item_name}'?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    if os.path.isdir(selected_item):
                        shutil.rmtree(selected_item)
                    else:
                        os.remove(selected_item)
                    QMessageBox.information(self.cccore.editor_manager.current_window, "Success", f"'{item_name}' deleted successfully.")
                    self.cccore.widget_manager.file_explorer.refresh()
                except OSError as e:
                    QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", f"Failed to delete item: {str(e)}")
        else:
            QMessageBox.warning(self.cccore.editor_manager.current_window, "Error", "No item selected for deletion.")
    def update_explorer_views(self,file_tree_view):
        root_path = self.cccore.vault_manager.get_current_vault_path()
        if root_path and os.path.exists(root_path):
            try:
                file_tree_view.set_root_path(str(root_path))
            except Exception as e:
                logging.error(f"Error setting root path for vault explorer: {e}")
        else:
            logging.warning(f"Current vault path does not exist or is not set: {root_path}")

        default_path = os.path.expanduser("~")
        file_tree_view.set_root_path(default_path)  # Changed from set_root_index to set_root_path
        
    class FileVersionStore:
        def __init__(self, store_path):
            self.store_path = store_path

        def save_version(self, file_path, content):
            hash = self.generate_hash(content)
            version_path = f"{self.store_path}/{hash}"
            with open(version_path, 'w') as f:
                f.write(content)
            self.update_version_history(file_path, hash)
            return hash

        def get_version(self, hash):
            version_path = f"{self.store_path}/{hash}"
            with open(version_path, 'r') as f:
                return f.read()

        def update_version_history(self, file_path, hash):
            history_path = f"{self.store_path}/{file_path}.history"
            with open(history_path, 'a') as f:
                f.write(f"{hash}\n")
    class MediaStore:
        def __init__(self, store_path):
            self.store_path = store_path

        def add_media(self, file_path):
            with open(file_path, 'rb') as f:
                content = f.read()
            hash = self.generate_hash(content)
            media_path = f"{self.store_path}/{hash}"
            if not os.path.exists(media_path):
                with open(media_path, 'wb') as f:
                    f.write(content)
            return hash

        def get_media_path(self, hash):
            return f"{self.store_path}/{hash}"

        def generate_hash(self, content):
            return hashlib.sha256(content).hexdigest()

    def show_backlinks(self, file_path):
        backlinks = self.cccore.vault_manager.get_backlinks(file_path)
        # Display backlinks in a dialog or sidebar
        return backlinks

    def get_vault_for_file(self, file_path):
        vault = self.cccore.vault_manager.get_vault_for_file(file_path)
        return vault
    # class DependencyStore:
    #     def __init__(self, store_path):
    #         self.store_path = store_path

    #     def add_dependency(self, name, version, content):
    #         hash = self.generate_hash(content)
    #         dep_path = f"{self.store_path}/{name}/{version}/{hash}"
    #         os.makedirs(os.path.dirname(dep_path), exist_ok=True)
    #         with open(dep_path, 'wb') as f:
    #             f.write(content)
    #         return hash

    #     def get_dependency(self, name, version, hash):
    #         dep_path = f"{self.store_path}/{name}/{version}/{hash}"
    #         with open(dep_path, 'rb') as f:
    #             return f.read()