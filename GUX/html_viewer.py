from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton
from PyQt6.QtWebEngineWidgets import QWebEngineView

class HTMLViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or HTML content...")
        self.layout.addWidget(self.url_bar)

        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_content)
        self.layout.addWidget(self.load_button)

        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)

    def load_content(self):
        content = self.url_bar.text()
        if content.startswith("http://") or content.startswith("https://"):
            self.web_view.setUrl(content)
        else:
            self.web_view.setHtml(content)
