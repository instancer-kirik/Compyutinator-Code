from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QColorDialog, QComboBox, QHBoxLayout, QLabel, QSpinBox

class HTMLViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # URL/Content input
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or HTML content...")
        self.layout.addWidget(self.url_bar)

        # Style controls
        style_layout = QHBoxLayout()
        self.layout.addLayout(style_layout)

        # Flex direction
        self.flex_direction = QComboBox()
        self.flex_direction.addItems(["row", "column", "row-reverse", "column-reverse"])
        style_layout.addWidget(QLabel("Flex Direction:"))
        style_layout.addWidget(self.flex_direction)

        # Justify content
        self.justify_content = QComboBox()
        self.justify_content.addItems(["flex-start", "flex-end", "center", "space-between", "space-around"])
        style_layout.addWidget(QLabel("Justify Content:"))
        style_layout.addWidget(self.justify_content)

        # Align items
        self.align_items = QComboBox()
        self.align_items.addItems(["stretch", "flex-start", "flex-end", "center", "baseline"])
        style_layout.addWidget(QLabel("Align Items:"))
        style_layout.addWidget(self.align_items)

        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        self.font_size.setValue(16)
        style_layout.addWidget(QLabel("Font Size:"))
        style_layout.addWidget(self.font_size)

        # Background color
        self.bg_color = QColor(0, 0, 0)
        self.bg_color_button = QPushButton("Background Color")
        self.bg_color_button.clicked.connect(self.choose_bg_color)
        style_layout.addWidget(self.bg_color_button)

        # Text color
        self.text_color = QColor(255, 0, 0)
        self.text_color_button = QPushButton("Text Color")
        self.text_color_button.clicked.connect(self.choose_text_color)
        style_layout.addWidget(self.text_color_button)

        # Load button
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

    def choose_bg_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.bg_color = color
            self.bg_color_button.setStyleSheet(f"background-color: {color.name()};")

    def choose_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.text_color = color
            self.text_color_button.setStyleSheet(f"background-color: {color.name()};")

    def load_content(self):
        content = self.url_bar.text()
        if content.startswith("http://") or content.startswith("https://"):
            self.web_view.setUrl(content)
        else:
            # Add CSS to set the styles
            html_with_styles = f"""
            <html>
            <head>
                <style>
                    body {{
                        background-color: {self.bg_color.name()};
                        color: {self.text_color.name()};
                        font-size: {self.font_size.value()}px;
                        display: flex;
                        flex-direction: {self.flex_direction.currentText()};
                        justify-content: {self.justify_content.currentText()};
                        align-items: {self.align_items.currentText()};
                        height: 100vh;
                        margin: 0;
                        padding: 0;
                    }}
                </style>
            </head>
            <body>
                {content}
            </body>
            </html>
            """
            self.web_view.setHtml(html_with_styles)

        # Set the page's background color
        self.web_view.page().setBackgroundColor(self.bg_color)
