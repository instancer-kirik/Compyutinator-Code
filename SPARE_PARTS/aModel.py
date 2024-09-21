import os
import time
import logging
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal
from HMC.ai_model_manager import ModelManager

class AModel(QObject):
    
    model_downloaded = pyqtSignal()
    model_served = pyqtSignal()
    model_error = pyqtSignal(str)
    model_available = pyqtSignal()
    model_unavailable = pyqtSignal(str)
    model_changed = pyqtSignal(str)  # New signal for model change

    def __init__(self, model_name = "supernova-lite"):
        super().__init__()
        self.model_manager = ModelManager()
        self.model_name = model_name
        self.model_manager.download_complete.connect(self.on_download_complete)
        self.model_manager.download_error.connect(self.on_download_error)
        self.model_manager.model_served.connect(self.on_model_served)
        self.model_manager.serve_error.connect(self.on_serve_error)
        self.model_manager.model_available.connect(self.on_model_available)
        self.model_manager.model_unavailable.connect(self.on_model_unavailable)

    def ensure_model(self):
        self.model_manager.ensure_model()

    def on_download_complete(self, model_path):
        logging.info(f"Download complete. Model saved at {model_path}")
        self.model_downloaded.emit()

    def on_download_error(self, error):
        self.model_error.emit(f"Download error: {error}")

    def on_model_served(self):
        self.model_served.emit()

    def on_serve_error(self, error):
        self.model_error.emit(f"Serve error: {error}")

    def on_model_available(self):
        self.model_available.emit()

    def on_model_unavailable(self, error):
        self.model_unavailable.emit(error)

    def serve_model(self):
        self.model_manager.serve_model()

    def generate(self, prompt, system_prompt="", max_tokens=256):
        return self.model_manager.generate(prompt, system_prompt, max_tokens)

    def is_model_available(self):
        return self.model_manager.is_model_available()

    def shutdown(self):
        self.model_manager.shutdown()

    def change_model(self, new_model_name):
        if self.model_manager.is_model_available(new_model_name):
            self.model_name = new_model_name
            self.model_changed.emit(new_model_name)
            logging.info(f"Model changed to: {new_model_name}")
        else:
            error_message = f"Model {new_model_name} is not available"
            logging.error(error_message)
            self.model_unavailable.emit(error_message)

