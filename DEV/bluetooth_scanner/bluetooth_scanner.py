import sys
import subprocess
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QListWidget, QVBoxLayout,
    QWidget, QMessageBox, QLabel, QHBoxLayout, QWizard
)
from PyQt6.QtBluetooth import (
    QBluetoothDeviceDiscoveryAgent, QBluetoothDeviceInfo,
    QBluetoothLocalDevice
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from bluetooth_setup_wizard import SetupWizard
import signal


class BluetoothManager(QObject):
    # Define signals for communication
    status_changed = pyqtSignal(str)
    device_discovered = pyqtSignal(QBluetoothDeviceInfo)
    scan_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Initialize Bluetooth devices
        self.local_device = QBluetoothLocalDevice(self)
        self.agent = QBluetoothDeviceDiscoveryAgent(self)
        self.devices = {}

        # Connect signals
        self.agent.deviceDiscovered.connect(self._on_device_discovered)
        self.agent.finished.connect(self._on_scan_finished)
        self.agent.errorOccurred.connect(self._on_error)  # Changed from error to errorOccurred

        # Initialize Bluetooth if needed
        if self.local_device.hostMode() == QBluetoothLocalDevice.HostMode.HostPoweredOff:
            self.local_device.powerOn()
            self.status_changed.emit("Turning Bluetooth on...")

    def start_scan(self):
        """Start scanning for Bluetooth devices"""
        if self.agent.isActive():
            self.status_changed.emit("Scan already in progress...")
            return

        self.devices.clear()
        self.status_changed.emit("Scanning for Bluetooth devices...")
        self.agent.start()

    def stop_scan(self):
        """Stop the current scan"""
        if self.agent.isActive():
            self.agent.stop()
            self.status_changed.emit("Scan stopped")

    def _on_device_discovered(self, device: QBluetoothDeviceInfo):
        """Handle discovered device"""
        if device.address().toString() not in self.devices:
            self.devices[device.address().toString()] = device
            self.device_discovered.emit(device)

    def _on_scan_finished(self):
        """Handle scan completion"""
        if not self.devices:
            self.status_changed.emit("No Bluetooth devices found.")
        else:
            self.status_changed.emit(f"Found {len(self.devices)} device(s).")
        self.scan_finished.emit()

    def _on_error(self, error):
        """Handle Bluetooth errors"""
        error_messages = {
            QBluetoothDeviceDiscoveryAgent.Error.NoError: "No error",
            QBluetoothDeviceDiscoveryAgent.Error.PoweredOffError: "Bluetooth is powered off",
            QBluetoothDeviceDiscoveryAgent.Error.InputOutputError: "Bluetooth IO error",
            QBluetoothDeviceDiscoveryAgent.Error.InvalidBluetoothAdapterError: "Invalid Bluetooth adapter",
            QBluetoothDeviceDiscoveryAgent.Error.UnsupportedPlatformError: "Unsupported platform",
            QBluetoothDeviceDiscoveryAgent.Error.UnsupportedDiscoveryMethod: "Unsupported discovery method",
            QBluetoothDeviceDiscoveryAgent.Error.UnknownError: "Unknown error occurred"
        }
        error_msg = error_messages.get(error, "Unknown error occurred")
        self.status_changed.emit(f"Error: {error_msg}")

    def connect_device(self, device_address):
        """Connect to a Bluetooth device"""
        try:
            self.status_changed.emit(f"Attempting to connect to {device_address}...")
            # Use bluetoothctl for Linux systems
            subprocess.run(["bluetoothctl", "connect", device_address], check=True)
            self.status_changed.emit(f"Connected to {device_address}.")
        except Exception as e:
            self.status_changed.emit(f"Failed to connect: {str(e)}")
            QMessageBox.critical(None, "Connection Error", f"Failed to connect: {str(e)}")

    def disconnect_device(self, device_address):
        """Disconnect from a Bluetooth device"""
        try:
            self.status_changed.emit(f"Disconnecting from {device_address}...")
            # Use bluetoothctl for Linux systems
            subprocess.run(["bluetoothctl", "disconnect", device_address], check=True)
            self.status_changed.emit(f"Disconnected from {device_address}.")
        except Exception as e:
            self.status_changed.emit(f"Failed to disconnect: {str(e)}")
            QMessageBox.critical(None, "Disconnection Error", f"Failed to disconnect: {str(e)}")

    def restart_bluetooth_service(self):
        """Restart the Bluetooth service"""
        try:
            self.status_changed.emit("Restarting Bluetooth service...")
            # Use dbus-send instead of pkexec
            subprocess.run([
                "dbus-send", "--system", "--print-reply",
                "--dest=org.freedesktop.systemd1",
                "/org/freedesktop/systemd1",
                "org.freedesktop.systemd1.Manager.RestartUnit",
                "string:bluetooth.service", "string:replace"
            ], check=True)
            self.status_changed.emit("Bluetooth service restarted successfully.")
            # Wait a moment before starting a new scan
            QTimer.singleShot(2000, self.start_scan)
        except Exception as e:
            self.status_changed.emit(f"Failed to restart Bluetooth service: {str(e)}")
            QMessageBox.critical(None, "Service Error", f"Failed to restart service: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bluetooth Scanner (Manjaro)")
        self.setGeometry(100, 100, 600, 400)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        # Scan button
        self.scan_button = QPushButton("Scan for Devices")
        self.scan_button.clicked.connect(self.toggle_scan)
        layout.addWidget(self.scan_button)

        # Device list
        self.device_list = QListWidget()
        layout.addWidget(self.device_list)

        # Connect and Disconnect buttons
        btn_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_device)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_device)
        btn_layout.addWidget(self.connect_button)
        btn_layout.addWidget(self.disconnect_button)
        layout.addLayout(btn_layout)

        # Restart Bluetooth button
        self.restart_button = QPushButton("Restart Bluetooth")
        self.restart_button.clicked.connect(self.restart_bluetooth)
        layout.addWidget(self.restart_button)

        # Initialize bluetooth manager
        self.bluetooth_manager = BluetoothManager(self)
        self.bluetooth_manager.status_changed.connect(self.update_status)
        self.bluetooth_manager.device_discovered.connect(self.on_device_discovered)
        self.bluetooth_manager.scan_finished.connect(self.on_scan_finished)

        self.scanning = False

    def toggle_scan(self):
        """Toggle scanning on/off"""
        if not self.scanning:
            self.device_list.clear()
            self.scan_button.setText("Stop Scan")
            self.bluetooth_manager.start_scan()
            self.scanning = True
        else:
            self.bluetooth_manager.stop_scan()
            self.scan_button.setText("Scan for Devices")
            self.scanning = False

    def on_device_discovered(self, device_info):
        """Handle discovered device"""
        device_name = device_info.name() or "Unknown Device"
        address = device_info.address().toString()
        self.device_list.addItem(f"{device_name} ({address})")

    def on_scan_finished(self):
        """Handle scan completion"""
        self.scan_button.setText("Scan for Devices")
        self.scanning = False

    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(f"Status: {message}")

    def get_selected_device_address(self):
        """Get the address of the selected device"""
        selected = self.device_list.currentItem()
        if selected:
            try:
                # Extract address from item text (format: "Device Name (XX:XX:XX:XX:XX:XX)")
                return selected.text().split("(")[1].strip(")")
            except IndexError:
                return None
        return None

    def connect_device(self):
        """Connect to selected device"""
        device_address = self.get_selected_device_address()
        if device_address:
            self.bluetooth_manager.connect_device(device_address)
        else:
            QMessageBox.warning(self, "No Selection", "Please select a device to connect.")

    def disconnect_device(self):
        """Disconnect from selected device"""
        device_address = self.get_selected_device_address()
        if device_address:
            self.bluetooth_manager.disconnect_device(device_address)
        else:
            QMessageBox.warning(self, "No Selection", "Please select a device to disconnect.")

    def restart_bluetooth(self):
        """Restart Bluetooth service"""
        reply = QMessageBox.question(
            self,
            "Restart Bluetooth",
            "Are you sure you want to restart the Bluetooth service?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.bluetooth_manager.restart_bluetooth_service()

    def closeEvent(self, event):
        """Handle application closure"""
        self.bluetooth_manager.stop_scan()
        super().closeEvent(event)


def check_bluetooth_setup():
    """Check if Bluetooth is properly configured"""
    try:
        # Check if user is in bluetooth group
        groups = subprocess.check_output(['groups'], text=True).split()
        if 'bluetooth' not in groups:
            return False
        
        # Check if udev rules exist
        if not os.path.exists('/etc/udev/rules.d/51-bluetooth.rules'):
            return False
        
        # Check if polkit rules exist
        if not os.path.exists('/etc/polkit-1/rules.d/81-bluetooth-manage.rules'):
            return False
        
        # Check Python capabilities
        python_path = subprocess.check_output(['poetry', 'run', 'which', 'python'],
                                            text=True).strip()
        try:
            caps = subprocess.check_output(['getcap', python_path], text=True).strip()
            if not caps or 'cap_net_admin' not in caps:
                return False
        except subprocess.CalledProcessError:
            return False
        
        return True
    except Exception as e:
        print(f"Setup check failed: {e}")
        return False


def main():
    # Setup signal handling
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Enable Ctrl+C handling
    
    app = QApplication(sys.argv)
    
    # Check if setup is needed
    if not check_bluetooth_setup():
        reply = QMessageBox.question(
            None,
            "Bluetooth Setup Required",
            "Bluetooth permissions need to be configured. Would you like to run the setup wizard?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            wizard = SetupWizard()
            if wizard.exec() == QWizard.DialogCode.Rejected:
                return
            QMessageBox.information(
                None,
                "Setup Complete",
                "Please log out and log back in for changes to take effect."
            )
            return
        else:
            QMessageBox.warning(
                None,
                "Setup Skipped",
                "The application may not work correctly without proper setup."
            )
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
