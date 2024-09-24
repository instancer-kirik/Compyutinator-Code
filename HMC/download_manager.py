import os
import requests
import json
from threading import Thread
from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QProgressBar, QMessageBox, QFileDialog
import logging

class DownloadThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, destination):
        super().__init__()
        self.url = url
        self.destination = destination

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            written = 0

            with open(self.destination, 'wb') as f:
                for chunk in response.iter_content(block_size):
                    if chunk:
                        size = f.write(chunk)
                        written += size
                        self.progress.emit(written, max(total_size, written))

            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            logging.info(f"Download finished. Written: {written} bytes")

class DownloadManager(QObject):
    download_preparing = pyqtSignal()
    download_progress = pyqtSignal(str, int, int)  # id, bytes_downloaded, total_bytes
    download_complete = pyqtSignal(str)  # id
    download_error = pyqtSignal(str, str)  # id, error_message

    def __init__(self, cccore=None):
        super().__init__()
        self.cccore = cccore
        self.downloads = {}
        self.threads = []  # Keep track of active threads

    def start_download(self, url, destination):
        download_id = self.generate_download_id()
        self.downloads[download_id] = {"url": url, "destination": destination, "status": "downloading"}
        
        download_thread = DownloadThread(url, destination)
        download_thread.progress.connect(lambda b, t: self.download_progress.emit(download_id, b, t))
        download_thread.finished.connect(lambda: self.on_download_finished(download_id))
        download_thread.error.connect(lambda e: self.download_error.emit(download_id, e))
        
        self.threads.append(download_thread)  # Keep reference to the thread
        download_thread.start()

        logging.info(f"Started download with ID: {download_id}, URL: {url}, Destination: {destination}")
        return download_id

    def on_download_finished(self, download_id):
        self.download_complete.emit(download_id)
        self.cleanup_thread(download_id)

    def cleanup_thread(self, download_id):
        for thread in self.threads:
            if thread.url == self.downloads[download_id]["url"]:
                thread.wait()  # Wait for the thread to finish
                self.threads.remove(thread)
                break
        del self.downloads[download_id]

    def generate_download_id(self):
        return str(len(self.downloads))

    def get_download_status(self, download_id):
        return self.downloads.get(download_id, {}).get("status", "not_found")

class DownloadManagerUI(QWidget):
    def __init__(self, download_manager):
        super().__init__()
        self.download_manager = download_manager
        self.initUI()
        self.connect_signals()

    def initUI(self):
        layout = QVBoxLayout()

        # Add a specific button for downloading the chosen model
        self.model_download_button = QPushButton("Download Chosen Model")
        self.model_download_button.clicked.connect(self.download_chosen_model)
        layout.addWidget(self.model_download_button)

        # Add a progress bar for the model download
        self.model_progress_bar = QProgressBar()
        self.model_progress_bar.setValue(0)
        self.model_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.model_progress_bar.setFormat("Model Download: %p%")
        layout.addWidget(self.model_progress_bar)

        # Keep the existing UI elements
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter download URL")
        layout.addWidget(self.url_input)

        self.add_download_button = QPushButton("Add Download")
        self.add_download_button.clicked.connect(self.add_download)
        layout.addWidget(self.add_download_button)

        self.download_list = QListWidget()
        layout.addWidget(self.download_list)

        self.setLayout(layout)

    def download_chosen_model(self):
        model_url = "https://huggingface.co/Joseph717171/Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF/resolve/main/Llama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ6_K.gguf"
        save_path = os.path.join(os.path.expanduser("~"), ".cache", "ollama_models", "Llama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ6_K.gguf")
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        self.model_download_id = self.download_manager.start_download(model_url, save_path)
        self.model_progress_bar.setProperty("save_path", save_path)
        logging.info(f"Started model download with ID: {self.model_download_id}")

    def update_progress(self, download_id, bytes_downloaded, total_bytes):
        if download_id == getattr(self, 'model_download_id', None):
            if total_bytes > 0:
                progress = int((bytes_downloaded / total_bytes) * 100)
                self.model_progress_bar.setValue(progress)
                self.model_progress_bar.setFormat(f"Model Download: {progress}% ({self.format_size(bytes_downloaded)}/{self.format_size(total_bytes)})")
            else:
                self.model_progress_bar.setFormat(f"Model Download: {self.format_size(bytes_downloaded)} (unknown total)")
        else:
            for index in range(self.download_list.count()):
                item = self.download_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == download_id:
                    progress_bar = item.data(Qt.ItemDataRole.UserRole + 1)
                    progress_bar.setValue(progress)
                    break

    def download_complete(self, download_id):
        if download_id == getattr(self, 'model_download_id', None):
            QMessageBox.information(self, "Download Complete", "Chosen model download is complete.")
            self.add_downloaded_item("Llama-3.1-SuperNova-Lite", self.model_progress_bar.property("save_path"))
        else:
            QMessageBox.information(self, "Download Complete", f"Download {download_id} is complete.")
            item = self.find_download_item(download_id)
            if item:
                url = item.data(Qt.ItemDataRole.UserRole + 2)
                save_path = item.data(Qt.ItemDataRole.UserRole + 3)
                self.add_downloaded_item(os.path.basename(save_path), save_path, url)

    def download_error(self, download_id, error_message):
        if download_id == getattr(self, 'model_download_id', None):
            QMessageBox.critical(self, "Download Error", f"Chosen model download failed: {error_message}")
        else:
            QMessageBox.critical(self, "Download Error", f"Download {download_id} failed: {error_message}")

    def add_downloaded_item(self, item_name, item_path, item_url=None):
        self.downloaded_items[item_name] = {"path": item_path, "url": item_url}
        self.save_downloaded_items()

    def load_downloaded_items(self):
        try:
            with open('downloaded_items.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_downloaded_items(self):
        with open('downloaded_items.json', 'w') as f:
            json.dump(self.downloaded_items, f)

    def add_download(self):
        url = self.url_input.text()
        if url:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save As")
            if save_path:
                download_id = len(self.download_manager.downloads)
                self.download_manager.start_download(download_id, url, save_path)
                self.add_download_item(download_id, url, save_path)

    def add_download_item(self, download_id, url, save_path):
        item = QListWidgetItem(f"Downloading {os.path.basename(save_path)}")
        progress_bar = QProgressBar()
        progress_bar.setValue(0)
        progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.download_list.addItem(item)
        self.download_list.setItemWidget(item, progress_bar)
        item.setData(Qt.ItemDataRole.UserRole, download_id)
        item.setData(Qt.ItemDataRole.UserRole + 1, progress_bar)
        item.setData(Qt.ItemDataRole.UserRole + 2, url)
        item.setData(Qt.ItemDataRole.UserRole + 3, save_path)

    def find_download_item(self, download_id):
            for index in range(self.download_list.count()):
                item = self.download_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == download_id:
                    return item
            return None

    def connect_signals(self):
        self.download_manager.download_progress.connect(self.update_progress)
        self.download_manager.download_complete.connect(self.download_complete)
        self.download_manager.download_error.connect(self.download_error)

    def format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"