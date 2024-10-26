from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

class StatTracker(QWidget):
    statChanged = pyqtSignal(str, int)

    def __init__(self, label, initial_value=0, color="#00ffff"):
        super().__init__()
        self.label = label
        self.value = initial_value
        self.color = color
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        # Label
        label = QLabel(self.label)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {self.color};")
        layout.addWidget(label)

        # Value display
        self.value_label = QLabel(str(self.value))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {self.color};")
        layout.addWidget(self.value_label)

        # Increment button
        self.increment_button = QPushButton("+")
        self.increment_button.setStyleSheet("""
            QPushButton {
                background-color: #001a33;
                color: #00ffff;
                border: 2px solid #00ffff;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #003366;
            }
            QPushButton:pressed {
                background-color: #004080;
            }
        """)
        self.increment_button.clicked.connect(self.increment)
        layout.addWidget(self.increment_button)

    def increment(self):
        self.value += 1
        self.value_label.setText(str(self.value))
        self.statChanged.emit(self.label, self.value)

    def set_value(self, value):
        self.value = value
        self.value_label.setText(str(self.value))
        self.statChanged.emit(self.label, self.value)

class StatTrackerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.trackers = {}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        title = QLabel('User Action Statistics')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #ff9900; margin-bottom: 10px;")
        layout.addWidget(title)

        # Add some default trackers
        self.add_tracker("Clicks", "#00ff00")
        self.add_tracker("Keys Pressed", "#ff00ff")
        self.add_tracker("Commands Executed", "#ffff00")

    def add_tracker(self, label, color="#00ffff"):
        tracker = StatTracker(label, color=color)
        tracker.statChanged.connect(self.on_stat_changed)
        self.trackers[label] = tracker
        self.layout().addWidget(tracker)

    def on_stat_changed(self, label, value):
        print(f"Stat changed: {label} = {value}")

    def increment_stat(self, label):
        if label in self.trackers:
            self.trackers[label].increment()

    def set_stat(self, label, value):
        if label in self.trackers:
            self.trackers[label].set_value(value)

# Example usage
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Stat Tracker Example")
            self.setGeometry(100, 100, 300, 200)
            self.setStyleSheet("background-color: #001a33;")

            self.stat_panel = StatTrackerPanel()
            self.setCentralWidget(self.stat_panel)

            # Simulate some user actions
            QTimer.singleShot(1000, lambda: self.stat_panel.increment_stat("Clicks"))
            QTimer.singleShot(2000, lambda: self.stat_panel.increment_stat("Keys Pressed"))
            QTimer.singleShot(3000, lambda: self.stat_panel.increment_stat("Commands Executed"))

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

