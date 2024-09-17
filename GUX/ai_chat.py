import os
from dotenv import load_dotenv
import requests
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, 
                             QPushButton, QHBoxLayout, QLabel, QComboBox, 
                             QMessageBox, QFileDialog, QScrollArea, QInputDialog,
                             QDialog, QListWidget, QAbstractItemView)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QMimeData
from PyQt6.QtGui import QTextCursor, QDragEnterEvent, QDropEvent
from GUX.diff_merger import DiffMergerWidget
from HMC.context_manager import ContextManager
import tiktoken
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import importlib
import inspect
import mimetypes
import ast
from transformers import LlamaTokenizer
from NITTY_GRITTY.LSPClient import LSPClient
# Load environment variables from .env file
load_dotenv()

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", context=""):
        self.base_url = base_url
        self.context = context

    def ask_question(self, question, model):
        full_question = f"Context: {self.context}\nQuestion: {question}"
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": full_question,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()['response'].strip()

    def get_available_models(self):
        response = requests.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        return [model['name'] for model in response.json()['models']]

class AIChatWorker(QThread):
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, base_url, message, model, context="", parent=None):
        super().__init__(parent)
        self.client = OllamaClient(base_url, context)
        self.message = message
        self.model = model

    def run(self):
        try:
            response = self.client.ask_question(self.message, self.model)
            self.result.emit(response)
        except Exception as e:
            self.error.emit(str(e))

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

class NoveltyDetector:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', min_df=1)
        self.previous_vectors = None

    def get_novel_parts(self, text, num_sentences=5):
        sentences = text.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []  # Return empty list if there are no sentences

        try:
            # Compute TF-IDF
            tfidf_matrix = self.vectorizer.fit_transform(sentences)

            if self.previous_vectors is not None:
                # Compute novelty scores
                similarities = cosine_similarity(tfidf_matrix, self.previous_vectors)
                novelty_scores = 1 - similarities.max(axis=1)
            else:
                # If it's the first time, consider all sentences equally novel
                novelty_scores = np.ones(len(sentences))

            # Get indices of top novel sentences
            top_indices = novelty_scores.argsort()[-num_sentences:][::-1]

            # Update previous vectors
            self.previous_vectors = tfidf_matrix

            # Return top novel sentences
            return [sentences[i] for i in top_indices]
        except ValueError:
            # If vocabulary is empty, return all sentences
            return sentences[:num_sentences]

class ContextPickerDialog(QDialog):
    def __init__(self, parent, recent_files, open_files, existing_contexts):
        super().__init__(parent)
        self.setWindowTitle("Add Context")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setDragEnabled(True)
        self.file_list.setAcceptDrops(True)
        self.file_list.setDropIndicatorShown(True)
        self.file_list.dragEnterEvent = self.dragEnterEvent
        self.file_list.dropEvent = self.dropEvent
        layout.addWidget(self.file_list)

        self.populate_file_list(recent_files, open_files, existing_contexts)

        button_layout = QHBoxLayout()
        self.clipboard_button = QPushButton("Add from Clipboard")
        self.clipboard_button.clicked.connect(self.add_from_clipboard)
        button_layout.addWidget(self.clipboard_button)

        self.text_button = QPushButton("Add Custom Text")
        self.text_button.clicked.connect(self.add_custom_text)
        button_layout.addWidget(self.text_button)

        self.import_button = QPushButton("Add Python Import")
        self.import_button.clicked.connect(self.add_python_import)
        button_layout.addWidget(self.import_button)

        self.outline_button = QPushButton("Add File Outline")
        self.outline_button.clicked.connect(self.add_file_outline)
        button_layout.addWidget(self.outline_button)

        layout.addLayout(button_layout)

        button_box = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_box.addWidget(self.ok_button)
        button_box.addWidget(self.cancel_button)
        layout.addLayout(button_box)

    def populate_file_list(self, recent_files, open_files, existing_contexts):
        self.file_list.clear()
        for file in open_files:
            if file not in existing_contexts:
                self.file_list.addItem(f"[Open] {file}")
        for file in recent_files:
            if file not in existing_contexts and file not in open_files:
                self.file_list.addItem(f"[Recent] {file}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.add_file(file_path)
        elif event.mimeData().hasText():
            self.add_text(event.mimeData().text())

    def add_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        if mime_data.hasText():
            self.add_text(mime_data.text())

    def add_custom_text(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Custom Text", "Enter your text:")
        if ok and text:
            self.add_text(text)

    def add_python_import(self):
        module_name, ok = QInputDialog.getText(self, "Add Python Import", "Enter module name:")
        if ok and module_name:
            try:
                module_spec = importlib.util.find_spec(module_name)
                if module_spec:
                    self.file_list.addItem(f"[Import] {module_name}")
                else:
                    raise ImportError(f"Module {module_name} not found")
            except ImportError as e:
                QMessageBox.warning(self, "Import Error", str(e))

    def add_file(self, file_path):
        if os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('text'):
                self.file_list.addItem(f"[Text File] {file_path}")
            else:
                self.file_list.addItem(f"[Binary File] {file_path}")
        else:
            QMessageBox.warning(self, "Invalid File", f"The path {file_path} is not a valid file.")

    def add_text(self, text):
        preview = text[:50] + "..." if len(text) > 50 else text
        self.file_list.addItem(f"[Text] {preview}")

    def add_file_outline(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File for Outline")
        if file_path:
            self.file_list.addItem(f"[Outline] {file_path}")

    def get_selected_items(self):
        return [item.text() for item in self.file_list.selectedItems()]


class AIChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.context = ""
        self.client = OllamaClient(self.ollama_base_url)
        self.current_file_content = ""
        self.current_file_path = ""
        self.novelty_detector = NoveltyDetector()
        self.context_manager = ContextManager(max_tokens=4000, model_name="arcee-ai/Llama-3.1-SuperNova-Lite")
        self.instructions = """
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
        11. 
        """
        self.recent_files = []  # You'll need to populate this list
        self.lsp_client = LSPClient()
        self.lsp_client.completionsReceived.connect(self.show_completions)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Add a new horizontal layout for the context button
        context_layout = QHBoxLayout()
        self.context_label = QLabel("Context: None")
        context_layout.addWidget(self.context_label)

        self.add_context_button = QPushButton("+")
        self.add_context_button.setFixedSize(30, 30)  # Make the button small and square
        self.add_context_button.clicked.connect(self.add_context)
        context_layout.addWidget(self.add_context_button)

        layout.addLayout(context_layout)

        self.model_dropdown = QComboBox()
        layout.addWidget(self.model_dropdown)
        self.populate_model_dropdown()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type your message here...")
        self.input_line.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_line)

        button_layout = QHBoxLayout()
        self.scroll_to_top_button = QPushButton("Scroll to Top")
        self.scroll_to_top_button.clicked.connect(self.scroll_to_top)
        button_layout.addWidget(self.scroll_to_top_button)

        self.scroll_to_bottom_button = QPushButton("Scroll to Bottom")
        self.scroll_to_bottom_button.clicked.connect(self.scroll_to_bottom)
        button_layout.addWidget(self.scroll_to_bottom_button)

        layout.addLayout(button_layout)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        self.compare_button = QPushButton("Compare Changes")
        self.compare_button.clicked.connect(self.open_diff_merger)
        layout.addWidget(self.compare_button)

        self.original_code = ""  # Store the original code here

        self.reference_widget = ChatReferenceWidget(self)
        layout.addWidget(self.reference_widget)

        # Add code editor
        self.code_editor = QTextEdit(self)
        layout.addWidget(self.code_editor)

        # Connect signals
        self.code_editor.textChanged.connect(self.request_completions)

    def populate_model_dropdown(self):
        try:
            models = self.client.get_available_models()
            self.model_dropdown.addItems(models)
        except Exception as e:
            print(f"Error fetching models: {e}")
            self.model_dropdown.addItem("Error fetching models")

    def set_context(self, context):
        self.context = context
        self.context_label.setText(f"Context: {context}")
        self.original_code = context  # Store the original code

    def set_current_file(self, file_path, file_content):
        self.current_file_path = file_path
        self.current_file_content = file_content
        self.context_label.setText(f"Context: {os.path.basename(file_path)}")

    def send_message(self):
        user_message = self.input_line.text().strip()
        if user_message:
            self.chat_display.append(f"User: {user_message}")
            self.input_line.clear()
            self.get_ai_response(user_message)

    def get_ai_response(self, message):
        selected_model = self.model_dropdown.currentText()
        context = self.get_context()
        
        novel_parts = self.novelty_detector.get_novel_parts(self.current_file_content)
        novel_content = "\n".join(novel_parts) if novel_parts else "No novel content detected."

        full_context = f"""
        File: {self.current_file_path}

        Novel parts of current content:
        ```
        {novel_content}
        ```

        Context:
        {context}

        Instructions:
        {self.instructions}

        User message: {message}
        """
        
        truncated_context = self.truncate_context(full_context)
        
        self.thread = AIChatWorker(self.ollama_base_url, truncated_context, selected_model, self.context)
        self.thread.result.connect(self.display_response)
        self.thread.error.connect(self.display_error)
        self.thread.start()

    def display_response(self, response):
        formatted_response = self.format_response_with_file_references(response)
        self.chat_display.setPlainText(formatted_response)
        self.scroll_to_bottom()

    def format_response_with_file_references(self, response):
        formatted_response = f"Response for {self.current_file_path}:\n\n"
        diff_blocks = []
        current_file = None
        current_block = []

        for line in response.split('\n'):
            if line.startswith('```diff:'):
                if current_block:
                    diff_blocks.append((current_file, current_block))
                    current_block = []
                current_file = line.split(':')[1].strip()
            elif line.startswith('```') and current_file:
                if current_block:
                    diff_blocks.append((current_file, current_block))
                current_file = None
                current_block = []
            elif current_file and (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
                current_block.append(line)
            else:
                formatted_response += line + '\n'

        if current_block:
            diff_blocks.append((current_file, current_block))

        for file_path, block in diff_blocks:
            formatted_response += f"\nDiff for {file_path}:\n"
            formatted_response += '\n'.join(block) + '\n'

        return formatted_response

    def display_error(self, error_message):
        self.chat_display.append(f"Error: {error_message}")

    def scroll_to_top(self):
        self.chat_display.moveCursor(QTextCursor.MoveOperation.Start)

    def scroll_to_bottom(self):
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def open_diff_merger(self):
        if not self.current_file_content:
            QMessageBox.warning(self, "No File Open", "Please open a file in the editor first.")
            return

        ai_response = self.chat_display.toPlainText()
        diff_blocks = self.extract_diff_blocks(ai_response)
        
        if not diff_blocks:
            QMessageBox.warning(self, "No Diff Found", "No diff information found in the AI response.")
            return

        diff_merger = DiffMergerWidget()
        diff_merger.x_box.text_edit.setPlainText(self.current_file_content)
        
        suggested_content = self.apply_diff_to_content(self.current_file_content, diff_blocks)
        diff_merger.y_box.text_edit.setPlainText(suggested_content)
        
        diff_merger.show_diff()
        diff_merger.show()

    def extract_diff_blocks(self, response):
        diff_blocks = []
        current_file = None
        current_block = []

        for line in response.split('\n'):
            if line.startswith('```diff:'):
                if current_block:
                    diff_blocks.append((current_file, current_block))
                    current_block = []
                current_file = line.split(':')[1].strip()
            elif line.startswith('```') and current_file:
                if current_block:
                    diff_blocks.append((current_file, current_block))
                current_file = None
                current_block = []
            elif current_file and (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
                current_block.append(line)

        if current_block:
            diff_blocks.append((current_file, current_block))

        return diff_blocks

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

    def get_suggested_changes(self):
        # This method should return the AI's suggested changes
        # For now, we'll just return the entire chat display content
        return self.chat_display.toPlainText()

    def add_chat_reference(self, text, context):
        self.reference_widget.add_reference(text, context)
        self.context_manager.add_context(context, text)
        self.update_context_label()

    def get_context(self):
        return self.context_manager.get_context()

    def truncate_context(self, context, max_tokens=4000):
        tokens = self.context_manager.tokenize(context)
        if len(tokens) > max_tokens:
            truncated_tokens = tokens[:max_tokens]
            return self.context_manager.detokenize(truncated_tokens)
        return context

    def get_instructions(self):
        return self.instructions

    def set_instructions(self, new_instructions):
        self.instructions = new_instructions

    def add_context(self):
        open_files = self.parent().get_open_files()
        existing_contexts = [ref[1] for ref in self.context_manager.contexts]
        dialog = ContextPickerDialog(self, self.recent_files, open_files, existing_contexts)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = dialog.get_selected_items()
            for item in selected_items:
                item_type, item_content = item.split("] ", 1)
                item_type = item_type[1:]  # Remove the leading '['
                
                if item_type in ["Open", "Recent", "Text File"]:
                    if self.context_manager.is_file_too_large(item_content):
                        QMessageBox.warning(self, "File Too Large", f"The file {item_content} is too large to add as context.")
                        continue
                    with open(item_content, 'r', encoding='utf-8') as file:
                        content = file.read()
                    self.context_manager.add_context(content, f"File: {item_content}")
                elif item_type == "Binary File":
                    if self.context_manager.is_file_too_large(item_content):
                        QMessageBox.warning(self, "File Too Large", f"The file {item_content} is too large to add as context.")
                        continue
                    with open(item_content, 'rb') as file:
                        content = file.read().hex()
                    self.context_manager.add_context(f"Hexdump of {item_content}:\n{content}", f"Binary File: {item_content}")
                elif item_type == "Import":
                    try:
                        module = importlib.import_module(item_content)
                        content = inspect.getsource(module)
                        self.context_manager.add_context(content, f"Import: {item_content}")
                    except Exception as e:
                        QMessageBox.warning(self, "Import Error", f"Failed to import {item_content}: {str(e)}")
                elif item_type == "Text":
                    self.context_manager.add_context(item_content, "Custom Text")
                elif item_type == "Outline":
                    outline = self.generate_file_outline(item_content)
                    self.context_manager.add_context(outline, f"File Outline: {item_content}")

            self.update_context_label()

    def generate_file_outline(self, file_path):
        with open(file_path, 'r') as file:
            content = file.read()
        
        try:
            tree = ast.parse(content)
            outline = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    outline.append(f"Function: {node.name}")
                elif isinstance(node, ast.ClassDef):
                    outline.append(f"Class: {node.name}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        outline.append(f"Import: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        outline.append(f"From {node.module} import {alias.name}")
            
            return "\n".join(outline)
        except SyntaxError:
            return f"Unable to parse {file_path}. It may not be a valid Python file."

    def add_selected_context(self):
        # This method should be called from the main window when text is selected
        selected_text = self.parent().get_selected_text()  # Implement this method in AuraTextWindow
        if selected_text:
            self.reference_widget.add_reference(f"Selection from {self.current_file_path}", selected_text)
            self.context_manager.add_context(selected_text, f"Selection from {self.current_file_path}")
            self.update_context_label()
        else:
            QMessageBox.warning(self, "No Selection", "Please select some text to add as context.")

    def add_file_context(self):
        if self.current_file_content:
            self.reference_widget.add_reference(f"Full content of {self.current_file_path}", self.current_file_content)
            self.context_manager.add_context(self.current_file_content, f"Full content of {self.current_file_path}")
            self.update_context_label()
        else:
            QMessageBox.warning(self, "No File Open", "Please open a file in the editor first.")

    def update_context_label(self):
        num_contexts = len(self.context_manager.contexts)
        total_tokens = self.context_manager.get_total_tokens()
        self.context_label.setText(f"Context: {num_contexts} item{'s' if num_contexts != 1 else ''} ({total_tokens} tokens)")

    def request_completions(self):
        cursor = self.code_editor.textCursor()
        position = {"line": cursor.blockNumber(), "character": cursor.columnNumber()}
        file_uri = f"file://{self.current_file_path}"
        self.lsp_client.request_completions(file_uri, position)

    def show_completions(self, completions):
        # Implement completion display logic here
        print("Received completions:", completions)

