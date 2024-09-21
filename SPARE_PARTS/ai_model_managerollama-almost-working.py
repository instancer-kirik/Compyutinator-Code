import os
import subprocess
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from GUX.status_dialog import StatusDialog
from HMC.download_manager import DownloadManager
from SPARE_PARTS.ollama_client import OllamaClient
from HMC.thread_controller import ProcessController
import time
import psutil
import hashlib
import requests
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QProcess
class AIChatWorker(QThread):
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, client, message, model, system_prompt=""):
        super().__init__()
        self.client = client
        self.message = message
        self.model = model
        self.system_prompt = system_prompt

    def run(self):
        try:
            response = self.client.generate(self.message, self.system_prompt, self.model)
            self.result.emit(response)
        except Exception as e:
            self.error.emit(str(e))

class ModelManager(QObject):
    model_download_started = pyqtSignal(str)  # download_id
    model_download_progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes
    model_download_complete = pyqtSignal()
    model_download_error = pyqtSignal(str)  # error_message
    download_progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    download_preparing = pyqtSignal()
    model_served = pyqtSignal()
    serve_error = pyqtSignal(str)
    model_available = pyqtSignal()
    model_unavailable = pyqtSignal(str)
    start_ollama_signal = pyqtSignal()
    ollama_started_signal = pyqtSignal()
    model_changed = pyqtSignal(str)  # New signal for model change

    def __init__(self):
        super().__init__()
        self.download_manager = DownloadManager()
        self.download_manager.download_progress.connect(self.handle_download_progress)
        self.download_manager.download_complete.connect(self.handle_download_complete)
        self.download_manager.download_error.connect(self.handle_download_error)
        self.download_manager.download_preparing.connect(self.on_download_preparing)
        self.ollama_client = OllamaClient.get_instance()
        self.process_controller = ProcessController()
        self.model_name = "supernova-lite"
        self.gguf_model_name = "Llama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ6_K.gguf"
        self.model_url = f"https://huggingface.co/Joseph717171/Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF/resolve/main/{self.gguf_model_name}"
        self.model_path = self.get_default_model_path()
        self.model_is_served = False
        self.model_size = 3_700_000_000  # Approximate size in bytes (3.7 GB)
        self.current_download_id = None  # Add this line
        self.processes = []  # Keep track of running processes

    def get_default_model_path(self):
        home = os.path.expanduser("~")
        model_dir = os.path.join(home, ".cache", "llama_models")
        os.makedirs(model_dir, exist_ok=True)
        return os.path.join(model_dir, self.gguf_model_name)

    def set_model_path(self, new_path):
        self.model_path = os.path.join(new_path, self.gguf_model_name)
        logging.info(f"Model path changed to: {self.model_path}")

    def create_modelfile(self):
        modelfile_path = os.path.join(os.path.dirname(self.model_path), "Modelfile")
        with open(modelfile_path, 'w') as f:
            f.write(f"FROM {self.model_path}\n")
            f.write("PARAMETER stop \"Human:\"\n")
            f.write("PARAMETER stop \"Assistant:\"\n")
            f.write("SYSTEM You are a helpful AI assistant.\n")
        logging.info(f"Modelfile created at {modelfile_path}")
        return modelfile_path

    def ensure_model(self):
        if not self.ollama_client.is_initialized:
            logging.info("Ollama server not initialized. Initializing...")
            self.start_ollama_signal.emit()
            # Use QTimer to avoid blocking
            QTimer.singleShot(0, self.start_ollama)
        else:
            self.check_model_availability()

    def start_ollama(self):
        process = QProcess()
        process.finished.connect(lambda: self.processes.remove(process))
        self.processes.append(process)
        process.start("ollama", ["serve"])
        self.ollama_started_signal.emit()
        self.check_model_availability()

    def check_model_availability(self):
        logging.info("Checking model availability...")
        max_retries = 5
        for _ in range(max_retries):
            try:
                available_models = self.ollama_client.get_installed_models()
                if self.model_name in available_models:
                    logging.info(f"Model {self.model_name} is available")
                    self.model_available.emit()
                else:
                    logging.info(f"Model {self.model_name} is not available. Initiating download.")
                    self.download_model()
                return
            except Exception as e:
                logging.warning(f"Failed to check model availability: {str(e)}. Retrying...")
                time.sleep(2)
        logging.error("Failed to check model availability after multiple attempts")
        self.model_unavailable.emit("Failed to check model availability")

    def download_model(self):
        self.current_download_id = self.download_manager.start_download(self.model_url, self.model_path)
        self.model_download_started.emit(self.current_download_id)

    def handle_download_progress(self, download_id, bytes_downloaded, total_bytes):
        if download_id == self.current_download_id:
            self.model_download_progress.emit(bytes_downloaded, total_bytes)

    def handle_download_complete(self, download_id):
        if download_id == self.current_download_id:
            self.model_download_complete.emit()
            self.verify_model_integrity()
            self.current_download_id = None  # Reset the current download ID

    def handle_download_error(self, download_id, error_message):
        if download_id == self.current_download_id:
            detailed_error = f"Download failed for model {self.model_name}.\nError: {error_message}\nPlease check your internet connection and try again."
            self.model_download_error.emit(detailed_error)
            self.current_download_id = None  # Reset the current download ID

    def verify_model_integrity(self):
        # For now, let's assume the file is always corrupted to force a redownload
        logging.info("Model file integrity check failed. Redownloading...")
        os.remove(self.model_path)
        self.download_model()

    def handle_progress(self, destination, bytes_downloaded, total_bytes):
        # Ensure total_bytes is treated as unsigned
        total_bytes = int(total_bytes) & 0xFFFFFFFF
        logging.info(f"ModelManager: Progress {bytes_downloaded}/{total_bytes} bytes")
        self.download_progress.emit(bytes_downloaded, total_bytes)

    def handle_complete(self, download_id):
        modelfile_path = self.create_modelfile()
        self.download_complete.emit(self.model_path)
        logging.info(f"Download complete. Model saved at {self.model_path}")
        logging.info(f"Modelfile created at {modelfile_path}")

    def handle_error(self, download_id, error_message):
        logging.error(f"Download error: {error_message}")
        self.download_error.emit(error_message)
        # Reset the download state
        self.model_is_served = False
        # You might want to delete the partially downloaded file here
        if os.path.exists(self.model_path):
            os.remove(self.model_path)

    def serve_model(self):
        if not os.path.exists(self.model_path):
            error_message = f"Model file not found at {self.model_path}. Please download the model first."
            logging.error(error_message)
            self.serve_error.emit(error_message)
            return

        try:
            if not self.is_ollama_running():
                logging.info("Launching Ollama process...")
                self.process_controller.launch_ollama()
                logging.info("Waiting for Ollama to start...")
                time.sleep(5)
            else:
                logging.info("Ollama is already running.")

            # Check if the model already exists
            available_models = self.ollama_client.get_installed_models()
            if self.model_name not in available_models:
                modelfile_path = os.path.join(os.path.dirname(self.model_path), "Modelfile")
                if not os.path.exists(modelfile_path):
                    modelfile_path = self.create_modelfile()
                
                command = f"ollama create {self.model_name} -f {modelfile_path}"
                logging.info(f"Creating model. Running command: {command}")
                
                result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
                logging.info(f"Command output: {result.stdout}")
            else:
                logging.info(f"Model {self.model_name} already exists. No need to create.")
            
            # Ensure the model is loaded and ready
            command = f"ollama run {self.model_name} 'Hello'"
            logging.info(f"Testing model. Running command: {command}")
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            logging.info(f"Test output: {result.stdout}")
            
            if "error loading model" in result.stderr.lower():
                raise Exception("Model loading failed. The model may be corrupted.")

            self.model_is_served = True
            self.model_served.emit()
            logging.info("Model served successfully")
        except subprocess.CalledProcessError as e:
            error_message = f"Failed to serve model {self.model_name}.\nCommand '{e.cmd}' returned non-zero exit status {e.returncode}.\nOutput: {e.stdout}\nError: {e.stderr}"
            logging.error(error_message)
            self.serve_error.emit(error_message)
        except Exception as e:
            error_message = f"Unexpected error while serving model {self.model_name}: {str(e)}"
            logging.error(error_message, exc_info=True)
            self.serve_error.emit(error_message)

    def is_ollama_running(self):
        return self.ollama_client.is_server_running()

    def ensure_ollama_running(self):
        if not self.is_ollama_running():
            return self.start_ollama()
        return True

    def get_installed_models(self):
        if not self.ensure_ollama_running():
            raise Exception("Ollama server is not running and could not be started")
        return self.ollama_client.get_installed_models()

    def edit_modelfile(self, new_content):
        modelfile_path = os.path.join(os.path.dirname(self.model_path), "Modelfile")
        with open(modelfile_path, "w") as f:
            f.write(new_content)
        logging.info(f"Modelfile updated at {modelfile_path}")
        
        # Recreate the model with the new Modelfile
        command = f"ollama create {self.model_name} -f {modelfile_path}"
        subprocess.run(command, shell=True, check=True)
        logging.info(f"Model {self.model_name} recreated with updated Modelfile")

    def generate(self, prompt, system_prompt="", max_tokens=256):
        if not self.model_is_served:
            return "Model is not served yet. Please serve the model first."
        
        try:
            response = self.ollama_client.generate(prompt, system_prompt, self.model_name)
            return response
        except Exception as e:
            error_message = f"Generation error: {str(e)}"
            logging.error(error_message)
            return error_message

    def is_model_available(self, model_name):
        if not self.ollama_client.is_initialized:
            logging.info("Ollama server is not initialized.")
            return False

        try:
            available_models = self.ollama_client.get_installed_models()
            return model_name in available_models
        except Exception as e:
            logging.error(f"Failed to check model availability: {str(e)}")
            return False

    def shutdown(self):
        for process in self.processes:
            process.terminate()
            if not process.waitForFinished(5000):  # Wait for 5 seconds
                process.kill()  # Force kill if it doesn't terminate
        self.processes.clear()

    def on_download_preparing(self):
        self.download_preparing.emit()

    def on_download_progress(self, destination, bytes_downloaded, total_bytes):
        logging.info(f"ModelManager: Progress {bytes_downloaded}/{total_bytes} bytes")
        self.download_progress.emit(bytes_downloaded, total_bytes)

    def get_model_size(self):
        return self.model_size

    def change_model(self, new_model_name):
        if new_model_name != self.model_name:
            self.model_name = new_model_name
            if self.is_model_available(new_model_name):
                self.model_changed.emit(new_model_name)
                logging.info(f"Model changed to: {new_model_name}")
            else:
                error_message = f"Model {new_model_name} is not available"
                logging.error(error_message)
                self.model_unavailable.emit(error_message)

