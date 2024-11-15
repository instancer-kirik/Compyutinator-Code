from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QApplication, 
    QHBoxLayout, QPushButton, QLineEdit, QLabel, QMenu,
    QMessageBox, QHeaderView, QComboBox, QDialog, QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt,  pyqtSignal, QSize
from PyQt6.QtGui import QFont 
import os
import subprocess
import re
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict
import json
from enum import Enum
from datetime import datetime
import sys
@dataclass
class AtomIdentifier:
    scheme: Optional[str]
    user: Optional[str]
    password: Optional[str]
    url_alias: Optional[str]
    url_fragment: Optional[str]
    atom_id: str
    version: Optional[str]

    @classmethod
    def parse(cls, uri: str) -> 'AtomIdentifier':
        """Parse an Atom URI into components"""
        # Implementation of the Atom URI parser
        pass

class AtomStore(Enum):
    GIT = "git"
    S3 = "s3"
    NIX = "nix"
    LOCAL = "local"

class NixStoreBrowser(QWidget):
    """Browser for the Nix store with human-readable paths"""
    
    item_selected = pyqtSignal(str)  # Emits full store path when item selected

    def __init__(self, nix_manager, parent=None):
        super().__init__(parent)
        self.nix_manager = nix_manager
        self.atom_manager = AtomManager(nix_manager)
        self.nix_available = self.nix_manager.nix_available
        self.setup_ui()
        if self.nix_available:
            self.load_store_items()
        else:
            self.show_nix_not_found_message()

    def check_nix_installation(self):
        """Check if Nix is installed and available"""
        try:
            result = subprocess.run(
                ['which', 'nix-store'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def show_nix_not_found_message(self):
        """Show message when Nix is not installed"""
        self.store_tree.clear()
        item = QTreeWidgetItem(["Nix package manager not found"])
        self.store_tree.addTopLevelItem(item)
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Nix Not Found")
        msg.setText("The Nix package manager is not installed or not in PATH")
        msg.setInformativeText(
            "To use the Nix Store Browser, please install Nix:\n"
            "1. Visit https://nixos.org/download.html\n"
            "2. Follow the installation instructions for your system\n"
            "3. Restart the application after installation"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def setup_ui(self):
        """Setup the main UI components"""
        layout = QVBoxLayout()
        
        # Add Atom URI input
        uri_layout = QHBoxLayout()
        self.uri_input = QLineEdit()
        self.uri_input.setPlaceholderText("Enter Atom URI (e.g., gh:owner/repo::my-atom@^1)")
        self.resolve_btn = QPushButton("Resolve")
        self.resolve_btn.clicked.connect(self.resolve_atom)
        
        uri_layout.addWidget(self.uri_input)
        uri_layout.addWidget(self.resolve_btn)
        layout.addLayout(uri_layout)
        
        # Add store type selector
        store_layout = QHBoxLayout()
        self.store_combo = QComboBox()
        self.store_combo.addItems([store.value for store in AtomStore])
        store_layout.addWidget(QLabel("Store Type:"))
        store_layout.addWidget(self.store_combo)
        layout.addLayout(store_layout)
        
        # Add main store browser components
        self.setup_store_browser(layout)
        
        self.setLayout(layout)
    def setup_atom_actions(self):
            """Setup Atom-specific actions"""
            self.atom_actions = [
                ("Show Dependencies", self.show_atom_deps),
                ("Show Reverse Dependencies", self.show_atom_reverse_deps),
                ("Show Build Log", self.show_atom_build_log),
                ("Copy Atom URI", self.copy_atom_uri),
                ("Publish Atom", self.publish_atom),
                ("Generate Lock", self.generate_lock),
                ("Show Module Info", self.show_module_info)
            ]
    def resolve_atom(self):
        """Resolve an Atom URI and display info"""
        try:
            uri = self.uri_input.text()
            store_type = AtomStore(self.store_combo.currentText())
            
            info = self.atom_manager.resolve_atom(uri, store_type)
            self.display_atom_info(info)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to resolve Atom: {e}")

    def show_nix_info(self, path):
        """Show detailed Nix package information"""
        try:
            # Get basic info
            result = subprocess.run(
                ['nix', 'path-info', '--json', path],
                capture_output=True, text=True, check=True
            )
            info = json.loads(result.stdout)[0]
            
            # Format info nicely
            details = [
                f"Path: {info.get('path')}",
                f"Size: {self.format_size(info.get('narSize', 0))}",
                f"Hash: {info.get('narHash', 'N/A')}",
                f"References: {len(info.get('references', []))}",
                f"Referrers: {len(info.get('referrers', []))}",
                f"Registration Time: {datetime.fromtimestamp(info.get('registrationTime', 0))}",
            ]
            
            self.show_info_dialog("Package Information", "\n".join(details))
        except Exception as e:
            raise Exception(f"Failed to get package info: {e}")

    def open_in_file_manager(self, path):
        """Open the package directory in system file manager"""
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', path])
            elif sys.platform == 'win32':
                subprocess.run(['explorer', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            raise Exception(f"Failed to open file manager: {e}")

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def show_dependencies(self, path):
        """Show dependencies of a store item"""
        try:
            result = subprocess.run(
                ['nix-store', '--query', '--references', path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                deps = result.stdout.strip().split('\n')
                self.show_info_dialog("Dependencies", '\n'.join(deps))
            else:
                raise Exception(result.stderr)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get dependencies: {e}")

    def show_referrers(self, path):
        """Show items that refer to this store item"""
        try:
            result = subprocess.run(
                ['nix-store', '--query', '--referrers', path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                refs = result.stdout.strip().split('\n')
                self.show_info_dialog("Referrers", '\n'.join(refs))
            else:
                raise Exception(result.stderr)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get referrers: {e}")

    def show_tree(self, path):
        """Show dependency tree of a store item"""
        try:
            result = subprocess.run(
                ['nix-store', '--query', '--tree', path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.show_info_dialog("Dependency Tree", result.stdout)
            else:
                raise Exception(result.stderr)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get dependency tree: {e}")

    def delete_item(self, path):
        """Delete a store item"""
        try:
            if QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete this item?\n{path}"
            ) == QMessageBox.StandardButton.Yes:
                subprocess.run(['nix-store', '--delete', path], check=True)
                self.load_store_items()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete item: {e}")

    def show_info_dialog(self, title, text, monospace=False):
        """Show information in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(text)
        
        if monospace:
            font = QFont("Monospace")
            font.setStyleHint(QFont.StyleHint.Monospace)
            text_edit.setFont(font)
            
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()

    def on_item_double_clicked(self, item, column):
        """Handle double click on item"""
        full_path = item.toolTip(0)
        self.item_selected.emit(full_path) 

    def on_sort_changed(self, index):
        """Handle sort combo box changes"""
        self.sort_column = index
        self.sort_items()

    def toggle_sort_order(self):
        """Toggle between ascending and descending sort"""
        self.sort_order = Qt.SortOrder.DescendingOrder if self.sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        self.sort_order_btn.setText("↓" if self.sort_order == Qt.SortOrder.DescendingOrder else "↑")
        self.sort_items()

    def on_header_clicked(self, index):
        """Handle clicking on tree widget header"""
        self.sort_combo.setCurrentIndex(index)
        self.toggle_sort_order()

    def sort_items(self):
        """Sort items based on current sort column and order"""
        self.store_tree.sortItems(
            self.sort_column,
            self.sort_order
        )

    def parse_size(self, size_str):
        """Convert size string to numeric value for sorting"""
        try:
            if size_str == "N/A":
                return 0
            value, unit = size_str.split()
            value = float(value)
            multiplier = {
                'B': 1,
                'KB': 1024,
                'MB': 1024**2,
                'GB': 1024**3,
                'TB': 1024**4,
                'PB': 1024**5
            }
            return value * multiplier[unit]
        except:
            return 0
        
    def setup_advanced_features(self):
        """Setup advanced package management features"""
        self.add_toolbar([
            ("Analyze Dependencies", self.analyze_dependencies),
            ("Check Updates", self.check_updates),
            ("Build Schedule", self.show_build_schedule),
            ("Package Health", self.show_health_metrics)
        ])
        
    def setup_existing_ui(self, layout):
        """Setup the main UI components"""
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search packages...")
        self.search_input.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.search_input)
        
        # Sort controls
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Size", "Date"])
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        self.sort_column = 0
        
        self.sort_order = Qt.SortOrder.AscendingOrder
        self.sort_order_btn = QPushButton("↑")
        self.sort_order_btn.setFixedWidth(30)
        self.sort_order_btn.clicked.connect(self.toggle_sort_order)
        
        search_layout.addWidget(self.sort_combo)
        search_layout.addWidget(self.sort_order_btn)
        layout.addLayout(search_layout)
        
        # Store tree
        self.store_tree = QTreeWidget()
        self.store_tree.setHeaderLabels(["Package", "Size", "Last Modified"])
        self.store_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.store_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.store_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.store_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.store_tree.header().sectionClicked.connect(self.on_header_clicked)
        layout.addWidget(self.store_tree)
        
    def filter_items(self, text):
        """Filter store items based on search text"""
        for i in range(self.store_tree.topLevelItemCount()):
            item = self.store_tree.topLevelItem(i)
            matches = any(
                text.lower() in item.text(col).lower()
                for col in range(item.columnCount())
            )
            item.setHidden(not matches)

    def load_store_items(self):
        """Load items from the Nix store"""
        try:
            self.store_tree.clear()
            
            if not self.nix_available:
                self.show_nix_not_found_message()
                return
            
            result = subprocess.run(
                ['nix-store', '--gc', '--print-live'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"nix-store command failed: {result.stderr}")
            
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                    
                path = line.strip()
                name = os.path.basename(path)
                size = self.get_item_size(path)
                modified = self.get_item_modified(path)
                
                item = QTreeWidgetItem([name, size, modified])
                item.setToolTip(0, path)  # Store full path in tooltip
                self.store_tree.addTopLevelItem(item)
                
            self.sort_items()
            
        except FileNotFoundError:
            logging.error("Nix commands not found. Please install Nix package manager.")
            self.show_nix_not_found_message()
        except Exception as e:
            logging.error(f"Error loading store items: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load store items: {e}")

    def get_item_size(self, path):
        """Get human-readable size of store item"""
        try:
            result = self.run_nix_command(['nix-store', '--query', '--size', path])
            size_bytes = int(result.stdout.strip())
            return self.format_size(size_bytes)
        except:
            return "N/A"

    def get_item_modified(self, path):
        """Get last modified time of store item"""
        try:
            mtime = os.path.getmtime(path)
            return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        except:
            return "N/A"

    def format_size(self, size_bytes):
        """Format bytes into human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"


    def show_context_menu(self, position):
        """Show context menu for store items"""
        item = self.store_tree.itemAt(position)
        if not item:
            return
            
        path = item.toolTip(0)  # Full path stored in tooltip
        menu = QMenu(self)
        
        # Basic Nix actions
        menu.addAction("Show Info", lambda: self.show_nix_info(path))
        menu.addAction("Show Dependencies", lambda: self.show_dependencies(path))
        menu.addAction("Show Referrers", lambda: self.show_referrers(path))
        menu.addAction("Copy Path", lambda: self.copy_to_clipboard(path))
        
        # Atom-specific actions
        menu.addSeparator()
        menu.addAction("Show Atom Dependencies", lambda: self.show_atom_deps(path))
        menu.addAction("Show Atom Reverse Deps", lambda: self.show_atom_reverse_deps(path))
        menu.addAction("Show Build Log", lambda: self.show_atom_build_log(path))
        menu.addAction("Copy Atom URI", lambda: self.copy_atom_uri(path))
        menu.addAction("Generate Lock File", lambda: self.generate_lock(path))
        
        menu.exec(self.store_tree.viewport().mapToGlobal(position))

    def show_atom_deps(self, path):
        """Show Atom dependencies"""
        try:
            deps = self.atom_manager.get_atom_deps(path)
            info = f"Dependencies for {os.path.basename(path)}:\n\n"
            for dep in deps:
                if dep:
                    info += f"• {os.path.basename(dep)}\n"
                    info += f"  {dep}\n"
            self.show_info_dialog("Atom Dependencies", info)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get dependencies: {e}")

    def show_atom_reverse_deps(self, path):
        """Show reverse dependencies"""
        try:
            rev_deps = self.atom_manager.get_atom_reverse_deps(path)
            info = f"Reverse Dependencies for {os.path.basename(path)}:\n\n"
            for dep in rev_deps:
                if dep:
                    info += f"• {os.path.basename(dep)}\n"
                    info += f"  {dep}\n"
            self.show_info_dialog("Reverse Dependencies", info)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get reverse dependencies: {e}")

    def show_atom_build_log(self, path):
        """Show build log"""
        try:
            log = self.atom_manager.get_atom_build_log(path)
            if log:
                self.show_info_dialog(
                    f"Build Log - {os.path.basename(path)}", 
                    log,
                    monospace=True
                )
            else:
                QMessageBox.information(self, "No Build Log", "No build log found")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get build log: {e}")

    def copy_atom_uri(self, path):
        """Copy Atom URI to clipboard"""
        try:
            uri = self.atom_manager.get_atom_uri(path)
            QApplication.clipboard().setText(uri)
            QMessageBox.information(self, "URI Copied", f"Copied Atom URI: {uri}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to copy URI: {e}")