
import difflib
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel)

class DiffMergerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.original_text = QPlainTextEdit()
        self.new_text = QPlainTextEdit()
        self.diff_result = QPlainTextEdit()
        self.diff_result.setReadOnly(True)

        merge_button = QPushButton('Merge')
        merge_button.clicked.connect(self.merge_texts)

        layout.addWidget(QLabel("Original Text"))
        layout.addWidget(self.original_text)
        layout.addWidget(QLabel("New Text"))
        layout.addWidget(self.new_text)
        layout.addWidget(merge_button)
        layout.addWidget(QLabel("Diff Result"))
        layout.addWidget(self.diff_result)

        self.setLayout(layout)

    def merge_texts(self):
        original_lines = self.original_text.toPlainText().splitlines()
        new_lines = self.new_text.toPlainText().splitlines()
        diff = difflib.unified_diff(original_lines, new_lines, lineterm='')

        diff_result_text = '\n'.join(diff)
        self.diff_result.setPlainText(diff_result_text)