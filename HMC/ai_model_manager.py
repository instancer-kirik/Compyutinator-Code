import os
import subprocess
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from GUX.status_dialog import StatusDialog
from HMC.download_manager import DownloadManager
from NITTY_GRITTY.ollama_client import OllamaClient
from HMC.thread_controller import ProcessController
import time
import psutil
import hashlib
import requests
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QProcess
from llama_cpp import Llama

from PyQt6.QtCore import QSettings

class ModelLoadWorker(QThread):
    finished = pyqtSignal(Llama)
    error = pyqtSignal(str)
    
    def __init__(self, model_path):
        super().__init__()
        self.model_path = model_path

    def run(self):
        try:
            model = Llama(model_path=self.model_path, n_ctx=2048)
            self.finished.emit(model)
        except Exception as e:
            self.error.emit(str(e))

class GenerateWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model, prompt, max_tokens):
        super().__init__()
        self.model = model
        self.prompt = prompt
        self.max_tokens = max_tokens

    def run(self):
        try:
            output = self.model(self.prompt, max_tokens=self.max_tokens)
            self.finished.emit(output['choices'][0]['text'])
        except Exception as e:
            self.error.emit(str(e))

class ModelManager(QObject):
    model_loaded = pyqtSignal(str)  # Emit model name when loaded
    model_changed = pyqtSignal(str)  # Emit model name when loaded
    model_error = pyqtSignal(str)
    model_unloaded = pyqtSignal()  # Emit when model is unloaded
    
    model_download_started = pyqtSignal(str)  # Emit download ID
    model_download_progress = pyqtSignal(str, int, int)  # id, bytes_downloaded, total_bytes
    model_download_complete = pyqtSignal(str)  # Emit download ID
    model_download_error = pyqtSignal(str, str)  # id, error_message
    models_list_updated = pyqtSignal(list)
    model_path_changed = pyqtSignal(str)  # New signal for path change

    def __init__(self, settings, download_manager):
        super().__init__()
        self.settings = settings
        self.download_manager = download_manager
        self.model = None
        self.current_model_name = None
        self.models_dir = self.load_models_directory()
        os.makedirs(self.models_dir, exist_ok=True)
        self.connect_download_signals()
        self.update_models_list()
        logging.info(f"ModelManager initialized. Models directory: {self.models_dir}")
        self.active_downloads = {}  # Keep track of active downloads

    def load_models_directory(self):
        saved_dir = self.settings.value("models_directory", None)
        if saved_dir and os.path.isdir(saved_dir):
            return saved_dir
        return self.get_default_models_directory()

    def get_default_models_directory(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        return os.path.join(project_root, 'llama_models')

    def set_model_path(self, new_path):
        if os.path.isdir(new_path):
            self.models_dir = new_path
            self.settings.setValue("models_directory", new_path)
            os.makedirs(self.models_dir, exist_ok=True)
            self.update_models_list()
            self.model_path = new_path
            self.model_path_changed.emit(new_path)
            logging.info(f"Model path changed to: {new_path}")
        else:
            logging.error(f"Invalid path: {new_path}")
            raise ValueError(f"Invalid path: {new_path}")
        
        
      
    def connect_download_signals(self):
        self.download_manager.download_preparing.connect(lambda id: self.model_download_started.emit(id))
        self.download_manager.download_progress.connect(self.model_download_progress)
        self.download_manager.download_complete.connect(self.on_download_complete)
        self.download_manager.download_error.connect(self.model_download_error)

    def update_models_list(self):
        models = [f for f in os.listdir(self.models_dir) if f.endswith('.gguf')]
        logging.info(f"Found models: {models}")
        self.models_list_updated.emit(models)

    def load_model(self, model_name):
        model_path = os.path.join(self.models_dir, model_name)
        if not os.path.exists(model_path):
            error_msg = f"Model file not found: {model_path}"
            logging.error(error_msg)
            self.model_error.emit(error_msg)
            return
        self.model_path = model_path
        self.load_worker = ModelLoadWorker(model_path)
        self.load_worker.finished.connect(lambda model: self.on_model_loaded(model, model_name))
        self.load_worker.error.connect(self.model_error)
        self.load_worker.start()
        logging.info(f"Starting to load model: {model_name}")

    def on_model_loaded(self, model, model_name):
        self.model = model
        self.current_model_name = model_name
        logging.info(f"Model loaded successfully: {model_name}")
        self.model_loaded.emit(model_name)

    def unload_model(self):
        self.model = None
        self.current_model_name = None
        self.model_unloaded.emit()

    def generate(self, prompt, max_tokens=256):
        if not self.model:
            return "Model not loaded. Please load a model first."
        
        self.generate_worker = GenerateWorker(self.model, prompt, max_tokens)
        self.generate_worker.finished.connect(self.on_generation_finished)
        self.generate_worker.error.connect(self.on_generation_error)
        self.generate_worker.start()

    def on_generation_finished(self, response):
        # You might want to emit a signal here or handle the response in some way
        pass

    def on_generation_error(self, error):
        # Handle the error, maybe emit a signal
        pass

    def download_model(self, model_url, model_name):
        destination = os.path.join(self.models_dir, model_name)
        download_id = self.download_manager.start_download(model_url, destination)
        self.active_downloads[download_id] = model_name
        return download_id

    def on_download_complete(self, download_id):
        if download_id in self.active_downloads:
            model_name = self.active_downloads[download_id]
            del self.active_downloads[download_id]
            self.model_download_complete.emit(download_id)
            self.update_models_list()
            logging.info(f"Download completed for model: {model_name}")

    def get_model_path(self):
        return self.models_dir  # Changed from self.model_path to self.models_dir

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

    def check_model_integrity(self, model_name):
        model_path = os.path.join(self.models_dir, model_name)
        if os.path.exists(model_path):
            expected_size = 3_981_927_424  # Size of the fully downloaded model in bytes
            actual_size = os.path.getsize(model_path)
            if actual_size == expected_size:
                return True
            else:
                logging.warning(f"Model {model_name} is incomplete. Expected {expected_size} bytes, found {actual_size} bytes.")
                return False
        return False

    def get_installed_models(self):
        models = [f for f in os.listdir(self.models_dir) if f.endswith('.gguf')]
        complete_models = [model for model in models if self.check_model_integrity(model)]
        return complete_models

