import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

class PowerBar(QProgressBar):
    def __init__(self, *args, **kwargs):
        super(PowerBar, self).__init__(*args, **kwargs)
        self.setTextVisible(False)
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2c3e50;
                border-radius: 5px;
                background-color: #34495e;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 10px;
                margin: 0.5px;
            }
        """)

class PowerRoutingWidget(QWidget):
    power_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.systems = ['Shields', 'Weapons', 'Engines', 'Life Support']
        self.power_levels = {system: 25 for system in self.systems}
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #2c3e50; color: #ecf0f1;")
        layout = QVBoxLayout()

        title = QLabel('Power Distribution')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Arial', 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #3498db; margin-bottom: 20px;")
        layout.addWidget(title)

        self.sliders = {}
        self.power_bars = {}
        self.power_labels = {}

        for system in self.systems:
            system_layout = QHBoxLayout()
            
            label = QLabel(system)
            label.setFixedWidth(100)
            system_layout.addWidget(label)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(25)
            slider.setFixedWidth(150)
            slider.valueChanged.connect(lambda value, sys=system: self.update_power(sys, value))
            system_layout.addWidget(slider)
            self.sliders[system] = slider

            power_bar = PowerBar()
            power_bar.setRange(0, 100)
            power_bar.setValue(25)
            power_bar.setFixedWidth(200)
            system_layout.addWidget(power_bar)
            self.power_bars[system] = power_bar

            power_label = QLabel("25%")
            power_label.setFixedWidth(50)
            system_layout.addWidget(power_label)
            self.power_labels[system] = power_label

            layout.addLayout(system_layout)

        self.total_power_bar = PowerBar()
        self.total_power_bar.setRange(0, 200)
        self.total_power_bar.setValue(100)
        layout.addWidget(self.total_power_bar)

        self.total_power_label = QLabel("Total Power: 100%")
        self.total_power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_power_label.setFont(QFont('Arial', 16))
        self.total_power_label.setStyleSheet("color: #ecf0f1; margin-top: 10px;")
        layout.addWidget(self.total_power_label)

        self.emergency_button = QPushButton("Emergency Power Redistribution")
        self.emergency_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.emergency_button.clicked.connect(self.emergency_redistribution)
        layout.addWidget(self.emergency_button)

        self.setLayout(layout)

    def update_power(self, system, value):
        self.power_levels[system] = value
        self.power_bars[system].setValue(value)
        self.power_labels[system].setText(f"{value}%")
        
        total_power = sum(self.power_levels.values())
        self.total_power_bar.setValue(total_power)
        self.total_power_label.setText(f"Total Power: {total_power}%")
        self.total_power_label.setStyleSheet(f"color: {'#e74c3c' if total_power > 100 else '#ecf0f1'}; margin-top: 10px;")
        
        self.power_updated.emit(self.power_levels)

    def emergency_redistribution(self):
        power_per_system = 100 // len(self.systems)
        remainder = 100 % len(self.systems)
        
        for i, (system, slider) in enumerate(self.sliders.items()):
            if i < remainder:
                slider.setValue(power_per_system + 1)
            else:
                slider.setValue(power_per_system)

        self.update_power()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PowerRoutingWidget()
    ex.show()
    sys.exit(app.exec())
