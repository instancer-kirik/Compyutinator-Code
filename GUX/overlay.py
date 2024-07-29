import sys
import threading
from ctypes import windll, c_void_p
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QEvent, QPointF
from PyQt6.QtGui import QPainter, QCursor, QRadialGradient, QBrush, QColor, QGuiApplication, QImage, QColorSpace
import serial
import serial.tools.list_ports

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        screen_geometry = QGuiApplication.primaryScreen().geometry()
        self.resize(screen_geometry.width(), screen_geometry.height())

        # Make the window truly click-through on Windows
        hwnd = self.winId().__int__()
        windll.user32.SetWindowLongPtrW(c_void_p(hwnd), -20, 
            windll.user32.GetWindowLongPtrW(c_void_p(hwnd), -20) | 0x80000 | 0x20)

    def event(self, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick, QEvent.Type.MouseMove):
            return False
        return super().event(event)
class Flashlight(Overlay):
    def __init__(self, size=200, power=0.5):
        super().__init__()
        self.size = size
        self.power = power

        self.cursor_effect_timer = QTimer(self)
        self.cursor_effect_timer.timeout.connect(self.update_cursor_effect)
        self.cursor_effect_timer.start(30)
        self.cursor_pos = QCursor.pos()

    def set_power(self, power):
        self.power = power

    def set_size(self, size):
        self.size = size

    def update_cursor_effect(self):
        self.cursor_pos = QCursor.pos()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Increase contrast around the cursor
        center = QPointF(self.cursor_pos.x() - self.x(), self.cursor_pos.y() - self.y())
        gradient = QRadialGradient(center, self.size)
        gradient.setColorAt(0, QColor(255, 255, 255, int(255 * self.power)))
        gradient.setColorAt(0.4, QColor(255, 255, 255, int(255 * self.power * 0.7)))
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        brush = QBrush(gradient)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, self.size, self.size)

class CharachorderOverlay(Overlay):
    def __init__(self, serial_port=None, baud_rate=115200):
        super().__init__()
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.initUI()
        if serial_port:
            self.serial_thread = threading.Thread(target=self.read_serial_data)
            self.serial_thread.daemon = True
            self.serial_thread.start()

    def initUI(self):
        self.label = QLabel(self)
        self.label.setStyleSheet("QLabel { color : white; font-size: 20px; }")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def read_serial_data(self):
        with serial.Serial(self.serial_port, self.baud_rate, timeout=1) as ser:
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    self.update_overlay(line)

    def update_overlay(self, data):
        keys_pressed = data.split(',')
        self.label.setText(f"Keys Pressed: {', '.join(keys_pressed)}")

    def set_serial_port(self, port):
        self.serial_port = port
        if self.serial_port:
            self.serial_thread = threading.Thread(target=self.read_serial_data)
            self.serial_thread.daemon = True
            self.serial_thread.start()

class CompositeOverlay(Overlay):
    def __init__(self, flashlight_size=200, flashlight_power=0.5, serial_port=None, baud_rate=115200):
        super().__init__()
        self.flashlight_overlay = Flashlight(size=flashlight_size, power=flashlight_power)
        self.flashlight_overlay.setParent(self)
        
        self.charachorder_overlay = CharachorderOverlay(serial_port, baud_rate)
        self.charachorder_overlay.setParent(self)

        self.cursor_effect_timer = QTimer(self)
        self.cursor_effect_timer.timeout.connect(self.update_cursor_effect)
        self.cursor_effect_timer.start(30)
        self.cursor_pos = QCursor.pos()

        self.label = QLabel(self)
        self.label.setText("Charachorder Display Active")
        self.label.setStyleSheet("QLabel { color : white; font-size: 20px; }")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_cursor_effect(self):
        self.cursor_pos = QCursor.pos()
        self.flashlight_overlay.cursor_pos = self.cursor_pos
        self.flashlight_overlay.update()
        self.charachorder_overlay.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
        self.flashlight_overlay.render(painter)
        self.charachorder_overlay.render(painter)

    def set_serial_port(self, port):
        self.charachorder_overlay.set_serial_port(port)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    composite_overlay = CompositeOverlay(flashlight_size=200, flashlight_power=0.6, serial_port="COM3")
    composite_overlay.show()
    sys.exit(app.exec())
