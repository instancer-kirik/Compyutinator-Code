import os
import psutil
import json
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, 
    QDialog, QTextEdit, QComboBox, QLineEdit, QMessageBox, 
    QDockWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction
import logging

class DeviceCommand:
    def __init__(self, name, command, device_type="*"):
        self.name = name
        self.command = command
        self.device_type = device_type  # '*' for all devices
        
    def to_dict(self):
        return {
            "name": self.name,
            "command": self.command,
            "device_type": self.device_type
        }
        
    @staticmethod
    def from_dict(data):
        return DeviceCommand(data["name"], data["command"], data.get("device_type", "*"))

class DeviceManagerView(QWidget):
    device_mounted = pyqtSignal(str, str)  # device_path, mount_point
    device_unmounted = pyqtSignal(str)     # device_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.commands = []
        self.load_commands()
        self.setup_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_devices)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.add_command_btn = QPushButton("Add Command")
        self.add_command_btn.clicked.connect(self.add_command)
        self.manage_flows_btn = QPushButton("Manage Flows")
        self.manage_flows_btn.clicked.connect(self.manage_flows)
        
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.add_command_btn)
        toolbar.addWidget(self.manage_flows_btn)
        toolbar.addStretch()
        
        # Device Tree
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["Device", "Type", "Mount Point", "Size", "Status"])
        self.device_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addLayout(toolbar)
        layout.addWidget(self.device_tree)
        self.setLayout(layout)
        
        self.refresh_devices()
        
    def refresh_devices(self):
        """Update the device list"""
        self.device_tree.clear()
        
        # Get all disk partitions
        partitions = psutil.disk_partitions(all=True)
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                size = f"{usage.total / (1024**3):.1f} GB"
                item = QTreeWidgetItem([
                    partition.device,
                    partition.fstype,
                    partition.mountpoint,
                    size,
                    "Mounted"
                ])
                self.device_tree.addTopLevelItem(item)
            except Exception as e:
                logging.error(f"Error getting partition info: {e}")
                
        # Add removable devices
        self.add_removable_devices()
        
    def add_removable_devices(self):
        """Add removable devices to the tree"""
        try:
            if os.name == 'posix':
                # Linux: Check /dev/sd* devices
                import glob
                for device in glob.glob("/dev/sd*"):
                    if device[-1].isdigit():  # Skip partitions
                        continue
                    item = QTreeWidgetItem([
                        device,
                        "Removable",
                        "Not Mounted",
                        "Unknown",
                        "Available"
                    ])
                    self.device_tree.addTopLevelItem(item)
            else:
                # Windows: Use WMI
                import wmi
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive():
                    if disk.MediaType and "Removable" in disk.MediaType:
                        item = QTreeWidgetItem([
                            disk.DeviceID,
                            disk.MediaType,
                            "Not Mounted",
                            f"{int(disk.Size)/(1024**3):.1f} GB",
                            "Available"
                        ])
                        self.device_tree.addTopLevelItem(item)
        except Exception as e:
            logging.error(f"Error detecting removable devices: {e}")

    def show_context_menu(self, position):
        """Show context menu for device operations"""
        item = self.device_tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        device_path = item.text(0)
        device_type = item.text(1)
        
        # Basic operations
        if item.text(4) == "Mounted":
            menu.addAction("Unmount", lambda: self.unmount_device(device_path))
        else:
            menu.addAction("Mount", lambda: self.mount_device(device_path))
            
        # Commands submenu
        commands_menu = menu.addMenu("Commands")
        for cmd in self.commands:
            if cmd.device_type == "*" or cmd.device_type == device_type:
                commands_menu.addAction(cmd.name, 
                    lambda c=cmd: self.execute_command(c, device_path))
                    
        # Flows submenu
        flows_menu = menu.addMenu("Flows")
        self.add_flows_to_menu(flows_menu, device_path)
        
        menu.exec(self.device_tree.viewport().mapToGlobal(position))
        
    def execute_command(self, command, device_path):
        """Execute a command on a device"""
        try:
            cmd = command.command.replace("{device}", device_path)
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to execute command: {e}")
            
    def add_command(self):
        """Add a new command"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Command")
        layout = QVBoxLayout()
        
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Command Name")
        
        cmd_edit = QTextEdit()
        cmd_edit.setPlaceholderText("Command (use {device} for device path)")
        
        type_combo = QComboBox()
        type_combo.addItems(["*", "Removable", "Fixed", "Network"])
        
        def save_command():
            name = name_edit.text()
            cmd = cmd_edit.toPlainText()
            dev_type = type_combo.currentText()
            if name and cmd:
                self.commands.append(DeviceCommand(name, cmd, dev_type))
                self.save_commands()
                dialog.accept()
                
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(save_command)
        
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(name_edit)
        layout.addWidget(QLabel("Command:"))
        layout.addWidget(cmd_edit)
        layout.addWidget(QLabel("Device Type:"))
        layout.addWidget(type_combo)
        layout.addWidget(save_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
        
    def load_commands(self):
        """Load saved commands"""
        try:
            if os.path.exists("device_commands.json"):
                with open("device_commands.json", "r") as f:
                    data = json.load(f)
                    self.commands = [DeviceCommand.from_dict(cmd) for cmd in data]
        except Exception as e:
            logging.error(f"Error loading commands: {e}")
            
    def save_commands(self):
        """Save commands to file"""
        try:
            with open("device_commands.json", "w") as f:
                json.dump([cmd.to_dict() for cmd in self.commands], f)
        except Exception as e:
            logging.error(f"Error saving commands: {e}")

    def add_flows_to_menu(self, menu, device_path):
        """Add flows to the context menu"""
        try:
            # Load flows
            with open("device_flows.json", "r") as f:
                flows = json.load(f)
                for flow in flows:
                    menu.addAction(flow["name"], 
                        lambda f=flow: self.execute_flow(f, device_path))
        except FileNotFoundError:
            menu.addAction("No flows available").setEnabled(False)
        except Exception as e:
            logging.error(f"Error loading flows: {e}")
            menu.addAction("Error loading flows").setEnabled(False)

    def execute_flow(self, flow, device_path):
        """Execute a flow on a device"""
        try:
            for step in flow["steps"]:
                cmd = DeviceCommand.from_dict(step)
                self.execute_command(cmd, device_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to execute flow: {e}")