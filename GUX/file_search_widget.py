import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
import logging
from PyQt6.QtWidgets import QDialog
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QListWidget, QLabel, QSplitter, 
                             QTextEdit, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtWidgets import QMessageBox
import os
import re
import logging
from fuzzywuzzy import fuzz
import asyncio

class AsyncSearchWorker(QThread):
    result_found = pyqtSignal(str, int, str)
    search_completed = pyqtSignal()

    def __init__(self, vault_path, query, file_types):
        super().__init__()
        self.vault_path = vault_path
        self.query = query
        self.file_types = file_types

    async def search_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                filename_score = fuzz.partial_ratio(self.query, os.path.basename(file_path))
                if filename_score > 70:
                    self.result_found.emit(file_path, 0, "[Filename Match]")
                
                for i, line in enumerate(content.splitlines(), 1):
                    if fuzz.partial_ratio(self.query, line) > 70:
                        self.result_found.emit(file_path, i, line.strip())
        except Exception as e:
            logging.error(f"Error searching file {file_path}: {e}")

    async def search_files(self):
        tasks = []
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if self.file_types == "All" or file.endswith(tuple(self.file_types)):
                    file_path = os.path.join(root, file)
                    tasks.append(self.search_file(file_path))
        await asyncio.gather(*tasks)

    def run(self):
        asyncio.run(self.search_files())
        self.search_completed.emit()

class FileSearchWidget(QDialog):
    file_selected = pyqtSignal(str, int)

    def __init__(self, vault_manager=None, parent=None):
        super().__init__(parent)
        self.vault_manager = vault_manager
        self.setWindowTitle("File Search")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files, classes, functions...")
        self.search_button = QPushButton("Search")
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["All", "Python (.py)", "JavaScript (.js)", "C++ (.cpp, .h)"])
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.file_type_combo)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.results_list = QListWidget()
        splitter.addWidget(self.results_list)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        splitter.addWidget(self.preview_text)

        layout.addWidget(splitter)

        self.results_label = QLabel("Results: 0")
        layout.addWidget(self.results_label)

        self.search_button.clicked.connect(self.perform_search)
        self.search_input.returnPressed.connect(self.perform_search)
        self.results_list.itemClicked.connect(self.show_preview)
        self.results_list.itemDoubleClicked.connect(self.open_selected_item)

        self.resize(800, 600)

    def perform_search(self):
        query = self.search_input.text().lower()
        if not query:
            return

        self.results_list.clear()
        self.preview_text.clear()

        if self.vault_manager is None:
            logging.error("Vault manager is not initialized")
            QMessageBox.warning(self, "Error", "Vault manager is not initialized. Unable to perform search.")
            return

        try:
            vault_path = self.vault_manager.get_current_vault_path()
            if not vault_path:
                logging.error("No current vault path")
                QMessageBox.warning(self, "Error", "No current vault selected. Please select a vault first.")
                return
        except AttributeError as e:
            logging.error(f"Error getting current vault path: {e}")
            QMessageBox.warning(self, "Error", "Unable to access vault manager. Please check the application setup.")
            return

        file_types = self.get_selected_file_types()
        self.search_worker = AsyncSearchWorker(vault_path, query, file_types)
        self.search_worker.result_found.connect(self.add_search_result)
        self.search_worker.search_completed.connect(self.search_completed)
        self.search_worker.start()

    def get_selected_file_types(self):
        selected = self.file_type_combo.currentText()
        if selected == "All":
            return "All"
        elif selected == "Python (.py)":
            return [".py"]
        elif selected == "JavaScript (.js)":
            return [".js"]
        elif selected == "C++ (.cpp, .h)":
            return [".cpp", ".h"]

    @pyqtSlot(str, int, str)
    def add_search_result(self, file_path, line_number, content):
        relative_path = os.path.relpath(file_path, self.vault_manager.get_current_vault_path())
        item_text = f"{relative_path} (Line {line_number}): {content}"
        self.results_list.addItem(item_text)
        self.results_label.setText(f"Results: {self.results_list.count()}")

    @pyqtSlot()
    def search_completed(self):
        self.results_label.setText(f"Results: {self.results_list.count()} (Search completed)")

    def show_preview(self, item):
        text = item.text()
        file_path = text.split(' (Line')[0]
        line_number = int(text.split('(Line ')[1].split('):')[0])
        full_path = os.path.join(self.vault_manager.get_current_vault_path(), file_path)
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
                start = max(0, line_number - 5)
                end = min(len(content), line_number + 5)
                preview = ''.join(content[start:end])
                self.preview_text.setPlainText(preview)
        except Exception as e:
            self.preview_text.setPlainText(f"Error loading preview: {str(e)}")

    def open_selected_item(self, item):
        text = item.text()
        file_path = text.split(' (Line')[0]
        line_number = int(text.split('(Line ')[1].split('):')[0])
        full_path = os.path.join(self.vault_manager.get_current_vault_path(), file_path)
        self.file_selected.emit(full_path, line_number)
        self.accept()

    def show_search_dialog(self):
        self.search_input.clear()
        self.results_list.clear()
        self.preview_text.clear()
        self.show()