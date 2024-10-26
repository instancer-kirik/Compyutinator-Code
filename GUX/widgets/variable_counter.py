from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QDialog, QFormLayout, QColorDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

class VariableCounterSettings(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Variable Counter Settings")
        self.setStyleSheet("background-color: #001a33; color: #00ffff;")

        layout = QFormLayout()
        self.setLayout(layout)

        self.label_edit = QLineEdit(self.parent.label)
        self.min_edit = QLineEdit(str(self.parent.min_value))
        self.max_edit = QLineEdit(str(self.parent.max_value))
        self.low_inc_edit = QLineEdit(str(self.parent.low_inc))
        self.mid_inc_edit = QLineEdit(str(self.parent.mid_inc))
        self.high_inc_edit = QLineEdit(str(self.parent.high_inc))

        self.low_color_btn = QPushButton("Choose")
        self.low_color_btn.clicked.connect(lambda: self.choose_color("low"))
        self.mid_color_btn = QPushButton("Choose")
        self.mid_color_btn.clicked.connect(lambda: self.choose_color("mid"))
        self.high_color_btn = QPushButton("Choose")
        self.high_color_btn.clicked.connect(lambda: self.choose_color("high"))

        layout.addRow("Label:", self.label_edit)
        layout.addRow("Min Value:", self.min_edit)
        layout.addRow("Max Value:", self.max_edit)
        layout.addRow("Low Increment:", self.low_inc_edit)
        layout.addRow("Mid Increment:", self.mid_inc_edit)
        layout.addRow("High Increment:", self.high_inc_edit)
        layout.addRow("Low Color:", self.low_color_btn)
        layout.addRow("Mid Color:", self.mid_color_btn)
        layout.addRow("High Color:", self.high_color_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        layout.addRow(save_btn)

    def choose_color(self, color_type):
        color = QColorDialog.getColor()
        if color.isValid():
            setattr(self.parent, f"{color_type}_color", color.name())
            getattr(self, f"{color_type}_color_btn").setStyleSheet(f"background-color: {color.name()};")

    def save_settings(self):
        self.parent.label = self.label_edit.text()
        self.parent.min_value = int(self.min_edit.text())
        self.parent.max_value = int(self.max_edit.text())
        self.parent.low_inc = int(self.low_inc_edit.text())
        self.parent.mid_inc = int(self.mid_inc_edit.text())
        self.parent.high_inc = int(self.high_inc_edit.text())
        self.parent.update_ui()
        self.accept()

class VariableCounter(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, label, min_value, max_value, initial_value=0, 
                 low_color="#ff0000", mid_color="#ffff00", high_color="#00ff00",
                 low_inc=-10, mid_inc=5, high_inc=10):
        super().__init__()
        self.label = label
        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value
        self.low_color = low_color
        self.mid_color = mid_color
        self.high_color = high_color
        self.low_inc = low_inc
        self.mid_inc = mid_inc
        self.high_inc = high_inc
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Label
        self.label_widget = QLabel(self.label)
        self.label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_widget.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.label_widget.setStyleSheet("color: #00ffff;")
        layout.addWidget(self.label_widget)

        # Value display and increment button
        value_layout = QHBoxLayout()
        self.value_label = QLabel(str(self.value))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.update_color()
        value_layout.addWidget(self.value_label)

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
        self.increment_button.clicked.connect(lambda: self.increment(self.mid_inc))
        value_layout.addWidget(self.increment_button)

        layout.addLayout(value_layout)

        # Buttons
        button_layout = QHBoxLayout()
        
        self.low_button = QPushButton("Low")
        self.mid_button = QPushButton("Mid")
        self.high_button = QPushButton("High")

        for button in (self.low_button, self.mid_button, self.high_button):
            button.setStyleSheet("""
                QPushButton {
                    background-color: #001a33;
                    color: #00ffff;
                    border: 2px solid #00ffff;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #003366;
                }
                QPushButton:pressed {
                    background-color: #004080;
                }
            """)
            button_layout.addWidget(button)

        self.low_button.clicked.connect(lambda: self.increment(self.low_inc))
        self.mid_button.clicked.connect(lambda: self.increment(self.mid_inc))
        self.high_button.clicked.connect(lambda: self.increment(self.high_inc))

        layout.addLayout(button_layout)

        # Settings button
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.open_settings)
        layout.addWidget(settings_button)

    def increment(self, amount):
        new_value = max(self.min_value, min(self.max_value, self.value + amount))
        if new_value != self.value:
            self.value = new_value
            self.value_label.setText(str(self.value))
            self.update_color()
            self.valueChanged.emit(self.value)

    def update_color(self):
        range_size = (self.max_value - self.min_value) / 3
        if self.value < self.min_value + range_size:
            color = self.low_color
        elif self.value < self.min_value + 2 * range_size:
            color = self.mid_color
        else:
            color = self.high_color
        self.value_label.setStyleSheet(f"color: {color};")

    def set_value(self, value):
        self.value = max(self.min_value, min(self.max_value, value))
        self.value_label.setText(str(self.value))
        self.update_color()
        self.valueChanged.emit(self.value)

    def open_settings(self):
        settings_dialog = VariableCounterSettings(self)
        settings_dialog.exec()

    def update_ui(self):
        self.label_widget.setText(self.label)
        self.set_value(self.value)

# Example usage
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Variable Counter Example")
            self.setGeometry(100, 100, 300, 200)
            self.setStyleSheet("background-color: #001a33;")

            counter = VariableCounter("Energy Level", 0, 100, 50)
            counter.valueChanged.connect(self.on_value_changed)

            self.setCentralWidget(counter)

        def on_value_changed(self, value):
            print(f"Value changed to: {value}")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

