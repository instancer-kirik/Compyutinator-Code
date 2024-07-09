from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtCore import Qt, QTimer, QPoint
import sys

class AlphaMapFlashlight:
    def __init__(self, image_path, size=100):
        self.pixmap = QPixmap(image_path)
        self.size = size

    def draw(self, painter, center):
        scaled_pixmap = self.pixmap.scaled(self.size, self.size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        top_left = QPoint(center.x() - scaled_pixmap.width() // 2, center.y() - scaled_pixmap.height() // 2)
        painter.drawPixmap(top_left, scaled_pixmap)

class CursorOverlay(QWidget):
    def __init__(self, flashlight):
        super().__init__()
        self.flashlight = flashlight
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.resize(QApplication.primaryScreen().size())
        self.cursor_pos = QApplication.instance().overrideCursor().pos() if QApplication.instance().overrideCursor() else QPoint(0, 0)
        
        timer = QTimer(self)
        timer.timeout.connect(self.update_cursor_effect)
        timer.start(16)
    
    def update_cursor_effect(self):
        self.cursor_pos = QApplication.instance().overrideCursor().pos() if QApplication.instance().overrideCursor() else QPoint(0, 0)
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = QPoint(self.cursor_pos.x(), self.cursor_pos.y())
        self.flashlight.draw(painter, center)

        painter.end()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    flashlight = AlphaMapFlashlight("path/to/your/flashlight.png")
    overlay = CursorOverlay(flashlight)
    overlay.show()
    sys.exit(app.exec())
    