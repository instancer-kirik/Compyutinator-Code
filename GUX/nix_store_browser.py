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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nix_available = self.check_nix_installation()
        self.setup_atom_support()
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

    def setup_atom_support(self):
        """Initialize Atom support"""
        self.atom_config = self.load_atom_config()
        self.atom_stores = {}
        self.setup_atom_stores()
        
    def load_atom_config(self) -> Dict:
        """Load eka config"""
        try:
            config_path = os.path.expanduser("~/.config/eka/eka.json")
            if os.path.exists(config_path):
                with open(config_path) as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"Error loading Atom config: {e}")
            return {}

    def setup_atom_stores(self):
        """Initialize configured Atom stores"""
        # Setup store backends based on config
        pass

    def setup_ui(self):
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

        # Existing UI components...
        self.setup_existing_ui(layout)
        
        # Add Atom-specific actions
        self.setup_atom_actions()
        
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
        """Resolve an Atom URI and display package info"""
        try:
            uri = self.uri_input.text()
            atom = AtomIdentifier.parse(uri)
            
            # Resolve the Atom using appropriate store
            store_type = AtomStore(self.store_combo.currentText())
            if store_type in self.atom_stores:
                store = self.atom_stores[store_type]
                info = store.resolve(atom)
                self.display_atom_info(info)
            else:
                raise Exception(f"Unsupported store type: {store_type}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to resolve Atom: {e}")

    def publish_atom(self, path: str):
        """Publish a new Atom version"""
        try:
            store_type = AtomStore(self.store_combo.currentText())
            if store_type in self.atom_stores:
                store = self.atom_stores[store_type]
                result = store.publish(path)
                QMessageBox.information(self, "Success", f"Published Atom: {result}")
            else:
                raise Exception(f"Unsupported store type: {store_type}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to publish Atom: {e}")

    def show_context_menu(self, position):
        """Enhanced context menu with Atom support"""
        menu = QMenu()
        item = self.store_tree.itemAt(position)
        
        if item:
            # Add standard Nix actions
            self.add_standard_actions(menu, item)
            
            # Add Atom-specific actions
            menu.addSeparator()
            for label, callback in self.atom_actions:
                action = menu.addAction(label)
                action.triggered.connect(
                    lambda checked, cb=callback: self.create_safe_callback(cb)(item)
                )
        
        menu.exec(self.store_tree.viewport().mapToGlobal(position))

    def create_safe_callback(self, callback):
        """Create a callback with error handling"""
        def safe_callback():
            try:
                callback()
            except Exception as e:
                logging.error(f"Error in menu action: {e}")
                QMessageBox.critical(self, "Error", str(e))
        return safe_callback

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
            
        menu = QMenu(self)
        
        # Add basic actions
        menu.addAction("Copy Path", lambda: self.copy_path(item))
        menu.addAction("Show Info", lambda: self.show_item_info(item))
        menu.addAction("Delete", lambda: self.delete_item(item.toolTip(0)))
        
        # Add Atom-specific actions if configured
        if hasattr(self, 'atom_actions'):
            menu.addSeparator()
            for action_name, action_handler in self.atom_actions:
                menu.addAction(action_name, 
                             lambda h=action_handler: h(item.toolTip(0)))
        
        menu.exec(self.store_tree.viewport().mapToGlobal(position))

    def copy_path(self, item):
        """Copy full path to clipboard"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(item.toolTip(0))

    def show_item_info(self, item):
        """Show detailed information about store item"""
        path = item.toolTip(0)
        try:
            result = subprocess.run(
                ['nix-store', '--query', '--references', path],
                capture_output=True,
                text=True
            )
            refs = result.stdout.strip().split('\n')
            
            info = f"Path: {path}\n"
            info += f"Size: {item.text(1)}\n"
            info += f"Modified: {item.text(2)}\n"
            info += f"\nReferences ({len(refs)}):\n"
            info += '\n'.join(refs)
            
            self.show_info_dialog("Store Item Info", info)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get item info: {e}")
        
    def show_atom_deps(self, path):
        """Show Atom dependencies"""
        try:
            result = self.run_nix_command(['nix-store', '--query', '--references', path])
            deps = result.stdout.strip().split('\n')
            
            info = f"Dependencies for {os.path.basename(path)}:\n\n"
            for dep in deps:
                if dep:
                    info += f"• {os.path.basename(dep)}\n"
                    info += f"  {dep}\n"
            
            self.show_info_dialog("Atom Dependencies", info)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get dependencies: {e}")

    def show_atom_reverse_deps(self, path):
        """Show reverse dependencies (what depends on this atom)"""
        try:
            result = subprocess.run(
                ['nix-store', '--query', '--referrers', path],
                capture_output=True,
                text=True
            )
            rev_deps = result.stdout.strip().split('\n')
            
            info = f"Reverse Dependencies for {os.path.basename(path)}:\n\n"
            for dep in rev_deps:
                if dep:
                    info += f"• {os.path.basename(dep)}\n"
                    info += f"  {dep}\n"
            
            self.show_info_dialog("Reverse Dependencies", info)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get reverse dependencies: {e}")

    def show_atom_build_log(self, path):
        """Show build log for an atom"""
        try:
            result = subprocess.run(
                ['nix', 'log', path],
                capture_output=True,
                text=True
            )
            log = result.stdout.strip()
            
            if log:
                self.show_info_dialog(
                    f"Build Log - {os.path.basename(path)}", 
                    log,
                    monospace=True
                )
            else:
                QMessageBox.information(
                    self,
                    "No Build Log",
                    "No build log found for this item"
                )
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get build log: {e}")

    def copy_atom_uri(self, path):
        """Copy Atom URI to clipboard"""
        try:
            # Extract Atom identifier from path
            match = re.search(r'/nix/store/[^-]+-([^/]+)', path)
            if match:
                atom_name = match.group(1)
                uri = f"nix:{atom_name}"
                QApplication.clipboard().setText(uri)
                QMessageBox.information(
                    self,
                    "URI Copied",
                    f"Copied Atom URI: {uri}"
                )
            else:
                raise ValueError("Could not extract Atom name from path")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to copy URI: {e}")
    def generate_lock(self, path):
        """Generate a lock file for an atom"""
        try:
            result = subprocess.run(
                ['nix', 'generate-lock-file', path],
                capture_output=True,
                text=True
            )
            lock_file = result.stdout.strip()
            
            self.show_info_dialog(
                f"Lock File - {os.path.basename(path)}",
                lock_file,
                monospace=True
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate lock file: {e}")

    def show_module_info(self, path):
        """Show detailed information about a Nix module"""
        try:
            result = subprocess.run(
                ['nix', 'show-derivation', path],   
                capture_output=True,
                text=True
            )
            info = result.stdout.strip()
            
            self.show_info_dialog("Module Info", info)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get module info: {e}")

    def run_nix_command(self, cmd, **kwargs):
        """Run a Nix command with proper error handling"""
        if not self.nix_available:
            raise FileNotFoundError("Nix package manager is not installed")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
            if result.returncode != 0:
                raise Exception(f"Command failed: {result.stderr}")
            return result
        except FileNotFoundError:
            raise FileNotFoundError(f"Command not found: {cmd[0]}")
        except Exception as e:
            raise Exception(f"Error running command: {e}")
