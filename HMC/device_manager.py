from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QComboBox, QMessageBox, QDialogButtonBox, QCheckBox, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt
from DEV.devices.device_flows import DeviceFlow, FlowManagerDialog
from DEV.devices.device_command import DeviceCommand
from pathlib import Path
import psutil
import logging
import os
import subprocess
import json

class DeviceManager:
    def __init__(self):
        self.commands = []
        self.flows = []
        self.bt_hid_enabled = False
        self.nix_store_path = "/nix/store"
        self.error_count = 0
        self.last_error = None
        self.mount_count = 0
        self.mounted_devices = {}
        self.setup_logging()
        self.load_commands()
        self.load_flows()

    def setup_logging(self):
        """Configure logging for device operations"""
        self.logger = logging.getLogger('device_manager')
        self.logger.setLevel(logging.DEBUG)
        
        # Add file handler
        fh = logging.FileHandler('device_manager.log')
        fh.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)

    def get_device_stats(self):
        """Get device operation statistics"""
        return {
            'total_mounts': self.mount_count,
            'failed_mounts': self.error_count,
            'last_error': self.last_error,
            'active_devices': len(self.get_devices())
        }

    def get_devices(self):
        """Get list of all devices"""
        devices = []
        try:
            # Get mounted partitions
            partitions = psutil.disk_partitions(all=True)
            for partition in partitions:
                try:
                    # Skip system paths
                    if any(skip in partition.mountpoint for skip in [
                        '/run/user', '/proc', '/sys', '/dev', 
                        '/run/docker', '/snap', '/boot/efi'
                    ]):
                        continue
                    
                    # Get disk usage
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        size = f"{usage.total / (1024**3):.1f} GB"
                        status = "Mounted"
                    except PermissionError:
                        size = "N/A"
                        status = "No Access"
                    except Exception:
                        size = "Unknown"
                        status = "Error"

                    devices.append({
                        'path': partition.device,
                        'type': partition.fstype or "Unknown",
                        'mount_point': partition.mountpoint,
                        'size': size,
                        'status': status
                    })
                    
                except Exception as e:
                    if not isinstance(e, PermissionError):
                        logging.debug(f"Skipping partition {partition.device}: {e}")
            
            # Add removable devices
            devices.extend(self.get_removable_devices())
            
        except Exception as e:
            logging.error(f"Error getting device list: {e}")
            
        return devices

    def get_removable_devices(self):
        """Get list of removable devices"""
        devices = []
        try:
            if os.name == 'posix':  # Linux
                try:
                    import pyudev
                    context = pyudev.Context()
                    
                    for device in context.list_devices(subsystem='block', DEVTYPE='disk'):
                        try:
                            if device.get('ID_BUS') == 'usb' or \
                               device.get('ID_DRIVE_FLASH_SD') == '1' or \
                               device.get('ID_DRIVE_REMOVABLE') == '1':
                                
                                device_path = device.device_node
                                device_type = "USB" if device.get('ID_BUS') == 'usb' else "Removable"
                                model = device.get('ID_MODEL', 'Unknown Device')
                                
                                try:
                                    size = int(device.attributes.get('size', 0)) * 512
                                    size_gb = f"{size / (1024**3):.1f} GB"
                                except:
                                    size_gb = "Unknown"
                                
                                devices.append({
                                    'path': device_path,
                                    'type': device_type,
                                    'mount_point': "Not Mounted",
                                    'size': size_gb,
                                    'status': "Available"
                                })
                                
                        except Exception as e:
                            logging.debug(f"Error processing device {device.device_node}: {e}")
                            
                except ImportError:
                    # Fallback to basic detection
                    import glob
                    for device in glob.glob("/dev/sd*"):
                        if not device[-1].isdigit():  # Skip partitions
                            devices.append({
                                'path': device,
                                'type': "Removable",
                                'mount_point': "Not Mounted",
                                'size': "Unknown",
                                'status': "Available"
                            })
                    
        except Exception as e:
            logging.error(f"Error getting removable devices: {e}")
            
        return devices

    # Command and Flow Management
    def add_context_menu_actions(self, menu, device_path, device_type):
        """Add device-specific actions to context menu"""
        # Recovery options
        recovery_menu = menu.addMenu("Recovery Options")
        recovery_menu.addAction("Scan Device", lambda: self.scan_device(device_path))
        recovery_menu.addAction("Deep Search", lambda: self.deep_search(device_path))

        # Nix store actions if applicable
        if device_path.startswith(self.nix_store_path):
            nix_menu = menu.addMenu("Nix Operations")
            nix_menu.addAction("Show Dependencies", lambda: self.show_nix_dependencies(device_path))
            nix_menu.addAction("Show Referrers", lambda: self.show_nix_referrers(device_path))
            nix_menu.addAction("Show Tree", lambda: self.show_nix_tree(device_path))

        # Regular commands
        if self.commands:
            cmd_menu = menu.addMenu("Commands")
            for cmd in self.commands:
                if cmd.device_type == "*" or cmd.device_type == device_type:
                    cmd_menu.addAction(cmd.name, 
                        lambda c=cmd: self.execute_command(c, device_path))

        # Flows
        if self.flows:
            flow_menu = menu.addMenu("Flows")
            for flow in self.flows:
                flow_menu.addAction(flow.name,
                    lambda f=flow: self.execute_flow(f, device_path))

    # Device Operations
    def mount_device(self, device_path):
        """Mount a device with proper error handling and permissions"""
        try:
            # Use udisksctl for mounting instead of direct mount
            result = subprocess.run(
                ['udisksctl', 'mount', '-b', device_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Parse mount point from udisksctl output
                mount_point = result.stdout.strip().split("at ")[-1].strip('.')
                self.mount_count += 1
                self.mounted_devices[device_path] = mount_point
                return mount_point
            else:
                self.error_count += 1
                self.last_error = result.stderr
                raise Exception(f"Mount failed: {result.stderr}")
                
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logging.error(f"Error mounting device {device_path}: {e}")
            raise

    def unmount_device(self, device_path):
        """Unmount a device"""
        try:
            if os.name == 'posix':  # Linux
                result = subprocess.run(
                    ['sudo', 'umount', device_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return True
                else:
                    raise Exception(result.stderr)
            else:
                # Windows implementation
                pass
                
        except Exception as e:
            logging.error(f"Error unmounting device {device_path}: {e}")
            raise

    # File Operations and Recovery
    def scan_device(self, device_path):
        """Scan device for recoverable files"""
        try:
            # Basic scan implementation
            result = subprocess.run(
                ['sudo', 'fdisk', '-l', device_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout
            else:
                raise Exception(result.stderr)
        except Exception as e:
            logging.error(f"Error scanning device {device_path}: {e}")
            raise

    def deep_search(self, device_path):
        """Perform deep file search"""
        try:
            # Basic deep search implementation
            result = subprocess.run(
                ['sudo', 'testdisk', device_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout
            else:
                raise Exception(result.stderr)
        except Exception as e:
            logging.error(f"Error performing deep search on {device_path}: {e}")
            raise

    # Data Management
    def load_commands(self):
        """Load saved commands"""
        try:
            if os.path.exists("device_commands.json"):
                with open("device_commands.json", "r") as f:
                    data = json.load(f)
                    self.commands = [DeviceCommand.from_dict(cmd) for cmd in data]
        except Exception as e:
            logging.error(f"Error loading commands: {e}")
            self.commands = []

    def save_commands(self):
        """Save commands to file"""
        try:
            with open("device_commands.json", "w") as f:
                json.dump([cmd.to_dict() for cmd in self.commands], f)
        except Exception as e:
            logging.error(f"Error saving commands: {e}")

    def load_flows(self):
        """Load saved flows"""
        try:
            if os.path.exists("device_flows.json"):
                with open("device_flows.json", "r") as f:
                    data = json.load(f)
                    self.flows = [DeviceFlow.from_dict(flow) for flow in data]
        except Exception as e:
            logging.error(f"Error loading flows: {e}")
            self.flows = []

    def add_command(self):
        """Add a new device command"""
        try:
            dialog = QDialog()
            dialog.setWindowTitle("Add Device Command")
            layout = QVBoxLayout()

            # Command inputs
            name_layout = QHBoxLayout()
            name_label = QLabel("Name:")
            name_input = QLineEdit()
            name_layout.addWidget(name_label)
            name_layout.addWidget(name_input)

            cmd_layout = QHBoxLayout()
            cmd_label = QLabel("Command:")
            cmd_input = QLineEdit()
            cmd_layout.addWidget(cmd_label)
            cmd_layout.addWidget(cmd_input)

            type_layout = QHBoxLayout()
            type_label = QLabel("Device Type:")
            type_input = QComboBox()
            type_input.addItems(["*", "USB", "Removable", "Fixed"])
            type_layout.addWidget(type_label)
            type_layout.addWidget(type_input)

            # Add to layout
            layout.addLayout(name_layout)
            layout.addLayout(cmd_layout)
            layout.addLayout(type_layout)

            # Buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | 
                QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            dialog.setLayout(layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                command = DeviceCommand(
                    name_input.text(),
                    cmd_input.text(),
                    type_input.currentText()
                )
                self.commands.append(command)
                self.save_commands()
                return True
            return False
                
        except Exception as e:
            logging.error(f"Error adding command: {e}")
            return False

    def execute_command(self, command: DeviceCommand, device_path: str):
        """Execute a device command"""
        try:
            # Replace placeholders in command
            cmd = command.command.replace("{device}", device_path)
            
            # Execute command
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                logging.info(f"Command '{command.name}' executed successfully")
                return True
            else:
                logging.error(f"Command failed: {result.stderr}")
                raise Exception(result.stderr)
                
        except Exception as e:
            logging.error(f"Error executing command: {e}")
            raise

    def execute_flow(self, flow: DeviceFlow, device_path: str):
        """Execute a device flow"""
        try:
            for step in flow.steps:
                self.execute_command(step, device_path)
            return True
        except Exception as e:
            logging.error(f"Error executing flow: {e}")
            raise
