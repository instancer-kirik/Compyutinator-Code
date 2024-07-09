import os
import signal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QMessageBox

class ProcessManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.process_list = QListWidget()
        self.layout.addWidget(self.process_list)

        self.kill_button = QPushButton("Kill Selected Process")
        self.kill_button.clicked.connect(self.kill_selected_process)
        self.layout.addWidget(self.kill_button)

        self.update_process_list()

    def update_process_list(self):
        self.process_list.clear()
        for pid, proc in self.parent.child_processes.items():
            self.process_list.addItem(f"PID: {pid}, Command: {' '.join(proc.args)}")

    def kill_selected_process(self):
        selected_item = self.process_list.currentItem()
        if selected_item:
            pid = int(selected_item.text().split(",")[0].split(":")[1].strip())
            try:
                os.kill(pid, signal.SIGTERM)
                del self.parent.child_processes[pid]
                self.update_process_list()
                QMessageBox.information(self, "Success", f"Process {pid} killed successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to kill process {pid}: {e}")

    def add_process(self, process):
        self.parent.child_processes[process.pid] = process
        self.update_process_list()
