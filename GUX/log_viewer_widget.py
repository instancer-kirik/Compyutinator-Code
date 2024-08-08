from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import QFileSystemWatcher, QTimer
from PyQt6.QtGui import QTextCursor

class LogViewerWidget(QWidget):
    def __init__(self, log_file_path, parent=None):
        super().__init__(parent)
        self.log_file_path = log_file_path

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        self.refresh_button = QPushButton("Refresh Logs", self)
        self.refresh_button.clicked.connect(self.load_logs)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.refresh_button)
        self.setLayout(layout)

        # File system watcher to auto-refresh logs
        self.file_watcher = QFileSystemWatcher([self.log_file_path])
        self.file_watcher.fileChanged.connect(self.load_logs)

        self.load_logs()

    def load_logs(self):
        try:
            with open(self.log_file_path, 'r') as log_file:
                self.text_edit.setPlainText(log_file.read())

                # Move the cursor to the end to display the latest log entries
                cursor = self.text_edit.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.text_edit.setTextCursor(cursor)
        except FileNotFoundError:
            self.text_edit.setPlainText("Log file not found.")
