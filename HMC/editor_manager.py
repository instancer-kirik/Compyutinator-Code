import logging
from PyQt6.Qsci import QsciScintilla
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QInputDialog
from AuraText.auratext.Core.CodeEditor import CodeEditor
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal
import traceback
import os
import time
from NITTY_GRITTY.ThreadTrackers import SafeQThread

class FileLoaderThread(SafeQThread):
    file_loaded = pyqtSignal(str, str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            with open(self.path, 'r') as file:
                content = file.read()
            self.file_loaded.emit(self.path, content)
        except Exception as e:
            logging.error(f"Error reading file: {e}")

class EditorManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.windows = []
        self.current_window = None
        self.current_editor = None
        self.window_editors = {}  # Map of windows to their editors

    def add_window(self, window):
        
        self.windows.append(window)
        self.window_editors[window] = []
        self.set_current_window(window)
   
        
    def set_current_window(self, window):
        if window in self.windows:
            self.current_window = window
            logging.info(f"Current AuraText window set in EditorManager: {window}")
        else:
            self.windows.append(window)
            self.current_window=window
    def open_file(self, file_path, line=0):
        if self.is_file_in_current_context(file_path):
            # Existing open_file logic
            pass
        else:
            logging.warning(f"File {file_path} is not in the current project context")

        existing_editor = self.get_editor_by_path(file_path)
        if existing_editor:
            self.set_current_editor(existing_editor)
            return existing_editor

        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return None

        try:
            with open(file_path, 'r') as file:
                content = file.read()
            new_editor = self.create_new_editor_tab(file_path, content)
            new_editor.goto_line(line)
            return new_editor
        except Exception as e:
            logging.error(f"Error opening file: {file_path}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self.current_window, "Error", f"Could not open file: {e}")
            return None

    def create_new_editor_tab(self, file_path=None, content=None):
        if self.current_window is None:
            logging.warning("No current AuraText window set in EditorManager")
            return None
       
        if file_path is None:
            logging.warning("No file path provided for new editor tab")
            file_path = "Untitled"
        if content is None:
            logging.warning("No content provided for new editor tab")
            content = ""
        
        try:
            editor = CodeEditor(mm=self.cccore, parent=self.current_window)
            editor.set_file_path(file_path)
            editor.setText(content)
            
            file_extension = self.get_file_extension(file_path)
            self.apply_lexer(editor, file_extension)
            
            index = self.current_window.add_new_tab(editor, os.path.basename(file_path))
            if index is not None:
                if self.current_window not in self.window_editors:
                    self.window_editors[self.current_window] = []#mAYBE this deletes old editors
                self.window_editors[self.current_window].append(editor)
                self.set_current_editor(editor)
            
            return editor
        except Exception as e:
            logging.error(f"Error creating new editor tab: {e}")
            logging.error(traceback.format_exc())
            return None

    def new_document(self):
        if self.current_window is None:
            logging.error("No current AuraText window set in EditorManager")
            return None

        try:
            new_editor = CodeEditor(self.cccore)
            index = self.current_window.add_new_tab(new_editor, "Untitled")
            if index is not None:
                self.set_current_editor(new_editor)
                return new_editor
            else:
                logging.error("Failed to add new tab to current AuraText window")
                return None
        except Exception as e:
            logging.error(f"Error creating new document: {str(e)}")
            logging.error(traceback.format_exc())
            return None

    def save_file(self, editor=None):
        # Similar check as in open_file
        pass

    def save_file_as(self, editor=None):
        editor = editor or self.current_editor
        if not editor:
            return
        file_path, _ = QFileDialog.getSaveFileName(self.current_window, "Save File")
        if file_path:
            editor.file_path = file_path
            return self.save_file(editor)
        return False

    def close_tab(self, index):
        if self.current_window is None:
            logging.error("No current window set in EditorManager")
            return False

        editor = self.current_window.tab_widget.widget(index)
        if editor is None:
            logging.error(f"No editor found at index {index}")
            return False

        # Check if the file needs to be saved
        if editor.document().isModified():
            # Implement save prompt logic here
            save_prompt = QMessageBox.question(self.current_window, "Save File", "Do you want to save the file?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if save_prompt == QMessageBox.StandardButton.Yes:
                self.save_file(editor)
            elif save_prompt == QMessageBox.StandardButton.Cancel:
                return False

        # Remove the editor from the list safely
        if self.current_window in self.window_editors:
            if editor in self.window_editors[self.current_window]:
                self.window_editors[self.current_window].remove(editor)
            else:
                logging.warning(f"Editor not found in window_editors list for the current window")

        # Close the tab
        self.current_window.tab_widget.removeTab(index)

        # If it was the current editor, set current_editor to None
        if editor == self.current_editor:
            self.current_editor = None

        # Clean up the editor
        editor.deleteLater()

        return True

    def apply_lexer(self, editor, file_extension):
        self.cccore.lexer_manager.apply_lexer(file_extension, editor)

    def apply_theme_to_all_editors(self, theme):
        for window, editors in self.window_editors.items():
            for editor in editors:
                self.apply_theme_to_editor(editor, theme)

    def apply_theme_to_editor(self, editor, theme):
        editor.setColor(QColor(theme['text_color']))
        editor.setPaper(QColor(theme['background_color']))
        # Add more theme applications as needed

    def duplicate_line(self):
        if self.current_editor:
            self.current_editor.SendScintilla(QsciScintilla.SCI_LINEDUPLICATE)

    def goto_line(self):
        if self.current_editor:
            line, ok = QInputDialog.getInt(self.current_window, "Go to Line", "Line number:", 1, 1, self.current_editor.lines())
            if ok:
                self.current_editor.setCursorPosition(line - 1, 0)

    def get_file_extension(self, path):
        return os.path.splitext(path)[1].lower()[1:]

    def get_current_editor(self):
        return self.current_editor

    def get_editor_by_index(self, index):
        return self.current_window.tab_widget.widget(index)

    def get_editor_by_path(self, path):
        for window, editors in self.window_editors.items():
            for editor in editors:
                if editor.file_path == path:
                    return editor
        return None

    def get_editor_by_name(self, name):
        for window, editors in self.window_editors.items():
            for editor in editors:
                if os.path.basename(editor.file_path) == name:
                    return editor
        return None

    
    def get_all_editors(self):
        all_editors = []
        for window, editors in self.window_editors.items():
            all_editors.extend(editors)
        return all_editors
    
    def get_all_editor_paths(self):
        all_editor_paths = []
        for window, editors in self.window_editors.items():
            for editor in editors:
                all_editor_paths.append(editor.file_path)
        return all_editor_paths
    
    def get_project_path(self,project_name):
        return self.cccore.project_manager.get_project_path(project_name)
    def on_vault_switch(self, new_vault_path):
        for window, editors in self.window_editors.items():
            for editor in editors:
                editor.on_vault_switch(new_vault_path)

    def update_tab_title(self, editor):
        for window, editors in self.window_editors.items():
            if editor in editors:
                index = window.tab_widget.indexOf(editor)
                if index != -1:
                    title = os.path.basename(editor.file_path) if editor.file_path else f"Untitled_{int(time.time())}"
                    window.set_tab_title(index, title)
                return

    def get_editor_count(self):
        return sum(len(editors) for editors in self.window_editors.values())

    def on_tab_moved(self, from_index, to_index):
        if self.current_window:
            editors = self.window_editors[self.current_window]
            editor = editors.pop(from_index)
            editors.insert(to_index, editor)

    def on_current_tab_changed(self, index):
        if self.current_window and index >= 0:
            self.set_current_editor(self.current_window.tab_widget.widget(index))

    def comment_selection(self):
        if self.current_editor:
            self.current_editor.toggle_comment()

    def uncomment_selection(self):
        if self.current_editor:
            self.current_editor.toggle_comment(uncomment=True)

    def close_other_tabs(self):
        if self.current_window:
            current_index = self.current_window.tab_widget.currentIndex()
            for i in range(self.current_window.tab_widget.count() - 1, -1, -1):
                if i != current_index:
                    self.close_tab(i)

    def close_all_tabs(self):
        if self.current_window:
            for i in range(self.current_window.tab_widget.count() - 1, -1, -1):
                self.close_tab(i)

    def remove_window(self, window):
        if window in self.windows:
            self.windows.remove(window)
            del self.window_editors[window]
            if self.current_window == window:
                self.current_window = self.windows[0] if self.windows else None
                self.current_editor = None
    def close_editor(self, editor):
        for window, editors in self.window_editors.items():
            if editor in editors:
                if window.close_editor(editor):
                    editors.remove(editor)
                    if editor == self.current_editor:
                        self.current_editor = None
                    return True
        return False

    def get_open_files(self):
        open_files = []
        for window, editors in self.window_editors.items():
            for editor in editors:
                if editor.file_path:
                    open_files.append(editor.file_path)
                else:
                    # For untitled files, we'll use a placeholder name
                    open_files.append(f"Untitled_{id(editor)}")
        
        logging.info(f"Open files: {open_files}")
        return open_files

    
    def get_editors_for_window(self, window):
        return self.window_editors.get(window, [])

    def get_editor_by_file_path(self, file_path):
        for editors in self.window_editors.values():
            for editor in editors:
                if editor.file_path == file_path:
                    return editor
        return None
    def set_current_editor(self, editor):
        if editor in self.current_window.tab_widget.findChildren(CodeEditor):
            self.current_window.tab_widget.setCurrentWidget(editor)
        else:
            logging.error(f"Attempted to set current editor that is not in the tab widget: {editor.file_path}")

    def is_file_in_current_context(self, file_path):
        current_vault = self.cccore.vault_manager.get_current_vault()
        current_project = self.cccore.project_manager.current_project
        if current_vault and current_project:
            project_path = self.get_project_path(current_project)
            try:
                return os.path.commonpath([file_path, project_path]) == project_path
            except ValueError:
                # Paths are on different drives, so we'll compare them as strings
                return file_path.lower().startswith(project_path.lower())
        return True  # If no vault or project is set, consider all files in context

    def update_current_editor_content(self, new_content):
        if self.current_editor:
            self.current_editor.setPlainText(new_content)
            self.current_editor.document().setModified(True)
        else:
            logging.warning("No current editor to update")

    def update_editor_content(self, file_path, new_content):
        editor = self.get_editor_by_file_path(file_path)
        if editor:
            editor.setPlainText(new_content)
            editor.document().setModified(True)
        else:
            logging.warning(f"No editor found for file: {file_path}")
    
    def refresh_current_editor(self):
        if self.current_editor:
            current_file = self.current_editor.file_path
            self.close_file(current_file)
            self.open_file(current_file)

    def get_file_content(self, file_path):
        editor = self.get_editor_by_file_path(file_path)
        if editor:
            return editor.toPlainText()
        else:
            try:
                with open(file_path, 'r') as file:
                    return file.read()
            except FileNotFoundError:
                return None

    def update_file_content(self, file_path, new_content):
        editor = self.get_editor_by_file_path(file_path)
        if editor:
            editor.setPlainText(new_content)
            editor.document().setModified(True)
        else:
            try:
                with open(file_path, 'w') as file:
                    file.write(new_content)
            except IOError as e:
                logging.error(f"Error writing to file {file_path}: {str(e)}")
                raise
    def get_editor_by_id(self, editor_id):
        for window, editors in self.window_editors.items():
            for editor in editors:
                if id(editor) == editor_id:
                    return editor
        return None
    def get_open_file_paths(self):
        open_files = []
        for window, editors in self.window_editors.items():
            for editor in editors:
                if editor.file_path:
                    open_files.append(editor.file_path)
                else:
                    # For untitled files, we'll use a placeholder name
                    open_files.append(f"Untitled_{id(editor)}")
        return open_files