from PyQt6.QtWidgets import QTreeView, QMenu, QFileDialog, QHBoxLayout, QMessageBox, QInputDialog, QStyle, QAbstractItemView, QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QApplication
from PyQt6.QtCore import Qt, QMimeData, QTimer, QEvent, QUrl, QIODevice, QDir, QFileInfo
from PyQt6.QtGui import QDrag, QCursor, QAction, QPixmap, QKeySequence
import os
import shutil
import subprocess

class CustomTreeView(QTreeView):
    def __init__(self, parent=None, file_explorer=None):
        super().__init__(parent)
        self.file_explorer = file_explorer
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.timeout.connect(self.auto_scroll)
        self.installEventFilter(self)
        self.ctrl_pressed = False

        # Add toggle view action
        self.toggle_view_action = QAction("Toggle List/Tree View", self)
        self.toggle_view_action.triggered.connect(self.toggle_view)
        self.addAction(self.toggle_view_action)

        # Add sort by last modified action
        self.sort_by_modified_action = QAction("Sort by Last Modified", self)
        self.sort_by_modified_action.triggered.connect(self.sort_by_last_modified)
        self.addAction(self.sort_by_modified_action)

        # Set up the file system model
        self.file_system_model = self.model()

        # Add keyboard shortcuts
        self.toggle_view_action.setShortcut(QKeySequence("Ctrl+T"))
        self.sort_by_modified_action.setShortcut(QKeySequence("Ctrl+M"))

        # If you have a toolbar, you can add these actions to it
        if hasattr(self.file_explorer, 'toolbar'):
            self.file_explorer.toolbar.addAction(self.toggle_view_action)
            self.file_explorer.toolbar.addAction(self.sort_by_modified_action)

    def open_context_menu(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu()

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        menu.addAction(open_action)

        open_with_action = QAction("Open with...", self)
        open_with_action.triggered.connect(self.open_file_with)
        menu.addAction(open_with_action)

        new_file_action = QAction("New File", self)
        new_file_action.triggered.connect(self.create_new_file)
        menu.addAction(new_file_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_file)
        menu.addAction(delete_action)

        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(self.rename_file)
        menu.addAction(rename_action)

        copy_as_path_action = QAction("Copy as Path", self)
        copy_as_path_action.triggered.connect(self.copy_as_path)
        menu.addAction(copy_as_path_action)

        provide_as_context_action = QAction("Provide as Context", self)
        provide_as_context_action.triggered.connect(self.provide_as_context)
        menu.addAction(provide_as_context_action)

        # Add toggle view action to the context menu
        menu.addAction(self.toggle_view_action)

        # Add sort by last modified action to the context menu
        menu.addAction(self.sort_by_modified_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def open_file(self):
        index = self.currentIndex()
        if index.isValid():
            file_path = self.model().filePath(index)
            if os.path.isfile(file_path):
                self.file_explorer.play_audio(file_path)

    def open_file_with(self):
        index = self.currentIndex()
        if index.isValid():
            file_path = self.model().filePath(index)
            if os.path.isfile(file_path):
                program, _ = QFileDialog.getOpenFileName(self, "Open with", "", "Programs (*.exe)")
                if program:
                    subprocess.Popen([program, file_path])

    def create_new_file(self):
        index = self.currentIndex()
        if index.isValid():
            dir_path = self.model().filePath(index)
            if os.path.isdir(dir_path):
                file_name, _ = QFileDialog.getSaveFileName(self, "Create New File", dir_path)
                if file_name:
                    open(file_name, 'w').close()
                    self.model().refresh()

    def delete_file(self):
        index = self.currentIndex()
        if index.isValid():
            file_path = self.model().filePath(index)
            if os.path.exists(file_path):
                reply = QMessageBox.question(self, 'Delete File', f"Are you sure you want to delete {file_path}?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                    self.model().refresh()

    def rename_file(self):
        index = self.currentIndex()
        if index.isValid():
            file_path = self.model().filePath(index)
            dir_path, old_name = os.path.split(file_path)
            new_name, ok = QInputDialog.getText(self, "Rename File", "Enter new name:", text=old_name)
            if ok and new_name:
                new_path = os.path.join(dir_path, new_name)
                os.rename(file_path, new_path)
                self.model().refresh()

    def copy_as_path(self):
        index = self.currentIndex()
        if index.isValid():
            file_path = self.model().filePath(index)
            mime_data = QMimeData()
            mime_data.setText(file_path)
            clipboard = QApplication.clipboard()
            clipboard.setMimeData(mime_data)

    def provide_as_context(self):
        index = self.currentIndex()
        if index.isValid():
            file_path = self.model().filePath(index)
            files_to_include = self.show_file_selection_dialog(file_path)
            if files_to_include:
                context_path = '; '.join(files_to_include)
                # Assuming the AI Chat Widget has a method to receive and handle context
                self.file_explorer.parent.ai_chat_widget.set_context(context_path)

    def show_file_selection_dialog(self, initial_path):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select files to provide as context")
        layout = QVBoxLayout()

        list_widget = QListWidget()
        for root, dirs, files in os.walk(initial_path):
            for file in files:
                item = QListWidgetItem(os.path.join(root, file))
                item.setCheckState(Qt.CheckState.Checked)
                list_widget.addItem(item)

        layout.addWidget(list_widget)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return [list_widget.item(i).text() for i in range(list_widget.count()) if list_widget.item(i).checkState() == Qt.CheckState.Checked]
        return []

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.ctrl_pressed = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.ctrl_pressed = False
        super().keyReleaseEvent(event)

    def startDrag(self, actions):
        index = self.currentIndex()
        if not index.isValid():
            return

        file_path = self.model().filePath(index)
        mime_data = QMimeData()
        mime_data.setText(file_path)

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setHotSpot(self.viewport().mapFromGlobal(QCursor.pos()) - self.visualRect(index).topLeft())
        
        if os.path.isdir(file_path):
            drag.setPixmap(self.style().standardPixmap(QStyle.StandardPixmap.SP_DirOpenIcon))
        else:
            drag.setPixmap(self.style().standardPixmap(QStyle.StandardPixmap.SP_FileIcon))

        drag.exec(Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()
        self.start_auto_scroll(event.position())

        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            event.setDropAction(Qt.DropAction.CopyAction)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            file_path = self.model().filePath(index)
            if os.path.isdir(file_path):
                event.setDropAction(Qt.DropAction.CopyAction)
                self.setCursor(Qt.CursorShape.DragCopyCursor)
            else:
                if self.ctrl_pressed:
                    event.setDropAction(Qt.DropAction.CopyAction)
                    self.setCursor(Qt.CursorShape.DragCopyCursor)
                else:
                    event.setDropAction(Qt.DropAction.MoveAction)
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    
    def dropEvent(self, event):
        self.stop_auto_scroll()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        mime_data = event.mimeData()
        source_path = mime_data.text()
        index = self.indexAt(event.position().toPoint())

        if not index.isValid():
            target_path = self.model().rootPath()
        else:
            target_path = self.model().filePath(index)
            if not os.path.isdir(target_path):
                target_path = os.path.dirname(target_path)

        if os.path.exists(source_path):
            if os.path.isdir(source_path):
                target_path = os.path.join(target_path, os.path.basename(source_path))
                shutil.copytree(source_path, target_path)
            else:
                shutil.copy(source_path, target_path)
            event.acceptProposedAction()
            self.model().refresh()

            # Handle opening the file or pasting the path
            if not self.ctrl_pressed:
                # Open the file
                self.open_file_with_editor(source_path)
            else:
                # Paste the path as text
                self.paste_path_as_text(source_path)

    def open_file_with_editor(self, file_path):
        if hasattr(self.file_explorer.parent, 'code_editor_widget'):
            self.file_explorer.parent.code_editor_widget.open_file(file_path)

    def paste_path_as_text(self, file_path):
        if hasattr(self.file_explorer.parent, 'code_editor_widget'):
            self.file_explorer.parent.code_editor_widget.paste_text(file_path)
        def start_auto_scroll(self, pos):
            if pos.y() < 30 or pos.y() > self.viewport().height() - 30:
                self.auto_scroll_timer.start(50)
            else:
                self.auto_scroll_timer.stop()

    def stop_auto_scroll(self):
        self.auto_scroll_timer.stop()

    def auto_scroll(self):
        cursor_pos = self.viewport().mapFromGlobal(QCursor.pos())
        if cursor_pos.y() < 30:
            new_value = self.verticalScrollBar().value() - 10
            self.verticalScrollBar().setValue(new_value)
        elif cursor_pos.y() > self.viewport().height() - 30:
            new_value = self.verticalScrollBar().value() + 10
            self.verticalScrollBar().setValue(new_value)

    def toggle_view(self):
        if self.isTreePosition():
            self.setRootIndex(self.file_system_model.index(self.file_system_model.rootPath()))
        else:
            self.setRootIndex(self.file_system_model.index(""))

    def sort_by_last_modified(self):
        self.file_system_model.sort(3, Qt.SortOrder.DescendingOrder)  # 3 is the column index for "Date Modified"
