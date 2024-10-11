from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QInputDialog, QMessageBox

class FilesetManagerWidget(QWidget):
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.fileset_list = QListWidget()
        layout.addWidget(self.fileset_list)

        button_layout = QHBoxLayout()
        self.create_button = QPushButton("Create Fileset")
        self.remove_button = QPushButton("Remove Fileset")
        self.activate_button = QPushButton("Activate Fileset")
        
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.activate_button)

        layout.addLayout(button_layout)

        self.create_button.clicked.connect(self.create_fileset)
        self.remove_button.clicked.connect(self.remove_fileset)
        self.activate_button.clicked.connect(self.activate_fileset)

        self.update_fileset_list()

    def update_fileset_list(self):
        self.fileset_list.clear()
        current_vault = self.cccore.vault_manager.get_current_vault()
        current_workspace = self.cccore.workspace_manager.get_active_workspace()
        if current_vault and current_workspace:
            filesets = current_workspace.filesets.keys()
            self.fileset_list.addItems(filesets)

    def create_fileset(self):
        name, ok = QInputDialog.getText(self, "Create Fileset", "Enter fileset name:")
        if ok and name:
            current_vault = self.cccore.vault_manager.get_current_vault()
            current_workspace = self.cccore.workspace_manager.get_active_workspace()
            if current_vault and current_workspace:
                success = self.cccore.workspace_manager.create_fileset(current_vault.path, current_workspace.name, name)
                if success:
                    self.update_fileset_list()
                    QMessageBox.information(self, "Success", f"Fileset '{name}' created.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to create fileset.")

    def remove_fileset(self):
        selected_item = self.fileset_list.currentItem()
        if selected_item:
            name = selected_item.text()
            current_vault = self.cccore.vault_manager.get_current_vault()
            current_workspace = self.cccore.workspace_manager.get_active_workspace()
            if current_vault and current_workspace:
                success = self.cccore.workspace_manager.remove_fileset(current_vault.path, current_workspace.name, name)
                if success:
                    self.update_fileset_list()
                    QMessageBox.information(self, "Success", f"Fileset '{name}' removed.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to remove fileset.")

    def activate_fileset(self):
        selected_item = self.fileset_list.currentItem()
        if selected_item:
            name = selected_item.text()
            current_vault = self.cccore.vault_manager.get_current_vault()
            current_workspace = self.cccore.workspace_manager.get_active_workspace()
            if current_vault and current_workspace:
                success = self.cccore.workspace_manager.set_active_fileset(current_vault.path, current_workspace.name, name)
                if success:
                    QMessageBox.information(self, "Success", f"Fileset '{name}' activated.")
                    # Here you would typically update the open files in your editor
                    active_files = self.cccore.workspace_manager.get_active_files(current_vault.path, current_workspace.name)
                    # Implement a method to open these files in your editor
                    self.cccore.editor_manager.open_files(active_files)
                else:
                    QMessageBox.warning(self, "Error", "Failed to activate fileset.")