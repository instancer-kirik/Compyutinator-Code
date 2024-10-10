from PyQt6.QtWidgets import (QTreeView, QWidget, QVBoxLayout, QLabel, QScrollArea, 
                             QPushButton, QHBoxLayout, QLineEdit, QHeaderView)
from PyQt6.QtCore import Qt, QTimer, QModelIndex, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QFileSystemModel, QDragMoveEvent, QDropEvent
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import QEvent
import os

class PathBreadcrumb(QWidget):
    path_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)

        self.path_edit = QLineEdit()
        self.path_edit.returnPressed.connect(self.on_path_edit)
        self.layout.addWidget(self.path_edit)

    def set_path(self, path):
        self.path_edit.setText(path)

    def on_path_edit(self):
        new_path = self.path_edit.text()
        if os.path.exists(new_path):
            self.path_changed.emit(new_path)
        else:
            self.path_edit.setText(self.current_path)

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeView, QHeaderView, QMenu, QInputDialog, QMessageBox, QFileDialog
from PyQt6.QtCore import  QTimer, QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QAction,QFileSystemModel
import os
import subprocess


class FileTreeView(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, file_system_model=None, theme_manager=None, parent=None):
        super().__init__(parent)
        self.model = file_system_model or QFileSystemModel()
        self.model.setRootPath("")
        self.theme_manager = theme_manager
        self.setup_ui()
        self.setup_model(self.model)
        self.is_scrolling = False

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Path breadcrumb
        self.breadcrumb = PathBreadcrumb()
        self.breadcrumb.path_changed.connect(self.on_path_changed)
        layout.addWidget(self.breadcrumb)

        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(self.model.index(""))
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setExpandsOnDoubleClick(False)
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enable drag and drop
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDropIndicatorShown(True)
        self.tree_view.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        
        # Adjust column sizes
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name column
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Date Modified column
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Size column
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Type column

        # Set a larger initial size for the Name column
        header.resizeSection(0, 300)  # Adjust this value as needed
        
        # Make columns resizable by user
        header.setSectionsMovable(True)
        header.setStretchLastSection(False)
        
        # Add tree view to layout
        layout.addWidget(self.tree_view)

        # Auto-scroll timers
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.auto_scroll)
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.start_auto_scroll)

        # Install event filter for mouse tracking
        self.tree_view.setMouseTracking(True)
        self.tree_view.viewport().installEventFilter(self)

    def setup_model(self,model):
        self.tree_view.setModel(model)
        self.tree_view.setRootIndex(model.index(""))

    def on_path_changed(self, new_path):
        index = self.model.index(new_path)
        self.tree_view.setRootIndex(index)
        self.breadcrumb.set_path(new_path)

    def on_item_clicked(self, index):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            self.file_selected.emit(path)
        self.breadcrumb.set_path(path)

    def get_item_path(self, index):
        return self.model.filePath(index)

    def eventFilter(self, obj, event):
        if obj == self.tree_view.viewport():
            if event.type() == QEvent.Type.MouseMove:
                self.handle_mouse_move(event)
            elif event.type() == QEvent.Type.Leave:
                self.stop_auto_scroll()
                self.hover_timer.stop()
        return super().eventFilter(obj, event)

    def handle_mouse_move(self, event):
        viewport_height = self.tree_view.viewport().height()
        y = event.pos().y()
        
        if y < 50 or y > viewport_height - 50:
            if not self.is_scrolling:
                self.hover_timer.start(500)  # 0.5 second delay
        else:
            self.stop_auto_scroll()
            self.hover_timer.stop()

    def start_auto_scroll(self):
        self.is_scrolling = True
        self.scroll_timer.start(50)  # Adjust for smoother or faster scrolling

    def stop_auto_scroll(self):
        self.is_scrolling = False
        self.scroll_timer.stop()

    def auto_scroll(self):
        viewport = self.tree_view.viewport()
        pos = viewport.mapFromGlobal(QCursor.pos())
        y = pos.y()
        viewport_height = viewport.height()
        
        if y < 50:
            self.tree_view.verticalScrollBar().setValue(
                self.tree_view.verticalScrollBar().value() - 5)
        elif y > viewport_height - 50:
            self.tree_view.verticalScrollBar().setValue(
                self.tree_view.verticalScrollBar().value() + 5)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self.navigate_up()
        elif event.key() == Qt.Key.Key_Down:
            self.navigate_down()
        elif event.key() == Qt.Key.Key_Left:
            self.navigate_left()
        elif event.key() == Qt.Key.Key_Right:
            self.navigate_right()
        elif event.key() == Qt.Key.Key_Return:
            self.activate_current_item()
        else:
            super().keyPressEvent(event)

    def navigate_up(self):
        current = self.tree_view.currentIndex()
        if current.isValid():
            next_index = self.tree_view.indexAbove(current)
            if next_index.isValid():
                self.tree_view.setCurrentIndex(next_index)

    def navigate_down(self):
        current = self.tree_view.currentIndex()
        if current.isValid():
            next_index = self.tree_view.indexBelow(current)
            if next_index.isValid():
                self.tree_view.setCurrentIndex(next_index)

    def navigate_left(self):
        current = self.tree_view.currentIndex()
        if current.isValid():
            if self.tree_view.isExpanded(current):
                self.tree_view.collapse(current)
            else:
                parent = current.parent()
                if parent.isValid():
                    self.tree_view.setCurrentIndex(parent)

    def navigate_right(self):
        current = self.tree_view.currentIndex()
        if current.isValid():
            if not self.tree_view.isExpanded(current):
                self.tree_view.expand(current)
            else:
                child = self.tree_view.model().index(0, 0, current)
                if child.isValid():
                    self.tree_view.setCurrentIndex(child)

    def activate_current_item(self):
        current = self.tree_view.currentIndex()
        if current.isValid():
            self.on_item_clicked(current)

    def set_root_path(self, path):
        if os.path.exists(path):
            index = self.model.index(path)
            self.tree_view.setRootIndex(index)
            self.breadcrumb.set_path(path)

    def get_selected_files(self):
        selected_indexes = self.tree_view.selectedIndexes()
        selected_files = []
        for index in selected_indexes:
            if index.column() == 0:  # Assuming the file path is in the first column
                file_path = self.model.filePath(index)
                if os.path.isfile(file_path):
                    selected_files.append(file_path)
        return selected_files

    def set_root_index(self, index):
        self.tree_view.setRootIndex(index)

    def show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        self.apply_theme_to_menu(menu)
        file_path = self.model.filePath(index)
        is_file = os.path.isfile(file_path)

        # File/Folder Operations
        add_file_action = self.create_action("Add File", "file-add", lambda: self.add_file(file_path))
        add_folder_action = self.create_action("Add Folder", "folder-add", lambda: self.add_folder(file_path))
        rename_action = self.create_action("Rename", "edit", lambda: self.rename_item(index))
        delete_action = self.create_action("Delete", "delete", lambda: self.delete_item(index))

        menu.addAction(add_file_action)
        menu.addAction(add_folder_action)
        menu.addSeparator()
        menu.addAction(rename_action)
        menu.addAction(delete_action)

        # File-specific actions
        if is_file:
            menu.addSeparator()
            open_with_action = self.create_action("Open With...", "open-with", lambda: self.open_with(file_path))
            menu.addAction(open_with_action)

        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def create_action(self, text, icon_name, callback):
        action = QAction(text, self)
        action.triggered.connect(callback)
        if self.theme_manager:
            icon = self.theme_manager.get_icon(icon_name)
            if icon:
                action.setIcon(icon)
        return action
 
    def apply_theme_to_menu(self, menu):
        if self.theme_manager:
            theme_data = self.theme_manager.get_current_theme()
            if isinstance(theme_data, dict) and 'colors' in theme_data:
                sidebar_bg = theme_data['colors'].get('sidebarBackground', '#F0F0F0')
                sidebar_text = theme_data['colors'].get('sidebarText', '#000000')
                sidebar_highlight = theme_data['colors'].get('sidebarHighlight', '#E0E0E0')
                stylesheet = f"""
                    QTreeView {{
                        background-color: {sidebar_bg};
                        color: {sidebar_text};
                        border: none;
                    }}
                    QTreeView::item:selected {{
                        background-color: {sidebar_highlight};
                    }}
                """
                menu.setStyleSheet(stylesheet)

    def add_file(self, parent_path):
        file_name, ok = QInputDialog.getText(self, "Add File", "Enter file name:")
        if ok and file_name:
            new_file_path = os.path.join(parent_path, file_name)
            try:
                with open(new_file_path, 'w') as f:
                    pass  # Create an empty file
                self.model.layoutChanged.emit()
            except IOError as e:
                QMessageBox.critical(self, "Error", f"Could not create file: {str(e)}")

    def add_folder(self, parent_path):
        folder_name, ok = QInputDialog.getText(self, "Add Folder", "Enter folder name:")
        if ok and folder_name:
            new_folder_path = os.path.join(parent_path, folder_name)
            try:
                os.mkdir(new_folder_path)
                self.model.layoutChanged.emit()
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Could not create folder: {str(e)}")

    def rename_item(self, index):
        old_name = self.model.fileName(index)
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=old_name)
        if ok and new_name:
            old_path = self.model.filePath(index)
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
                self.model.layoutChanged.emit()
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Could not rename: {str(e)}")

    def delete_item(self, index):
        file_path = self.model.filePath(index)
        reply = QMessageBox.question(self, "Delete", f"Are you sure you want to delete {file_path}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                else:
                    os.rmdir(file_path)
                self.model.layoutChanged.emit()
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Could not delete: {str(e)}")

    def open_with(self, file_path):
        program, ok = QFileDialog.getOpenFileName(self, "Select Program")
        if ok and program:
            try:
                subprocess.Popen([program, file_path])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.exists(file_path):
                    # Handle the dropped file/folder
                    target_path = self.model.filePath(self.tree_view.indexAt(event.pos()))
                    if os.path.isdir(target_path):
                        # Move or copy the file/folder to the target directory
                        new_path = os.path.join(target_path, os.path.basename(file_path))
                        if os.path.exists(new_path):
                            # Handle name conflict
                            pass
                        else:
                            # Perform the move/copy operation
                            # You may want to ask the user whether to move or copy
                            os.rename(file_path, new_path)
