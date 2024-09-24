from PyQt6.QtWidgets import QDialog, QLineEdit, QPushButton, QCheckBox, QLabel, QMessageBox
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel
from AuraText.auratext.Core.CodeEditor import CodeEditor
class SearchDialog(QDialog):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__()
        self.setObjectName("Search")
        self.editor = editor

        self.textBox = QLineEdit(self)
        self.textBox.setObjectName("Textbox")
        self.textBox.setGeometry(QRect(10, 30, 251, 21))
        self.textBox.setPlaceholderText("Enter text to find")

        self.cs = QCheckBox(self)
        self.cs.setObjectName("Case")
        self.cs.setGeometry(QRect(10, 70, 41, 17))
        self.cs.setText("Case sensitive")

        self.next = QPushButton(self)
        self.next.setObjectName("Next")
        self.next.setGeometry(QRect(190, 70, 71, 23))
        self.next.setText("Next")
        self.next.clicked.connect(self.find_next)

        self.previous = QPushButton(self)
        self.previous.setObjectName("Previous")
        self.previous.setText("Previous")
        self.previous.setGeometry(QRect(110, 70, 75, 23))
        self.previous.clicked.connect(self.find_previous)

        self.label = QLabel(self)
        self.label.setObjectName("Label")
        self.label.setGeometry(QRect(10, 10, 91, 16))
        self.label.setText("Enter Text to Find")

        self.setWindowTitle("Find")

    def find_next(self):
        search_text = self.textBox.text()
        case_sensitive = self.cs.isChecked()
        if search_text:
            self.editor.search(search_text, case_sensitive, forward=True)
        else:
            QMessageBox.warning(self, "Warning", "Please enter text to find.")

    def find_previous(self):
        search_text = self.textBox.text()
        case_sensitive = self.cs.isChecked()
        if search_text:
            self.editor.search(search_text, case_sensitive, forward=False)
        else:
            QMessageBox.warning(self, "Warning", "Please enter text to find.")

