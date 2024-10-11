#text_entry_widget.py
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QClipboard
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
#unused
class TextEntryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        self.text_edit = QTextEdit()
        self.text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self.on_context_menu)
        self.text_edit.setFocus()  # Focus the text edit when the widget is created
        load_button = QPushButton("Load from File")
        load_button.clicked.connect(self.load_from_file)

        main_layout.addWidget(self.text_edit)
        main_layout.addWidget(load_button)

        self.setLayout(main_layout)

    def load_from_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Text File", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'r') as file:
                    text = file.read()
                self.text_edit.setText(text)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
    def on_context_menu(self, pos):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        self.text_edit.insertPlainText(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = TextEntryWidget()
    widget.show()
    sys.exit(app.exec())