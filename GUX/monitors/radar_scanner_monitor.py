import sys
import random
import math
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QGridLayout)
from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QBrush
from PyQt6.QtSvgWidgets import QSvgWidget

class RadarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 300)
        self.angle = 0
        self.blips = []

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw radar background
        painter.setPen(QPen(QColor("#00ffff"), 2))
        painter.setBrush(QBrush(QColor("#001a33")))
        painter.drawEllipse(10, 10, 280, 280)

        # Draw radar circles
        for i in range(1, 4):
            painter.drawEllipse(10 + i*70, 10 + i*70, 280 - i*140, 280 - i*140)

        # Draw radar lines
        painter.drawLine(10, 150, 290, 150)
        painter.drawLine(150, 10, 150, 290)

        # Draw radar sweep
        painter.setPen(QPen(QColor("#00ff00"), 2))
        painter.drawLine(150, 150, 
                         150 + 140 * math.cos(math.radians(self.angle)),
                         150 - 140 * math.sin(math.radians(self.angle)))

        # Draw blips
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#ff0000")))
        for blip in self.blips:
            painter.drawEllipse(blip, 5, 5)

    def update_radar(self):
        self.angle = (self.angle + 5) % 360
        self.update()

    def add_blip(self):
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, 140)
        x = 150 + distance * math.cos(angle)
        y = 150 - distance * math.sin(angle)
        self.blips.append(QPointF(x, y))
        if len(self.blips) > 10:
            self.blips.pop(0)

class RadarScannerMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Radar Scanner Monitor')
        self.setGeometry(100, 100, 800, 400)
        self.setStyleSheet("background-color: #001a33; color: #00ffff;")
        
        main_layout = QHBoxLayout()
        
        # Left side: Radar widget
        self.radar_widget = RadarWidget()
        main_layout.addWidget(self.radar_widget)
        
        # Right side: Status indicators
        status_layout = QVBoxLayout()
        
        # Title
        title = QLabel('Radar Scanner Monitor')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #ff9900; margin-bottom: 20px;")
        status_layout.addWidget(title)
        
        # Grid for status indicators
        grid_layout = QGridLayout()
        
        # Scan Status
        scan_frame = self.create_status_frame("Scan Status")
        self.scan_label = QLabel("Active")
        self.scan_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00ff00;")
        scan_frame.layout().addWidget(self.scan_label)
        grid_layout.addWidget(scan_frame, 0, 0)
        
        # Range
        range_frame = self.create_status_frame("Range")
        self.range_label = QLabel("1000 km")
        self.range_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        range_frame.layout().addWidget(self.range_label)
        grid_layout.addWidget(range_frame, 0, 1)
        
        # Objects Detected
        objects_frame = self.create_status_frame("Objects Detected")
        self.objects_label = QLabel("0")
        self.objects_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        objects_frame.layout().addWidget(self.objects_label)
        grid_layout.addWidget(objects_frame, 1, 0)
        
        # Last Detection
        detection_frame = self.create_status_frame("Last Detection")
        self.detection_label = QLabel("N/A")
        self.detection_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        detection_frame.layout().addWidget(self.detection_label)
        grid_layout.addWidget(detection_frame, 1, 1)
        
        status_layout.addLayout(grid_layout)
        main_layout.addLayout(status_layout)
        
        self.setLayout(main_layout)
        
        # Timer to update radar
        self.radar_timer = QTimer(self)
        self.radar_timer.timeout.connect(self.radar_widget.update_radar)
        self.radar_timer.start(50)  # Update every 50 ms
        
        # Timer to add blips
        self.blip_timer = QTimer(self)
        self.blip_timer.timeout.connect(self.add_blip)
        self.blip_timer.start(2000)  # Add blip every 2 seconds
        
    def create_status_frame(self, title):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                border: 2px solid #00ffff;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout()
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        frame.setLayout(layout)
        return frame
        
    def add_blip(self):
        self.radar_widget.add_blip()
        self.objects_label.setText(str(len(self.radar_widget.blips)))
        self.detection_label.setText(f"{random.randint(10, 990)} km, {random.randint(0, 359)}°")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RadarScannerMonitor()
    ex.show()
    sys.exit(app.exec())

