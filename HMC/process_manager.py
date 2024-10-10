import os
import signal
import logging
import psutil
import subprocess
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, QProcess
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QMessageBox, QHBoxLayout

class ProcessManager(QObject):
    process_updated = pyqtSignal()

    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.processes = {}

    def start_process(self, command, process_name, cwd=None, capture_output=False):
        logging.warning(f"Starting process: {process_name}")
        try:
            process = QProcess()
            process.finished.connect(lambda exit_code, exit_status: self.process_finished(process_name, exit_code, exit_status))
            if cwd:
                process.setWorkingDirectory(cwd)
            if capture_output:
                process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            process.start(command)
            pid = process.processId()
            self.processes[process_name] = {
                'process': process,
                'pid': pid,
                'command': command
            }
            logging.info(f"Started process: {process_name} (PID: {pid})")
            return process
        except Exception as e:
            logging.error(f"Failed to start process '{process_name}': {e}")
            return None

    def process_finished(self, process_name, exit_code, exit_status):
        if process_name in self.processes:
            pid = self.processes[process_name]['pid']
            del self.processes[process_name]
            logging.info(f"Process finished: {process_name} (PID: {pid}) with exit code: {exit_code}")
            self.process_updated.emit()

    def get_running_processes(self):
        return {name: {
            'pid': info['pid'],
            'command': info['command']
        } for name, info in self.processes.items()}

    def kill_process(self, process_name):
        if process_name in self.processes:
            try:
                process_info = self.processes[process_name]
                process = process_info['process']
                pid = process_info['pid']
                process.terminate()
                if not process.waitForFinished(1000):  # Wait for up to 2 seconds
                    logging.warning(f"Process {process_name} (PID: {pid}) did not terminate, forcing kill")
                    process.kill()
                if not process.waitForFinished(1000):  # Wait additional 2 seconds after force kill
                    logging.error(f"Failed to kill process {process_name} (PID: {pid})")
                else:
                    logging.info(f"Killed process: {process_name} (PID: {pid})")
                del self.processes[process_name]
                self.process_updated.emit()
                return True
            except Exception as e:
                logging.error(f"Error killing process {process_name}: {e}")
                return False
        return False

    def cleanup_processes(self):
        logging.info(f"Starting cleanup of {len(self.processes)} processes")
        for name, process_info in list(self.processes.items()):
            process = process_info['process']
            pid = process_info['pid']
            logging.info(f"Terminating process: {name} (PID: {pid})")
            process.terminate()
            if not process.waitForFinished(5000):  # 5 second timeout
                logging.warning(f"Process {name} (PID: {pid}) did not terminate, forcing kill")
                process.kill()
        self.processes.clear()
        logging.info("Process cleanup completed")
        self.process_updated.emit()

    def __del__(self):
        self.cleanup_processes()

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
        try:
            self.process_list.clear()
            for name, proc_info in self.cccore.process_manager.get_running_processes().items():
                self.process_list.addItem(f"Name: {name}, PID: {proc_info['pid']}, Command: {proc_info['command']}")
        except Exception as e:
            logging.error(f"Error updating process list: {e}")

    def kill_selected_process(self):
        selected_item = self.process_list.currentItem()
        if selected_item:
            try:
                pid = int(selected_item.text().split(",")[0].split(":")[1].strip())
                if self.cccore.process_manager.kill_process(pid):
                    self.update_process_list()
                    QMessageBox.information(self, "Success", f"Process {pid} killed successfully.")
                else:
                    QMessageBox.warning(self, "Warning", f"Process {pid} was not found or already terminated.")
            except Exception as e:
                logging.error(f"Error killing process: {e}")
                QMessageBox.critical(self, "Error", f"Failed to kill process: {e}")

    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)
