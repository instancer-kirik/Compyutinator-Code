import pytesseract
from PIL import Image
from typing import List, Tuple
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QFileDialog, QLabel, QLineEdit, QMessageBox
from PyQt6.QtCore import Qt

class OCRBatchProcessor:
    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size

    def process_image_batch(self, image_paths: List[str]) -> List[Tuple[str, str]]:
        results = []
        for i in range(0, len(image_paths), self.batch_size):
            batch = image_paths[i:i + self.batch_size]
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
        return results

    def _process_batch(self, batch: List[str]) -> List[Tuple[str, str]]:
        results = []
        for image_path in batch:
            try:
                image = Image.open(image_path)
                text = pytesseract.image_to_string(image)
                results.append((image_path, text))
            except Exception as e:
                results.append((image_path, f"Error processing image: {str(e)}"))
        return results

class DisplayMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Display Monitor - OCR Batch Processor")
        self.ocr_processor = OCRBatchProcessor(batch_size=5)
        self.image_paths = []
        self.results = []

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.create_widgets()

    def create_widgets(self):
        # File selection
        self.select_button = QPushButton("Select Images")
        self.select_button.clicked.connect(self.select_images)
        self.layout.addWidget(self.select_button)

        # Batch size input
        self.batch_size_label = QLabel("Batch Size:")
        self.layout.addWidget(self.batch_size_label)
        self.batch_size_entry = QLineEdit()
        self.batch_size_entry.setText("5")
        self.layout.addWidget(self.batch_size_entry)

        # Process button
        self.process_button = QPushButton("Process Images")
        self.process_button.clicked.connect(self.process_images)
        self.layout.addWidget(self.process_button)

        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.layout.addWidget(self.results_text)

    def select_images(self):
        file_dialog = QFileDialog()
        self.image_paths, _ = file_dialog.getOpenFileNames(self, "Select Images", "", "Image files (*.png *.jpg *.jpeg *.bmp)")
        QMessageBox.information(self, "Image Selection", f"{len(self.image_paths)} images selected.")

    def process_images(self):
        try:
            batch_size = int(self.batch_size_entry.text())
            self.ocr_processor.batch_size = batch_size
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid batch size. Using default value of 5.")
            self.batch_size_entry.setText("5")
            self.ocr_processor.batch_size = 5

        self.results = self.ocr_processor.process_image_batch(self.image_paths)
        self.display_results()

    def display_results(self):
        self.results_text.clear()
        for image_path, text in self.results:
            self.results_text.append(f"OCR result for {image_path}:")
            self.results_text.append(f"{text}")
            self.results_text.append("---")

# Usage example:
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    monitor = DisplayMonitor()
    monitor.show()
    sys.exit(app.exec())
