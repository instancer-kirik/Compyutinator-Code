import os
import requests
from threading import Thread
from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QProgressBar, QMessageBox,QFileDialog

class DownloadManager(QObject):
    download_progress = pyqtSignal(int, int)  # Emits (download_id, progress)
    download_complete = pyqtSignal(int)       # Emits download_id
    download_error = pyqtSignal(int, str)     # Emits (download_id, error_message)

    def __init__(self):
        super().__init__()
        self.downloads = {}

    def start_download(self, download_id, url, save_path):
        thread = Thread(target=self.download_file, args=(download_id, url, save_path))
        self.downloads[download_id] = {"thread": thread, "status": "downloading"}
        thread.start()

    def download_file(self, download_id, url, save_path):
        try:
            response = requests.get(url, stream=True)
            total_length = response.headers.get('content-length')

            if total_length is None:  # No content length header
                save_path.write(response.content)
            else:
                with open(save_path, 'wb') as f:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=4096):
                        dl += len(data)
                        f.write(data)
                        progress = int(100 * dl / total_length)
                        self.download_progress.emit(download_id, progress)

            self.downloads[download_id]["status"] = "complete"
            self.download_complete.emit(download_id)
        except Exception as e:
            self.downloads[download_id]["status"] = "error"
            self.download_error.emit(download_id, str(e))

    def get_download_status(self, download_id):
        return self.downloads.get(download_id, {}).get("status", "unknown")


class DownloadManagerUI(QWidget):
    def __init__(self, download_manager, parent=None):
        super().__init__(parent)
        self.download_manager = download_manager
        self.download_manager.download_progress.connect(self.update_progress)
        self.download_manager.download_complete.connect(self.download_complete)
        self.download_manager.download_error.connect(self.download_error)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter download URL")
        layout.addWidget(self.url_input)

        self.add_download_button = QPushButton("Add Download")
        self.add_download_button.clicked.connect(self.add_download)
        layout.addWidget(self.add_download_button)

        self.download_list = QListWidget()
        layout.addWidget(self.download_list)

        self.setLayout(layout)

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

    def update_progress(self, download_id, progress):
        for index in range(self.download_list.count()):
            item = self.download_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == download_id:
                progress_bar = item.data(Qt.ItemDataRole.UserRole + 1)
                progress_bar.setValue(progress)
                break

    def download_complete(self, download_id):
        QMessageBox.information(self, "Download Complete", f"Download {download_id} is complete.")

    def download_error(self, download_id, error_message):
        QMessageBox.critical(self, "Download Error", f"Download {download_id} failed: {error_message}")
