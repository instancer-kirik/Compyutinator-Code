import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class FileSearchWidget(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, vault_manager, parent=None):
        super().__init__(parent)
        self.vault_manager = vault_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files...")
        self.search_button = QPushButton("Search")
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        self.results_label = QLabel("Results:")
        layout.addWidget(self.results_label)

        self.results_list = QListWidget()
        layout.addWidget(self.results_list)

        self.search_button.clicked.connect(self.perform_search)
        self.search_input.returnPressed.connect(self.perform_search)
        self.results_list.itemDoubleClicked.connect(self.open_selected_file)

    def perform_search(self):
        query = self.search_input.text().lower()
        if not query:
            return

        self.results_list.clear()
        vault_path = self.vault_manager.get_current_vault_path()

        # First, search for filename matches
        filename_matches = []
        for root, _, files in os.walk(vault_path):
            for file in files:
                if query in file.lower():
                    filename_matches.append(os.path.join(root, file))

        # Then, search for in-text matches
        in_text_matches = []
        for root, _, files in os.walk(vault_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in filename_matches:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if query in content.lower():
                                in_text_matches.append(file_path)
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")

        # Add results to the list widget
        for match in filename_matches:
            self.results_list.addItem(f"[Filename] {os.path.relpath(match, vault_path)}")
        for match in in_text_matches:
            self.results_list.addItem(f"[Content] {os.path.relpath(match, vault_path)}")

        self.results_label.setText(f"Results: {len(filename_matches) + len(in_text_matches)}")

    def open_selected_file(self, item):
        file_path = item.text().split('] ', 1)[1]
        full_path = os.path.join(self.vault_manager.get_current_vault_path(), file_path)
        self.file_selected.emit(full_path)