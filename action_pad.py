from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

class ActionPadWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Action Pad", self)
        self.layout.addWidget(self.label)

        self.button = QPushButton("Perform Action", self)
        self.layout.addWidget(self.button)
