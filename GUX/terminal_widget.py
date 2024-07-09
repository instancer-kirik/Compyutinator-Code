from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QProcess, Qt
import os

class TerminalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.output.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.output)

        self.input = QLineEdit()
        self.input.returnPressed.connect(self.execute_command)
        self.layout.addWidget(self.input)

        if os.name == 'nt':
            # Windows
            self.process.start("cmd.exe")
        else:
            # Unix-like
            self.process.start("/bin/bash")

        self.process.readyReadStandardOutput.connect(self.update_output)
        self.process.readyReadStandardError.connect(self.update_output)

    def execute_command(self):
        command = self.input.text()
        self.process.write(command.encode() + b'\n')
        self.input.clear()

    def update_output(self):
        output = self.process.readAllStandardOutput().data().decode()
        self.output.append(output)
        error_output = self.process.readAllStandardError().data().decode()
        if error_output:
            self.output.append(error_output)

    def show_context_menu(self, position):
        menu = QMenu()
        
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_text)
        menu.addAction(copy_action)

        clear_action = QAction("Clear", self)
        clear_action.triggered.connect(self.clear_output)
        menu.addAction(clear_action)
        
        menu.exec(self.output.mapToGlobal(position))

    def copy_text(self):
        cursor = self.output.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            QApplication.clipboard().setText(selected_text)

    def clear_output(self):
        self.output.clear()

    def closeEvent(self, event):
        self.process.terminate()
        self.process.waitForFinished()
        super().closeEvent(event)
