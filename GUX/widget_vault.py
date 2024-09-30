from PyQt6.QtWidgets import QWidget, QDockWidget, QVBoxLayout, QPushButton, QListWidget, QInputDialog, QMessageBox, QHBoxLayout, QSplitter
from PyQt6.QtCore import Qt
from AuraText.auratext.Core.CodeEditor import CodeEditor
from GUX.markdown_viewer import MarkdownViewer
import os
from PyQt6.QtCore import pyqtSignal
import logging
class ProjectsManagerWidget(QWidget):
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        # Implement projects manager widget
        # This could include a list of projects and buttons to add/remove projects

class VaultsManagerWidget(QWidget):
    vault_selected = pyqtSignal(str)

    def __init__(self, cccore):
        super().__init__()
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
    def __init__(self, cccore):
        super().__init__()
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
