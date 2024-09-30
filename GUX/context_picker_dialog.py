from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTreeWidget, QPushButton, QFileDialog, 
                             QTextEdit, QLabel, QLineEdit, QTreeWidgetItem, QSplitter, 
                             QWidget, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
import os
from PyQt6.QtWidgets import QInputDialog
class ContextPickerDialog(QDialog):
    context_added = pyqtSignal(str, str)  # context_type, context_content

    def __init__(self, parent=None, recent_files=None, open_files=None, existing_contexts=None):
        super().__init__(parent)
        self.setWindowTitle("Add Context")
        self.recent_files = recent_files or []
        self.open_files = open_files or []
        self.existing_contexts = existing_contexts or []
        self.initUI()
        self.setAcceptDrops(True)

    def initUI(self):
        layout = QVBoxLayout(self)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search contexts...")
        self.search_bar.textChanged.connect(self.filter_contexts)
        layout.addWidget(self.search_bar)

        # Splitter for tree view and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Tree view for contexts
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Contexts"])
        self.tree_widget.itemClicked.connect(self.preview_context)
        splitter.addWidget(self.tree_widget)

        # Preview area
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        splitter.addWidget(self.preview_area)

        # Populate tree
        self.populate_tree()

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Selected")
        add_button.clicked.connect(self.add_selected_contexts)
        button_layout.addWidget(add_button)

        add_file_button = QPushButton("Add File")
        add_file_button.clicked.connect(self.add_file)
        button_layout.addWidget(add_file_button)

        add_text_button = QPushButton("Add Custom Text")
        add_text_button.clicked.connect(self.add_custom_text)
        button_layout.addWidget(add_text_button)

        layout.addLayout(button_layout)

    def populate_tree(self):
        self.tree_widget.clear()

        # Open Files
        open_files_item = QTreeWidgetItem(self.tree_widget, ["Open Files"])
        for file in self.open_files:
            QTreeWidgetItem(open_files_item, [os.path.basename(file)])

        # Recent Files
        recent_files_item = QTreeWidgetItem(self.tree_widget, ["Recent Files"])
        for file in self.recent_files:
            QTreeWidgetItem(recent_files_item, [os.path.basename(file)])

        # Existing Contexts
        existing_contexts_item = QTreeWidgetItem(self.tree_widget, ["Existing Contexts"])
        for context in self.existing_contexts:
            QTreeWidgetItem(existing_contexts_item, [context])

        self.tree_widget.expandAll()

    def filter_contexts(self, text):
        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                child.setHidden(text.lower() not in child.text(0).lower())

    def preview_context(self, item, column):
        if item.parent():  # It's a child item (actual context)
            context_type = item.parent().text(0)
            context_name = item.text(0)
            content = self.get_context_content(context_type, context_name)
            self.preview_area.setPlainText(content)

    def get_context_content(self, context_type, context_name):
        if context_type == "Open Files":
            file_path = next(f for f in self.open_files if os.path.basename(f) == context_name)
            with open(file_path, 'r') as file:
                return file.read()
        elif context_type == "Recent Files":
            file_path = next(f for f in self.recent_files if os.path.basename(f) == context_name)
            with open(file_path, 'r') as file:
                return file.read()
        elif context_type == "Existing Contexts":
            return next(content for desc, content in self.existing_contexts if desc == context_name)
        return ""

    def add_selected_contexts(self):
        for item in self.tree_widget.selectedItems():
            if item.parent():  # It's a child item (actual context)
                context_type = item.parent().text(0)
                context_name = item.text(0)
                content = self.get_context_content(context_type, context_name)
                self.context_added.emit(f"{context_type}: {context_name}", content)
        self.accept()

    def add_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            with open(file_path, 'r') as file:
                content = file.read()
            self.context_added.emit(f"File: {os.path.basename(file_path)}", content)

    def add_custom_text(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Custom Text", "Enter your text:")
        if ok and text:
            self.context_added.emit("Custom Text", text)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                with open(file_path, 'r') as file:
                    content = file.read()
                self.context_added.emit(f"File: {os.path.basename(file_path)}", content)
        event.acceptProposedAction()

