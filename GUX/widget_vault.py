from PyQt6.QtWidgets import QWidget, QDockWidget, QMenu,QVBoxLayout, QComboBox, QPushButton, QListWidget, QInputDialog, QMessageBox, QHBoxLayout, QSplitter
from PyQt6.QtCore import Qt
from AuraText.auratext.Core.CodeEditor import CodeEditor
from GUX.markdown_viewer import MarkdownViewer
import os
import hashlib

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
                             QLineEdit, QMessageBox, QApplication)

import requests
from AuraText.auratext.scripts.def_path import resource
from PyQt6.QtCore import pyqtSignal
import logging
from PyQt6.QtGui import QIcon

class VaultsManagerWidget(QWidget):
    vault_selected = pyqtSignal(str)

    def __init__(self, parent, cccore):
        super().__init__(parent)
        self.cccore = cccore
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.vault_list = QListWidget()
        self.vault_list.itemClicked.connect(self.on_vault_selected)
        layout.addWidget(self.vault_list)

        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Vault")
        add_button.clicked.connect(self.add_vault)
        remove_button = QPushButton("Remove Vault")
        remove_button.clicked.connect(self.remove_vault)
        rename_button = QPushButton("Rename Vault")
        rename_button.clicked.connect(self.rename_vault)
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(rename_button)
        
        layout.addLayout(button_layout)

        self.open_config_button = QPushButton("Open Vault Config File")
        self.open_config_button.clicked.connect(self.open_config_file)
        layout.addWidget(self.open_config_button)
        
        self.refresh_vaults()

    def refresh_vaults(self):
        self.vault_list.clear()
        try:
            vaults = self.cccore.vault_manager.get_vaults()
            self.vault_list.addItems(vaults)
        except AttributeError:
            logging.error("VaultManager does not have get_vaults method")
        except Exception as e:
            logging.error(f"Error refreshing vaults: {str(e)}")

    def on_vault_selected(self, item):
        self.vault_selected.emit(item.text())

    def add_vault(self):
        name, ok = QInputDialog.getText(self, "Add Vault", "Enter vault name:")
        if ok and name:
            self.cccore.vault_manager.add_vault(name)
            self.refresh_vaults()

    def remove_vault(self):
        current_item = self.vault_list.currentItem()
        if current_item:
            reply = QMessageBox.question(self, "Remove Vault", 
                                         f"Are you sure you want to remove {current_item.text()}?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.cccore.vault_manager.remove_vault(current_item.text())
                self.refresh_vaults()

    def rename_vault(self):
        current_item = self.vault_list.currentItem()
        if current_item:
            new_name, ok = QInputDialog.getText(self, "Rename Vault", 
                                                "Enter new vault name:", 
                                                text=current_item.text())
            if ok and new_name:
                self.cccore.vault_manager.rename_vault(current_item.text(), new_name)
                self.refresh_vaults()

    def open_config_file(self):
        config_path = self.cccore.vault_manager.get_config_file_path()
        if config_path and os.path.exists(config_path):
            self.cccore.editor_manager.open_file(config_path)
        else:
            QMessageBox.warning(self, "Error", "Config file not found.")

class VaultWidget(QWidget):
    def __init__(self, parent, cccore):
        super().__init__(parent)
        self.cccore = cccore
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # File list
        file_list_widget = QWidget()
        file_list_layout = QVBoxLayout(file_list_widget)
        
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.open_file)
        file_list_layout.addWidget(self.file_list)

        button_layout = QHBoxLayout()
        add_file_button = QPushButton("Add File")
        add_file_button.clicked.connect(self.add_file)
        remove_file_button = QPushButton("Remove File")
        remove_file_button.clicked.connect(self.remove_file)
        button_layout.addWidget(add_file_button)
        button_layout.addWidget(remove_file_button)
        
        file_list_layout.addLayout(button_layout)

        # Editor/Viewer
        self.editor_viewer = QSplitter(Qt.Orientation.Vertical)
        self.code_editor = CodeEditor(self.cccore)
        self.markdown_viewer = MarkdownViewer(self.cccore.vault_manager.get_vault_path())
        self.editor_viewer.addWidget(self.code_editor)
        self.editor_viewer.addWidget(self.markdown_viewer)
        self.markdown_viewer.hide()  # Initially hide the markdown viewer

        # Add widgets to main layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(file_list_widget)
        splitter.addWidget(self.editor_viewer)
        layout.addWidget(splitter)

        self.refresh_files()

    def refresh_files(self):
        self.file_list.clear()
        files = self.cccore.vault_manager.get_files()
        self.file_list.addItems(files)

    def open_file(self, item):
        file_path = self.cccore.vault_manager.get_file_path(item.text())
        if file_path:
            _, file_extension = os.path.splitext(file_path)
            if file_extension.lower() == '.md':
                self.code_editor.hide()
                self.markdown_viewer.show()
                self.markdown_viewer.load_markdown(file_path)
            else:
                self.markdown_viewer.hide()
                self.code_editor.show()
                self.code_editor.load_file(file_path)

    def add_file(self):
        name, ok = QInputDialog.getText(self, "Add File", "Enter file name:")
        if ok and name:
            self.cccore.vault_manager.add_file(name)
            self.refresh_files()

    def remove_file(self):
        current_item = self.file_list.currentItem()
        if current_item:
            reply = QMessageBox.question(self, "Remove File", 
                                         f"Are you sure you want to remove {current_item.text()}?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.cccore.vault_manager.remove_file(current_item.text())
                self.refresh_files()

    def on_vault_switch(self, new_vault_path):
        self.markdown_viewer.set_vault_path(new_vault_path)
        self.refresh_files()
class FileExplorerWidget(QWidget):
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.setWindowTitle("File Explorer")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #282828; color: #FFFFFF;")
        self.setWindowIcon(QIcon(resource(r"../media/terminal/new.svg")))
        self.setWindowIcon(QIcon(resource(r"../media/terminal/remove.svg")))
        self.setWindowIcon(QIcon(resource(r"../media/terminal/remove.svg")))
        self.setWindowIcon(QIcon(resource(r"../media/terminal/remove.svg")))
        self.setWindowIcon(QIcon(resource(r"../media/terminal/remove.svg")))
            

class HashSlingingHasherWidget(QWidget):
    def __init__(self, backend_url):
        super().__init__()
        self.backend_url = backend_url
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        file_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("File path...")
        file_layout.addWidget(self.file_path_input)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_button)

        layout.addLayout(file_layout)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter file name (optional)")
        layout.addWidget(self.name_input)

        check_button = QPushButton("Check/Add Hash")
        check_button.clicked.connect(self.check_or_add_hash)
        layout.addWidget(check_button)

        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_label)

        self.setLayout(layout)
        self.setWindowTitle("File Hash Checker/Adder")

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.file_path_input.setText(file_path)
            if not self.name_input.text():
                self.name_input.setText(os.path.basename(file_path))

    def calculate_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def check_or_add_hash(self):
        file_path = self.file_path_input.text()
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "Error", "Invalid file path")
            return

        file_hash = self.calculate_hash(file_path)
        file_name = self.name_input.text() or os.path.basename(file_path)
        
        try:
            response = requests.post(
                f"{self.backend_url}/check_or_add_hash",
                json={"hash": file_hash, "name": file_name}
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("exists", False):
                name = data.get("name", "Unknown")
                self.result_label.setText(f"Hash found in database. Name: {name}")
            else:
                self.result_label.setText(f"Hash added to database with name: {file_name}")
        except requests.RequestException as e:
            QMessageBox.critical(self, "Error", f"Failed to check/add hash: {str(e)}")
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt

class AudioLevelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0

    def setLevel(self, level):
        self.level = level
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        bar_width = width - 4
        bar_height = height - 4

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(2, 2, bar_width, bar_height)

        level_height = int(bar_height * (self.level / 100))
        painter.setBrush(QColor(0, 255, 0))
        painter.drawRect(2, 2 + bar_height - level_height, bar_width, level_height)