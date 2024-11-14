import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from HMC.device_manager import DeviceManager

class TestDeviceManager(unittest.TestCase):
    def setUp(self):
        self.dm = DeviceManager()

    def test_device_manager_initialization(self):
        """Test basic initialization"""
        self.assertEqual(self.dm.commands, [])
        self.assertEqual(self.dm.flows, [])
        self.assertEqual(self.dm.mount_count, 0)
        self.assertEqual(self.dm.error_count, 0)
        self.assertIsNone(self.dm.last_error)

    @patch('subprocess.run')
    def test_mount_device(self, mock_run):
        """Test device mounting using udisksctl"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Mounted /dev/sdb1 at /run/media/user/DEVICE."
        )
        
        result = self.dm.mount_device('/dev/sdb1')
        self.assertEqual(result, "/run/media/user/DEVICE")
        mock_run.assert_called_once_with(
            ['udisksctl', 'mount', '-b', '/dev/sdb1'],
            capture_output=True,
            text=True
        )

if __name__ == '__main__':
    unittest.main() 