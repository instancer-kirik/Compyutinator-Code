import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QStackedWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from GUX.monitors.spaceship_status_monitor import SpaceshipStatusMonitor
from GUX.monitors.organism_vitals_monitor import VitalsMonitor
from GUX.monitors.power_routing_widget import PowerRoutingWidget

class MonitorWrapper(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Advanced Monitoring System')
        self.setGeometry(100, 100, 1400, 600)  # Increased width to accommodate SVG
        self.setStyleSheet("background-color: #2c3e50; color: #ecf0f1;")

        main_layout = QHBoxLayout()

        # Left side: Monitors
        monitor_layout = QVBoxLayout()

        # Title
        title = QLabel('Advanced Monitoring System')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #3498db; margin-bottom: 20px;")
        monitor_layout.addWidget(title)

        # Tools and Selector
        tools_layout = QHBoxLayout()

        self.monitor_selector = QComboBox()
        self.monitor_selector.addItems(["Spaceship Status", "Organism Vitals"])
        self.monitor_selector.setStyleSheet("""
            QComboBox {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 14px;
                height: 14px;
            }
        """)
        self.monitor_selector.currentIndexChanged.connect(self.change_monitor)
        tools_layout.addWidget(self.monitor_selector)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: #ecf0f1;
                border: none;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_monitor)
        tools_layout.addWidget(self.refresh_button)

        monitor_layout.addLayout(tools_layout)

        # Stacked Widget for monitors
        self.stack = QStackedWidget()
        self.spaceship_monitor = SpaceshipStatusMonitor()
        self.organism_monitor = VitalsMonitor()
        self.stack.addWidget(self.spaceship_monitor)
        self.stack.addWidget(self.organism_monitor)
        monitor_layout.addWidget(self.stack)

        main_layout.addLayout(monitor_layout, 3)  # Increased ratio for monitors

        # Right side: Power Routing Widget
        self.power_routing = PowerRoutingWidget()
        main_layout.addWidget(self.power_routing, 1)

        self.setLayout(main_layout)

        # Connect power routing to spaceship monitor
        self.power_routing.power_updated.connect(self.update_spaceship_power)

        # Timer to update monitors
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_current_monitor)
        self.timer.start(1000)  # Update every second

    def change_monitor(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:  # Spaceship Status
            self.power_routing.setVisible(True)
        else:  # Organism Vitals
            self.power_routing.setVisible(False)

    def refresh_monitor(self):
        self.update_current_monitor()

    def update_current_monitor(self):
        current_widget = self.stack.currentWidget()
        if isinstance(current_widget, SpaceshipStatusMonitor):
            current_widget.update_status()
        elif isinstance(current_widget, VitalsMonitor):
            current_widget.update_vitals()

    def update_spaceship_power(self):
        power_levels = {system: slider.value() for system, slider in self.power_routing.sliders.items()}
        self.spaceship_monitor.set_power_levels(power_levels)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MonitorWrapper()
    ex.show()
    sys.exit(app.exec())
