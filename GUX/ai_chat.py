import os
from dotenv import load_dotenv
import requests
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QLabel, QComboBox, QMessageBox, QFileDialog
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QTextCursor
from GUX.diff_merger import DiffMergerWidget

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

class AIChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.context = ""
        self.client = OllamaClient(self.ollama_base_url)
        self.current_file_content = ""
        self.current_file_path = ""
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.context_label = QLabel("Context: None")
        self.layout.addWidget(self.context_label)

        self.model_dropdown = QComboBox()
        self.layout.addWidget(self.model_dropdown)
        self.populate_model_dropdown()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.layout.addWidget(self.chat_display)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type your message here...")
        self.input_line.returnPressed.connect(self.send_message)
        self.layout.addWidget(self.input_line)

        button_layout = QHBoxLayout()
        self.scroll_to_top_button = QPushButton("Scroll to Top")
        self.scroll_to_top_button.clicked.connect(self.scroll_to_top)
        button_layout.addWidget(self.scroll_to_top_button)

        self.scroll_to_bottom_button = QPushButton("Scroll to Bottom")
        self.scroll_to_bottom_button.clicked.connect(self.scroll_to_bottom)
        button_layout.addWidget(self.scroll_to_bottom_button)

        self.layout.addLayout(button_layout)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)

        self.compare_button = QPushButton("Compare Changes")
        self.compare_button.clicked.connect(self.open_diff_merger)
        self.layout.addWidget(self.compare_button)

        self.original_code = ""  # Store the original code here

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
        full_context = f"File: {self.current_file_path}\n\nCurrent content:\n{self.current_file_content}\n\nUser message: {message}"
        self.thread = AIChatWorker(self.ollama_base_url, full_context, selected_model, self.context)
        self.thread.result.connect(self.display_response)
        self.thread.error.connect(self.display_error)
        self.thread.start()

    def display_response(self, response):
        formatted_response = f"AI Suggested Changes:\n\n{response}"
        self.chat_display.setPlainText(formatted_response)
        self.scroll_to_bottom()

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

        ai_suggested_code = self.chat_display.toPlainText()
        
        diff_merger = DiffMergerWidget()
        diff_merger.x_box.text_edit.setPlainText(self.current_file_content)
        diff_merger.y_box.text_edit.setPlainText(ai_suggested_code)
        diff_merger.show_diff()
        diff_merger.show()
