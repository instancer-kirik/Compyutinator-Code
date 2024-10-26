import sys
import random
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QGridLayout, QFrame)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QPainter, QPen, QColor
from PyQt6.QtSvgWidgets import QSvgWidget

class CircularIndicator(QWidget):
    def __init__(self, color=QColor("#e94560")):
        super().__init__()
        self.value = 0
        self.color = color
        self.setMinimumSize(100, 100)

    def setValue(self, value):
        self.value = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background circle
        painter.setPen(QPen(self.color.lighter(), 2))
        painter.drawEllipse(10, 10, 80, 80)

        # Draw value arc
        painter.setPen(QPen(self.color, 4))
        span_angle = int(-self.value * 3.6)  # Convert percentage to degrees (360 * value/100)
        painter.drawArc(10, 10, 80, 80, 90 * 16, span_angle * 16)  # Qt uses 16th of a degree

        # Draw value text
        painter.setPen(self.color)
        painter.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.value}")

class VitalsMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Organism Vitals Monitor')
        self.setGeometry(100, 100, 800, 400)
        self.setStyleSheet("background-color: #1a1a2e; color: #e94560;")
        
        main_layout = QHBoxLayout()
        
        # Left side: SVG image
        svg_widget = QSvgWidget("organism.svg")
        svg_widget.setFixedSize(300, 300)
        main_layout.addWidget(svg_widget)
        
        # Right side: Vitals indicators
        vitals_layout = QVBoxLayout()
        
        # Title
        title = QLabel('Organism Vitals Monitor')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #16213e; margin-bottom: 20px;")
        vitals_layout.addWidget(title)
        
        # Grid for vitals indicators
        grid_layout = QGridLayout()
        
        # Heart Rate
        heart_frame = self.create_vital_frame("Heart Rate")
        self.heart_indicator = CircularIndicator(QColor("#e94560"))
        self.heart_value = QLabel("0 BPM")
        heart_frame.layout().addWidget(self.heart_indicator)
        heart_frame.layout().addWidget(self.heart_value)
        grid_layout.addWidget(heart_frame, 0, 0)
        
        # Blood Pressure
        bp_frame = self.create_vital_frame("Blood Pressure")
        self.bp_value = QLabel("0/0 mmHg")
        self.bp_value.setStyleSheet("font-size: 18px; font-weight: bold;")
        bp_frame.layout().addWidget(self.bp_value)
        grid_layout.addWidget(bp_frame, 0, 1)
        
        # Oxygen Saturation
        oxygen_frame = self.create_vital_frame("Oxygen Saturation")
        self.oxygen_bar = QProgressBar()
        self.oxygen_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #0f3460;
                border-radius: 5px;
                background-color: #16213e;
            }
            QProgressBar::chunk {
                background-color: #e94560;
            }
        """)
        self.oxygen_value = QLabel("0%")
        oxygen_frame.layout().addWidget(self.oxygen_bar)
        oxygen_frame.layout().addWidget(self.oxygen_value)
        grid_layout.addWidget(oxygen_frame, 1, 0)
        
        # Body Temperature
        temp_frame = self.create_vital_frame("Body Temperature")
        self.temp_indicator = QFrame()
        self.temp_indicator.setFixedSize(50, 50)
        self.temp_indicator.setStyleSheet("background-color: #e94560; border-radius: 25px;")
        self.temp_value = QLabel("0°C")
        temp_frame.layout().addWidget(self.temp_indicator)
        temp_frame.layout().addWidget(self.temp_value)
        grid_layout.addWidget(temp_frame, 1, 1)
        
        vitals_layout.addLayout(grid_layout)
        main_layout.addLayout(vitals_layout)
        
        self.setLayout(main_layout)
        
        # Timer to update vitals
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_vitals)
        self.timer.start(1000)  # Update every second
    
    def create_vital_frame(self, title):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                border: 2px solid #0f3460;
                border-radius: 10px;
                padding: 10px;
                background-color: #16213e;
            }
        """)
        layout = QVBoxLayout()
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        frame.setLayout(layout)
        return frame

    def update_vitals(self):
        # Update heart rate
        heart_rate = random.randint(60, 100)
        self.heart_indicator.setValue(heart_rate)
        self.heart_value.setText(f"{heart_rate} BPM")
        
        # Update blood pressure
        systolic = random.randint(110, 140)
        diastolic = random.randint(70, 90)
        self.bp_value.setText(f"{systolic}/{diastolic} mmHg")
        
        # Update oxygen saturation
        oxygen = random.randint(95, 100)
        self.oxygen_bar.setValue(oxygen)
        self.oxygen_value.setText(f"{oxygen}%")
        
        # Update temperature
        temp = round(random.uniform(36.5, 37.5), 1)
        self.temp_value.setText(f"{temp}°C")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VitalsMonitor()
    ex.show()
    sys.exit(app.exec())
