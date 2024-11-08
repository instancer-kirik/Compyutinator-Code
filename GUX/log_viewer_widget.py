from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import (
    QFileSystemWatcher, QTimer, pyqtSignal, 
    QSettings, QMutex, QThread, QMutexLocker
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QPushButton, 
    QVBoxLayout, QFileDialog, QMessageBox
)
import logging

from NITTY_GRITTY.ThreadTrackers import SafeQThread

class LogLoader(SafeQThread):
    log_chunk_loaded = pyqtSignal(str)
    finished = pyqtSignal()
    update_signal = pyqtSignal(str)

    def __init__(self, log_path: str, parent=None):
        super().__init__(parent)
        self.log_path = log_path
        self._stop = False
        self._mutex = QMutex()
        self.setObjectName(f"LogLoader-{log_path}")

    def stop(self):
        """Safely stop the thread"""
        with QMutexLocker(self._mutex):
            self._stop = True

    def run(self):
        try:
            with open(self.log_path, 'r') as log_file:
                while not self._stop and (chunk := log_file.read(1024 * 1024)):  # Read 1MB at a time
                    self.log_chunk_loaded.emit(chunk)
                    if self._stop:
                        break
        except FileNotFoundError:
            self.log_chunk_loaded.emit(f"Log file not found: {self.log_path}")
        except Exception as e:
            logging.error(f"Error reading log file: {e}")
        finally:
            self.finished.emit()

class LogViewerWidget(QWidget):
    def __init__(self, initial_log_file_path, parent=None):
        super().__init__(parent)
        self.settings = QSettings("YourCompany", "YourApp")
        self.log_paths = self.settings.value("log_paths", [initial_log_file_path])
        self.current_log_path = initial_log_file_path
        self.full_log_content = ""
        self.log_loader = None
        self._loading = False
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_load_logs)
        self._file_changed = False
        
        self.setup_ui()
        QTimer.singleShot(0, self.load_logs)

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

        # Update file watcher setup
        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.fileChanged.connect(self._on_file_changed)
        if self.current_log_path:
            self.file_watcher.addPath(self.current_log_path)

    def _on_file_changed(self, path):
        """Handle file change events with debounce"""
        if path == self.current_log_path and not self._loading:
            self._file_changed = True
            self.load_logs()

    def load_logs(self):
        """Debounced log loading"""
        if self._loading:
            return
        
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
        self._debounce_timer.start(500)  # 500ms debounce

    def _do_load_logs(self):
        """Actual log loading implementation"""
        if self._loading:
            return
            
        self._loading = True
        self._file_changed = False
        
        try:
            # Clean up previous loader if it exists
            if self.log_loader and self.log_loader.isRunning():
                self.log_loader.stop()
                self.log_loader.quit()
                self.log_loader.wait()
                
            self.full_log_content = ""
            self.text_edit.clear()
            
            self.log_loader = LogLoader(self.current_log_path, parent=self)
            self.log_loader.log_chunk_loaded.connect(self.append_log_chunk)
            self.log_loader.finished.connect(self._on_loading_complete)
            self.log_loader.start()
            
            # Re-add the file to the watcher if needed
            if self.current_log_path not in self.file_watcher.files():
                self.file_watcher.addPath(self.current_log_path)
                
        except Exception as e:
            logging.error(f"Error loading logs: {e}")
            self._loading = False

    def _on_loading_complete(self):
        """Handle completion of log loading"""
        self._loading = False
        self.filter_logs()

    def append_log_chunk(self, chunk):
        self.full_log_content += chunk
        self.text_edit.append(chunk)

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
        """Change the current log file"""
        if new_path == self.current_log_path:
            return
            
        self.current_log_path = new_path
        self.file_watcher.removePaths(self.file_watcher.files())
        if new_path:
            self.file_watcher.addPath(new_path)
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

    def closeEvent(self, event):
        """Clean up threads when widget is closed"""
        self._debounce_timer.stop()
        if self.log_loader and self.log_loader.isRunning():
            self.log_loader.stop()
            self.log_loader.quit()
            self.log_loader.wait()
        super().closeEvent(event)
