import os
import re
import mimetypes
import importlib
import inspect
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QMessageBox, 
                             QTextEdit, QLineEdit, QInputDialog, QFileDialog, QTextBrowser,
                             QDialog, QScrollArea, QComboBox, QProgressBar, QApplication)
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from HMC.context_manager import ContextManager, NoveltyDetector
from GUX.context_picker_dialog import ContextPickerDialog
from GUX.diff_merger import DiffMergerWidget
from HMC.LSP_manager import LSPManager
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

from HMC.download_manager import DownloadManager
from requests.exceptions import RequestException
import requests
import traceback

from DEV.utils import extract_code_blocks, extract_diff_blocks, apply_diff_to_content

from GUX.diff_merger import DiffMergerWidget, DiffMergerDialog

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

        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)

        self.layout.addWidget(self.scroll_area)

    def add_reference(self, text, context):
        reference = ReferenceItem(text, context, self)
        self.references.append(reference)
        self.scroll_layout.addWidget(reference)

    def remove_reference(self, reference):
        self.references.remove(reference)
        logging.info(f"Removing reference: {reference}")
        if reference is not None and reference in self.scroll_layout.children():
            logging.debug(f"Removing reference widget: {reference}")
            self.scroll_layout.removeWidget(reference)
        reference.deleteLater()

class ReferenceItem(QWidget):
    def __init__(self, text, context, parent):
        super().__init__(parent)
        self.context = context
        self.parent = parent

        layout = QHBoxLayout(self)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(self.remove)
        layout.addWidget(self.close_button)

    def remove(self):
        self.parent.remove_reference(self)

class AIChatWidget(QWidget):
    file_clicked = pyqtSignal(str)
    merge_requested = pyqtSignal(str, str)

    def __init__(self, parent=None, context_manager=None, editor_manager=None, model_manager=None, download_manager=None, settings_manager=None):
        super().__init__(parent)
        logging.info("Initializing AIChatWidget")
        self.code_block_pattern = re.compile(r'```(\w+)?:?(.*?)\n(.*?)\n```', re.DOTALL)
        try:
            logging.info(f"Parent: {parent}")
            logging.info(f"Context manager: {context_manager}")
            logging.info(f"Editor manager: {editor_manager}")
            logging.info(f"Model manager: {model_manager}")
            logging.info(f"Download manager: {download_manager}")
            logging.info(f"Settings manager: {settings_manager}")
          
            self.settings = settings_manager.settings if settings_manager else QSettings("NEWCOMPANY", "OTHERAPPLICATION")
            self.download_manager = download_manager if download_manager else DownloadManager(self.settings)
            self.model_manager = model_manager if model_manager else ModelManager(self.settings)
            self.editor_manager = editor_manager    
            self.settings_manager = settings_manager
            self.context_manager = context_manager if context_manager else ContextManager()
            
            
            logging.info("Creating NoveltyDetector")
            self.novelty_detector = NoveltyDetector()
            
            logging.info("Creating ChatReferenceWidget")
            self.chat_reference_widget = ChatReferenceWidget()
         
            self.current_model = None
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

    def set_default_instructions(self):
        return """
        Please follow these instructions in your response:
        1. Use file path references when referring to specific parts of the code.
        2. When writing out code blocks, specify the file path after the initial backticks, like so:
        ```python:path/to/file.py
        # Your code here
        ```
        3. When suggesting changes, use a diff-like format with '+' for additions, '-' for deletions, and provide line numbers. For example:
        ```diff:path/to/file.py
        -10: old_line = "This is the old version"
        +10: new_line = "This is the new version"
        ```
        4. Always provide a brief explanation of your suggestions.
        5. For context lines (unchanged lines), use a space at the beginning of the line, followed by the line number. For example:
        ``` 15: unchanged_line = "This line stays the same"
        ```
        6. If you are asked to make changes to the code, always include the line number in your response. 
        7. If you detect duplicate functions, within a file, include a diff to reduce the duplicate functions. This means identical signature, code may differ; prefer the version with the most features, and least issues
        8. If you detect duplicate classes, within a file, include a diff to reduce the duplicate classes. This means identical name, code may differ; prefer the version with the most features, and least issues
        9. If a file has a different path than expected, use the new path as the new expected
        10. If we are creating a new class or function, and the context is significantly different than the current class, create a new class or relevant definition, and if needed, generate a new filepath in the most applicable location; otherwise, continue within the current class in appropriate location.
        """

    def set_instructions(self, instructions):
        self.instructions = instructions

    def initUI(self):
        logging.info("Initializing UI")
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.status_label = QLabel("Model not loaded")
        layout.addWidget(self.status_label)

        self.load_button = QPushButton("Load Model")
        layout.addWidget(self.load_button)

        self.progress_display = QTextEdit()
        self.progress_display.setReadOnly(True)
        self.progress_display.setFixedHeight(100)  # Adjust as needed
        self.progress_display.setVisible(False)
        layout.addWidget(self.progress_display)
        
        # Add References button and context display
        ref_layout = QHBoxLayout()
        self.add_ref_button = QPushButton("Add References")
        self.add_ref_button.clicked.connect(self.add_references)
        ref_layout.addWidget(self.add_ref_button)
        ref_layout.addStretch()
        layout.addLayout(ref_layout)
        
        self.chat_reference_widget = ChatReferenceWidget(self)
        layout.addWidget(self.chat_reference_widget)
        
        # Chat display
        self.chat_display = QTextBrowser()
        self.chat_display.setReadOnly(True)
        self.chat_display.setOpenLinks(False)
        self.chat_display.anchorClicked.connect(self.handle_link_click)
        layout.addWidget(self.chat_display)
        
        # User input
        self.user_input = QTextEdit()
        self.user_input.setFixedHeight(100)
        layout.addWidget(self.user_input)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)
        
        # Collapsible Model Section
        self.model_section = CollapsibleSection("Model Controls")
        layout.addWidget(self.model_section)

        # Change Model Directory button
        change_dir_button = QPushButton("Change Model Directory")
        change_dir_button.clicked.connect(self.change_download_path)
        self.model_section.add_widget(change_dir_button)

        # Download Model section
        self.download_url_input = QLineEdit()
        self.download_url_input.setPlaceholderText("Enter model URL or leave blank for default")
        self.model_section.add_widget(QLabel("Download Model:"))
        self.model_section.add_widget(self.download_url_input)

        self.download_model_button = QPushButton("Download Model")
        self.download_model_button.clicked.connect(self.download_model)
        self.model_section.add_widget(self.download_model_button)

        # Set default model URL hint
        self.set_default_model_url_hint()
        logging.info("UI initialized successfully")

    def set_default_model_url_hint(self):
        default_model_name = "Llama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ6_K.gguf"
        default_model_url = f"https://huggingface.co/Joseph717171/Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF/resolve/main/{default_model_name}"
        self.download_url_input.setPlaceholderText(f"Default: {default_model_url}")

    def update_status(self, message):
        self.status_label.setText(message)
        logging.info(message)

    def on_model_changed(self, new_model):
        self.model_manager.change_model(new_model)

    def on_model_loaded(self, model_name):
        self.status_label.setText(f"Model loaded: {model_name}")
        self.load_button.setEnabled(True)
        self.progress_display.setVisible(False)
        self.context_manager.load_tokenizer(model_name)

    def on_model_unloaded(self):
        self.status_label.setText("No model loaded")

    def on_model_error(self, error):
        self.status_label.setText(f"Model error: {error}")
        QMessageBox.critical(self, "Model Error", error)
        self.load_button.setEnabled(True)
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

    def load_model(self):
        repo_id = "Joseph717171/Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF"
        filename = "Llama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ4_K_M.gguf"
        self.model_manager.load_model(repo_id, filename)
        self.load_button.setEnabled(False)
        self.progress_display.setVisible(True)
        self.progress_display.clear()

    def on_model_loading(self):
        self.status_label.setText("Loading model...")

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
        self.load_button.clicked.connect(self.load_model)
        self.send_button.clicked.connect(self.send_message)
        self.model_manager.model_loading.connect(self.on_model_loading)
        self.model_manager.model_loaded.connect(self.on_model_loaded)
        self.model_manager.model_error.connect(self.on_model_error)
        self.model_manager.model_download_progress.connect(self.on_download_progress)
        self.model_manager.generation_finished.connect(self.on_generation_finished)
        self.model_manager.generation_error.connect(self.on_generation_error)

    def on_model_path_changed(self, new_path):
        self.status_label.setText(f"Model path changed to: {new_path}")
        self.model_manager.update_models_list()  # Refresh the list of available models

    def send_message(self):
        user_input = self.user_input.toPlainText()
        if not user_input.strip():
            return  # Don't send empty messages

        self.chat_display.append(f"You: {user_input}")
        self.user_input.clear()

        if not self.model_manager.model:
            self.chat_display.append("AI: Model not loaded. Please load a model first.")
            return

        # Get relevant context
        relevant_context = self.context_manager.get_most_relevant_context(user_input)
        
        # Prepare the full prompt with context
        messages = [
            {"role": "system", "content": f"Context:\n{relevant_context}"},
            {"role": "user", "content": user_input}
        ]

        self.send_button.setEnabled(False)
        self.chat_display.append("AI is thinking...")
        self.model_manager.generate(messages)

    def on_generation_finished(self, response):
        self.chat_display.append(f"AI: {response}")
        
        # Detect novel parts in the response
        novel_parts = self.novelty_detector.get_novel_parts(response)
        
        # Add novel parts to context
        for part in novel_parts:
            self.context_manager.add_context(part, "AI Response")

        self.send_button.setEnabled(True)
        # Scroll to the bottom of the chat display
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def on_generation_error(self, error):
        self.chat_display.append(f"Error: {error}")
        self.send_button.setEnabled(True)
        logging.error(f"Generation error: {error}")

    def display_response(self, response):
        formatted_response = self.format_response_with_file_references(response)
        self.chat_display.append(f"AI: {formatted_response}")
        
        novel_parts = self.novelty_detector.get_novel_parts(response, self.context_manager.contexts)
        
        for part in novel_parts:
            self.context_manager.add_context(part, "AI Response")

    def display_error(self, error):
        self.chat_display.append(f"Error: {error}")

    def format_response_with_file_references(self, response):
        lines = response.split('\n')
        formatted_lines = []
        in_file_block = False
        current_file = None

        for line in lines:
            if line.startswith("```") and ":" in line:
                in_file_block = not in_file_block
                if in_file_block:
                    current_file = line.split(":")[1].strip()
                    formatted_lines.append(f"<b>File: {current_file}</b>")
                else:
                    current_file = None
                continue

            if in_file_block and current_file:
                formatted_lines.append(f"<font color='blue'>{line}</font>")
            else:
                formatted_lines.append(line)

        return "<br>".join(formatted_lines)

    def apply_code_changes(self, file_path, suggested_code):
        if not file_path:
            QMessageBox.warning(self, "No File Specified", "No file path specified for this code block.")
            return

        current_content = self.mm.editor_manager.get_file_content(file_path)
        if current_content is None:
            QMessageBox.warning(self, "File Not Found", f"The file {file_path} could not be found or opened.")
            return

        diff_merger = DiffMergerDialog(self.mm, current_content, suggested_code, file_path)
        if diff_merger.exec() == QDialog.DialogCode.Accepted:
            merged_content = diff_merger.get_merged_content()
            self.mm.editor_manager.update_file_content(file_path, merged_content)
            QMessageBox.information(self, "Changes Applied", f"Changes have been applied to {file_path}")

    def update_file_content(self, new_content):
        self.current_file_content = new_content
        # Update the main editor with the new content
        self.mm.editor_manager.update_current_editor_content(self.current_file_content)

    def add_references(self):
        open_files = []
        if hasattr(self, 'editor_manager') and self.editor_manager is not None:
            open_files = self.editor_manager.get_open_files()
        else:
            logging.warning("Editor manager is not available. Open files won't be included in the context picker.")

        dialog = ContextPickerDialog(
            self,
            recent_files=self.recent_files,
            open_files=open_files,
            existing_contexts=[desc for desc, _ in self.context_manager.contexts]
        )
        if dialog.exec():
            selected_items = dialog.get_selected_items()
            for item in selected_items:
                item_type, item_content = item.split("] ", 1)
                item_type = item_type[1:]  # Remove the leading '['
                
                if item_type in ["Open", "Recent", "File"]:
                    self.add_file_reference(item_content)
                elif item_type == "Text":
                    self.add_text_reference()
                elif item_type == "Import":
                    self.add_import_reference(item_content)
                elif item_type == "Context":
                    self.add_existing_context(item_content)

    def add_file_reference(self, file_path):
        if self.context_manager.is_file_too_large(file_path):
            QMessageBox.warning(self, "File Too Large", f"The file {file_path} is too large to add as reference.")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.context_manager.add_context(content, f"File: {file_path}")
            self.chat_reference_widget.add_reference(os.path.basename(file_path), content)
        except Exception as e:
            SelectableMessageBox.warning(self, "Error", f"Failed to add file reference: {str(e)}").exec()

    def add_text_reference(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Custom Text", "Enter your text:")
        if ok and text:
            self.context_manager.add_context(text, "Custom Text")
            self.chat_reference_widget.add_reference("Custom Text", text)

    def add_import_reference(self, module_name):
        try:
            module = importlib.import_module(module_name)
            content = inspect.getsource(module)
            self.context_manager.add_context(content, f"Import: {module_name}")
            self.chat_reference_widget.add_reference(f"Import: {module_name}", content)
        except Exception as e:
            SelectableMessageBox.warning(self, "Import Error", f"Failed to import {module_name}: {str(e)}").exec()

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

    def display_message(self, message, is_user=False):
        parts = self.process_message(message)
        for part_type, *content in parts:
            if part_type == 'text':
                self.chat_display.append(content[0])
            elif part_type == 'code':
                self.add_code_block_widget(*content)

    def process_message(self, message):
        parts = []
        last_end = 0
        for match in self.code_block_pattern.finditer(message):
            start, end = match.span()
            if start > last_end:
                parts.append(('text', message[last_end:start]))
            language = match.group(1) or 'text'
            file_path = match.group(2).strip()
            code = match.group(3)
            parts.append(('code', language, file_path, code))
            last_end = end
        if last_end < len(message):
            parts.append(('text', message[last_end:]))
        return parts

    def add_code_block_widget(self, language, file_path, code):
        code_widget = QWidget()
        layout = QVBoxLayout(code_widget)
        
        code_display = QTextEdit()
        code_display.setPlainText(code)
        code_display.setReadOnly(True)
        
        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(lambda: self.apply_code_changes(file_path, code))
        
        layout.addWidget(QLabel(f"File: {file_path}"))
        layout.addWidget(code_display)
        layout.addWidget(apply_button)
        
        self.chat_display.addWidget(code_widget)