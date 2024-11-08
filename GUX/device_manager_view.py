from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from DEV.devices.device_flows import FlowManagerDialog
import logging

class DeviceManagerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.flow_manager = None
        self.init_ui()
        
     
    def init_ui(self):
        """Initialize the UI components"""
        try:
            layout = QVBoxLayout(self)
            
            # Add flow management button
            flow_btn = QPushButton("Manage Device Flows", self)
            flow_btn.clicked.connect(self.manage_flows)
            layout.addWidget(flow_btn)
            
            # Add other UI components as needed
            self.setLayout(layout)
            
        except Exception as e:
            logging.error(f"Error initializing DeviceManagerView UI: {e}")
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