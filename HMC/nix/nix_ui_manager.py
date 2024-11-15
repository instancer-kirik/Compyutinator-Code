from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
from .nix_manager import NixManager, NixStore, NixPackage
from typing import Optional, Dict
import logging

class NixUIManager:
    def __init__(self, nix_manager: NixManager):
        self.nix_manager = nix_manager
        self.current_store = NixStore.SYSTEM
        self.widgets: Dict[str, QWidget] = {}
        
    def create_store_browser(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create a store browser widget"""
        from GUX.nix_store_browser import NixStoreBrowser
        browser = NixStoreBrowser(self.nix_manager, parent)
        self.widgets['store_browser'] = browser
        return browser
        
    def create_package_viewer(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create a package viewer widget"""
        from GUX.nix_package_viewer import NixPackageViewer
        viewer = NixPackageViewer(self.nix_manager, parent)
        self.widgets['package_viewer'] = viewer
        return viewer
        
    def refresh_widgets(self):
        """Refresh all Nix-related widgets"""
        try:
            items = self.nix_manager.get_store_items(self.current_store)
            
            for widget in self.widgets.values():
                if hasattr(widget, 'update_items'):
                    widget.update_items(items)
                    
        except Exception as e:
            logging.error(f"Error refreshing Nix widgets: {e}") 