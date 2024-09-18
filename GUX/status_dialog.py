from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer

class StatusDialog(QDialog):
    def __init__(self, parent=None, title="Status", message="Please wait..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        self.message_label = QLabel(message)
        layout.addWidget(self.message_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
    def update_progress(self, progress, message):
        self.progress_bar.setValue(progress)
        self.message_label.setText(message)
        
    def show_with_timer(self):
        self.show()
        
    def hide_and_stop_timer(self):
        self.hide()