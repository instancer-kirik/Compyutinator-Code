import os
from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QPushButton, QFileDialog, 
                             QTextEdit, QLabel, QLineEdit, QTreeWidgetItem, QSplitter, 
                             QWidget, QHBoxLayout, QInputDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
import os
import importlib
import inspect
import math
import logging
from PyQt6.QtGui import QFont
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

    def __init__(self, parent=None, recent_files=None, open_files=None, existing_contexts=None, editor_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Add Context")
        self.recent_files = recent_files or []
        self.open_files = open_files or []
        self.existing_contexts = existing_contexts or []
        self.editor_manager = editor_manager
        logging.debug(f"Initializing ContextPickerDialog with {len(self.open_files)} open files, "
                      f"{len(self.recent_files)} recent files, and {len(self.existing_contexts)} existing contexts")
        self.initUI()
        self.setAcceptDrops(True)
        self.resize(1000, 800)

    def initUI(self):
        layout = QVBoxLayout(self)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search contexts...")
        self.search_bar.textChanged.connect(self.filter_contexts)
        layout.addWidget(self.search_bar)

        # Splitter for grid view and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Grid view for filenames
        self.grid_widget = QTableWidget()
        self.grid_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.grid_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.grid_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.grid_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.grid_widget.itemSelectionChanged.connect(self.preview_context)
        splitter.addWidget(self.grid_widget)

        # Preview area
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        splitter.addWidget(self.preview_area)

        # Populate grid
        self.populate_grid()

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Selected")
        add_button.clicked.connect(self.add_selected_contexts)
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

    def populate_grid(self):
        all_files = [(f, "Open Files") for f in self.open_files] + \
                    [(f, "Recent Files") for f in self.recent_files] + \
                    [(ctx[0], "Existing Contexts") for ctx in self.existing_contexts]
        
        num_files = len(all_files)
        num_cols = max(1, int(math.sqrt(num_files * 2)))  # Increase number of columns
        num_rows = math.ceil(num_files / num_cols)

        self.grid_widget.setRowCount(num_rows)
        self.grid_widget.setColumnCount(num_cols)
        self.grid_widget.horizontalHeader().setVisible(False)
        self.grid_widget.verticalHeader().setVisible(False)

        for i, (file, file_type) in enumerate(all_files):
            row = i // num_cols
            col = i % num_cols
            
            file_widget = FileItemWidget(file, file_type)
            self.grid_widget.setCellWidget(row, col, file_widget)
            
            # Store the file and file_type in the cell's data
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, (file, file_type))
            self.grid_widget.setItem(row, col, item)

        self.grid_widget.resizeColumnsToContents()
        self.grid_widget.resizeRowsToContents()

        logging.debug(f"Populated grid with {num_files} files in a {num_rows}x{num_cols} grid")

    def filter_contexts(self, text):
        for row in range(self.grid_widget.rowCount()):
         #  $# match = False
            for col in range(self.grid_widget.columnCount()):
                item = self.grid_widget.item(row, col)
                if item:
                    item.setHidden(text.lower() not in item.text().lower())

    def preview_context(self):
        selected_items = self.grid_widget.selectedItems()
        if selected_items:
            item = selected_items[0]
            row, col = item.row(), item.column()
            file_widget = self.grid_widget.cellWidget(row, col)
            file, file_type = item.data(Qt.ItemDataRole.UserRole)
            logging.debug(f"Previewing context: {file_type} - {file}")
            try:
                content = self.get_context_content(file_type, file, preview=True)
                self.preview_area.setPlainText(content)
            except Exception as e:
                error_message = f"Error previewing content: {str(e)}"
                self.preview_area.setPlainText(error_message)
                logging.error(error_message)

    def get_context_content(self, context_type, context_name, preview=False):
        try:
            if context_type == "Open Files":
                return self.editor_manager.get_editor_by_path(context_name).text()
            elif context_type == "Recent Files":
                with open(context_name, 'r', encoding='utf-8') as file:
                    return file.read()
            elif context_type == "Existing Contexts":
                return next(content for desc, content in self.existing_contexts if desc == context_name)
            return ""
        except Exception as e:
            logging.error(f"Error getting context content: {e}")
            return f"Error loading content: {str(e)}"

    def add_selected_contexts(self):
        selected_items = self.grid_widget.selectedItems()
        for item in selected_items:
            file, file_type = item.data(Qt.ItemDataRole.UserRole)
            content = self.get_context_content(file_type, file)
            self.context_added.emit(f"[{file_type}] {os.path.basename(file)}", content)
        self.accept()

    def add_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            with open(file_path, 'r') as file:
                content = file.read()
            self.context_added.emit(f"[File] {os.path.basename(file_path)}", content)

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
        import requests
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
                self.context_added.emit(f"[File] {os.path.basename(file_path)}", content)
        event.acceptProposedAction()

    def get_selected_items(self):
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.grid_widget.selectedItems()]