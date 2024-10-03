from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QApplication

class CursorManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.transparent_cursor = QCursor(QPixmap(1, 1))
        self.transparent_cursor.pixmap().fill(Qt.GlobalColor.transparent)
        self.default_cursor = QCursor()

    def set_transparent_cursor(self):
        QApplication.setOverrideCursor(self.transparent_cursor)

    def restore_default_cursor(self):
        QApplication.restoreOverrideCursor()

    def get_current_cursor_pos(self):
        return QCursor.pos()

    def set_cursor_pos(self, pos: QPoint):
        QCursor.setPos(pos)

    def move_cursor_relative(self, dx: int, dy: int):
        current_pos = self.get_current_cursor_pos()
        new_pos = current_pos + QPoint(dx, dy)
        self.set_cursor_pos(new_pos)