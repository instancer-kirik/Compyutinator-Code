import os
import re
import mimetypes
import importlib
import inspect
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QMessageBox, 
                             QTextEdit, QLineEdit, QInputDialog, QFileDialog, 
                             QDialog, QScrollArea, QComboBox, QProgressBar, QApplication)
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from SPARE_PARTS.ollama_client import OllamaClient, OllamaOutputWindow
from HMC.context_manager import ContextManager, NoveltyDetector
from GUX.context_picker_dialog import ContextPickerDialog
from GUX.diff_merger import DiffMergerWidget
from NITTY_GRITTY.LSPClient import LSPClient
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
    
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)


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

class ModelFetchWorker(QObject):
    finished = pyqtSignal(list)

    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self):
        models = self.client.get_installed_models()
        self.finished.emit(models)

class AIChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.client = OllamaClient.get_instance(base_url=self.ollama_base_url)
        self.context_manager = ContextManager(max_tokens=4000)
        self.novelty_detector = NoveltyDetector()
        self.model_path = None
        self.current_file_path = None
        self.current_file_content = None
        self.recent_files = []  # Initialize this with your recent files list
        self.lsp_client = LSPClient()
        self.instructions = self.set_default_instructions()
        self.model_manager = ModelManager()
        self.model_manager.download_complete.connect(self.on_model_downloaded)
        self.model_manager.model_served.connect(self.on_model_served)
        self.model_manager.model_download_error.connect(self.on_model_error)
        
        self.current_model = None
        self.initUI()
        
        # Connect signals
        self.client.status_update.connect(self.update_status)
        self.client.models_loaded.connect(self.update_model_dropdown)
        self.client.initialization_finished.connect(self.on_ollama_initialized)
        self.client.server_ready.connect(self.on_server_ready)
        self.client.status_update.connect(self.client.output_window.append_output)

        # Initialize server in a separate thread
        self.init_thread = QThread()
        self.init_worker = OllamaInitWorker(self.client)
        self.init_worker.moveToThread(self.init_thread)
        self.init_thread.started.connect(self.init_worker.run)
        self.init_worker.finished.connect(self.init_thread.quit)
        self.init_worker.finished.connect(self.init_worker.deleteLater)
        self.init_thread.finished.connect(self.init_thread.deleteLater)
        self.init_worker.log_message.connect(self.log_message)
        self.init_thread.start()
        
        # Connect signals
        self.client.status_update.connect(self.update_status)
        self.client.models_loaded.connect(self.update_model_dropdown)
        self.client.initialization_finished.connect(self.on_ollama_initialized)
        self.model_manager.start_ollama_signal.connect(self.show_ollama_starting_dialog)
        self.model_manager.ollama_started_signal.connect(self.hide_ollama_starting_dialog)
        self.model_manager.download_preparing.connect(self.on_download_preparing)
        self.model_manager.download_progress.connect(self.on_download_progress)
        
        # Connect signals after initialization
        self.model_dropdown.currentTextChanged.connect(self.on_model_changed)
        self.model_manager.model_changed.connect(self.on_model_change_success)
        self.model_manager.model_unavailable.connect(self.on_model_change_failure)

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
        layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Initializing...")
        layout.addWidget(self.status_label)

        # Model selection dropdown
        model_layout = QHBoxLayout()
        model_label = QLabel("Select Model:")
        self.model_dropdown = QComboBox()
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_dropdown)
        layout.addLayout(model_layout)
        
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
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)
        
        # User input
        self.user_input = QTextEdit()
        self.user_input.setFixedHeight(100)
        layout.addWidget(self.user_input)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel(self)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # Collapsible Model Section
        self.model_section = CollapsibleSection("Model Controls")
        layout.addWidget(self.model_section)
        
        self.model_button = QPushButton("Download Model")
        self.model_button.clicked.connect(self.download_model)
        self.model_section.add_widget(self.model_button)
        
        self.change_path_button = QPushButton("Change Download Path")
        self.change_path_button.clicked.connect(self.change_download_path)
        self.model_section.add_widget(self.change_path_button)
        
        self.serve_button = QPushButton("Serve Model")
        self.serve_button.clicked.connect(self.serve_model)
        self.model_section.add_widget(self.serve_button)
        
        self.edit_instructions_button = QPushButton("Edit AI Instructions")
        self.edit_instructions_button.clicked.connect(self.edit_instructions)
        self.model_section.add_widget(self.edit_instructions_button)

        # Add a button to show/hide Ollama output window
        self.show_ollama_output_button = QPushButton("Show Ollama Output")
        self.show_ollama_output_button.clicked.connect(self.toggle_ollama_output)
        layout.addWidget(self.show_ollama_output_button)
        
        self.setLayout(layout)

    def toggle_ollama_output(self):
        if self.client.output_window.isVisible():
            self.client.hide_output_window()
            self.show_ollama_output_button.setText("Show Ollama Output")
        else:
            self.client.show_output_window()
            self.show_ollama_output_button.setText("Hide Ollama Output")

    def update_status(self, message):
        self.status_label.setText(message)
        logging.info(message)

    def on_model_changed(self, new_model):
        self.model_manager.change_model(new_model)

    def on_model_change_success(self, new_model):
        self.current_model = new_model
        self.status_label.setText(f"Model changed to: {new_model}")
        self.status_label.setStyleSheet("color: green")

    def on_model_change_failure(self, error_message):
        self.status_label.setText(f"Failed to change model: {error_message}")
        self.status_label.setStyleSheet("color: red")
        # Revert the dropdown to the current model
        self.model_dropdown.setCurrentText(self.current_model)

    def update_model_dropdown(self, models):
        self.model_dropdown.clear()
        self.model_dropdown.addItems(models)
        if models:
            self.current_model = models[0]
            self.model_dropdown.setCurrentText(self.current_model)

    def on_model_downloaded(self):
        self.model_button.setText("Model Downloaded")
        self.model_button.setEnabled(False)
        self.progress_bar.setVisible(False)

    def on_model_served(self):
        self.serve_button.setText("Model Served")
        self.serve_button.setEnabled(False)

    def on_model_error(self, error):
        SelectableMessageBox("AAAAAAAAA", error, self).exec()
        self.model_button.setText("Download Model")
        self.model_button.setEnabled(True)
        self.serve_button.setEnabled(False)
        self.progress_bar.setVisible(False)

    def on_download_progress(self, bytes_downloaded, total_bytes):
        logging.info(f"AIChatWidget: Progress {bytes_downloaded}/{total_bytes} bytes")
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        # Ensure total_bytes is treated as unsigned
        total_bytes = int(total_bytes) & 0xFFFFFFFF

        if total_bytes > 0:
            progress = int((bytes_downloaded / total_bytes) * 100)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress)
            
            downloaded_size = self.format_size(bytes_downloaded)
            total_size = self.format_size(total_bytes)
            
            self.progress_bar.setFormat(f"{progress}%")
            self.progress_label.setText(f"Downloaded {downloaded_size} of {total_size}")
        else:
            self.progress_bar.setRange(0, 0)
            downloaded_size = self.format_size(bytes_downloaded)
            self.progress_label.setText(f"Downloaded {downloaded_size}")

        # Update the status dialog
        if hasattr(self, 'status_dialog'):
            self.status_dialog.update_progress(progress, f"Downloaded {downloaded_size} of {total_size}")

        # Force the UI to update
        QApplication.processEvents()

    def format_size(self, size_bytes):
        # Convert bytes to human-readable format
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def change_download_path(self):
        new_path = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if new_path:
            self.model_manager.set_model_path(new_path)
            SelectableMessageBox.information(self, "Path Changed", f"Download path changed to:\n{new_path}").exec()

    def download_model(self):
        model_size = self.model_manager.get_model_size()
        model_path = self.model_manager.model_path
        
        confirm_message = (
            f"Are you sure you want to download the model?\n\n"
            f"Model: {self.model_manager.model_name}\n"
            f"Size: {humanize.naturalsize(model_size)}\n"
            f"Location: {model_path}\n\n"
            f"If disk space is an issue, consider using BigLinks to create a symlink and free up space, or edit path; untested"
        )
        
        reply = QMessageBox.question(self, 'Confirm Download', confirm_message,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.model_button.setEnabled(False)
            self.model_button.setText("Downloading...")
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.model_manager.download_model()
        else:
            self.chat_display.append("Model download cancelled by user.")

    def serve_model(self):
        self.model_manager.serve_model()

    def send_message(self):
        user_message = self.user_input.toPlainText()
        if user_message:
            self.chat_display.append(f"User: {user_message}")
            self.user_input.clear()
            
            context = self.context_manager.get_context()
            novel_parts = self.novelty_detector.get_novel_parts(context)
            novel_content = "\n".join(novel_parts) if novel_parts else "No novel content detected."

            system_prompt = f"""
            Instructions for AI:
            {self.instructions}

            Novel parts of current context:
            ```
            {novel_content}
            ```

            Full Context:
            {context}
            """

            if self.client.is_initialized:
                self.status_label.setText("Generating response...")
                response = self.client.generate(user_message, system_prompt, self.current_model)
                self.chat_display.append(f"AI: {response}")
                self.status_label.setText("Response generated")
            else:
                self.chat_display.append("Error: Ollama server is not initialized. Please wait for initialization to complete.")
                self.status_label.setText("Ollama server not initialized")

    def display_response(self, response):
        formatted_response = self.format_response_with_file_references(response)
        self.chat_display.append(f"AI: {formatted_response}")

        diff_blocks = self.extract_diff_blocks(response)
        if diff_blocks:
            self.show_diff_merger(diff_blocks)

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

    def extract_diff_blocks(self, response):
        diff_blocks = []
        lines = response.split('\n')
        current_file = None
        current_block = []

        for line in lines:
            if line.startswith("```") and ":" in line:
                if current_file and current_block:
                    diff_blocks.append((current_file, current_block))
                    current_block = []
                current_file = line.split(":")[1].strip()
            elif line.startswith("```"):
                if current_file and current_block:
                    diff_blocks.append((current_file, current_block))
                    current_file = None
                    current_block = []
            elif current_file:
                current_block.append(line)

        if current_file and current_block:
            diff_blocks.append((current_file, current_block))

        return diff_blocks

    def show_diff_merger(self, diff_blocks):
        if self.current_file_path and self.current_file_content:
            for file_path, block in diff_blocks:
                if os.path.basename(file_path) == os.path.basename(self.current_file_path):
                    merged_content = self.apply_diff_to_content(self.current_file_content, [(file_path, block)])
                    diff_merger = DiffMergerWidget(self.current_file_content, merged_content, self)
                    if diff_merger.exec() == QDialog.DialogCode.Accepted:
                        self.current_file_content = diff_merger.get_merged_content()
                        # Here you might want to update the main editor with the new content
                        # self.parent().update_editor_content(self.current_file_content)
                    break

    def apply_diff_to_content(self, content, diff_blocks):
        lines = content.split('\n')
        for _, block in diff_blocks:
            for line in block:
                if line.startswith('+'):
                    match = re.match(r'\+(\d+):', line)
                    if match:
                        line_num = int(match.group(1)) - 1
                        new_line = line[len(match.group(0)):].strip()
                        lines.insert(line_num, new_line)
                elif line.startswith('-'):
                    match = re.match(r'-(\d+):', line)
                    if match:
                        line_num = int(match.group(1)) - 1
                        if 0 <= line_num < len(lines):
                            lines.pop(line_num)
        return '\n'.join(lines)

    def add_references(self):
        dialog = ContextPickerDialog(self, recent_files=self.recent_files, open_files=self.parent().get_open_files(), existing_contexts=[desc for desc, _ in self.context_manager.contexts])
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
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setFormat("Preparing download...")
        self.progress_bar.setVisible(True)

    def on_ollama_initialized(self, success):
        if success:
            self.status_label.setText("Ollama server initialized and ready")
            self.load_installed_models()
        else:
            self.status_label.setText("Failed to initialize Ollama server. Please check the logs and try again.")
        self.init_thread.quit()
        self.init_thread.wait()

    def load_installed_models(self):
        models = self.client.get_installed_models()
        self.update_model_dropdown(models)

    def on_server_ready(self):
        logging.info("Server is ready, performing post-initialization tasks...")
        self.client.output_window.append_output("Server is ready, loading models...")
        self.fetch_models()

    def fetch_models(self):
        self.model_fetch_thread = QThread()
        self.model_fetch_worker = ModelFetchWorker(self.client)
        self.model_fetch_worker.moveToThread(self.model_fetch_thread)
        self.model_fetch_thread.started.connect(self.model_fetch_worker.run)
        self.model_fetch_worker.finished.connect(self.update_model_dropdown)
        self.model_fetch_worker.finished.connect(self.model_fetch_thread.quit)
        self.model_fetch_worker.finished.connect(self.model_fetch_worker.deleteLater)
        self.model_fetch_thread.finished.connect(self.model_fetch_thread.deleteLater)
        self.model_fetch_thread.start()

    def log_message(self, message):
        logging.info(message)

    def show_ollama_starting_dialog(self):
        self.client.show_output_window()
        self.show_ollama_output_button.setText("Hide Ollama Output")

    def hide_ollama_starting_dialog(self):
        self.client.hide_output_window()
        self.show_ollama_output_button.setText("Show Ollama Output")
        # You can also update your UI here if needed

class OllamaInitWorker(QObject):
    finished = pyqtSignal()
    log_message = pyqtSignal(str)

    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self):
        self.log_message.emit("Starting Ollama initialization...")
        self.client.initialize_server()
        self.log_message.emit("Ollama initialization finished.")
        self.finished.emit()


    