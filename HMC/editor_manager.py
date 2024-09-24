import logging
from PyQt6.Qsci import QsciScintilla
from PyQt6.QtWidgets import QMessageBox
from AuraText.auratext.Core.CodeEditor import CodeEditor
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QThread, pyqtSignal
import traceback

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

    def new_document(self, title="Untitled"):
        logging.info(f"Creating new document with title: {title}")
        try:
            logging.debug("Creating CodeEditor instance")
            editor = CodeEditor(self.window.mm)
            logging.debug("CodeEditor instance created")
            
            logging.debug("Adding tab to tab_widget")
            self.window.tab_widget.addTab(editor, title)
            logging.debug("Tab added")
            
            self.editors.append(editor)
            self.current_editor = editor
            self.window.tab_widget.setCurrentWidget(editor)
            
            logging.debug("Applying default lexer")
            self.apply_lexer(editor, "python")  # Default to Python lexer
            logging.debug("Default lexer applied")
            
            logging.info("New document created successfully")
        except Exception as e:
            logging.error(f"Error creating new document: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self.cccore.window, "Error", f"Could not create new document: {e}")

    def open_file(self, path):
        logging.info(f"Attempting to open file: {path}")
        try:
            self.file_loader = FileLoaderThread(path)
            self.file_loader.file_loaded.connect(self.create_new_editor_tab)
            self.file_loader.start()
        except Exception as e:
            logging.error(f"Error initiating file open process: {e}")
            QMessageBox.critical(self.cccore.window, "Error", f"Could not open file: {e}")

    def create_new_editor_tab(self, path, content):
        try:
            editor = CodeEditor(self.cccore.window.mm)
            editor.setText(content)
            self.cccore.window.tab_widget.addTab(editor, path.split('/')[-1])
            self.editors.append(editor)
            self.current_editor = editor
            self.cccore.window.tab_widget.setCurrentWidget(editor)
            self.apply_lexer(editor, self.get_file_extension(path))
            logging.info(f"File opened successfully: {path}")
        except Exception as e:
            logging.error(f"Error creating new editor tab: {e}")
            QMessageBox.critical(self.cccore.window, "Error", f"Could not create new editor tab: {e}")

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
            QMessageBox.critical(self.cccore.window, "Error", f"Could not save file: {e}")
            return False

    def save_file_as(self, editor=None):
        editor = editor or self.current_editor
        if not editor:
            return
        file_path, _ = QFileDialog.getSaveFileName(self.cccore.window, "Save File")
        if file_path:
            editor.file_path = file_path
            return self.save_file(editor)
        return False

    def close_tab(self, index):
        editor = self.cccore.window.tab_widget.widget(index)
        if editor.isModified():
            reply = QMessageBox.question(self.cccore.window, "Save Changes?",
                                         "Do you want to save your changes?",
                                         QMessageBox.StandardButton.Save | 
                                         QMessageBox.StandardButton.Discard | 
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file(editor):
                    return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        self.cccore.window.tab_widget.removeTab(index)
        self.editors.remove(editor)
        if editor == self.current_editor:
            self.current_editor = self.cccore.window.tab_widget.currentWidget()
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
            self.current_editor.SendScintilla(QsciScintilla.SCI_COPY)
            self.current_editor.SendScintilla(QsciScintilla.SCI_PASTE)

    def get_file_extension(self, path):
        return path.split('.')[-1].lower()

    def get_all_editors(self):
        # Return a list of all open CodeEditor instances
        return [tab for tab in self.cccore.window.tab_widget.children() if isinstance(tab, CodeEditor)]
