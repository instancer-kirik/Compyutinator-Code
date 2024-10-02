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
        if not self.current_window:
            self.current_window = window

    def set_current_window(self, window):
        if window in self.windows:
            self.current_window = window

    def open_file(self, file_path):
        existing_editor = self.get_editor_by_path(file_path)
        if existing_editor:
            self.set_current_editor(existing_editor)
            return existing_editor

        try:
            with open(file_path, 'r') as file:
                content = file.read()
            new_editor = self.create_new_editor_tab(file_path, content)
            return new_editor
        except Exception as e:
            logging.error(f"Error opening file: {file_path}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self.current_window, "Error", f"Could not open file: {e}")
            return None

    def create_new_editor_tab(self, file_path, content):
        try:
            editor = CodeEditor(self.cccore)
            editor.set_file_path(file_path)
            editor.setText(content)
            
            file_extension = self.get_file_extension(file_path)
            self.apply_lexer(editor, file_extension)
            
            index = self.current_window.add_new_tab(editor, os.path.basename(file_path))
            if index is not None:
                self.window_editors[self.current_window].append(editor)
                self.set_current_editor(editor)
            
            return editor
        except Exception as e:
            logging.error(f"Error creating new editor tab: {e}")
            logging.error(traceback.format_exc())
            return None

    def new_document(self):
        logging.info("Creating new document")
        try:
            editor = CodeEditor(self.cccore)
            title = f"Untitled_{int(time.time())}"
            
            if self.current_window:
                index = self.current_window.add_new_tab(editor, title)
                if index is not None:
                    self.window_editors[self.current_window].append(editor)
                    self.set_current_editor(editor)
                    logging.info(f"New document created successfully at index {index}")
                else:
                    logging.error("Failed to add new tab")
                    raise Exception("Failed to add new tab")
            else:
                logging.error("No current window to add the new document")
                raise Exception("No current window")
            
        except Exception as e:
            logging.error(f"Error creating new document: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self.current_window, "Error", f"Could not create new document: {e}")

    def save_file(self, editor=None):
        editor = editor or self.current_editor
        if not editor:
            return
        if not editor.file_path:
            return self.save_file_as(editor)
        try:
            with open(editor.file_path, 'w') as file:
                file.write(editor.text())
            editor.setModified(False)
            return True
        except Exception as e:
            logging.error(f"Error saving file: {e}")
            QMessageBox.critical(self.current_window, "Error", f"Could not save file: {e}")
            return False

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
        if not self.current_window:
            return False
        
        editor = self.current_window.tab_widget.widget(index)
        if editor.isModified():
            reply = QMessageBox.question(self.current_window, "Save Changes?",
                                         "Do you want to save your changes?",
                                         QMessageBox.StandardButton.Save | 
                                         QMessageBox.StandardButton.Discard | 
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file(editor):
                    return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        
        self.current_window.close_tab(index)
        self.window_editors[self.current_window].remove(editor)
        if editor == self.current_editor:
            self.set_current_editor(self.current_window.get_current_tab())
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
        for editors in self.window_editors.values():
            open_files.extend([editor.file_path for editor in editors if editor.file_path])
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
        for window, editors in self.window_editors.items():
            if editor in editors:
                self.current_editor = editor
                self.current_window = window
                index = editors.index(editor)
                window.tab_widget.setCurrentIndex(index)
                logging.info(f"Current editor set to index {index} in window {window}")
                return
        logging.warning(f"Editor not found in any window. Unable to set as current.")
    