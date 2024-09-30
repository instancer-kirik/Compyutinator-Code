from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

class CursorManager:
    def __init__(self, cccore):
        self.cccore = cccore
        # Create a transparent cursor
        transparent_pixmap = QPixmap(1, 1)
        transparent_pixmap.fill(Qt.GlobalColor.transparent)
        self.transparent_cursor = QCursor(transparent_pixmap)

        # Store the default cursor
        self.default_cursor = QCursor()

    def set_transparent_cursor(self):
        QApplication.setOverrideCursor(self.transparent_cursor)

    def restore_default_cursor(self):
        QApplication.restoreOverrideCursor()

    def get_current_cursor_pos(self):
        return QCursor.pos()