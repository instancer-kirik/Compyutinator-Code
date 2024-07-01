from PyQt6.QtWidgets import QTreeView, QMenu, QFileDialog, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
import os
import shutil
import subprocess

class CustomTreeView(QTreeView):
    def __init__(self, parent=None, file_explorer=None):
        super().__init__(parent)
        self.file_explorer = file_explorer
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.cut_file_path = None

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

        cut_action = QAction("Cut", self)
        cut_action.triggered.connect(self.cut_file)
        menu.addAction(cut_action)

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_file)
        menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self.paste_file)
        menu.addAction(paste_action)

        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(self.selectAll)
        menu.addAction(select_all_action)

        menu.exec_(self.viewport().mapToGlobal(position))

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
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
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

    def cut_file(self):
        index = self.currentIndex()
        if index.isValid():
            self.cut_file_path = self.model().filePath(index)

    def copy_file(self):
        index = self.currentIndex()
        if index.isValid():
            file_path = self.model().filePath(index)
            mime_data = QMimeData()
            urls = [QUrl.fromLocalFile(file_path)]
            mime_data.setUrls(urls)
            clipboard = QApplication.clipboard()
            clipboard.setMimeData(mime_data)

    def paste_file(self):
        index = self.currentIndex()
        if index.isValid():
            target_dir = self.model().filePath(index)
            if os.path.isdir(target_dir):
                if self.cut_file_path:
                    shutil.move(self.cut_file_path, os.path.join(target_dir, os.path.basename(self.cut_file_path)))
                    self.cut_file_path = None
                else:
                    clipboard = QApplication.clipboard()
                    mime_data = clipboard.mimeData()
                    if mime_data.hasUrls():
                        for url in mime_data.urls():
                            src_path = url.toLocalFile()
                            shutil.copy(src_path, target_dir)
                self.model().refresh()

    def keyPressEvent(self, event):
        current_index = self.currentIndex()
        if event.key() == Qt.Key_Up:
            next_index = self.indexAbove(current_index)
        elif event.key() == Qt.Key_Down:
            next_index = self.indexBelow(current_index)
        elif event.key() == Qt.Key_PageUp:
            next_index = self.moveCursor(QAbstractItemView.MovePageUp, Qt.NoModifier)
        elif event.key() == Qt.Key_PageDown:
            next_index = self.moveCursor(QAbstractItemView.MovePageDown, Qt.NoModifier)
        elif event.key() == Qt.Key_Home:
            next_index = self.moveCursor(QAbstractItemView.MoveHome, Qt.NoModifier)
        elif event.key() == Qt.Key_End:
            next_index = self.moveCursor(QAbstractItemView.MoveEnd, Qt.NoModifier)
        else:
            super().keyPressEvent(event)
            return

        if next_index.isValid():
            self.setCurrentIndex(next_index)
            self.file_explorer.current_index = next_index
            self.file_explorer.play_current_audio()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            target_dir = self.model().filePath(self.indexAt(event.pos()))
            if os.path.isdir(target_dir):
                for url in event.mimeData().urls():
                    src_path = url.toLocalFile()
                    shutil.copy(src_path, target_dir)
                self.model().refresh()
            event.acceptProposedAction()
