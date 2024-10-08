from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, 
                             QPushButton, QCheckBox, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal

class FindReplaceWidget(QWidget):
    findNext = pyqtSignal(str, bool, bool)  # text, case sensitive, whole words
    replace = pyqtSignal(str, str, bool, bool)  # find text, replace text, case sensitive, whole words
    replaceAll = pyqtSignal(str, str, bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Find row
        find_layout = QHBoxLayout()
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find")
        find_layout.addWidget(self.find_input)
        self.find_next_button = QPushButton("Find Next")
        find_layout.addWidget(self.find_next_button)
        layout.addLayout(find_layout)

        # Replace row
        replace_layout = QHBoxLayout()
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace")
        replace_layout.addWidget(self.replace_input)
        self.replace_button = QPushButton("Replace")
        replace_layout.addWidget(self.replace_button)
        self.replace_all_button = QPushButton("Replace All")
        replace_layout.addWidget(self.replace_all_button)
        layout.addLayout(replace_layout)

        # Options row
        options_layout = QHBoxLayout()
        self.case_sensitive = QCheckBox("Case Sensitive")
        options_layout.addWidget(self.case_sensitive)
        self.whole_words = QCheckBox("Whole Words")
        options_layout.addWidget(self.whole_words)
        layout.addLayout(options_layout)

        # Connect signals
        self.find_next_button.clicked.connect(self.on_find_next)
        self.replace_button.clicked.connect(self.on_replace)
        self.replace_all_button.clicked.connect(self.on_replace_all)

    def on_find_next(self):
        self.findNext.emit(self.find_input.text(), 
                           self.case_sensitive.isChecked(), 
                           self.whole_words.isChecked())

    def on_replace(self):
        self.replace.emit(self.find_input.text(), 
                          self.replace_input.text(),
                          self.case_sensitive.isChecked(), 
                          self.whole_words.isChecked())

    def on_replace_all(self):
        self.replaceAll.emit(self.find_input.text(), 
                             self.replace_input.text(),
                             self.case_sensitive.isChecked(), 
                             self.whole_words.isChecked())
