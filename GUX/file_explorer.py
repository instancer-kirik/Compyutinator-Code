from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLineEdit, QLabel, QToolBar
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt
import os
from GUX.custom_tree_view import CustomTreeView
class FileExplorerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.model = QFileSystemModel()
        self.model.setRootPath('')

        # Splitter for split-screen functionality
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # First tree view and navigation bar
        self.tree1_layout = QVBoxLayout()
        self.tree1_nav_bar = QToolBar()
        self.tree1_path_label = QLabel("Path:")
        self.tree1_path_edit = QLineEdit()
        self.tree1_path_edit.returnPressed.connect(self.navigate_to_path_tree1)
        self.tree1_nav_bar.addWidget(self.tree1_path_label)
        self.tree1_nav_bar.addWidget(self.tree1_path_edit)
        self.tree1_layout.addWidget(self.tree1_nav_bar)

        self.tree1 = CustomTreeView(self)
        self.tree1.setModel(self.model)
        self.tree1.setRootIndex(self.model.index(''))
        self.tree1.doubleClicked.connect(self.on_double_click)
        self.tree1_layout.addWidget(self.tree1)

        self.tree1_container = QWidget()
        self.tree1_container.setLayout(self.tree1_layout)
        self.splitter.addWidget(self.tree1_container)

        # Second tree view and navigation bar
        self.tree2_layout = QVBoxLayout()
        self.tree2_nav_bar = QToolBar()
        self.tree2_path_label = QLabel("Path:")
        self.tree2_path_edit = QLineEdit()
        self.tree2_path_edit.returnPressed.connect(self.navigate_to_path_tree2)
        self.tree2_nav_bar.addWidget(self.tree2_path_label)
        self.tree2_nav_bar.addWidget(self.tree2_path_edit)
        self.tree2_layout.addWidget(self.tree2_nav_bar)

        self.tree2 = CustomTreeView(self)
        self.tree2.setModel(self.model)
        self.tree2.setRootIndex(self.model.index(''))
        self.tree2.doubleClicked.connect(self.on_double_click)
        self.tree2_layout.addWidget(self.tree2)

        self.tree2_container = QWidget()
        self.tree2_container.setLayout(self.tree2_layout)
        self.splitter.addWidget(self.tree2_container)

        self.layout.addWidget(self.splitter)

    def navigate_to_path_tree1(self):
        path = self.tree1_path_edit.text()
        if os.path.exists(path):
            index = self.model.index(path)
            if index.isValid():
                self.tree1.setRootIndex(index)
                self.parent.update_history(path)

    def navigate_to_path_tree2(self):
        path = self.tree2_path_edit.text()
        if os.path.exists(path):
            index = self.model.index(path)
            if index.isValid():
                self.tree2.setRootIndex(index)
                self.parent.update_history(path)

    def on_double_click(self, index):
        file_path = self.model.filePath(index)
        self.parent.update_history(file_path)
