from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QLabel
)
from PyQt6.QtCore import Qt
import json
import logging
from .device_manager import DeviceCommand  # Import from device_manager

class DeviceFlow:
    def __init__(self, name, steps):
        self.name = name
        self.steps = steps  # List of DeviceCommand objects
        
    def to_dict(self):
        return {
            "name": self.name,
            "steps": [step.to_dict() for step in self.steps]
        }
        
    @staticmethod
    def from_dict(data):
        steps = [DeviceCommand.from_dict(step) for step in data["steps"]]
        return DeviceFlow(data["name"], steps)

class FlowManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Flow Manager")
        self.flows = []
        self.load_flows()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Flow list
        self.flow_list = QTreeWidget()
        self.flow_list.setHeaderLabels(["Flow Name", "Steps"])
        self.refresh_flows()
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Flow")
        add_btn.clicked.connect(self.add_flow)
        edit_btn = QPushButton("Edit Flow")
        edit_btn.clicked.connect(self.edit_flow)
        delete_btn = QPushButton("Delete Flow")
        delete_btn.clicked.connect(self.delete_flow)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        
        layout.addWidget(self.flow_list)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def load_flows(self):
        """Load saved flows"""
        try:
            with open("device_flows.json", "r") as f:
                data = json.load(f)
                self.flows = [DeviceFlow.from_dict(flow) for flow in data]
        except FileNotFoundError:
            logging.info("No saved flows found")
        except Exception as e:
            logging.error(f"Error loading flows: {e}")
            
    def save_flows(self):
        """Save flows to file"""
        try:
            with open("device_flows.json", "w") as f:
                json.dump([flow.to_dict() for flow in self.flows], f)
        except Exception as e:
            logging.error(f"Error saving flows: {e}")
            
    def refresh_flows(self):
        """Refresh the flow list display"""
        self.flow_list.clear()
        for flow in self.flows:
            item = QTreeWidgetItem([flow.name])
            for step in flow.steps:
                step_item = QTreeWidgetItem([f"→ {step.name}"])
                item.addChild(step_item)
            self.flow_list.addTopLevelItem(item)
            
    def add_flow(self):
        """Add a new flow"""
        from .flow_editor_dialog import FlowEditorDialog  # Import here to avoid circular imports
        dialog = FlowEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.flows.append(dialog.flow)
            self.save_flows()
            self.refresh_flows()
            
    def edit_flow(self):
        """Edit selected flow"""
        selected = self.flow_list.currentItem()
        if selected and selected.parent() is None:  # Only top-level items
            flow_index = self.flow_list.indexOfTopLevelItem(selected)
            if 0 <= flow_index < len(self.flows):
                from .flow_editor_dialog import FlowEditorDialog
                dialog = FlowEditorDialog(self, self.flows[flow_index])
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.flows[flow_index] = dialog.flow
                    self.save_flows()
                    self.refresh_flows()
                    
    def delete_flow(self):
        """Delete selected flow"""
        selected = self.flow_list.currentItem()
        if selected and selected.parent() is None:
            flow_index = self.flow_list.indexOfTopLevelItem(selected)
            if 0 <= flow_index < len(self.flows):
                self.flows.pop(flow_index)
                self.save_flows()
                self.refresh_flows()