import sys
import os
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QTextEdit, QPushButton
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QClipboard
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from GUX.splash_screen import TransparentSplashScreen
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtCore import QSize
from PyQt6.QtCore import QTimer, Qt, QCoreApplication
from PyQt6.QtGui import QClipboard, QMovie
from PyQt6.QtWidgets import QHBoxLayout, QLabel
import logging

import tempfile
class SplashWithInput(QWidget):
    def __init__(self, splash_path):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)

        # Create a QLabel to hold the animation
        self.animation_label = QLabel(self)
        self.movie = QMovie(splash_path)
        if self.movie.isValid():
            logging.info("Movie is valid")
            self.movie.setScaledSize(QSize(400, 400))  # Adjust size as needed
            self.animation_label.setMovie(self.movie)
            self.movie.start()  # Start the movie immediately
        else:
            logging.error(f"Failed to load movie from {splash_path}")
        layout.addWidget(self.animation_label)

        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("Start typing here...")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(10, 10, 10, 240);
                color: white;
                border: 1px solid gray;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.text_edit)

        button_layout = QVBoxLayout()

        self.copy_button = QPushButton("Copy to Clipboard", self)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 123, 255, 240);
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(0, 86, 179, 240);
            }
        """)
        button_layout.addWidget(self.copy_button)

        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.close)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 53, 69, 240);
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(200, 35, 51, 240);
            }
        """)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())

    def close_and_cancel(self):
        self.save_content_to_file()
        QCoreApplication.instance().quit()

    def save_content_to_file(self):
        content = self.text_edit.toPlainText()
        if content:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
                temp_file.write(content)
                logging.info(f"Saved splash input to temporary file: {temp_file.name}")

def run_splash():
    app = QApplication(sys.argv)
    
    splash_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'splash.gif'))
    logging.info(f"Attempting to load GIF from: {splash_path}")
    
    if not os.path.exists(splash_path):
        logging.error(f"GIF file does not exist at {splash_path}")
        return

    splash_with_input = SplashWithInput(splash_path)
    splash_with_input.show()

    def on_timeout():
        splash_with_input.copy_to_clipboard()
        app.quit()

    # Exit the splash screen after a timeout (adjust as needed)
    QTimer.singleShot(30000, on_timeout)  # 30 seconds timeout

    sys.exit(app.exec())

if __name__ == '__main__':
    run_splash()