import sys
import serial
import threading
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel

from PyQt6.QtCore import Qt, QTimer, QPoint, QEvent, QPointF
import serial.tools.list_ports


from PyQt6.QtGui import QPainter, QCursor, QRadialGradient, QBrush, QColor


class BrightnessFlashlight:
    def __init__(self, size=100, power=0.5):
        self.size = size
        self.power = power

    def set_power(self, power):
        self.power = power

    def draw(self, painter, center):
        centerF = QPointF(center)
        gradient = QRadialGradient(centerF, self.size)
        gradient.setColorAt(0, QColor(255, 255, 255, int(255 * self.power)))
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        brush = QBrush(gradient)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(centerF, self.size, self.size)

class CursorOverlay(QWidget):
    def __init__(self, flashlight):
        super().__init__()
        self.flashlight = flashlight
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.resize(QApplication.primaryScreen().size())
        self.cursor_pos = QCursor.pos()
        
        timer = QTimer(self)
        timer.timeout.connect(self.update_cursor_effect)
        timer.start(16)
    
    def update_cursor_effect(self):
        self.cursor_pos = QCursor.pos()
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = QPointF(self.cursor_pos)
        self.flashlight.draw(painter, center)

        painter.end()

    def event(self, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick, QEvent.Type.MouseMove):
            return False
        return super().event(event)

class CharachorderOverlay(QWidget):
    def __init__(self, flashlight, serial_port=None, baud_rate=115200, parent=None):
        super().__init__(parent)
        self.flashlight = flashlight
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.initUI()
        if serial_port:
            self.serial_thread = threading.Thread(target=self.read_serial_data)
            self.serial_thread.daemon = True
            self.serial_thread.start()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.resize(QApplication.primaryScreen().size())

    def read_serial_data(self):
        with serial.Serial(self.serial_port, self.baud_rate, timeout=1) as ser:
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    self.update_overlay(line)

    def update_overlay(self, data):
        keys_pressed = data.split(',')
        self.label.setText(f"Keys Pressed: {', '.join(keys_pressed)}")

    def paintEvent(self, event):
        painter = QPainter(self)
        self.flashlight.draw(painter, QCursor.pos())
        painter.end()

    def set_serial_port(self, port):
        self.serial_port = port
        if self.serial_port:
            self.serial_thread = threading.Thread(target=self.read_serial_data)
            self.serial_thread.daemon = True
            self.serial_thread.start()
