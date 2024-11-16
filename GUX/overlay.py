import sys
import threading
from ctypes import c_void_p
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QEvent, QPointF
from PyQt6.QtGui import QPainter, QCursor, QRadialGradient, QBrush, QColor, QGuiApplication, QImage, QColorSpace, QPixmap
import serial
import serial.tools.list_ports
from HMC.cursor_pointer_manager import CursorPointerManager
import os
import logging

# Platform-specific imports
if sys.platform == 'win32':
    from ctypes import windll
else:
    # For Linux/Mac, we'll use X11/Wayland specific methods if needed
    windll = None

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

        # Make the window truly click-through on Windows only
        if sys.platform == 'win32':
            hwnd = self.winId().__int__()
            windll.user32.SetWindowLongPtrW(c_void_p(hwnd), -20, 
                windll.user32.GetWindowLongPtrW(c_void_p(hwnd), -20) | 0x80000 | 0x20)
        elif sys.platform.startswith('linux'):
            # Check for Wayland vs X11
            session_type = os.environ.get('XDG_SESSION_TYPE', '')
            if session_type == 'wayland':
                # Wayland-specific code
                self.setWindowFlags(
                    self.windowFlags() | 
                    Qt.WindowType.WindowDoesNotAcceptFocus |
                    Qt.WindowType.WindowTransparentForInput
                )
            else:
                # X11-specific code
                try:
                    from Xlib import display, X
                    d = display.Display()
                    w = d.create_resource_object('window', self.winId().__int__())
                    w.change_attributes(override_redirect=True)
                    d.sync()
                except ImportError:
                    print("Warning: python-xlib not installed, some features may not work")
        else:
            # MacOS specific code if needed
            pass

    def event(self, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick, QEvent.Type.MouseMove):
            return False
        return super().event(event)

class Flashlight(Overlay):
    def __init__(self, cccore, size=200, power=0.5):
        super().__init__()
        self.size = size
        self.power = power
        self.cursor_manager = cccore.cursor_manager

        self.cursor_effect_timer = QTimer(self)
        self.cursor_effect_timer.timeout.connect(self.update_cursor_effect)
        self.cursor_effect_timer.start(30)
        self.cursor_pos = self.cursor_manager.get_current_cursor_pos()

    def set_power(self, power):
        self.power = power

    def set_size(self, size):
        self.size = size

    def update_cursor_effect(self):
        self.cursor_pos = self.cursor_manager.get_current_cursor_pos()
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

class CustomchorderOverlay(Overlay):
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
    def __init__(self, cccore, flashlight_size=200, flashlight_power=0.07, serial_port=None, baud_rate=115200):
        super().__init__()
        self.cccore = cccore
        self.cursor_pointer_manager = cccore.cursor_pointer_manager
        
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        
        # Create flashlight overlay
        self.flashlight_overlay = Flashlight(cccore, size=flashlight_size, power=flashlight_power)
        self.flashlight_overlay.setParent(self)
        
        self.customchorder_overlay = CustomchorderOverlay(serial_port, baud_rate)
        self.customchorder_overlay.setParent(self)

        self.cursor_effect_timer = QTimer(self)
        self.cursor_effect_timer.timeout.connect(self.update_cursor_effect)
        self.cursor_effect_timer.start(30)

        self.label = QLabel(self)
        self.label.setText("mysterious unselectable text")
        self.label.setStyleSheet("QLabel { color : black; font-size: 20px; }")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Enable mouse tracking
        self.setMouseTracking(True)
# Show the overlay
        self.show()
        self.raise_()
        
    def add_layer(self, widget):
        """Add a new layer to the overlay"""
        self.main_layout.addWidget(widget)
        widget.show()
        widget.raise_()

    def enterEvent(self, event):
        # Set transparent cursor when mouse enters the overlay
        self.cccore.cursor_pointer_manager.set_transparent_cursor()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Restore default cursor when mouse leaves the overlay
        self.cccore.cursor_pointer_manager.restore_default_cursor()
        super().leaveEvent(event)

    def update_cursor_effect(self):
        try:
            self.cursor_pos = self.cccore.cursor_pointer_manager.get_current_pos()
            if self.flashlight_overlay:
                self.flashlight_overlay.cursor_pos = self.cursor_pos
                self.flashlight_overlay.update()
            if self.customchorder_overlay:
                self.customchorder_overlay.update()
        except Exception as e:
            logging.error(f"Error updating cursor effect: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
        self.flashlight_overlay.render(painter)
        self.customchorder_overlay.render(painter)

    def set_serial_port(self, port):
        self.customchorder_overlay.set_serial_port(port)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    composite_overlay = CompositeOverlay(flashlight_size=200, flashlight_power=0.6, serial_port="COM3")
    composite_overlay.show()
    sys.exit(app.exec())
