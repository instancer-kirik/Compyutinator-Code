import os
import signal
import logging
import psutil
import subprocess
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QMessageBox, QHBoxLayout
class ProcessManager:
    def __init__(self, cccore):
        
        self.running_processes = {}

    def start_process(self, command, name, cwd=None, capture_output=False):
        try:
            if capture_output:
                process = subprocess.Popen(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            else:
                process = subprocess.Popen(command, shell=True, cwd=cwd)
            
            pid = process.pid
            self.running_processes[pid] = {'name': name, 'command': command, 'process': process}
            logging.info(f"Started process '{name}' with PID {pid}")
            return pid
        except Exception as e:
            logging.error(f"Failed to start process '{name}': {e}")
            return None

    def get_running_processes(self):
        # Update the list of running processes, removing any that have terminated
        self.running_processes = {pid: info for pid, info in self.running_processes.items() if psutil.pid_exists(pid)}
        return self.running_processes

    def kill_process(self, pid):
        if pid in self.running_processes:
            try:
                process = self.running_processes[pid]['process']
                process.terminate()
                process.wait(timeout=5)  # Wait for up to 5 seconds for the process to terminate
                if process.poll() is None:
                    process.kill()  # Force kill if it doesn't terminate
                del self.running_processes[pid]
                logging.info(f"Killed process with PID {pid}")
                return True
            except Exception as e:
                logging.error(f"Error killing process with PID {pid}: {e}")
                del self.running_processes[pid]
                return False
        return False

    def cleanup_processes(self):
        for pid in list(self.running_processes.keys()):
            self.kill_process(pid)

class ProcessManagerWidget(QWidget):
    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.cccore = cccore
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.process_list = QListWidget()
        self.layout.addWidget(self.process_list)

        button_layout = QHBoxLayout()
        self.kill_button = QPushButton("Kill Selected Process")
        self.kill_button.clicked.connect(self.kill_selected_process)
        button_layout.addWidget(self.kill_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_process_list)
        button_layout.addWidget(self.refresh_button)

        self.layout.addLayout(button_layout)

        # Set up a timer to periodically update the process list
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_process_list)
        self.update_timer.start(5000)  # Update every 5 seconds

        self.update_process_list()

    def update_process_list(self):
        self.process_list.clear()
        for pid, proc_info in self.cccore.process_manager.get_running_processes().items():
            self.process_list.addItem(f"PID: {pid}, Name: {proc_info['name']}, Command: {proc_info['command']}")

    def kill_selected_process(self):
        selected_item = self.process_list.currentItem()
        if selected_item:
            pid = int(selected_item.text().split(",")[0].split(":")[1].strip())
            try:
                if self.cccore.process_manager.kill_process(pid):
                    self.update_process_list()
                    QMessageBox.information(self, "Success", f"Process {pid} killed successfully.")
                else:
                    QMessageBox.warning(self, "Warning", f"Process {pid} was not found or already terminated.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to kill process {pid}: {e}")
