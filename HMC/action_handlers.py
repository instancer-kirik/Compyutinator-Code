import logging
import os
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
from PyQt6.QtWidgets import QDialog
from GUX.settings_dialog import SettingsDialog

class ActionHandlers:
    def __init__(self, cccore):
        self.cccore = cccore

    def new_file(self):
        self.cccore.editor_manager.new_document()
    def new_project(self):
        self.cccore.project_manager.new_project()
    
    def open_file(self, path=None, file_path=None):
        if path is None:
            
            file_path, _ = QFileDialog.getOpenFileName(self.cccore.main_window, "Open File")
            if file_path:
                self.cccore.editor_manager.open_file(file_path)

        path = file_path if file_path else path#refactored lol
        if hasattr(self.cccore, 'file_manager') and self.cccore.file_manager:
            self.cccore.file_manager.open_file(path)
        else:
            logging.error("File manager not properly initialized")
    def open_project(self):
        self.cccore.project_manager.open_project()
    def toggle_python_console(self):
        self.cccore.python_console.toggle_visibility()
    def show_project_settings(self):
        self.cccore.project_manager.show_project_settings()
    def save_file(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            if current_editor.file_path:
                current_editor.save_file()
            else:
                self.save_file_as()

    def save_file_as(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            file_path, _ = QFileDialog.getSaveFileName(self.cccore.main_window, "Save File As")
            if file_path:
                current_editor.save_file(file_path)

    def close_file(self):
        self.cccore.editor_manager.close_current_tab()

    def close_all_files(self):
        while self.cccore.auratext_window.tab_widget.count() > 0:
            self.cccore.editor_manager.close_tab(0)

    def cut(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.cut()

    def cut_document(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.cut()

    def copy(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.copy()

    def copy_document(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.copy()

    def paste(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.paste()

    def paste_document(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.paste()

    def undo(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.undo()

    def redo(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.redo()

    def duplicate_line(self):
        self.cccore.editor_manager.duplicate_line()

    def pastebin(self):
        self.cccore.editor_manager.pastebin()

    def code_formatting(self):
        self.cccore.editor_manager.code_formatting()

    def goto_line(self):
        self.cccore.editor_manager.goto_line()

    def git_commit(self):
        self.cccore.git_manager.show_commit_dialog()

    def git_push(self):
        self.cccore.git_manager.push()

    def show_plugin_manager(self):
        if "Plugin Manager" in self.cccore.widget_manager.all_dock_widgets:
            dock = self.cccore.widget_manager.all_dock_widgets["Plugin Manager"]
            dock.show()
            dock.raise_()
        else:
            logging.warning("Plugin Manager dock not found")

    def show_settings(self):
        if "Settings" in self.cccore.widget_manager.all_dock_widgets:
            dock = self.cccore.widget_manager.all_dock_widgets["Settings"]
            dock.show()
            dock.raise_()
        else:
            logging.warning("Settings dock not found")
            try:
                dialog = SettingsDialog(self.settings_manager, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # Reload settings in all relevant widgets
                    self.terminal_emulator.load_typing_effect_settings()
                    self.code_editor.load_typing_effect_settings()
            except Exception as e:
                logging.error(f"Failed to load typing effect settings: {e}")

    def show_theme_manager(self):
        logging.info("Showing Theme Manager window")
        self.cccore.widget_manager.show_theme_manager()

    def show_workspace_manager(self):
        if "Workspace Manager" in self.cccore.widget_manager.all_dock_widgets:
            dock = self.cccore.widget_manager.all_dock_widgets["Workspace Manager"]
            dock.show()
            dock.raise_()
        else:
            logging.warning("Workspace Manager dock not found")

    def show_model_manager(self):
        logging.info("Showing Model Manager dock")
        if "Model Manager" in self.cccore.widget_manager.all_dock_widgets:
            dock = self.cccore.widget_manager.all_dock_widgets["Model Manager"]
            dock.show()
            dock.raise_()
        else:
            logging.warning("Model Manager dock not found")

    def show_download_manager(self):
        logging.info("Showing Download Manager dock")
        if "Download Manager" in self.cccore.widget_manager.all_dock_widgets:
            dock = self.cccore.widget_manager.all_dock_widgets["Download Manager"]
            dock.show()
            dock.raise_()
        else:
            logging.warning("Download Manager dock not found")

    def load_layout(self):
        if "Layout Manager" in self.cccore.widget_manager.all_dock_widgets:
            dock = self.cccore.widget_manager.all_dock_widgets["Layout Manager"]
            dock.show()
            dock.raise_()
        else:
            logging.warning("Layout Manager dock not found")

    def show_about(self):
        if "About" in self.cccore.widget_manager.all_dock_widgets:
            dock = self.cccore.widget_manager.all_dock_widgets["About"]
            dock.show()
            dock.raise_()
        else:
            logging.warning("About dock not found")

    def add_vault_directory(self):
        path = QFileDialog.getExistingDirectory(self.cccore.main_window, "Select Vault Directory")
        if path:
            default_name = os.path.basename(path)
            name, ok = QInputDialog.getText(self.cccore.main_window, "Add Vault", "Enter vault name (or leave blank for default):", text=default_name)
            if ok:
                if not name:  # If the user left the name blank, use None to trigger default naming
                    name = None
                final_name = self.cccore.add_vault_directory(path, name)
                if final_name:
                    QMessageBox.information(self.cccore.main_window, "Vault Added", f"Added new vault: {final_name}")
                else:
                    QMessageBox.warning(self.cccore.main_window, "Error", "Failed to add vault")

    def remove_vault_directory(self):
        vaults = list(self.cccore.vault_manager.vaults["vaults"].keys())
        name, ok = QInputDialog.getItem(self.cccore.main_window, "Remove Vault", "Select vault to remove:", vaults, 0, False)
        if ok and name:
            if self.cccore.remove_vault_directory(name):
                QMessageBox.information(self.cccore.main_window, "Vault Removed", f"Removed vault: {name}")
            else:
                QMessageBox.warning(self.cccore.main_window, "Error", "Failed to remove vault")

    def set_default_vault(self):
        vaults = list(self.cccore.vault_manager.vaults["vaults"].keys())
        name, ok = QInputDialog.getItem(self.cccore.main_window, "Set Default Vault", "Select default vault:", vaults, 0, False)
        if ok and name:
            if self.cccore.set_default_vault(name):
                QMessageBox.information(self.cccore.main_window, "Default Vault Set", f"Set default vault to: {name}")
            else:
                QMessageBox.warning(self.cccore.main_window, "Error", "Failed to set default vault")

    def setup_powershell(self):
        # Implement the setup for Powershell
        pass

    def create_snippet(self):
        # Implement the create snippet functionality
        pass

    def edit_snippet(self):
        # Implement the edit snippet functionality
        pass

    def delete_snippet(self):
        # Implement the delete snippet functionality
        pass

    def import_snippet(self):
        # Implement the import snippet functionality
        pass

    def boilerplates(self):
        # Implement the boilerplates functionality
        pass

    def show_shortcuts(self):
        # Implement the show shortcuts functionality
        pass

    def getting_started(self):
        # Implement the getting started functionality
        pass

    def bug_report(self):
        # Implement the bug report functionality
        pass

    def discord(self):
        # Implement the discord functionality
        pass

    def buymeacoffee(self):
        # Implement the buymeacoffee functionality
        pass

    def about_github(self):
        # Implement the about github functionality
        pass

    def contribute(self):
        # Implement the contribute functionality
        pass

    def code_jokes(self):
        # Implement the code jokes functionality
        pass

    def version(self):
        # Implement the version functionality
        pass

    def notes(self):
        self.cccore.sticky_note_manager.show()

    def apply_workspace(self):
        self.cccore.widget_manager.apply_workspace()

    def toggle_comment(self):
        current_editor = self.cccore.editor_manager.current_editor
        if current_editor:
            current_editor.toggle_comment()

    