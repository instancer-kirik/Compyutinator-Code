from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

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

        # Set initial background color to black
        self.web_view.setStyleSheet("background-color: black;")
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0))

        # Load empty HTML with black background
        initial_html = """
        <html>
        <head>
            <style>
                body { background-color: black; margin: 0; padding: 0; height: 100vh; }
            </style>
        </head>
        <body></body>
        </html>
        """
        self.web_view.setHtml(initial_html)

    def load_content(self):
        content = self.url_bar.text()
        if content.startswith("http://") or content.startswith("https://"):
            self.web_view.setUrl(content)
        else:
            # Add CSS to set the background color to black
            html_with_black_bg = f"""
            <html>
            <head>
                <style>
                    body {{ background-color: black; color: red; }}
                </style>
            </head>
            <body>
                {content}
            </body>
            </html>
            """
            self.web_view.setHtml(html_with_black_bg)

        # Set the page's background color to black for both URL and HTML content
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0))
