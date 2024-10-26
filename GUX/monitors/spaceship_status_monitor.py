import sys
import random
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QGridLayout, QFrame)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
from PyQt6.QtSvg import QSvgWidget

class SpaceshipStatusMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.power_levels = {"Shields": 25, "Weapons": 25, "Engines": 25, "Life Support": 25}
        self.initUI()
        
    def initUI(self):
        self.setStyleSheet("background-color: #001a33; color: #00ffff;")
        
        main_layout = QHBoxLayout()
        
        # Left side: SVG image
        svg_widget = QSvgWidget("spaceship.svg")
        svg_widget.setFixedSize(400, 300)
        main_layout.addWidget(svg_widget)
        
        # Right side: Status indicators
        status_layout = QVBoxLayout()
        
        # Title
        title = QLabel('USS Nebula - Status Monitor')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #ff9900; margin-bottom: 20px;")
        status_layout.addWidget(title)
        
        # Grid for status indicators
        grid_layout = QGridLayout()
        
        # Shields
        shields_frame = self.create_status_frame("Shields")
        self.shields_bar = QProgressBar()
        self.shields_bar.setStyleSheet(self.get_progress_bar_style())
        shields_frame.layout().addWidget(self.shields_bar)
        grid_layout.addWidget(shields_frame, 0, 0)
        
        # Weapons
        weapons_frame = self.create_status_frame("Weapons")
        self.weapons_bar = QProgressBar()
        self.weapons_bar.setStyleSheet(self.get_progress_bar_style())
        weapons_frame.layout().addWidget(self.weapons_bar)
        grid_layout.addWidget(weapons_frame, 0, 1)
        
        # Engines
        engines_frame = self.create_status_frame("Engines")
        self.engines_bar = QProgressBar()
        self.engines_bar.setStyleSheet(self.get_progress_bar_style())
        engines_frame.layout().addWidget(self.engines_bar)
        grid_layout.addWidget(engines_frame, 1, 0)
        
        # Life Support
        life_support_frame = self.create_status_frame("Life Support")
        self.life_support_bar = QProgressBar()
        self.life_support_bar.setStyleSheet(self.get_progress_bar_style())
        life_support_frame.layout().addWidget(self.life_support_bar)
        grid_layout.addWidget(life_support_frame, 1, 1)
        
        status_layout.addLayout(grid_layout)
        main_layout.addLayout(status_layout)
        
        self.setLayout(main_layout)
        
        # Timer to update status
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)  # Update every second
        
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

    def get_progress_bar_style(self):
        return """
            QProgressBar {
                border: 2px solid #00ffff;
                border-radius: 5px;
                background-color: #001a33;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #00ffff;
            }
        """

    def update_status(self):
        self.shields_bar.setValue(self.power_levels["Shields"])
        self.weapons_bar.setValue(self.power_levels["Weapons"])
        self.engines_bar.setValue(self.power_levels["Engines"])
        self.life_support_bar.setValue(self.power_levels["Life Support"])

    def set_power_levels(self, power_levels):
        self.power_levels = power_levels
        self.update_status()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SpaceshipStatusMonitor()
    ex.show()
    sys.exit(app.exec())
