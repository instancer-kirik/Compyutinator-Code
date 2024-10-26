import sys
import evdev
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QCheckBox, QComboBox, QHBoxLayout,
                             QPushButton, QDialog, QFormLayout, QSpinBox, QDialogButtonBox)
from PyQt6.QtCore import Qt, QEvent, QPoint, QThread, pyqtSignal
from PyQt6.QtGui import QCursor, QGuiApplication, QPainter, QColor
from evdev import ecodes, InputEvent, UInput

class PenSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pen Settings")
        layout = QFormLayout(self)

        self.pressure_threshold = QSpinBox()
        self.pressure_threshold.setRange(0, 1000)
        self.pressure_threshold.setValue(5)
        layout.addRow("Pressure Threshold:", self.pressure_threshold)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

class PenDevice:
    def __init__(self):
        self.device = self.find_pen_device()
        self.uinput = None

    def find_pen_device(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            if "IPTSD Virtual Stylus" in device.name:
                print(f"Pen device found: {device.name}")
                return device
        print("No pen device found")
        return None

    def get_name(self):
        return self.device.name if self.device else "Unknown"

    def create_uinput(self):
        cap = {
            ecodes.EV_ABS: [
                (ecodes.ABS_X, self.device.absinfo(ecodes.ABS_X)),
                (ecodes.ABS_Y, self.device.absinfo(ecodes.ABS_Y)),
                (ecodes.ABS_PRESSURE, self.device.absinfo(ecodes.ABS_PRESSURE)),
            ],
            ecodes.EV_KEY: [ecodes.BTN_TOUCH]
        }
        self.uinput = UInput(cap, name="Virtual IPTSD Touch", version=0x3)

class PenThread(QThread):
    pen_event = pyqtSignal(object)

    def __init__(self, pen_device):
        super().__init__()
        self.pen_device = pen_device
        self.running = True

    def run(self):
        while self.running:
            try:
                for event in self.pen_device.device.read():
                    self.pen_event.emit(event)
            except BlockingIOError:
                pass

    def stop(self):
        self.running = False

class EnhancedPenScrollWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.pen_device = PenDevice()
        self.initUI()
        self.pen_active = False
        self.overlay = None
        self.hotkey_pressed = False
        self.settings = PenSettings()
        self.current_x = 0
        self.current_y = 0
        
        print("Detected pen device:")
        if self.pen_device.device:
            print(f"  Name: {self.pen_device.get_name()}")
            print(f"  Path: {self.pen_device.device.path}")
            self.pen_device.create_uinput()
            self.pen_thread = PenThread(self.pen_device)
            self.pen_thread.pen_event.connect(self.handle_pen_event)
            self.pen_thread.start()
        else:
            print("  No pen device detected")

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.status_label = QLabel("Pen Scroll: Inactive")
        layout.addWidget(self.status_label)

        self.pen_label = QLabel(f"Pen Device: {self.pen_device.get_name()}")
        layout.addWidget(self.pen_label)

        self.system_wide_checkbox = QCheckBox("System-wide mode")
        self.system_wide_checkbox.stateChanged.connect(self.toggle_system_wide_mode)
        layout.addWidget(self.system_wide_checkbox)

        hotkey_layout = QHBoxLayout()
        hotkey_layout.addWidget(QLabel("Hotkey:"))
        self.hotkey_combo = QComboBox()
        self.hotkey_combo.addItems(["Ctrl", "Alt", "Shift"])
        hotkey_layout.addWidget(self.hotkey_combo)
        layout.addLayout(hotkey_layout)

        settings_button = QPushButton("Pen Settings")
        settings_button.clicked.connect(self.open_settings)
        layout.addWidget(settings_button)

        self.setGeometry(100, 100, 250, 200)
        self.setWindowTitle('Enhanced Pen Scroll')

    def open_settings(self):
        if self.settings.exec() == QDialog.DialogCode.Accepted:
            print(f"New pressure threshold: {self.settings.pressure_threshold.value()}")

    def toggle_system_wide_mode(self, state):
        if state:
            if not self.overlay:
                self.overlay = TransparentOverlay(self)
            self.overlay.show()
            self.status_label.setText("Pen Scroll: Active (System-wide)")
            QApplication.instance().installEventFilter(self)
        else:
            if self.overlay:
                self.overlay.hide()
            self.status_label.setText("Pen Scroll: Inactive")
            QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event):
        if self.system_wide_checkbox.isChecked():
            if event.type() == QEvent.Type.KeyPress:
                if self.is_hotkey_pressed(event):
                    self.hotkey_pressed = True
                    if self.overlay:
                        self.overlay.debug_text = f"Hotkey Pressed: {self.hotkey_combo.currentText()}"
                        self.overlay.update()
                    return True
            elif event.type() == QEvent.Type.KeyRelease:
                if self.is_hotkey_pressed(event):
                    self.hotkey_pressed = False
                    self.pen_active = False
                    if self.overlay:
                        self.overlay.debug_text = "Hotkey Released"
                        self.overlay.update()
                    return True
        return super().eventFilter(obj, event)

    def is_hotkey_pressed(self, event):
        hotkey = self.hotkey_combo.currentText()
        if hotkey == "Ctrl":
            return event.key() == Qt.Key.Key_Control
        elif hotkey == "Alt":
            return event.key() == Qt.Key.Key_Alt
        elif hotkey == "Shift":
            return event.key() == Qt.Key.Key_Shift
        return False

    def handle_pen_event(self, event):
        if self.hotkey_pressed:
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_X:
                    self.current_x = event.value
                elif event.code == ecodes.ABS_Y:
                    self.current_y = event.value
                elif event.code == ecodes.ABS_PRESSURE:
                    if event.value > self.settings.pressure_threshold.value():
                        if not self.pen_active:
                            self.pen_active = True
                            self.pen_device.uinput.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 1)
                        self.pen_device.uinput.write(ecodes.EV_ABS, ecodes.ABS_X, self.current_x)
                        self.pen_device.uinput.write(ecodes.EV_ABS, ecodes.ABS_Y, self.current_y)
                        self.pen_device.uinput.write(ecodes.EV_ABS, ecodes.ABS_PRESSURE, event.value)
                        self.pen_device.uinput.syn()
                        if self.overlay:
                            self.overlay.debug_text = f"Pen Touch: ({self.current_x}, {self.current_y})"
                            self.overlay.update()
                    elif self.pen_active:
                        self.pen_active = False
                        self.pen_device.uinput.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 0)
                        self.pen_device.uinput.syn()
                        if self.overlay:
                            self.overlay.debug_text = "Pen Released"
                            self.overlay.update()
            return True
        return False

    def closeEvent(self, event):
        if hasattr(self, 'pen_thread'):
            self.pen_thread.stop()
            self.pen_thread.wait()
        if self.pen_device.uinput:
            self.pen_device.uinput.close()
        super().closeEvent(event)

class TransparentOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
        self.debug_text = "Overlay Active"

    def showEvent(self, event):
        self.setGeometry(QGuiApplication.primaryScreen().geometry())
        super().showEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 0, 0, 30))  # Semi-transparent red
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, 20, self.debug_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EnhancedPenScrollWidget()
    ex.show()
    sys.exit(app.exec())

