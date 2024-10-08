import os
import importlib
import inspect
import math
import logging
import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QPushButton, QFileDialog, 
                             QTextEdit, QLabel, QLineEdit, QTreeWidgetItem, QSplitter, 
                             QWidget, QInputDialog, QMessageBox, QTableWidgetItem, QHeaderView,
                             QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QFileSystemModel
from pathlib import Path

from GUX.file_search_widget import FileSearchWidget
from GUX.file_tree_view import FileTreeView

class FileItemWidget(QWidget):
    def __init__(self, file_path, file_type, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        # File path (very small)
        self.path_label = QLabel(os.path.dirname(file_path))
        self.path_label.setWordWrap(True)
        path_font = QFont()
        path_font.setPointSize(2)  # Set to 2pt
        self.path_label.setFont(path_font)
        self.path_label.setStyleSheet("color: gray;")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Filename (much larger)
        self.name_label = QLabel(os.path.basename(file_path))
        self.name_label.setWordWrap(True)
        name_font = QFont()
        name_font.setPointSize(16)  # Set to 16pt
        name_font.setBold(True)
        self.name_label.setFont(name_font)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.path_label)
        layout.addWidget(self.name_label)

        self.setToolTip(f"{file_type}\n{file_path}")

        # Set a fixed size for the widget to ensure consistent cell sizes
        self.setFixedSize(200, 80)  # Adjust these values as needed

class ContextPickerDialog(QDialog):
    context_added = pyqtSignal(str, str)  # context_type, context_content

    def __init__(self, parent=None, recent_files=None, open_files=None, existing_contexts=None, editor_manager=None, vault_manager=None, context_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Add Context")
        self.recent_files = recent_files or []
        self.context_manager = context_manager  
        self.open_files = open_files or []
        self.existing_contexts = existing_contexts or []
        self.editor_manager = editor_manager
        self.vault_manager = vault_manager
        self.selected_files = []  # Initialize selected_files
        logging.info(f"Initializing ContextPickerDialog with {len(self.open_files)} open files, "
                     f"{len(self.recent_files)} recent files, and {len(self.existing_contexts)} existing contexts")
        self.initUI()
        self.setAcceptDrops(True)
        self.resize(1200, 800)

    def initUI(self):
        layout = QVBoxLayout(self)

        # Create a tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # File Explorer Tab
        file_explorer_widget = QWidget()
        file_explorer_layout = QVBoxLayout(file_explorer_widget)
        self.file_model = QFileSystemModel()

        # Set initial directory
        initial_directory = self.get_initial_directory()
        self.file_model.setRootPath(str(initial_directory))  # Convert to string
        self.file_tree_view = FileTreeView(self.file_model)
        self.file_tree_view.set_root_path(str(initial_directory))  # Convert to string
        self.file_tree_view.file_selected.connect(self.add_to_selected_files)  # Connect to method
        file_explorer_layout.addWidget(self.file_tree_view)
        self.tab_widget.addTab(file_explorer_widget, "File Explorer")

        # Search Tab
        search_widget = FileSearchWidget(self.vault_manager, parent=self)
        search_widget.file_selected.connect(self.preview_file)
        self.tab_widget.addTab(search_widget, "Search")

        # Recent and Open Files Tab
        recent_open_widget = QWidget()
        recent_open_layout = QVBoxLayout(recent_open_widget)
        self.recent_open_table = QTableWidget()
        self.recent_open_table.setColumnCount(2)
        self.recent_open_table.setHorizontalHeaderLabels(["File", "Type"])
        self.recent_open_table.horizontalHeader().setStretchLastSection(True)
        self.recent_open_table.itemSelectionChanged.connect(self.preview_selected_file)
        recent_open_layout.addWidget(self.recent_open_table)
        self.tab_widget.addTab(recent_open_widget, "Recent & Open Files")

        # Existing Contexts Tab
        existing_contexts_widget = QWidget()
        existing_contexts_layout = QVBoxLayout(existing_contexts_widget)
        self.existing_contexts_table = QTableWidget()
        self.existing_contexts_table.setColumnCount(1)
        self.existing_contexts_table.setHorizontalHeaderLabels(["Context"])
        self.existing_contexts_table.itemSelectionChanged.connect(self.preview_selected_context)
        existing_contexts_layout.addWidget(self.existing_contexts_table)
        self.tab_widget.addTab(existing_contexts_widget, "Existing Contexts")

        # Preview area
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)

        # Create a splitter for the tab widget and preview area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tab_widget)
        splitter.addWidget(self.preview_area)
        splitter.setSizes([600, 600])  # Adjust these values to make the name splitter larger
        layout.addWidget(splitter)

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Search")
        add_button.clicked.connect(self.add_selected_contexts)
        button_layout.addWidget(add_button)
        add_selected_button = QPushButton("Add Selected")
        add_selected_button.clicked.connect(self.add_selected_contexts)
        button_layout.addWidget(add_selected_button)
        layout.addLayout(button_layout)

        self.populate_tables()

    def populate_tables(self):
        # Populate Recent and Open Files table
        self.recent_open_table.setRowCount(len(self.recent_files) + len(self.open_files))
        row = 0
        for file in self.recent_files:
            self.recent_open_table.setItem(row, 0, QTableWidgetItem(file))
            self.recent_open_table.setItem(row, 1, QTableWidgetItem("Recent"))
            self.recent_open_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, (file, "Recent"))
            row += 1
        for file in self.open_files:
            if file.startswith("Untitled_"):
                display_name = "Untitled"
            else:
                display_name = file
            self.recent_open_table.setItem(row, 0, QTableWidgetItem(display_name))
            self.recent_open_table.setItem(row, 1, QTableWidgetItem("Open"))
            self.recent_open_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, (file, "Open"))
            row += 1

        # Populate Existing Contexts table
        self.existing_contexts_table.setRowCount(len(self.existing_contexts))
        for i, context in enumerate(self.existing_contexts):
            self.existing_contexts_table.setItem(i, 0, QTableWidgetItem(context[0]))

    def filter_contexts(self, text):
        for row in range(self.recent_open_table.rowCount()):
            for col in range(self.recent_open_table.columnCount()):
                item = self.recent_open_table.item(row, col)
                if item:
                    item.setHidden(text.lower() not in item.text().lower())

    def preview_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.preview_area.setPlainText(content)
        except Exception as e:
            self.preview_area.setPlainText(f"Error reading file: {str(e)}")

    def preview_selected_file(self):
        selected_items = self.recent_open_table.selectedItems()
        if selected_items:
            file_path = selected_items[0].text()
            self.preview_file(file_path)

    def preview_selected_context(self):
        selected_items = self.existing_contexts_table.selectedItems()
        if selected_items:
            context_name = selected_items[0].text()
            context_content = next((content for name, content in self.existing_contexts if name == context_name), "")
            self.preview_area.setPlainText(context_content)

    def get_context_content(self, context_type, context_name, preview=False):
        try:
            if context_type in ["Recent", "Open"]:
                editor = self.editor_manager.get_editor_by_file_path(context_name)
                if editor:
                    return editor.toPlainText()
                elif os.path.exists(context_name):
                    with open(context_name, 'r', encoding='utf-8') as file:
                        return file.read()
                else:
                    return f"Error: File not found - {context_name}"
            elif context_type == "Search":
                return self.vault_manager.get_vault_item_by_path(context_name).content
            elif context_type == "Existing Contexts":
                return next(content for desc, content in self.existing_contexts if desc == context_name)
            return ""
        except Exception as e:
            logging.error(f"Error getting context content: {e}")
            return f"Error loading content: {str(e)}"

    def add_to_selected_files(self, file_path):
        if file_path not in self.selected_files:
            self.selected_files.append(file_path)
        self.preview_file(file_path)
    def add_selected_contexts(self):
        for file_path in self.selected_files:
            if self.is_binary_file(file_path):
                logging.warning(f"Skipping binary file: {file_path}")
                QMessageBox.warning(self, "Binary File", f"Cannot read binary file: {os.path.basename(file_path)}")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as file:
                        content = file.read()
                except Exception as e:
                    logging.error(f"Error reading file {file_path}: {e}")
                    QMessageBox.critical(self, "File Read Error", f"Failed to read file {file_path} due to encoding issues.")
                    continue

            self.context_added.emit(f"[File] {file_path}", content)
            self.context_manager.add_context(content, f"Context: {file_path}")  # Use full file path

        # Process selected items from existing contexts
        selected_contexts = self.existing_contexts_table.selectedItems()
        for item in selected_contexts:
            if item.column() == 0:  # Only process the first column
                context_name = item.text()
                content = self.get_context_content("Existing Contexts", context_name)
                self.context_added.emit(f"[Context] {context_name}", content)
                logging.warning(f"Emitting context: [Context] {context_name}")

        self.accept()

    def is_binary_file(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                chunk = file.read(1024)
                return b'\0' in chunk
        except Exception as e:
            logging.error(f"Error checking if file is binary: {e}")
            return False
 
    def add_custom_text(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Custom Text", "Enter your text:")
        if ok and text:
            self.context_added.emit("[Text] Custom Text", text)

    def add_import(self):
        module_name, ok = QInputDialog.getText(self, "Add Import", "Enter module name:")
        if ok and module_name:
            try:
                module = importlib.import_module(module_name)
                content = inspect.getsource(module)
                self.context_added.emit(f"[Import] {module_name}", content)
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to import {module_name}: {str(e)}")

    def add_url(self):
        url, ok = QInputDialog.getText(self, "Add URL", "Enter URL:")
        if ok and url:
            try:
                response = requests.get(url)
                content = response.text
                self.context_added.emit(f"[URL] {url}", content)
            except Exception as e:
                QMessageBox.warning(self, "URL Error", f"Failed to fetch content from {url}: {str(e)}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                with open(file_path, 'r') as file:
                    content = file.read()
                self.context_added.emit(f"[File] {file_path}", content)
        event.acceptProposedAction()

    def get_selected_items(self):
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.recent_open_table.selectedItems() if item.data(Qt.ItemDataRole.UserRole) is not None]

    def get_initial_directory(self):
        # Determine the initial directory
        if self.open_files:
            return Path(self.open_files[0]).parent
        elif self.vault_manager:
            return Path(self.vault_manager.get_default_vault_path())
        return Path("")