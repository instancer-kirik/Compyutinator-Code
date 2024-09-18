import os
from PyQt6.QtCore import QThread, pyqtSignal

class ModelDownloadThread(QThread):
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)

    def __init__(self, download_manager, model_name):
        super().__init__()
        self.download_manager = download_manager
        self.model_name = model_name

    def run(self):
        try:
            model_url = f"https://huggingface.co/Joseph717171/Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF/resolve/main/{self.model_name}"
            save_path = os.path.join(os.path.expanduser("~"), ".cache", "ollama_models", self.model_name)
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            download_id = self.download_manager.start_download(model_url, save_path)
            
            while self.download_manager.get_download_status(download_id) == "downloading":
                import time
                time.sleep(0.1)
            
            if self.download_manager.get_download_status(download_id) == "complete":
                self.download_complete.emit(save_path)
            else:
                self.download_error.emit("Download failed")
        except Exception as e:
            self.download_error.emit(str(e))