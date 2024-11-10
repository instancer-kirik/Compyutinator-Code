from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget
from DEV.devices.device_flows import FlowManagerDialog
# from DEV.devices.device_manager import DeviceManager
import logging

class DeviceManagerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize required attributes
        self.manage_flows = True
        self.flow_manager = None
        self.device_manager = None
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Add your UI components here
        self.device_list = QListWidget()
        self.layout.addWidget(self.device_list)
        
        # Initialize device manager
        self.init_device_manager()
        
    def init_device_manager(self):
        try:
            # Initialize device manager
           # self.device_manager = DeviceManager()
            logging.info("Device manager initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize device manager: {e}")
    def manage_flows(self):
        """Handle device flow management"""
        try:
            if not self.flow_manager:
                self.flow_manager = FlowManagerDialog(self)
            self.flow_manager.exec()
        except Exception as e:
            logging.error(f"Error managing flows: {e}")
                  
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.flow_manager:
                self.flow_manager.close()
                self.flow_manager.deleteLater()
            logging.info("DeviceManagerView cleanup completed")
        except Exception as e:
            logging.error(f"Error cleaning up DeviceManagerView: {e}")