from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, 
    QHBoxLayout, QMenu, QMessageBox, QStatusBar, QLineEdit, QLabel
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from HMC.device_manager import DeviceManager
from DEV.devices.device_flows import FlowManagerDialog
import logging

class DeviceManagerView(QWidget):
    device_mounted = pyqtSignal(str, str)
    device_unmounted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_manager = DeviceManager()
        self.setup_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_devices)
        self.refresh_timer.start(5000)

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.add_command_btn = QPushButton("Add Command")
        self.add_command_btn.clicked.connect(self.device_manager.add_command)
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
        
        # Add status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        # Add search/filter
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter devices...")
        self.filter_input.textChanged.connect(self.filter_devices)
        layout.insertWidget(0, self.filter_input)
        
        # Add device stats
        self.stats_label = QLabel()
        self.update_stats()
        toolbar.addWidget(self.stats_label)
        
        self.setLayout(layout)
        
        self.refresh_devices()

    def refresh_devices(self):
        """Update device list in UI"""
        self.device_tree.clear()
        devices = self.device_manager.get_devices()
        for device in devices:
            item = QTreeWidgetItem([
                device['path'],
                device['type'],
                device['mount_point'],
                device['size'],
                device['status']
            ])
            self.device_tree.addTopLevelItem(item)

    def show_context_menu(self, position):
        """Show context menu for device item"""
        item = self.device_tree.itemAt(position)
        if not item:
            return
        
        # Create menu
        menu = QMenu(self)
        device_path = item.toolTip(0)  # Get device path from tooltip
        is_mounted = item.text(4).lower() == 'mounted'
        
        # Add mount/unmount actions based on current state
        if not is_mounted:
            mount_action = menu.addAction("Mount")
            mount_action.triggered.connect(
                lambda: self.handle_mount(device_path)
            )
        else:
            unmount_action = menu.addAction("Unmount")
            unmount_action.triggered.connect(
                lambda: self.handle_unmount(device_path)
            )
        
        # Add properties action
        properties_action = menu.addAction("Properties")
        properties_action.triggered.connect(
            lambda: self.show_properties(device_path)
        )
        
        # Show the menu at the given position
        menu.popup(self.device_tree.viewport().mapToGlobal(position))
        return menu  # Return menu for testing purposes

    def handle_mount(self, device_path):
        """Handle mount action"""
        try:
            mount_point = self.device_manager.mount_device(device_path)
            if mount_point:
                self.device_mounted.emit(device_path, mount_point)
                self.refresh_devices()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to mount device: {e}")

    def handle_unmount(self, device_path):
        """Handle unmount action"""
        try:
            if self.device_manager.unmount_device(device_path):
                self.device_unmounted.emit(device_path)
                self.refresh_devices()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to unmount device: {e}")

    def manage_flows(self):
        """Open flow manager dialog"""
        dialog = FlowManagerDialog(self)
        if dialog.exec():
            self.device_manager.load_flows()  # Reload flows after changes
        
    def update_stats(self):
        stats = self.device_manager.get_device_stats()
        self.stats_label.setText(
            f"Active: {stats['active_devices']} | "
            f"Mounted: {stats['total_mounts']}"
        )
        
    def filter_devices(self, text):
        """Filter devices based on search text"""
        search_text = text.lower()
        for i in range(self.device_tree.topLevelItemCount()):
            item = self.device_tree.topLevelItem(i)
            matches = any(
                search_text in item.text(col).lower()
                for col in range(item.columnCount())
            )
            item.setHidden(not matches)
        
    