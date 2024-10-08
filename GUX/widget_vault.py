from PyQt6.QtWidgets import QWidget, QDockWidget, QMenu,QVBoxLayout, QComboBox, QPushButton, QListWidget, QInputDialog, QMessageBox, QHBoxLayout, QSplitter
from PyQt6.QtCore import Qt
from AuraText.auratext.Core.CodeEditor import CodeEditor
from GUX.markdown_viewer import MarkdownViewer
import os
import hashlib
from GUX.custom_tree_view import CustomTreeView
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
                             QLineEdit, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, QAbstractItemModel, QModelIndex
from PyQt6.QtGui import QStandardItemModel, QStandardItem
import inspect

import requests
from AuraText.auratext.scripts.def_path import resource
from PyQt6.QtCore import pyqtSignal
import logging
from PyQt6.QtGui import QIcon, QFileSystemModel

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
            path = QFileDialog.getExistingDirectory(self, "Select Vault Directory")
            if path:
                self.cccore.vault_manager.add_vault(name, path)
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
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.parent = parent
        self.cccore = cccore
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.model = QFileSystemModel()
        self.model.setRootPath('')

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree1 = self.create_tree_view()
        self.tree2 = self.create_tree_view()

        self.splitter.addWidget(self.create_tree_container(self.tree1, "Tree 1"))
        self.splitter.addWidget(self.create_tree_container(self.tree2, "Tree 2"))

        self.layout.addWidget(self.splitter)

    def create_tree_view(self):
        tree = CustomTreeView(self)
        tree.setModel(self.model)
        tree.setRootIndex(self.model.index(self.model.rootPath()))
        tree.doubleClicked.connect(self.on_double_click)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_context_menu)
        return tree

    def set_root_path(self, path):
        if os.path.exists(path):
            self.model.setRootPath(path)
            self.tree1.setRootIndex(self.model.index(path))
            self.tree2.setRootIndex(self.model.index(path))
            self.update_path_edit(self.tree1, path)
            self.update_path_edit(self.tree2, path)

    def update_path_edit(self, tree, path):
        container = tree.parent()
        if container:
            path_edit = container.findChild(QLineEdit)
            if path_edit:
                path_edit.setText(path)

    # ... (rest of the methods)

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
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Open File")
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
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QTextEdit, QLabel

class MergeWidget(QDialog):
    def __init__(self, file_path, original_content, new_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Changes")
        
        layout = QVBoxLayout(self)
        
        self.path_label = QLabel(f"File: {file_path}")
        self.original_label = QLabel("Original Content:")
        self.original_text = QTextEdit(original_content)
        self.original_text.setReadOnly(True)
        
        self.new_label = QLabel("New Content:")
        self.new_text = QTextEdit(new_content)
        self.new_text.setReadOnly(True)
        
        self.merge_button = QPushButton("Merge")
        self.merge_button.clicked.connect(self.merge_changes)
        
        layout.addWidget(self.path_label)
        layout.addWidget(self.original_label)
        layout.addWidget(self.original_text)
        layout.addWidget(self.new_label)
        layout.addWidget(self.new_text)
        layout.addWidget(self.merge_button)
    
    def merge_changes(self):
        # Implement merge logic here
        merged_content = self.new_text.toPlainText()  # Example: use new content
        self.accept()
        return merged_content
    
# pomodoro_timer_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QToolBar
from PyQt6.QtCore import QTimer, Qt

class PomodoroTimerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.time_left = 25 * 60  # 25 minutes in seconds
        self.is_running = False

    def initUI(self):
        layout = QVBoxLayout(self)

        self.toolbar = QToolBar("Pomodoro Timer")
        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.reset_button = QPushButton("Reset")

        self.start_button.clicked.connect(self.start_timer)
        self.pause_button.clicked.connect(self.pause_timer)
        self.reset_button.clicked.connect(self.reset_timer)

        self.toolbar.addWidget(self.start_button)
        self.toolbar.addWidget(self.pause_button)
        self.toolbar.addWidget(self.reset_button)

        self.time_display = QLabel(self.format_time(self.time_left))
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.time_display)

    def start_timer(self):
        if not self.is_running:
            self.timer.start(1000)  # Update every second
            self.is_running = True

    def pause_timer(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False

    def reset_timer(self):
        self.timer.stop()
        self.time_left = 25 * 60
        self.time_display.setText(self.format_time(self.time_left))
        self.is_running = False

    def update_timer(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.time_display.setText(self.format_time(self.time_left))
        else:
            self.timer.stop()
            self.is_running = False
            # Optionally, add a notification or sound here

    def format_time(self, seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableView, QTreeView, QSplitter, QPushButton, QComboBox, QLineEdit
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from NITTY_GRITTY.object_tree import ObjectTreeModel
class DataTableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._data.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(self._data.index[section])
        return None

class AdvancedDataViewerWidget(QWidget):
    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Data loading controls
        load_controls = QHBoxLayout()
        self.file_combo = QComboBox()
        self.file_combo.addItems(["Sample Data 1", "Sample Data 2", "Load CSV..."])
        load_controls.addWidget(self.file_combo)
        self.load_button = QPushButton("Load Data")
        load_controls.addWidget(self.load_button)
        layout.addLayout(load_controls)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Tree view for data structure
        self.tree_view = QTreeView()
        splitter.addWidget(self.tree_view)

        # Right side: Table view and plotting area
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Table view
        self.table_view = QTableView()
        right_layout.addWidget(self.table_view)

        # Plotting area
        self.figure = plt.figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)

        # Plotting controls
        plot_controls = QHBoxLayout()
        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Scatter", "Line", "Bar", "Histogram"])
        self.plot_button = QPushButton("Plot")
        plot_controls.addWidget(self.x_combo)
        plot_controls.addWidget(self.y_combo)
        plot_controls.addWidget(self.plot_type_combo)
        plot_controls.addWidget(self.plot_button)
        right_layout.addLayout(plot_controls)

        splitter.addWidget(right_widget)
        layout.addWidget(splitter)

        # Connect signals
        self.load_button.clicked.connect(self.load_data)
        self.plot_button.clicked.connect(self.plot_data)

    def load_data(self):
        # For demonstration, we'll create a sample DataFrame
        self.data = pd.DataFrame({
            'A': np.random.rand(100),
            'B': np.random.rand(100),
            'C': np.random.rand(100)
        })
        self.update_views()

    def update_views(self):
        # Update table view
        model = DataTableModel(self.data)
        self.table_view.setModel(model)

        # Update tree view (simplified for demonstration)
        # In a real implementation, you'd create a proper tree model
        from PyQt6.QtGui import QStandardItemModel, QStandardItem
        tree_model = QStandardItemModel()
        root = tree_model.invisibleRootItem()
        for column in self.data.columns:
            item = QStandardItem(column)
            root.appendRow(item)
        self.tree_view.setModel(tree_model)

        # Update plot controls
        self.x_combo.clear()
        self.y_combo.clear()
        self.x_combo.addItems(self.data.columns)
        self.y_combo.addItems(self.data.columns)

    def plot_data(self):
        x = self.x_combo.currentText()
        y = self.y_combo.currentText()
        plot_type = self.plot_type_combo.currentText()

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if plot_type == "Scatter":
            ax.scatter(self.data[x], self.data[y])
        elif plot_type == "Line":
            ax.plot(self.data[x], self.data[y])
        elif plot_type == "Bar":
            ax.bar(self.data[x], self.data[y])
        elif plot_type == "Histogram":
            ax.hist(self.data[x], bins=20)

        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(f"{plot_type} Plot: {y} vs {x}")
        self.canvas.draw()

class StateInspectorWidget(QWidget):
    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Object selection
        select_layout = QHBoxLayout()
        self.object_input = QLineEdit()
        self.inspect_button = QPushButton("Inspect")
        self.lsp_state_button = QPushButton("Inspect LSP State")
        select_layout.addWidget(self.object_input)
        select_layout.addWidget(self.inspect_button)
        select_layout.addWidget(self.lsp_state_button)
        layout.addLayout(select_layout)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tree view for object structure
        self.tree_view = QTreeView()
        splitter.addWidget(self.tree_view)

        # Text area for detailed information
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        splitter.addWidget(self.detail_view)

        layout.addWidget(splitter)

        # Connect signals
        self.inspect_button.clicked.connect(self.inspect_object)
        self.lsp_state_button.clicked.connect(self.inspect_lsp_state)
        self.tree_view.clicked.connect(self.show_details)

    def inspect_object(self):
        object_name = self.object_input.text()
        try:
            obj = eval(object_name, vars(self.cccore))
            model = ObjectTreeModel(obj)
            self.tree_view.setModel(model)
            self.tree_view.expandToDepth(1)
        except Exception as e:
            self.detail_view.setText(f"Error: {str(e)}")

    def inspect_lsp_state(self):
        lsp_manager = self.cccore.lsp_manager
        state_info = {
            "Is LSP Running": lsp_manager.is_running(),
            "Current Language": lsp_manager.current_language,
            "Supported Languages": lsp_manager.supported_languages,
            "Active Clients": {lang: client.state for lang, client in lsp_manager.clients.items()},
            "Last Error": lsp_manager.last_error,
        }
        model = ObjectTreeModel(state_info)
        self.tree_view.setModel(model)
        self.tree_view.expandAll()

    def show_details(self, index):
        item = index.internalPointer()
        obj = item.obj
        details = f"Type: {type(obj)}\n\n"
        
        if hasattr(obj, '__dict__'):
            details += "Attributes:\n"
            for attr, value in obj.__dict__.items():
                if not attr.startswith('_'):
                    details += f"{attr}: {value}\n"
        
        if isinstance(obj, (int, float, str, bool)):
            details += f"Value: {obj}\n"
        
        if callable(obj):
            details += f"Signature: {inspect.signature(obj)}\n"
            if obj.__doc__:
                details += f"Docstring: {obj.__doc__}\n"

        self.detail_view.setText(details)
