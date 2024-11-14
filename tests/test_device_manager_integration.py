import unittest
import sys
import os
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem, QMenu
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QPoint
from unittest.mock import patch, Mock
# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from GUX.device_manager_view import DeviceManagerView
from HMC.device_manager import DeviceManager

class TestDeviceManagerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create the application once for all tests"""
        cls.app = QApplication([])

    def setUp(self):
        """Create a fresh widget for each test"""
        # Mock device manager to avoid actual device operations
        with patch('HMC.device_manager.DeviceManager') as mock_dm:
            mock_dm.return_value.get_device_stats.return_value = {
                'total_mounts': 0,
                'failed_mounts': 0,
                'last_error': None,
                'active_devices': 0
            }
            self.view = DeviceManagerView()
            
        # Add test data
        self.add_test_items()

    def add_test_items(self):
        """Add test items to the device tree"""
        self.view.device_tree.clear()
        test_items = [
            ['test1', 'usb', '/dev/sdb1', '1GB', 'unmounted'],
            ['test2', 'ssd', '/dev/sdc1', '2GB', 'mounted']
        ]
        for item_data in test_items:
            item = QTreeWidgetItem(item_data)
            item.setToolTip(0, item_data[2])  # Set device path as tooltip
            self.view.device_tree.addTopLevelItem(item)

    def test_device_manager_view_initialization(self):
        """Test basic UI initialization"""
        self.assertIsNotNone(self.view.device_manager)
        self.assertIsNotNone(self.view.device_tree)
        self.assertTrue(self.view.refresh_timer.isActive())

    def test_context_menu_creation(self):
        """Test context menu creation"""
        # Add test device data
        self.view.device_tree.clear()
        test_item = QTreeWidgetItem(['test_device', 'usb', '/dev/sdb1', '1GB', 'unmounted'])
        test_item.setToolTip(0, '/dev/sdb1')  # Set device path as tooltip
        self.view.device_tree.addTopLevelItem(test_item)
        
        # Create menu manually for testing
        menu = QMenu(self.view)
        
        # Add test actions
        mount_action = menu.addAction("Mount")
        unmount_action = menu.addAction("Unmount")
        properties_action = menu.addAction("Properties")
        
        # Mock the exec method to prevent actual menu display
        with patch.object(QMenu, 'exec') as mock_exec:
            # Get position for menu
            rect = self.view.device_tree.visualItemRect(test_item)
            pos = rect.center()
            
            # Show context menu
            self.view.show_context_menu(pos)
            
            # Verify menu was created and shown
            mock_exec.assert_called_once()
            
            # Get the menu from the show_context_menu call
            actual_menu = self.view.device_tree.findChild(QMenu)
            self.assertIsNotNone(actual_menu, "Context menu not created")
            
            # Verify menu actions
            actions = actual_menu.actions()
            action_texts = [a.text() for a in actions]
            
            expected_actions = ["Mount", "Unmount", "Properties"]
            for expected in expected_actions:
                self.assertTrue(
                    any(expected in text for text in action_texts),
                    f"Missing expected action: {expected}"
                )

    def test_filter_functionality(self):
        """Test device filtering"""
        # Clear existing items
        self.view.device_tree.clear()
        
        # Add test items
        test_items = [
            ['test1', 'usb', '/mnt/test1', '1GB', 'mounted'],
            ['test2', 'ssd', '/mnt/test2', '2GB', 'mounted']
        ]
        for item_data in test_items:
            self.view.device_tree.addTopLevelItem(
                QTreeWidgetItem(item_data)
            )
        
        # Test filter
        self.view.filter_input.setText('test1')
        QTest.qWait(100)  # Wait for filter to apply
        
        visible_count = sum(
            1 for i in range(self.view.device_tree.topLevelItemCount())
            if not self.view.device_tree.topLevelItem(i).isHidden()
        )
        self.assertEqual(visible_count, 1)

    def tearDown(self):
        """Clean up after each test"""
        self.view.deleteLater()
        QTest.qWait(0)  # Process pending events

    @classmethod
    def tearDownClass(cls):
        """Clean up the application"""
        cls.app.quit()

if __name__ == '__main__':
    unittest.main()