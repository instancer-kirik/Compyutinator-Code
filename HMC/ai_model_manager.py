import os
import subprocess
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread

import time
import psutil
import hashlib
import requests
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QProcess
from llama_cpp import Llama

from PyQt6.QtCore import QSettings

class ModelLoadWorker(QThread):
    progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes
    finished = pyqtSignal(Llama)
    error = pyqtSignal(str)
    
    def __init__(self, repo_id, filename):
        super().__init__()
        self.repo_id = repo_id
        self.filename = filename

    def run(self):
        try:
            def progress_callback(bytes_downloaded, total_bytes):
                self.progress.emit(bytes_downloaded, total_bytes)

            model = Llama.from_pretrained(
                repo_id=self.repo_id,
                filename=self.filename,
                n_ctx=2048,
                progress_callback=progress_callback
            )
            self.finished.emit(model)
        except Exception as e:
            self.error.emit(str(e))

class GenerateWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model, messages, max_tokens):
        super().__init__()
        self.model = model
        self.messages = messages
        self.max_tokens = max_tokens

    def run(self):
        try:
            response = self.model.create_chat_completion(
                messages=self.messages,
                max_tokens=self.max_tokens
            )
            self.finished.emit(response['choices'][0]['message']['content'])
        except Exception as e:
            self.error.emit(str(e))

class ModelManager(QObject):
    model_loading = pyqtSignal()
    model_loaded = pyqtSignal(str)
    model_error = pyqtSignal(str)
    model_download_progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes
    generation_finished = pyqtSignal(str)
    generation_error = pyqtSignal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.model = None
        self.current_model_name = None
        self.generate_worker = None
        self.load_worker = None

    def load_model(self, repo_id, filename):
        self.model_loading.emit()
        self.load_worker = ModelLoadWorker(repo_id, filename)
        self.load_worker.progress.connect(self.model_download_progress)
        self.load_worker.finished.connect(self.on_model_loaded)
        self.load_worker.error.connect(self.on_model_error)
        self.load_worker.start()

    def on_model_loaded(self, model):
        self.model = model
        self.current_model_name = self.load_worker.filename
        logging.info(f"Model loaded successfully: {self.current_model_name}")
        self.model_loaded.emit(self.current_model_name)

    def on_model_error(self, error):
        error_msg = f"Failed to load model: {error}"
        logging.error(error_msg)
        self.model_error.emit(error_msg)

    def generate(self, messages, max_tokens=256):
        if not self.model:
            raise RuntimeError("Model not loaded. Please load a model first.")
        
        logging.warning(f"Generating response for messages: {messages}")
        self.generate_worker = GenerateWorker(self.model, messages, max_tokens)
        self.generate_worker.finished.connect(self.on_generation_finished)
        self.generate_worker.error.connect(self.on_generation_error)
        self.generate_worker.start()

    def on_generation_finished(self, response):
        self.generation_finished.emit(response)

    def on_generation_error(self, error):
        logging.error(f"Generation error: {error}")
        self.generation_error.emit(str(error))

    def get_model_size(self, model_name=None):
        if model_name is None:
            model_name = self.current_model_name
        
        if model_name is None:
            logging.warning("No model specified and no current model loaded.")
            return 0
        
        model_path = os.path.join(self.models_dir, model_name)
        if not os.path.exists(model_path):
            logging.error(f"Model file not found: {model_path}")
            return 0
        
        return os.path.getsize(model_path)

   

    def get_installed_models(self):
        models = [f for f in os.listdir(self.models_dir) if f.endswith('.gguf')]
        complete_models = [model for model in models if self.check_model_integrity(model)]
        return complete_models

