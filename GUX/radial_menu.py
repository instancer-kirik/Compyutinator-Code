from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QSize, QPointF
import math

class RadialMenu(QWidget):
    optionSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.options = []
        self.hotkeys = {}
        self.hover_index = -1
        self.radius = 120
        self.inner_radius = 40
        self.option_radius = 35
        self.setMouseTracking(True)
        self.right_button_pressed = False
        self.background_color = QColor(240, 240, 240, 200)
        self.hover_color = QColor(200, 200, 255)
        self.text_color = QColor(0, 0, 0)
        self.hotkey_color = QColor(100, 100, 100)
        self.font = QFont("Arial", 10)
        self.hotkey_font = QFont("Arial", 8)

    def set_options_with_hotkeys(self, options_dict):
        self.options = list(options_dict.keys())
        self.hotkeys = options_dict
        self.update()

    def show_at(self, pos):
        size = QSize(self.radius * 2, self.radius * 2)
        self.setFixedSize(size)
        self.move(pos - QPoint(self.radius, self.radius))
        self.show()
        self.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2

        painter.setBrush(self.background_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), self.radius, self.radius)

        for i, option in enumerate(self.options):
            angle = 2 * math.pi * i / len(self.options)
            x = center_x + self.radius * 0.7 * math.cos(angle)
            y = center_y + self.radius * 0.7 * math.sin(angle)

            circle_rect = QRect(
                int(x - self.option_radius),
                int(y - self.option_radius),
                self.option_radius * 2,
                self.option_radius * 2
            )

            if i == self.hover_index:
                painter.setBrush(self.hover_color)
            else:
                painter.setBrush(self.background_color)

            painter.setPen(QPen(self.text_color))
            painter.drawEllipse(circle_rect)

            painter.setFont(self.font)
            painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, option)

            if option in self.hotkeys:
                hotkey_rect = QRect(
                    circle_rect.left(),
                    circle_rect.bottom() + 5,
                    circle_rect.width(),
                    20
                )
                painter.setFont(self.hotkey_font)
                painter.setPen(QPen(self.hotkey_color))
                painter.drawText(hotkey_rect, Qt.AlignmentFlag.AlignCenter, 
                               f"[{self.hotkeys[option]}]")

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = True
        self.update_hover_index(event.pos())

    def mouseMoveEvent(self, event):
        self.update_hover_index(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self.right_button_pressed:
           # if 0 <= self.hover_index < len(self.options):
            #     self.optionSelected.emit(self.options[self.hover_index])
            # self.right_button_pressed = False
            # self.close()
            pass
    def update_hover_index(self, pos):
        center = QPoint(self.radius, self.radius)
        pos = pos - center
        angle = math.atan2(pos.y(), pos.x())
        if angle < 0:
            angle += 2 * math.pi
        new_hover_index = int(angle / (2 * math.pi / len(self.options)))
        if new_hover_index != self.hover_index:
            self.hover_index = new_hover_index
            self.update()

    def leaveEvent(self, event):
        self.hover_index = -1
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif Qt.Key.Key_1 <= event.key()() <= Qt.Key.Key_9:  # Add parentheses
            index = event.key()() - Qt.Key.Key_1  # Add parentheses
            if index < len(self.options):
                self.optionSelected.emit(self.options[index])
                self.close()