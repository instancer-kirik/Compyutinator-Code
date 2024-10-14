import os
import re
import mimetypes
import importlib
import inspect
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QMessageBox, 
                             QTextEdit, QLineEdit, QInputDialog, QFileDialog, QTextBrowser,
                             QDialog, QScrollArea, QComboBox, QProgressBar, QApplication)
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSplitter, QHBoxLayout, QVBoxLayout
from PyQt6.QtGui import QMovie
from HMC.context_manager import ContextManager
from GUX.context_picker_dialog import ContextPickerDialog
from GUX.diff_merger import DiffMergerWidget
from PyQt6.QtCore import QEvent
from SPARE_PARTS.aModel import AModel
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QFrame
from GUX.status_dialog import StatusDialog
from PyQt6.QtCore import Qt
import logging
import humanize
from GUX.selectable_mexageboss import SelectableMessageBox
from PyQt6.QtCore import QTimer
import time
import subprocess
from PyQt6.QtCore import QObject
from HMC.ai_model_manager import ModelManager
from PyQt6.QtCore import QSettings
from GUX.merge_widget import MergeWidget
from HMC.download_manager import DownloadManager
from requests.exceptions import RequestException
import requests
import traceback
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit

from DEV.utils import extract_code_blocks, extract_diff_blocks, apply_diff_to_content

from GUX.diff_merger import DiffMergerWidget, DiffMergerDialog
##maybe implement profiler to track time and memory usage and optimize
class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.toggle_content)
        
        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content.setLayout(self.content_layout)
        self.content.setVisible(False)
        
        layout = QVBoxLayout()
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content)
        self.setLayout(layout)
    
    def toggle_content(self):
        self.content.setVisible(not self.content.isVisible())
    
    def setContentLayout(self, layout):
        # Remove any existing layout
        if self.content.layout():
            QWidget().setLayout(self.content.layout())
        # Set the new layout
        self.content.setLayout(layout)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

#https://github.com/getzep/zep?tab=readme-ov-file
#user knowledge graph and stuff 
# However, Zep cloud:
# Structured Data Extraction: Quickly extract business data from chat conversations using a schema you define. Understand what your assistant should ask for next to complete the task.

class ChatReferenceWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.references = []

        # Scroll area to contain all references
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)

        self.layout.addWidget(self.scroll_area)
    
   
    def add_reference(self, display_text, context):
        # Add a new reference item
        reference = ReferenceItem(display_text, context, self)
        self.references.append(reference)
        self.scroll_layout.addWidget(reference)
    def remove_reference(self, reference):
        # Remove a reference item
        self.references.remove(reference)
        self.scroll_layout.removeWidget(reference)
        reference.deleteLater()
    def get_file_path(self, file_name):
        for reference in self.references:
            if reference.label.text().startswith("File:"):
                # Extract the full path from the label text
                file_path = reference.label.text().split("File: ", 1)[-1].split(" (Full path: ", 1)[-1].split(")", 1)[0]
                if os.path.basename(file_path) == file_name:
                    return file_path
        return None
class ReferenceItem(QWidget):
    def __init__(self, display_text, context, parent):
        super().__init__(parent)
        self.context = context
        self.parent = parent

        layout = QHBoxLayout(self)
        self.label = QLabel(display_text)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(self.remove)
        layout.addWidget(self.close_button)
    def remove(self):
        self.parent.remove_reference(self)
class ContextReferenceWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.references = []

        # Scroll area to contain all references
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)

        self.layout.addWidget(self.scroll_area)
    def add_context_reference(self, display_text, context):
        # Add a new reference item
        reference = ReferenceItem(display_text, context, self)
        self.references.append(reference)
        self.scroll_layout.addWidget(reference)
    def remove_reference(self, reference):
        # Remove a reference item
        self.references.remove(reference)
        self.scroll_layout.removeWidget(reference)
        reference.deleteLater()
    def get_context_text(self):
        return "\n".join([f"{reference.label.text()}: {reference.context}" for reference in self.references])
class CodeBlockHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.code_block_format = QTextCharFormat()
        self.code_block_format.setBackground(QColor(240, 240, 240))

    def highlightBlock(self, text):
        code_block_regex = re.compile(r'```[\s\S]*?```')
        for match in code_block_regex.finditer(text):
            start, end = match.span()
            self.setFormat(start, end - start, self.code_block_format)

class MessageWidget(QFrame):
    def __init__(self, message, is_user=False, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        layout = QVBoxLayout(self)
        
        prefix = "You: " if is_user else "AI: "
        content = QPlainTextEdit(f"{prefix}{message}")
        content.setReadOnly(True)
        content.setFrameStyle(QFrame.Shape.NoFrame)
        content.setStyleSheet("background-color: transparent;")
        
        if not is_user:
            highlighter = CodeBlockHighlighter(content.document())
        
        layout.addWidget(content)

class ChatDisplay(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.setWidget(self.widget)
        self.setWidgetResizable(True)

    def add_message(self, message, is_user=False):
        message_widget = MessageWidget(message, is_user)
        self.layout.addWidget(message_widget)
        self.scroll_to_bottom()

    def add_widget(self, widget):
        self.layout.addWidget(widget)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

class AIChatWidget(QWidget):
    file_clicked = pyqtSignal(str)
    merge_requested = pyqtSignal(str, str)

    def __init__(self, parent=None, context_manager=None, editor_manager=None, model_manager=None, download_manager=None, settings_manager=None, vault_manager=None, project_manager=None):
        super().__init__(parent)
        logging.info("Initializing AIChatWidget")
        self.code_block_pattern = re.compile(r'```(\w+)?:?(.*?)\n(.*?)\n```', re.DOTALL)
        self.editor_manager = editor_manager
        try:
            self.local_chat_widget = None
            self.remote_chat_widget = None
            self.current_model = None    
            self.settings = settings_manager.settings if settings_manager else QSettings("NEWCOMPANY", "OTHERAPPLICATION")
            self.download_manager = download_manager if download_manager else DownloadManager(self.settings)
            self.model_manager = model_manager if model_manager else ModelManager(self.settings)
            self.editor_manager = editor_manager    
            self.settings_manager = settings_manager
            self.context_manager = context_manager if context_manager else ContextManager()
            self.vault_manager = vault_manager
            self.project_manager = project_manager  
            self.local_messages = []
            self.remote_messages = []
            self.chat_reference_widget = ChatReferenceWidget(self)
            self.context_reference_widget = ContextReferenceWidget(self)
            
            self.load_button = QPushButton("Load Model")
            self.status_label = QLabel("Status: Ready")
            self.progress_display = QProgressBar()
            self.progress_display.setVisible(False)
            
            logging.info("Initializing UI")
            self.initUI()
            
            logging.info("Connecting signals")
            self.connect_signals()
            
            logging.info("AIChatWidget initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing AIChatWidget: {str(e)}")
            logging.error(traceback.format_exc())
            raise
        
        self.current_file_path = None
        self.current_file_content = None
        self.recent_files = []  # Initialize this with your recent files list
      
        self.instructions = self.set_default_instructions()
        self.model_path = None
        self.partial_response_buffer = ""
        self.cursor_manager = CursorManager(self)

    def set_default_instructions(self):
        return """
        Please follow these instructions in your response:
        1. Use file path references when referring to specific parts of the code.
        2. If there is overlapping functionality and unneeded code, alert the user concisely. If the user agrees, remove the unneeded code.
        3a. When suggesting changes, use a diff-like format with '+' for additions, '-' for deletions, and provide line numbers. For example:
        ```diff:file_path/file_name.py
        -10: old_line = "This is the old version"
        +10: new_line = "This is the new version"
        ```
        3b. Standard code blocks should be formatted as follows:
            For example:
            ```python:file_path/file_name.py
            # Your code here
            ```
        4. Always provide a brief explanation of your suggestions.
        5. For context lines (unchanged lines), use a space at the beginning of the line, followed by the line number. For example:
        ```python:file_path/file_name.py
            15: unchanged_line = "This line stays the same"
        ```
        
        ```python:file_path/file_name.py
            18: def add_file_reference(self, file_path, content=None):
                #... (existing code)
                27: return relevant_value
        ```
        6. If you are asked to make changes to the code, always include the line number in your response. 
        7. If you detect duplicate functions, within a file, include a diff to reduce the duplicate functions. This means identical signature, code may differ; prefer the version with the most features, and least issues
        8. If you detect duplicate classes, within a file, include a diff to reduce the duplicate classes. This means identical name, code may differ; prefer the version with the most features, and least issues
        9. If a file has a different path than expected, use the new path as the new expected. Always use forward slashes (/) in file paths, even on Windows systems.
        10. If we are creating a new class or function, and the context is significantly different than the current class, create a new class or relevant definition, and if needed, generate a new filepath in the most applicable location; otherwise, continue within the current class in appropriate location.
        11. Make sure to keep track of the file path and line numbers of the code you are referencing.
        12. When referencing file paths, always use the full absolute path starting from the drive letter (e.g., X:/path/to/file.py).
        """

    def set_instructions(self, instructions):
        self.instructions = instructions

    def initUI(self):
        logging.info("Initializing UI")
        main_layout = QVBoxLayout(self)
        
        # Model selection area
        model_layout = QHBoxLayout()
        
        # Remote model dropdown (now on the left)
        self.remote_model_dropdown = QComboBox()
        self.remote_model_dropdown.addItems([
            'OpenAI: gpt-3.5-turbo', 
            'OpenAI: gpt-4', 
            'Anthropic: claude-2',
            'Anthropic: claude-instant-1'
        ])
        model_layout.addWidget(QLabel("Remote Model:"))
        model_layout.addWidget(self.remote_model_dropdown)
        
        # Local model dropdown (now on the right)
        self.local_model_dropdown = QComboBox()
        self.populate_local_model_dropdown()
        model_layout.addWidget(QLabel("Local Model:"))
        model_layout.addWidget(self.local_model_dropdown)
        
        self.load_local_button = QPushButton("Load Local Model")
        model_layout.addWidget(self.load_local_button)
        
        main_layout.addLayout(model_layout)
        main_layout.addWidget(self.chat_reference_widget)
        # Chat area
        chat_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.local_chat_widget = self.create_chat_area("Local")
        self.remote_chat_widget = self.create_chat_area("Remote") 
        chat_splitter.addWidget(self.remote_chat_widget)
        chat_splitter.addWidget(self.local_chat_widget)
        main_layout.addWidget(chat_splitter, stretch=1)  # Add stretch factor
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.add_context_button = QPushButton("Add Context")
        input_layout.addWidget(self.add_context_button)
        
        self.input_field = QPlainTextEdit()
        self.input_field.setPlaceholderText("Type your message here...Enter for local chat, Alt+Enter for remote chat")
        self.input_field.setFixedHeight(50)
        input_layout.addWidget(self.input_field)
        self.context_reference_widget = ContextReferenceWidget(self)
        self.context_reference_widget.setVisible(False)
        input_layout.addWidget(self.context_reference_widget)
        button_layout = QVBoxLayout()
        self.send_local_button = QPushButton("Send Local")
        self.send_remote_button = QPushButton("Send Remote")
        button_layout.addWidget(self.send_local_button)
        button_layout.addWidget(self.send_remote_button)
        
        input_layout.addLayout(button_layout)
        
        main_layout.addLayout(input_layout)
        
        # Status and progress
        self.status_label = QLabel("Status: Ready")
        self.progress_display = QProgressBar()
        self.progress_display.setVisible(False)
        self.loading_spinner = QLabel()
        self.loading_spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_spinner.setVisible(False)
        
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_display)
        status_layout.addWidget(self.loading_spinner)
        main_layout.addLayout(status_layout)
        
        self.setLayout(main_layout)
        
        # Set default instructions
        self.set_instructions(self.set_default_instructions())

    def populate_local_model_dropdown(self):
        repo_id = "Joseph717171/Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF"
        api_url = f"https://huggingface.co/api/models/{repo_id}"
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            repo_data = response.json()
            
            model_files = [file for file in repo_data.get('siblings', []) if file['rfilename'].endswith('.gguf')]
            
            for file in model_files:
                self.local_model_dropdown.addItem(file['rfilename'])
            
            if self.local_model_dropdown.count() == 0:
                self.local_model_dropdown.addItem("No models found")
                self.load_local_button.setEnabled(False)
        except Exception as e:
            logging.error(f"Error populating local model dropdown: {str(e)}")
            self.local_model_dropdown.addItem("Error loading models")
            self.load_local_button.setEnabled(False)

    def create_chat_area(self, title):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel(f"{title} Chat"))
        
        chat_display = ChatDisplay()
        layout.addWidget(chat_display, stretch=1)  # Add stretch factor
        
        partial_buffer = QPlainTextEdit()
        partial_buffer.setReadOnly(True)
        partial_buffer.setMaximumHeight(100)
        layout.addWidget(partial_buffer)
        
        setattr(self, f"{title.lower()}_chat_display", chat_display)
        setattr(self, f"{title.lower()}_partial_buffer", partial_buffer)
        
        return widget

    def display_message(self, message, is_user=False, chat_type='local'):
        chat_display = getattr(self, f"{chat_type}_chat_display")
        
        if is_user:
            chat_display.add_message(message, is_user=True)
        else:
            # Process the AI message to extract code blocks
            parts = self.process_message(message)
            for part in parts:
                if part[0] == 'text':
                    chat_display.add_message(part[1], is_user=False)
                elif part[0] == 'code':
                    language, file_path, code = part[1], part[2], part[3]
                    self.add_code_block_widget(language, file_path, code, chat_display)
        
        partial_buffer = getattr(self, f"{chat_type}_partial_buffer")
        partial_buffer.clear()

    def on_partial_response(self, partial_response, chat_type):
        partial_buffer = getattr(self, f"{chat_type}_partial_buffer")
        partial_buffer.appendPlainText(partial_response)
        partial_buffer.moveCursor(QTextCursor.MoveOperation.End)
        partial_buffer.ensureCursorVisible()

    def on_generation_error(self, error):
        QMessageBox.critical(self, "Generation Error", f"An error occurred during generation: {error}")
        self.hide_loading_spinner()
        
    def on_generation_finished(self, response, chat_type):
        self.display_message(response, is_user=False, chat_type=chat_type)
        
        chat_display = getattr(self, f"{chat_type}_chat_display")
        self.extract_code_suggestions(response, chat_display)
        
        if chat_type == 'local':
            self.local_messages.append({"role": "assistant", "content": response})
        else:
            self.remote_messages.append({"role": "assistant", "content": response})
        
        self.add_message_to_references(f"AI: {response[:30]}...")
        self.hide_loading_spinner()

        partial_buffer = getattr(self, f"{chat_type}_partial_buffer")
        partial_buffer.clear()

    def extract_code_suggestions(self, response, chat_display):
        code_blocks = re.findall(r'```(.*?)```', response, re.DOTALL)
        for i, code in enumerate(code_blocks):
            language, file_path, code_content = self.parse_code_block(code)
            self.add_code_block_widget(language, file_path, code_content, chat_display)

    def show_code_suggestions(self):
        # Logic to fetch and display code suggestions
        code_suggestions = self.get_code_suggestions()
        for suggestion in code_suggestions:
            self.add_code_block_widget(suggestion['language'], suggestion['file_path'], suggestion['code'])

    def get_code_suggestions(self):
        # Placeholder for fetching code suggestions
        return [
            {'language': 'python', 'file_path': 'example.py', 'code': 'print("Hello, World!")'}
        ]
   
 
    def show_context_reference(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Context Reference")
        layout = QVBoxLayout(dialog)

        context_reference = QTextEdit()
        context_reference.setReadOnly(True)
        layout.addWidget(context_reference)

        dialog.setLayout(layout)
        dialog.exec()

    
    def update_progress(self, bytes_downloaded, total_bytes):
        if total_bytes > 0:
            progress = int((bytes_downloaded / total_bytes) * 100)
            self.progress_display.setValue(progress)
        else:
            self.progress_display.setValue(0)

    
    def send_message(self, chat_type):
        user_message = self.input_field.toPlainText()
        self.input_field.clear()
        
        if chat_type == 'local':
            model_name = self.local_model_dropdown.currentText()
            messages = self.local_messages
            self.loading_spinner.setVisible(True)
        else:
            model_name = self.remote_model_dropdown.currentText()
            messages = self.remote_messages
        
        self.display_message(user_message, is_user=True, chat_type=chat_type)
        context = ""
        if len(messages) == 0 or messages[0]["role"] != "system":
            instructions = self.set_default_instructions()
            context = instructions
        # Ensure the context is included
        context += self.context_reference_widget.get_context_text()
        logging.warning(f"Context: {context}")
        messages.insert(0, {"role": "system", "content": context})
    
        messages.append({"role": "user", "content": user_message})
        
        self.model_manager.generate(messages, chat_type, model_name)
        
        self.add_message_to_references(user_message)
           
    def show_loading_spinner(self):
        movie = QMovie("resources/loading.gif")
        self.loading_spinner.setMovie(movie)
        self.loading_spinner.setVisible(True)
        movie.start()

    def hide_loading_spinner(self):
        self.loading_spinner.setVisible(False)

    def update_status(self, message):
        self.status_label.setText(message)
        logging.info(message)

    def on_local_model_changed(self, new_model):
        self.load_local_button.setEnabled(True)
        self.model_manager.change_model('local', new_model)
    def on_remote_model_changed(self, new_model):
        self.model_manager.change_model('remote', new_model)

    def load_model(self):
        self.progress_display.setVisible(True)
        model_type = 'local'
        model_name = self.local_model_dropdown.currentText()
                
        self.update_status(f"Loading {model_type} model: {model_name}")
        self.show_loading_spinner()
        self.load_local_button.setEnabled(False)
        
        if model_type == 'local':
            repo_id = "Joseph717171/Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF"
            filename = model_name
        else:
            repo_id = None
            filename = model_name
        
        self.model_manager.load_model(model_type, filename, repo_id)
    def on_model_loaded(self, filename):
        self.context_manager.load_tokenizer(filename)
        self.progress_display.setVisible(False)
        #QMessageBox.information(self, "Model Loaded", f"Model {model_name} has been successfully loaded.")
        self.status_label.setText(f"Model loaded: {filename}")
        self.load_local_button.setEnabled(False)
        
        self.loading_spinner.setVisible(False)
        instructions = self.set_default_instructions()
        self.set_instructions(instructions)
   
    def on_model_unloaded(self):
        self.status_label.setText("No model loaded")

    def on_model_error(self, error):
        self.status_label.setText(f"Model error: {error}")
        QMessageBox.critical(self, "Model Error", error)
        self.load_local_button.setEnabled(True)
        self.loading_spinner.setVisible(False)
        self.progress_display.setVisible(False)

    def update_model_dropdown(self, models):
        self.model_dropdown.clear()
        if models:
            self.model_dropdown.addItems(models)
            self.current_model = models[0]
            self.model_dropdown.setCurrentText(self.current_model)
        else:
            self.model_dropdown.addItem("No models available")
        logging.info(f"Updated model dropdown with models: {models}")

    def on_model_loading(self):
        self.status_label.setText("Loading model...")
        self.show_loading_spinner()

    def on_download_progress(self, bytes_downloaded, total_bytes):
        progress = int((bytes_downloaded / total_bytes) * 100)
        file_size = total_bytes / (1024 * 1024 * 1024)  # Convert to GB
        downloaded = bytes_downloaded / (1024 * 1024 * 1024)  # Convert to GB
        
        progress_text = f"\rLlama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ4_K_M.gguf: {progress}%|{'█' * (progress // 2)}{' ' * (50 - (progress // 2))}| {downloaded:.2f}GB/{file_size:.2f}GB"
        
        self.progress_display.setPlainText(progress_text)
        self.progress_display.moveCursor(Qt.TextCursor.MoveOperation.End)

    def change_download_path(self):
        base_dir = QFileDialog.getExistingDirectory(self, "Select Base Directory for Models")
        if base_dir:
            models_dir = os.path.join(base_dir, "_Models")
            ai_models_dir = os.path.join(models_dir, "AI")
            os.makedirs(ai_models_dir, exist_ok=True)
            try:
                self.model_manager.set_model_path(ai_models_dir)
                self.status_label.setText(f"Models directory changed to: {ai_models_dir}")
            except ValueError as e:
                QMessageBox.critical(self, "Invalid Directory", str(e))

    def download_model(self):
        url = self.download_url_input.text() or self.download_url_input.placeholderText().split("Default: ")[1]
        model_name = os.path.basename(url)
        model_path = os.path.join(self.model_manager.get_model_path(), model_name)
        
        if os.path.exists(model_path):
            reply = QMessageBox.question(self, 'File Exists', f"The file {model_name} already exists. Do you want to replace it?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            os.remove(model_path)
        
        confirm_message = (
            f"Are you sure you want to download the model?(3.7GB)\n\n"
            f"Model: {model_name}\n"
            f"URL: {url}\n"
            f"Save to: {model_path}\n\n"
            f"The download progress will be shown in the Download Manager."
        )
        
        reply = QMessageBox.question(self, 'Confirm Download', confirm_message,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.start_download(url, model_name, model_path)
        else:
            QMessageBox.information(self, "Download Cancelled", "Model download was cancelled.")

    def start_download(self, url, model_name, model_path):
        try:
            download_id = self.download_manager.start_download(url, model_path)
            self.model_manager.active_downloads[download_id] = model_name
            self.status_label.setText(f"Download started for model: {model_name}")
            logging.info(f"Download started for model: {model_name} from URL: {url}")
        except Exception as e:
            error_message = f"Error starting download: {str(e)}"
            logging.error(error_message)
            QMessageBox.critical(self, "Download Error", error_message)

    def connect_signals(self):
        self.load_local_button.clicked.connect(self.load_model)
    
        self.send_local_button.clicked.connect(lambda: self.send_message('local'))
        self.send_remote_button.clicked.connect(lambda: self.send_message('remote'))
        self.input_field.installEventFilter(self)
        self.model_manager.model_loading.connect(self.on_model_loading)
        self.model_manager.model_loaded.connect(self.on_model_loaded)
        self.model_manager.model_error.connect(self.on_model_error)
        self.model_manager.generation_finished.connect(self.on_generation_finished)
        self.model_manager.generation_error.connect(self.on_generation_error)
        self.model_manager.partial_response.connect(self.on_partial_response)
        self.local_model_dropdown.currentTextChanged.connect(self.on_local_model_changed)
        self.remote_model_dropdown.currentTextChanged.connect(self.on_remote_model_changed)
        self.add_context_button.clicked.connect(self.add_references)
        self.input_field.textChanged.connect(self.adjust_input_height)
    def on_model_path_changed(self, new_path):
        self.status_label.setText(f"Model path changed to: {new_path}")
        self.model_manager.update_models_list()  # Refresh the list of available models

    def on_context_added(self, context_type, context_content):
        logging.info(f"Received context: {context_type}")
        self.chat_reference_widget.add_reference(f"{context_type}", context_content)
        self.context_reference_widget.add_context_reference(f"{context_type}", context_content)
        
    def add_file_reference(self, file_path, content=None):
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as file:
                        content = file.read()
                except Exception as e:
                    logging.error(f"Error reading file {file_path}: {e}")
                    QMessageBox.critical(self, "File Read Error", f"Failed to read file {file_path} due to encoding issues.")
                    return

        # Store the original content
        self.context_manager.add_context(content, f"File: {file_path}", file_path=file_path)

        # Create a display version with HTML line breaks
        display_content = content.replace("\n", "<br>")

        # Use the display version for the UI
        self.context_reference_widget.add_context_reference(f"File: {os.path.basename(file_path)}", display_content)

        logging.info(f"Added file reference: {file_path}")

    def add_context_reference(self, context_name, content):
        self.context_manager.add_context(content,description= f"Context: {context_name}")
        self.context_reference_widget.add_context_reference(f"Context: {context_name}", content)
        logging.warning(f"Added context reference: {context_name}")

    def add_text_reference(self, content):
        self.context_manager.add_context(content, "Custom Text")
        self.context_reference_widget.add_context_reference("Custom Text", content)
        logging.info("Added custom text reference")

    def on_suggested_changes(self, file_path, original_content, new_content, language=None):
        merge_widget = MergeWidget(file_path, original_content, new_content, language=language, parent=self)
        if merge_widget.exec():
            merged_content = merge_widget.merge_changes()
            # Apply merged content to the editor or file
    def apply_code_changes(self, file_path, suggested_code):
        logging.debug(f"Attempting to apply code changes. File path: {file_path}")
        if not file_path or file_path.startswith("[File] ") or file_path.startswith("[PROJECT_ROOT]"):
            file_path = file_path.replace("[File] ", "").replace("[PROJECT_ROOT]", "") if file_path else None
            if not file_path:
                file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*)")
            if not file_path:
                QMessageBox.warning(self, "No File Selected", "No file was selected. Cannot apply changes.")
                return

        current_content = self.editor_manager.get_file_content(file_path)
        if current_content is None:
            logging.warning(f"File not found: {file_path}")
            response = QMessageBox.question(self, "File Not Found", 
                                            f"The file {file_path} could not be found. Would you like to create it?",
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if response == QMessageBox.StandardButton.Yes:
                current_content = ""
            else:
                return

        diff_merger = DiffMergerDialog(self.editor_manager, current_content, suggested_code, file_path)
        if diff_merger.exec() == QDialog.DialogCode.Accepted:
            merged_content = diff_merger.get_merged_content()
            self.editor_manager.update_file_content(file_path, merged_content)
            QMessageBox.information(self, "Changes Applied", f"Changes have been applied to {file_path}")
            logging.info(f"Changes applied successfully to {file_path}")
        else:
            logging.info(f"User cancelled applying changes to {file_path}")
            
    def update_file_content(self, new_content):
        self.current_file_content = new_content
        # Update the main editor with the new content
        self.editor_manager.update_current_editor_content(self.current_file_content)

    def add_references(self):
        open_files = []
        if hasattr(self, 'editor_manager') and self.editor_manager is not None:
            open_files = self.editor_manager.get_open_files()
        else:
            logging.warning("Editor manager is not available. Open files won't be included in the context picker.")

        dialog = ContextPickerDialog(self, self.recent_files, open_files, self.context_manager.get_contexts(), self.editor_manager, self.vault_manager, self.context_manager)
        dialog.context_added.connect(self.on_context_added)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = dialog.get_selected_items()
            logging.debug(f"Selected items from dialog: {selected_items}")
            added_references = set()  # To keep track of added references
            for item in selected_items:
                logging.debug(f"Processing item: {item}")
                if isinstance(item, tuple) and len(item) == 2:
                    item_type, item_content = item
                elif isinstance(item, str):
                    try:
                        item_type, item_content = item.split("] ", 1)
                        item_type = item_type.strip(":")
                        item_type = item_type.strip("[")
                    except ValueError:
                        item_type = "Unknown"
                        item_content = item
                else:
                    logging.warning(f"Unexpected item type in add_references: {type(item)}")
                    continue
                
                if item_type == "File":
                    full_path = os.path.abspath(item_content)
                    if full_path not in added_references:
                        self.add_file_reference(full_path)
                        added_references.add(full_path)
                elif item_type == "File:":
                    logging.warning(f"File: {item_content}")
                    full_path = os.path.abspath(item_content)
                    if full_path not in added_references:
                        self.add_file_reference(full_path)
                        added_references.add(full_path)
                elif item_type == "Text":
                    if item_content not in added_references:
                        self.context_manager.add_context(item_content, "Custom Text")
                        self.context_reference_widget.add_context_reference("Custom Text", item_content)
                        added_references.add(item_content)
                elif item_type == "Import":
                    if item_content not in added_references:
                        self.add_import_reference(item_content)
                        added_references.add(item_content)
                elif item_type in ["Open Files", "Recent Files", "Existing Contexts"]:
                    if item_content not in added_references:
                        self.add_existing_context(item_content)
                        added_references.add(item_content)
                else:
                    logging.warning(f"Unknown item type in add_references: {item_type}")

    def add_import_reference(self, module_name):
        try:
            module = importlib.import_module(module_name)
            content = inspect.getsource(module)
            self.context_manager.add_context(content, f"Import: {module_name}")
            self.chat_reference_widget.add_reference(f"Import: {module_name}", content)
        except Exception as e:
            SelectableMessageBox.warning(self, "Import Error", f"Failed to import {module_name}: {str(e)}")
    def add_existing_context(self, context_desc):
        for desc, content in self.context_manager.contexts:
            if desc == context_desc:
                self.chat_reference_widget.add_reference(desc, content)
                break

    def remove_reference(self, reference):
        self.chat_reference_widget.remove_reference(reference)
        # Also remove from context_manager
        for i, (desc, _) in enumerate(self.context_manager.contexts):
            if desc == reference.label.text():
                del self.context_manager.contexts[i]
                break
    def set_current_file(self, file_path, content):
        self.current_file_path = file_path
        self.current_file_content = content

    # Add this method to handle LSP completions
    def show_completions(self, completions):
        # Implement this method to show completions in your UI
        pass

    def edit_instructions(self):
        current_instructions = self.model_manager.get_modelfile_content()
        new_instructions, ok = QInputDialog.getMultiLineText(
            self, "Edit AI Instructions", "Enter new instructions:", current_instructions
        )
        if ok:
            self.model_manager.edit_modelfile(new_instructions)

    def on_download_preparing(self):
        pass

    def on_download_started(self, download_id):
        if download_id in self.model_manager.active_downloads:
            model_name = self.model_manager.active_downloads[download_id]
            self.status_label.setText(f"Starting download for model: {model_name}")
            logging.info(f"Download started for model: {model_name}")

    def on_download_complete(self, download_id):
        if download_id in self.model_manager.active_downloads:
            model_name = self.model_manager.active_downloads[download_id]
            del self.model_manager.active_downloads[download_id]
            self.status_label.setText(f"Download completed for model: {model_name}")
            self.model_manager.update_models_list()
            QMessageBox.information(self, "Download Complete", f"Model {model_name} has been successfully downloaded.")
        else:
            self.status_label.setText("Download completed?")

    def on_download_error(self, download_id, error_message):
        self.status_label.setText("Model download failed")
        QMessageBox.critical(self, "Download Error", f"Model download failed: {error_message}")

    def log_message(self, message):
        logging.info(message)

    def handle_link_click(self, url):
        file_path = url.toString()
        self.file_clicked.emit(file_path)

   

    def process_message(self, message):
        parts = []
        last_end = 0
        for match in self.code_block_pattern.finditer(message):
            start, end = match.span()
            if start > last_end:
                parts.append(('text', message[last_end:start]))
            language = match.group(1) or 'text'
            file_path = match.group(2).strip() if match.group(2) else None
            code = match.group(3)
            parts.append(('code', language, file_path, code))
            last_end = end
        if last_end < len(message):
            parts.append(('text', message[last_end:]))
        return parts

    
    def parse_code_block(self, code_block):
        lines = code_block.strip().split('\n')
        language = 'text'
        file_path = None
        content_start = 0

        logging.debug(f"Parsing code block. First line: {lines[0]}")

        # Check for language and file path in the first line
        if lines and lines[0].strip().startswith('```'):
            parts = lines[0].strip('`').split(':', 1)
            if len(parts) == 2:
                language, file_path = parts[0].strip(), parts[1].strip()
                content_start = 1
            else:
                language = parts[0].strip()
                content_start = 1
        elif lines and ':' in lines[0]:
            language, file_path = lines[0].split(':', 1)
            language = language.strip()
            file_path = file_path.strip()
            content_start = 1

        # If we haven't found a language yet, use 'text'
        if not language:
            language = 'text'

        # Normalize file path
        if file_path:
            file_path = os.path.normpath(file_path).replace('\\', '/')
            if not os.path.isabs(file_path):
                # Try to find the full path in chat references
                full_path = self.chat_reference_widget.get_file_path(os.path.basename(file_path))
                if full_path:
                    file_path = full_path
                else:
                    # If not found, try to use the project root
                    project_root = self.project_manager.get_project_path()
                    if project_root:
                        file_path = os.path.normpath(os.path.join(project_root, file_path)).replace('\\', '/')
                    else:
                        logging.warning(f"No project root found for file: {file_path}")
                        # Use a placeholder path if no project root is found
                        file_path = os.path.join("[PROJECT_ROOT]", file_path)

        # Include the function signature in the code content
        code_content = '\n'.join(lines[content_start:])

        logging.debug(f"Parsed code block - Language: {language}, File: {file_path}, Content length: {len(code_content)}")
        return language, file_path, code_content

    def add_code_block_widget(self, language, file_path, code_content, chat_display):
        code_widget = QWidget()
        layout = QVBoxLayout(code_widget)

        # Try to find the file path in the chat references if not provided
        if not file_path:
            file_name = f"new_file.{language}"  # Default file name based on language
            file_path = self.chat_reference_widget.get_file_path(file_name)

        # Add file path label
        if file_path:
            rel_path = self.project_manager.get_relative_path_in_project(file_path)
            file_label = QLabel(f"File: {rel_path} (Full path: {file_path})")
        else:
            file_label = QLabel(f"File: {file_name} (Not specified)")
        layout.addWidget(file_label)

        # Add language label
        lang_label = QLabel(f"Language: {language}")
        layout.addWidget(lang_label)

        # Add code content
        code_edit = QTextEdit()
        code_edit.setPlainText(code_content)
        code_edit.setReadOnly(True)
        layout.addWidget(code_edit)

        # Add buttons
        button_layout = QHBoxLayout()
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(code_content))
        button_layout.addWidget(copy_button)

        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(lambda: self.apply_code_changes(file_path, code_edit.toPlainText()))
        button_layout.addWidget(apply_button)

        specify_file_button = QPushButton("Specify File")
        specify_file_button.clicked.connect(lambda: self.specify_file_path(code_widget, file_label))
        button_layout.addWidget(specify_file_button)

        layout.addLayout(button_layout)

        # Add the code widget to the chat display
        chat_display.add_widget(code_widget)

    
    def on_model_type_changed(self, model_type):
        if model_type == 'llama':
            # Populate with Llama models
            self.update_model_dropdown(['Llama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ4_K_M.gguf'])
        elif model_type == 'anthropic':
            # Populate with Anthropic models
            self.update_model_dropdown(['claude-2.1', 'claude-instant-1.2'])
        elif model_type == 'openai':
            # Populate with OpenAI models
            self.update_model_dropdown(['gpt-3.5-turbo', 'gpt-4'])  # Add GPT-4 if you have access
            
    def add_message_to_references(self, message):
        self.chat_reference_widget.add_reference(f"User: {message[:30]}...", message)
        self.context_reference_widget.add_context_reference(f"User: {message[:30]}...", message)
    def eventFilter(self, obj, event):
        if obj == self.input_field and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                   self.send_message('remote')
                else:
                   self.send_message('local')
                
                return True
        return super().eventFilter(obj, event)

    def adjust_input_height(self):
        doc_height = self.input_field.document().size().height()
        if doc_height <= 50:
            self.input_field.setFixedHeight(50)
        elif doc_height > 200:
            self.input_field.setFixedHeight(200)
        else:
            self.input_field.setFixedHeight(int(doc_height))
    def specify_file_path(self, code_widget, file_label):
        initial_path = file_label.text().split("Full path: ")[-1].strip(")")
        file_path, _ = QFileDialog.getSaveFileName(self, "Specify File Path", initial_path, "All Files (*)")
        if file_path:
            rel_path = self.project_manager.get_relative_path_in_project(file_path)
            file_label.setText(f"File: {rel_path} (Full path: {file_path})")
            # Update the apply_button to use the new file_path
            for child in code_widget.children():
                if isinstance(child, QPushButton) and child.text() == "Apply Changes":
                    child.clicked.disconnect()
                    child.clicked.connect(lambda: self.apply_code_changes(file_path, code_widget.findChild(QTextEdit).toPlainText()))
                    break
        logging.debug(f"User specified file path: {file_path}")
class CursorManager:
    def __init__(self, chat_widget):
        self.chat_widget = chat_widget
        self.cursors = {}  # {chat_type: Cursor}

    def get_cursor(self, chat_type):
        if chat_type not in self.cursors:
            chat_display = getattr(self.chat_widget, f"{chat_type}_chat_display")
            self.cursors[chat_type] = chat_display.textCursor()
        return self.cursors[chat_type]

    def move_cursor(self, chat_type, direction, amount=1):
        cursor = self.get_cursor(chat_type)
        if direction == 'left':
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, amount)
        elif direction == 'right':
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, amount)
        elif direction == 'up':
            cursor.movePosition(QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.MoveAnchor, amount)
        elif direction == 'down':
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, amount)
        chat_display = getattr(self.chat_widget, f"{chat_type}_chat_display")
        chat_display.setTextCursor(cursor)
        chat_display.ensureCursorVisible()

    def select_word(self, chat_type):
        cursor = self.get_cursor(chat_type)
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        chat_display = getattr(self.chat_widget, f"{chat_type}_chat_display")
        chat_display.setTextCursor(cursor)
        chat_display.ensureCursorVisible()

    def select_line(self, chat_type):
        cursor = self.get_cursor(chat_type)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        chat_display = getattr(self.chat_widget, f"{chat_type}_chat_display")
        chat_display.setTextCursor(cursor)
        chat_display.ensureCursorVisible()