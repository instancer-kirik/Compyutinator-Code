import os
from dotenv import load_dotenv
import openai
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# Load environment variables from .env file
load_dotenv()
#want to get context drops working and the rest of it working too lol

class OpenAIClient:
    def __init__(self, api_key, context=""):
        self.client = openai.OpenAI(api_key=api_key)
        self.context = context

    def ask_question(self, question, model="gpt-3.5-turbo"):
        full_question = f"Context: {self.context}\nQuestion: {question}"
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_question}
            ]
        )
        return response.choices[0].message['content'].strip()

class AIChatWorker(QThread):
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, message, context="", parent=None):
        super().__init__(parent)
        self.client = OpenAIClient(api_key, context)
        self.message = message

    def run(self):
        try:
            response = self.client.ask_question(self.message)
            self.result.emit(response)
        except Exception as e:
            self.error.emit(str(e))

class AIChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.context = ""

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.context_label = QLabel("Context: None")
        self.layout.addWidget(self.context_label)

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

    def set_context(self, context):
        self.context = context
        self.context_label.setText(f"Context: {context}")

    def send_message(self):
        user_message = self.input_line.text().strip()
        if user_message:
            self.chat_display.append(f"User: {user_message}")
            self.input_line.clear()
            self.get_ai_response(user_message)

    def get_ai_response(self, message):
        if not self.api_key:
            self.chat_display.append("Error: OpenAI API key is not set.")
            return

        self.thread = AIChatWorker(self.api_key, message, self.context)
        self.thread.result.connect(self.display_response)
        self.thread.error.connect(self.display_error)
        self.thread.start()

    def display_response(self, response):
        self.chat_display.append(f"AI: {response}")
        self.scroll_to_bottom()

    def display_error(self, error_message):
        self.chat_display.append(f"Error: {error_message}")

    def scroll_to_top(self):
        self.chat_display.moveCursor(Qt.TextCursor.Start)

    def scroll_to_bottom(self):
        self.chat_display.moveCursor(Qt.TextCursor.End)
