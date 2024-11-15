from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from typing import Optional

class NixPackageViewer(QWidget):
    def __init__(self, nix_manager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.nix_manager = nix_manager
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI for the package viewer"""
        layout = QVBoxLayout()
        
        self.package_info = QTextEdit()
        self.package_info.setReadOnly(True)
        
        layout.addWidget(QLabel("Nix Package Viewer"))
        layout.addWidget(self.package_info)
        
        self.setLayout(layout)

    def display_package_info(self, package_name: str):
        """Display information about a specific Nix package"""
        # Fetch package info using nix_manager
        package_info = self.nix_manager.get_package_info(package_name)
        self.package_info.setPlainText(package_info) 