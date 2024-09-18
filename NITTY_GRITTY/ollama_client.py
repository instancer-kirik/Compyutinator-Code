import requests
import subprocess
import time
import logging
import os
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, Qt
import threading

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton

class OllamaOutputWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.output_text = QTextEdit(self)
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.hide)
        layout.addWidget(close_button)

        self.setLayout(layout)
        self.setWindowTitle("Ollama Status")
        self.resize(400, 300)

    def append_output(self, text):
        self.output_text.append(text)

class OllamaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = OllamaClient.get_instance()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.output_text = QTextEdit(self)
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)
        self.setLayout(layout)

        # Connect signals
        self.client.status_update.connect(self.update_status)
        self.client.initialization_finished.connect(self.on_initialization_finished)

    @pyqtSlot(str)
    def update_status(self, message):
        self.output_text.append(message)

    @pyqtSlot(bool)
    def on_initialization_finished(self, success):
        message = "Ollama initialization completed successfully." if success else "Ollama initialization failed."
        self.update_status(message)

class OllamaOutputReader(QObject):
    output_received = pyqtSignal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process

    def run(self):
        for line in self.process.stdout:
            self.output_received.emit(line.decode().strip())

class OllamaClient(QObject):
    status_update = pyqtSignal(str)
    models_loaded = pyqtSignal(list)
    initialization_finished = pyqtSignal(bool)
    server_ready = pyqtSignal()

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, base_url=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(base_url)
        return cls._instance

    def __init__(self, base_url=None):
        super().__init__()
        self.base_url = base_url or "http://localhost:11434"
        self.is_initialized = False
        self.models = []
        self.init_thread = None
        self.output_window = OllamaOutputWindow()

    def initialize_server(self):
        if self.init_thread and self.init_thread.isRunning():
            self.status_update.emit("Ollama server initialization already in progress.")
            return
        if self.is_initialized:
            self.status_update.emit("Ollama server already initialized.")
            return

        self.init_thread = QThread()
        worker = OllamaInitWorker(self)
        worker.moveToThread(self.init_thread)
        self.init_thread.started.connect(worker.run)
        worker.finished.connect(self.init_thread.quit)
        worker.finished.connect(worker.deleteLater)
        self.init_thread.finished.connect(self.init_thread.deleteLater)
        self.init_thread.start()

    def _initialize_server(self):
        self.status_update.emit("Initializing Ollama server...")
        max_retries = 5
        for attempt in range(max_retries):
            self.status_update.emit(f"Attempt {attempt + 1} to start Ollama server")
            if self.is_server_ready():
                self.is_initialized = True
                self.status_update.emit("Ollama server started and ready.")
                self.initialization_finished.emit(True)
                self.server_ready.emit()
                return
            time.sleep(2)
        self.status_update.emit("Failed to start Ollama server after multiple attempts.")
        self.initialization_finished.emit(False)

    def is_server_ready(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_installed_models(self):
        if self.models:
            self.status_update.emit(f"Using cached models: {self.models}")
            return self.models

        self.status_update.emit("Fetching installed models...")
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=30)
            response.raise_for_status()
            models = response.json()
            self.models = [model['name'] for model in models['models']]
            self.status_update.emit(f"Fetched models: {self.models}")
            self.models_loaded.emit(self.models)
            return self.models
        except requests.RequestException as e:
            error_message = f"Failed to fetch installed models: {str(e)}"
            self.status_update.emit(error_message)
            logging.error(error_message)
            return []

    def is_model_available(self, model_name):
        if not self.is_initialized:
            logging.info("Ollama server is not initialized.")
            return False

        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json()
            available_models = [model['name'] for model in models['models']]
            return model_name in available_models
        except requests.RequestException as e:
            logging.error(f"Failed to check model availability: {str(e)}")
            return False

    def generate(self, prompt, system_prompt, model):
        if not self.is_initialized:
            return "Ollama server is not initialized. Please initialize first."

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response.json()['response']
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    error_message = f"Generation failed after {max_retries} attempts: {str(e)}"
                    logging.error(error_message)
                    return error_message
                else:
                    logging.info(f"Generation attempt {attempt + 1} failed. Retrying...")
                    time.sleep(2)

    def update_status(self, message):
        self.status_update.emit(message)
        self.output_window.append_output(message)

    def show_output_window(self):
        self.output_window.show()

    def hide_output_window(self):
        self.output_window.hide()

class OllamaInitWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self):
        self.client._initialize_server()
        self.finished.emit()