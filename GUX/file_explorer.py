from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLineEdit, QLabel, QToolBar, QPushButton, QFileDialog, QMenu, QStackedWidget
from PyQt6.QtGui import QFileSystemModel, QAction
from PyQt6.QtCore import Qt, pyqtSignal
import os
import logging
from PyQt6.QtWidgets import QPushButton, QFileDialog, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal
from GUX.custom_tree_view import CustomTreeView

class FileExplorerWidget(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.parent = parent
        self.cccore = cccore
        self.model = QFileSystemModel()
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        
        # Add a button to cycle views
        self.cycle_view_button = QPushButton("Cycle View")
        self.cycle_view_button.clicked.connect(self.cycle_view)
        self.layout.addWidget(self.cycle_view_button)

        self.model.setRootPath('')
        self.tree1 = CustomTreeView(self)
        self.tree2 = CustomTreeView(self)
        
        self.stack = QStackedWidget()
        self.stack.addWidget(self.tree1)
        self.stack.addWidget(self.tree2)
        
        self.layout.addWidget(self.stack)

        self.setup_trees()

    def setup_trees(self):
        for tree in (self.tree1, self.tree2):
            tree.setModel(self.model)
            tree.setRootIndex(self.model.index(''))
            tree.setAnimated(False)
            tree.setIndentation(20)
            tree.setSortingEnabled(True)
            tree.setColumnWidth(0, 250)
            tree.doubleClicked.connect(self.on_double_click)

    def cycle_view(self):
        current_index = self.stack.currentIndex()
        next_index = (current_index + 1) % self.stack.count()
        self.stack.setCurrentIndex(next_index)

    def create_tree_view(self, model):
        tree = CustomTreeView(self)
        tree.setModel(model)
        tree.setRootIndex(model.index(''))
        tree.doubleClicked.connect(self.on_double_click)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_context_menu)
        return tree

    def create_tree_container(self, tree, name):
        container = QWidget()
        layout = QVBoxLayout(container)

        nav_bar = QToolBar()
        path_label = QLabel("Path:")
        path_edit = QLineEdit()
        path_edit.returnPressed.connect(lambda: self.navigate_to_path(tree, path_edit))
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda: self.browse_directory(tree, path_edit))

        nav_bar.addWidget(path_label)
        nav_bar.addWidget(path_edit)
        nav_bar.addWidget(browse_button)

        layout.addWidget(nav_bar)
        layout.addWidget(tree)

        return container

    def navigate_to_path(self, tree, path_edit):
        path = path_edit.text()
        if os.path.exists(path):
            index = self.model.index(path)
            if index.isValid():
                tree.setRootIndex(index)
                self.update_history(path)

    def browse_directory(self, tree, path_edit):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            path_edit.setText(directory)
            self.navigate_to_path(tree, path_edit)

    def on_double_click(self, index):
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path):
            self.file_selected.emit(file_path)
        self.update_history(file_path)

    def update_history(self, path):
        # Implement history tracking if needed
        pass

    def show_context_menu(self, position):
        tree = self.sender()
        index = tree.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        open_action = QAction("Open", self)
        open_action.triggered.connect(lambda: self.open_item(index))
        menu.addAction(open_action)
        view_menu = menu.addMenu("View Mode")
        view_menu.addAction(self.list_view_action)
        view_menu.addAction(self.tree_view_action)
        view_menu.addAction(self.column_view_action)
        if os.path.isdir(self.model.filePath(index)):
            set_as_root_action = QAction("Set as Root", self)
            set_as_root_action.triggered.connect(lambda: self.set_as_root(tree, index))
            menu.addAction(set_as_root_action)

        menu.exec(tree.viewport().mapToGlobal(position))

    def open_item(self, index):
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path):
            self.file_selected.emit(file_path)
        elif os.path.isdir(file_path):
            self.sender().setRootIndex(index)

    def set_as_root(self, tree, index):
        tree.setRootIndex(index)
        path = self.model.filePath(index)
        tree.parent().findChild(QLineEdit).setText(path)

    def get_selected_path(self, tree):
        indexes = tree.selectedIndexes()
        if indexes:
            return self.model.filePath(indexes[0])
        return None
    def set_root_path(self, path):
        if os.path.exists(path):
            logging.warning(f"Setting file explorer root path to: {path}")
            self.model.setRootPath(path)
            root_index = self.model.index(path)
            if root_index.isValid():
                self.tree1.setRootIndex(root_index)
                self.tree2.setRootIndex(root_index)
                self.update_path_edit(self.tree1, path)
                self.update_path_edit(self.tree2, path)
            else:
                logging.error(f"Invalid root index for path: {path}")
        else:
            logging.error(f"Path does not exist: {path}")