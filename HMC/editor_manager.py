import logging
from PyQt6.Qsci import QsciScintilla
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QInputDialog
from AuraText.auratext.Core.CodeEditor import CodeEditor
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QThread, pyqtSignal
import traceback
import os
import time

class FileLoaderThread(QThread):
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
        self.current_editor = None
        self.editors = []
        self.window = cccore.widget_manager.auratext_window 
        
    def new_document(self):
        logging.info("Creating new document")
        try:
            editor = CodeEditor(self.cccore)
            title = f"Untitled_{int(time.time())}"
            
            index = self.window.add_new_tab(editor, title)
            if index is not None:
                self.editors.append(editor)
                self.set_current_editor(editor)
                logging.info(f"New document created successfully at index {index}")
            else:
                logging.error("Failed to add new tab")
                raise Exception("Failed to add new tab")
            
        except Exception as e:
            logging.error(f"Error creating new document: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self.window, "Error", f"Could not create new document: {e}")

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
            QMessageBox.critical(self.window, "Error", f"Could not open file: {e}")
            return None

    def create_new_editor_tab(self, file_path, content):
        try:
            editor = CodeEditor(self.cccore)
            editor.set_file_path(file_path)
            editor.setText(content)
            
            file_extension = self.get_file_extension(file_path)
            self.apply_lexer(editor, file_extension)
            
            self.window.add_new_tab(editor, os.path.basename(file_path))
            self.editors.append(editor)
            self.set_current_editor(editor)
            
            return editor
        except Exception as e:
            logging.error(f"Error creating new editor tab: {e}")
            logging.error(traceback.format_exc())
            return None

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
            QMessageBox.critical(self.cccore.auratext_window, "Error", f"Could not save file: {e}")
            return False

    def save_file_as(self, editor=None):
        editor = editor or self.current_editor
        if not editor:
            return
        file_path, _ = QFileDialog.getSaveFileName(self.cccore.auratext_window, "Save File")
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
        
        self.window.close_tab(index)
        self.editors.remove(editor)
        if editor == self.current_editor:
            self.set_current_editor(self.window.get_current_tab())
        return True

    def apply_lexer(self, editor, file_extension):
        self.cccore.lexer_manager.apply_lexer(file_extension, editor)

    def apply_theme_to_all_editors(self, theme):
        for editor in self.editors:
            self.apply_theme_to_editor(editor, theme)

    def apply_theme_to_editor(self, editor, theme):
        # Apply theme settings to the editor
        editor.setColor(QColor(theme['text_color']))
        editor.setPaper(QColor(theme['background_color']))
        # Add more theme applications as needed

    def duplicate_line(self):
        if self.current_editor:
            self.current_editor.SendScintilla(QsciScintilla.SCI_LINEDUPLICATE)

    def goto_line(self):
        if self.current_editor:
            line, ok = QInputDialog.getInt(self.cccore.auratext_window, "Go to Line", "Line number:", 1, 1, self.current_editor.lines())
            if ok:
                self.current_editor.setCursorPosition(line - 1, 0)

    def get_file_extension(self, path):
        return path.split('.')[-1].lower()
    def get_current_editor(self):
        return self.current_editor
    def get_editor_by_index(self, index):
        return self.window.tab_widget.widget(index)
    def get_editor_by_path(self, path):
        for editor in self.editors:
            if editor.file_path == path:
                return editor
        return None
    def get_editor_by_name(self, name):
        for editor in self.editors:
            if os.path.basename(editor.file_path) == name:
                return editor
        return None
    def get_editor_by_title(self, title):
        for editor in self.editors:
            if os.path.basename(editor.file_path) == title:
                return editor
        return None
    def get_open_files(self):
        return [editor.file_path for editor in self.editors if editor.file_path]
    def get_all_editors(self):
        # Return a list of all open CodeEditor instances
        return [tab for tab in self.cccore.auratext_window.tab_widget.children() if isinstance(tab, CodeEditor)]

    def set_current_editor(self, editor):
        if editor not in self.editors:
            logging.warning(f"Editor not in list. Adding it.")
            self.editors.append(editor)
        
        self.current_editor = editor
        if editor:
            index = self.editors.index(editor)
            self.window.tab_widget.setCurrentIndex(index)
            logging.info(f"Current editor set to index {index}")

    def on_vault_switch(self, new_vault_path):
        # Update any necessary state or UI elements
        for editor in self.editors:
            editor.on_vault_switch(new_vault_path)

    def update_tab_title(self, editor):
        index = self.window.tab_widget.indexOf(editor)
        if index != -1:
            title = os.path.basename(editor.file_path) if editor.file_path else f"Untitled_{int(time.time())}"
            self.window.set_tab_title(index, title)

    def get_editor_count(self):
        return self.window.get_tab_count()

    def get_editor_at_index(self, index):
        return self.window.tab_widget.widget(index)

    def on_tab_moved(self, from_index, to_index):
        self.reorder_editors(from_index, to_index)

    def on_current_tab_changed(self, index):
        if index >= 0:
            self.set_current_editor(self.get_editor_at_index(index))

    def reorder_editors(self, from_index, to_index):
        editor = self.editors.pop(from_index)
        self.editors.insert(to_index, editor)

    def comment_selection(self):
        current_editor = self.current_editor
        if current_editor:
            current_editor.toggle_comment()

    def uncomment_selection(self):
        current_editor = self.current_editor
        if current_editor:
            current_editor.toggle_comment(uncomment=True)

    def close_other_tabs(self):
        current_index = self.window.tab_widget.currentIndex()
        for i in range(self.window.tab_widget.count() - 1, -1, -1):
            if i != current_index:
                self.close_tab(i)

    def close_all_tabs(self):
        for i in range(self.window.tab_widget.count() - 1, -1, -1):
            self.close_tab(i)
