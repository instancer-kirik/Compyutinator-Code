from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
import math

class RadialMenu(QWidget):
    optionSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.options = []
        self.hover_index = -1
        self.radius = 100
        self.setMouseTracking(True)

    def set_options(self, options):
        self.options = options
        self.update()

    def show_at(self, pos):
        self.move(pos - QPoint(self.radius, self.radius))
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPoint(self.radius, self.radius)
        painter.translate(center)

        for i, option in enumerate(self.options):
            angle = 2 * math.pi * i / len(self.options)
            x = self.radius * 0.7 * math.cos(angle)
            y = self.radius * 0.7 * math.sin(angle)

            if i == self.hover_index:
                painter.setBrush(QColor(200, 200, 255))
            else:
                painter.setBrush(QColor(240, 240, 240))

            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawEllipse(QPoint(x, y), 30, 30)

            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRect(x-25, y-25, 50, 50), Qt.AlignmentFlag.AlignCenter, option)

    def mouseMoveEvent(self, event):
        center = QPoint(self.radius, self.radius)
        pos = event.position().toPoint() - center
        angle = math.atan2(pos.y(), pos.x())
        if angle < 0:
            angle += 2 * math.pi

        self.hover_index = int(angle / (2 * math.pi / len(self.options)))
        self.update()

    def mouseReleaseEvent(self, event):
        if 0 <= self.hover_index < len(self.options):
            self.optionSelected.emit(self.options[self.hover_index])
        self.close()