import os
import sys
import subprocess
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QLabel, QVBoxLayout, QApplication,
    QPushButton, QProgressBar, QMessageBox, QCheckBox, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer

class SetupWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bluetooth Setup Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        # Add pages
        self.addPage(IntroPage())
        self.permissions_page = PermissionsPage()
        self.addPage(self.permissions_page)
        self.addPage(CompletionPage())
        
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # Remove the back button on the permissions page
        self.setOption(QWizard.WizardOption.DisabledBackButtonOnLastPage, True)

class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Bluetooth Setup Wizard")
        self.setSubTitle("This wizard will help you configure Bluetooth permissions")
        
        layout = QVBoxLayout()
        intro_text = QLabel(
            "This wizard will perform the following tasks:\n\n"
            "1. Configure Bluetooth permissions\n"
            "2. Add user to bluetooth group\n"
            "3. Create necessary udev rules\n"
            "4. Configure PolicyKit rules\n"
            "5. Restart Bluetooth service\n\n"
            "Note: Some steps require administrator privileges."
        )
        intro_text.setWordWrap(True)
        layout.addWidget(intro_text)
        self.setLayout(layout)

class PermissionsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Bluetooth Permissions")
        self.setSubTitle("Setting up Bluetooth permissions")
        
        # Define the rules as class attributes
        self.udev_rules = '''# Bluetooth devices
SUBSYSTEM=="bluetooth", MODE="0666", GROUP="bluetooth"
SUBSYSTEM=="hidraw", MODE="0666", GROUP="bluetooth"
KERNEL=="hidraw*", MODE="0666", GROUP="bluetooth"
'''
        
        # Update polkit rules to include DBus permissions
        self.polkit_rules = '''polkit.addRule(function(action, subject) {
    if ((action.id == "org.bluez.agent.capability") ||
        (action.id == "org.bluez.device.capability") ||
        (action.id == "org.freedesktop.systemd1.manage-units") ||
        (action.id == "org.bluez.profile.input") ||
        (action.id == "org.freedesktop.login1.power-off") ||
        (action.id == "org.freedesktop.login1.reboot")) {
        return polkit.Result.YES;
    }
});
'''
        
        self.layout = QVBoxLayout()
        self.progress = QProgressBar()
        self.status_label = QLabel("Ready to configure permissions...")
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.progress)
        self.setLayout(self.layout)
        
        self.tasks_completed = False

    def initializePage(self):
        QTimer.singleShot(0, self.setup_permissions)

    def setup_permissions(self):
        try:
            self.status_label.setText("Preparing setup files...")
            self.progress.setValue(10)
            
            username = os.getenv('USER')
            python_path = os.path.realpath(subprocess.check_output(
                ['poetry', 'run', 'which', 'python'],
                text=True
            ).strip())
            
            # Consolidate all privileged operations into a single script
            setup_script = f'''#!/bin/bash
set -e

# Enable and restart bluetooth service
systemctl enable bluetooth
systemctl restart bluetooth

# Create udev rules
cat > /etc/udev/rules.d/51-bluetooth.rules << 'EOL'
{self.udev_rules}
EOL

# Create PolicyKit rules
cat > /etc/polkit-1/rules.d/81-bluetooth-manage.rules << 'EOL'
{self.polkit_rules}
EOL

# Add user to bluetooth and systemd-journal groups
usermod -aG bluetooth,systemd-journal "{username}"

# Set capabilities on Python interpreter
setcap -r "{python_path}" 2>/dev/null || true
setcap "cap_net_admin,cap_net_raw,cap_dac_override+eip" "{python_path}"

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Set proper permissions
chmod 644 /etc/udev/rules.d/51-bluetooth.rules
chmod 644 /etc/polkit-1/rules.d/81-bluetooth-manage.rules

# Ensure DBus configuration
mkdir -p /etc/dbus-1/system.d/
cat > /etc/dbus-1/system.d/bluetooth.conf << 'EOL'
<?xml version="1.0" encoding="UTF-8"?>
<busconfig>
  <policy user="{username}">
    <allow send_destination="org.bluez"/>
    <allow send_interface="org.bluez.Agent1"/>
    <allow send_interface="org.bluez.MediaEndpoint1"/>
    <allow send_interface="org.bluez.MediaPlayer1"/>
    <allow send_interface="org.bluez.ThermometerWatcher1"/>
    <allow send_interface="org.bluez.AlertAgent1"/>
    <allow send_interface="org.bluez.Profile1"/>
    <allow send_interface="org.bluez.HeartRateWatcher1"/>
    <allow send_interface="org.bluez.CyclingSpeedWatcher1"/>
    <allow send_interface="org.freedesktop.systemd1.Manager"/>
  </policy>
</busconfig>
EOL

# Restart DBus to apply changes
systemctl restart dbus

# Configure HID service
cat > /etc/dbus-1/system.d/bluetooth-hid.conf << 'EOL'
<?xml version="1.0" encoding="UTF-8"?>
<busconfig>
  <policy user="{username}">
    <allow send_destination="org.bluez"/>
    <allow send_interface="org.bluez.Input1"/>
    <allow send_interface="org.bluez.Profile1"/>
    <allow send_interface="org.bluez.Device1"/>
    <allow send_interface="org.bluez.Agent1"/>
  </policy>
</busconfig>
EOL

# Enable HID support in Bluetooth daemon
sed -i 's/#Experimental = false/Experimental = true/' /etc/bluetooth/main.conf
echo 'Enable=Source,Sink,Media,Socket' >> /etc/bluetooth/main.conf
'''

            self.progress.setValue(30)
            self.status_label.setText("Creating setup script...")

            # Write the setup script
            with open('/tmp/bluetooth_setup.sh', 'w') as f:
                f.write(setup_script)
            os.chmod('/tmp/bluetooth_setup.sh', 0o755)

            self.progress.setValue(50)
            self.status_label.setText("Running setup script...")

            # Run single privileged command
            result = subprocess.run(
                ['pkexec', '/tmp/bluetooth_setup.sh'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise Exception(f"Setup failed: {result.stderr}")

            self.progress.setValue(100)
            self.status_label.setText("Setup completed successfully!")
            self.tasks_completed = True

            # Remove the next/back buttons for this page
            self.wizard().setOption(QWizard.WizardOption.HaveCustomButton1, False)
            self.wizard().setOption(QWizard.WizardOption.HaveNextButtonOnLastPage, False)

            # Automatically move to completion page
            QTimer.singleShot(1000, lambda: self.wizard().next())

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to configure permissions:\n{str(e)}")
            self.status_label.setText("Error configuring permissions!")
            return

    def isComplete(self):
        return self.tasks_completed

    def nextId(self):
        # Skip directly to completion page
        return self.wizard().pageIds()[-1]

class GroupsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("User Groups")
        self.setSubTitle("Adding user to bluetooth group")
        
        self.layout = QVBoxLayout()
        self.progress = QProgressBar()
        self.status_label = QLabel("Ready to configure groups...")
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.progress)
        self.setLayout(self.layout)
        
        self.tasks_completed = False

    def initializePage(self):
        QTimer.singleShot(0, self.setup_groups)

    def setup_groups(self):
        try:
            self.status_label.setText("Adding user to bluetooth group...")
            self.progress.setValue(50)
            
            username = os.getenv('USER')
            subprocess.run(['pkexec', 'usermod', '-aG', 'bluetooth', username], check=True)
            
            self.progress.setValue(100)
            self.status_label.setText("User added to bluetooth group successfully!")
            self.tasks_completed = True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to configure groups: {str(e)}")
            self.status_label.setText("Error configuring groups!")
            return

    def isComplete(self):
        return self.tasks_completed

class ServicePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Bluetooth Service")
        self.setSubTitle("Configuring Bluetooth service")
        
        self.layout = QVBoxLayout()
        self.progress = QProgressBar()
        self.status_label = QLabel("Ready to configure service...")
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.progress)
        self.setLayout(self.layout)
        
        self.tasks_completed = False

    def initializePage(self):
        QTimer.singleShot(0, self.setup_service)

    def setup_service(self):
        try:
            self.status_label.setText("Enabling Bluetooth service...")
            self.progress.setValue(33)
            
            subprocess.run(['pkexec', 'systemctl', 'enable', 'bluetooth'], check=True)
            
            self.progress.setValue(66)
            self.status_label.setText("Starting Bluetooth service...")
            
            subprocess.run(['pkexec', 'systemctl', 'restart', 'bluetooth'], check=True)
            
            self.progress.setValue(100)
            self.status_label.setText("Bluetooth service configured successfully!")
            self.tasks_completed = True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to configure service: {str(e)}")
            self.status_label.setText("Error configuring service!")
            return

    def isComplete(self):
        return self.tasks_completed

class CompletionPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle("Bluetooth configuration has been completed")
        
        layout = QVBoxLayout()
        completion_text = QLabel(
            "The Bluetooth configuration has been completed.\n\n"
            "You can either restart your computer now for changes to take effect,\n"
            "or continue to the Bluetooth Scanner (some features may require a restart)."
        )
        completion_text.setWordWrap(True)
        layout.addWidget(completion_text)
        
        # Add buttons layout
        button_layout = QHBoxLayout()
        
        self.restart_checkbox = QCheckBox("Restart computer now")
        button_layout.addWidget(self.restart_checkbox)
        
        self.start_scanner_btn = QPushButton("Start Scanner")
        self.start_scanner_btn.clicked.connect(self.start_scanner)
        button_layout.addWidget(self.start_scanner_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def start_scanner(self):
        # Close the wizard
        self.wizard().accept()
        # Import and start the scanner
        from .bluetooth_scanner import MainWindow
        self.scanner_window = MainWindow()
        self.scanner_window.show()

    def validatePage(self):
        if self.restart_checkbox.isChecked():
            reply = QMessageBox.question(
                self,
                "Restart Computer",
                "Are you sure you want to restart now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                subprocess.run(['pkexec', 'reboot'])
                return True
            return False
        return True

def main():
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
