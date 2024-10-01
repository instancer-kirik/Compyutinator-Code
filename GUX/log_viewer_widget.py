from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import QFileSystemWatcher, QTimer
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import QSettings

class LogViewerWidget(QWidget):
    def __init__(self, initial_log_file_path, parent=None):
        super().__init__(parent)
        self.settings = QSettings("YourCompany", "YourApp")
        self.log_paths = self.settings.value("log_paths", [initial_log_file_path])
        self.current_log_path = initial_log_file_path

        self.setup_ui()
        self.load_logs()

    def setup_ui(self):
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        self.refresh_button = QPushButton("Refresh Logs", self)
        self.refresh_button.clicked.connect(self.load_logs)

        self.clear_button = QPushButton("Clear Logs", self)
        self.clear_button.clicked.connect(self.clear_logs)

        self.log_type_filter = QComboBox(self)
        self.log_type_filter.addItems(["All", "INFO", "WARNING", "ERROR", "DEBUG"])
        self.log_type_filter.currentTextChanged.connect(self.filter_logs)

        self.log_path_selector = QComboBox(self)
        self.log_path_selector.addItems(self.log_paths)
        self.log_path_selector.setCurrentText(self.current_log_path)
        self.log_path_selector.currentTextChanged.connect(self.change_log_file)

        self.add_log_button = QPushButton("Add Log File", self)
        self.add_log_button.clicked.connect(self.add_log_file)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.log_type_filter)
        button_layout.addWidget(self.log_path_selector)
        button_layout.addWidget(self.add_log_button)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.file_watcher = QFileSystemWatcher([self.current_log_path])
        self.file_watcher.fileChanged.connect(self.load_logs)

    def load_logs(self):
        try:
            with open(self.current_log_path, 'r') as log_file:
                self.full_log_content = log_file.read()
                self.filter_logs()
        except FileNotFoundError:
            self.text_edit.setPlainText(f"Log file not found: {self.current_log_path}")

    def filter_logs(self):
        filter_type = self.log_type_filter.currentText()
        if filter_type == "All":
            filtered_content = self.full_log_content
        else:
            filtered_content = "\n".join([line for line in self.full_log_content.split("\n") if filter_type in line])

        self.text_edit.clear()
        cursor = self.text_edit.textCursor()
        for line in filtered_content.split("\n"):
            if "ERROR" in line:
                cursor.insertHtml(f'<span style="color: red;">{line}</span><br>')
            elif "WARNING" in line:
                cursor.insertHtml(f'<span style="color: orange;">{line}</span><br>')
            elif "INFO" in line:
                cursor.insertHtml(f'<span style="color: green;">{line}</span><br>')
            elif "DEBUG" in line:
                cursor.insertHtml(f'<span style="color: blue;">{line}</span><br>')
            else:
                cursor.insertHtml(f'{line}<br>')

        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

    def clear_logs(self):
        try:
            with open(self.current_log_path, 'w') as log_file:
                log_file.write("")
            self.load_logs()
        except IOError as e:
            self.text_edit.setPlainText(f"Error clearing log file: {str(e)}")

    def change_log_file(self, new_path):
        self.current_log_path = new_path
        self.file_watcher.removePaths(self.file_watcher.files())
        self.file_watcher.addPath(self.current_log_path)
        self.load_logs()

    def add_log_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Log File", "", "Log Files (*.log);;All Files (*)")
        if file_path:
            if file_path not in self.log_paths:
                self.log_paths.append(file_path)
                self.log_path_selector.addItem(file_path)
                self.log_path_selector.setCurrentText(file_path)
                self.settings.setValue("log_paths", self.log_paths)
            else:
                QMessageBox.information(self, "Log File Already Added", "This log file is already in the list.")

    def remove_current_log_file(self):
        if len(self.log_paths) > 1:
            current_path = self.log_path_selector.currentText()
            self.log_paths.remove(current_path)
            self.log_path_selector.removeItem(self.log_path_selector.currentIndex())
            self.settings.setValue("log_paths", self.log_paths)
            self.change_log_file(self.log_path_selector.currentText())
        else:
            QMessageBox.warning(self, "Cannot Remove", "You must have at least one log file.")
