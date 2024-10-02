from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import QFileSystemWatcher, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import QSettings
from NITTY_GRITTY.ThreadTrackers import SafeQThread
class LogLoader(SafeQThread):
    log_chunk_loaded = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            with open(self.file_path, 'r') as log_file:
                while chunk := log_file.read(1024 * 1024):  # Read 1MB at a time
                    self.log_chunk_loaded.emit(chunk)
        except FileNotFoundError:
            self.log_chunk_loaded.emit(f"Log file not found: {self.file_path}")
        self.finished.emit()

class LogViewerWidget(QWidget):
    def __init__(self, initial_log_file_path, parent=None):
        super().__init__(parent)
        self.settings = QSettings("YourCompany", "YourApp")
        self.log_paths = self.settings.value("log_paths", [initial_log_file_path])
        self.current_log_path = initial_log_file_path
        self.full_log_content = ""

        self.setup_ui()
        QTimer.singleShot(0, self.load_logs)  # Defer log loading

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
        self.full_log_content = ""
        self.text_edit.clear()
        self.log_loader = LogLoader(self.current_log_path)
        self.log_loader.log_chunk_loaded.connect(self.append_log_chunk)
        self.log_loader.finished.connect(self.on_log_loading_finished)
        if not self.log_loader.isRunning():
            self.log_loader.start()

    def append_log_chunk(self, chunk):
        self.full_log_content += chunk
        self.text_edit.append(chunk)

    def on_log_loading_finished(self):
        self.filter_logs()

    def filter_logs(self):
        filter_type = self.log_type_filter.currentText()
        self.text_edit.clear()
        cursor = self.text_edit.textCursor()

        for line in self.full_log_content.split("\n"):
            if filter_type == "All" or filter_type in line:
                if "ERROR" in line:
                    color = "red"
                elif "WARNING" in line:
                    color = "orange"
                elif "INFO" in line:
                    color = "green"
                elif "DEBUG" in line:
                    color = "blue"
                else:
                    color = "white"
                cursor.insertHtml(f'<span style="color: {color};">{line}</span><br>')

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
