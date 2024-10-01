from PyQt6.QtWidgets import (QTreeView, QWidget, QVBoxLayout, QLabel, QScrollArea, 
                             QPushButton, QHBoxLayout, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QModelIndex, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QFileSystemModel
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

class FileTreeView(QTreeView):
    file_selected = pyqtSignal(str)

    def __init__(self, file_system_model, parent=None):
        super().__init__(parent)
        self.model = file_system_model
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
        self.tree_view.setHeaderHidden(False)  # Show the header for file attributes
        self.tree_view.setExpandsOnDoubleClick(False)
        self.tree_view.clicked.connect(self.on_item_clicked)
        
        # Scroll area for tree view
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.tree_view)
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

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
