import sys
import os
import re
import subprocess
import tempfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QComboBox, QTextEdit, QLabel, 
                            QFileDialog, QMessageBox, QGroupBox, QCheckBox,
                            QWizard, QWizardPage, QProgressBar, QSizePolicy)
from PyQt6.QtCore import QProcess, QSettings, QPropertyAnimation, QEasingCurve, QTimer, Qt, QPoint, QMimeData  # Added QMimeData here
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QTextCursor
from GUX.keyboard.keyboard_layout import KeyboardLayout  # Changed from relative import
class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Manager Setup")
        self.addPage(IntroPage())
        self.addPage(PermissionsPage())
        self.addPage(ConfigurationPage())

class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Keyboard Manager")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(
            "This wizard will help you set up your keyboard management system.\n\n"
            "We'll need to:\n"
            "1. Set up required permissions\n"
            "2. Configure your keyboard device\n"
            "3. Create initial KMonad configuration"
        ))
        self.setLayout(layout)

class PermissionsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("System Permissions")
        layout = QVBoxLayout()
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def initializePage(self):
        self.setup_permissions()

    def setup_permissions(self):
        try:
            # Create a temporary script to run all commands
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp:
                temp.write(f"""#!/bin/bash
# Load uinput module
modprobe uinput

# Create uinput group if it doesn't exist
groupadd -f uinput

# Set uinput permissions
chmod 0660 /dev/uinput
chown root:input /dev/uinput

# Add user to groups
usermod -aG input {os.environ['USER']}
usermod -aG uinput {os.environ['USER']}

# Create udev rules
cat > /etc/udev/rules.d/99-kmonad.rules << EOL
KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
EOL

# Reload udev rules
udevadm control --reload-rules
udevadm trigger
""")
                temp.flush()
                script_path = temp.name

            # Make the script executable
            os.chmod(script_path, 0o755)

            # Run the script with pkexec (single password prompt)
            self.status_label.setText("Setting up permissions...")
            subprocess.run(['pkexec', script_path], check=True)

            # Clean up
            os.unlink(script_path)

            self.status_label.setText(
                "Setup complete! You'll need to log out and back in for changes to take effect.\n"
                "Please ensure KMonad is installed before continuing."
            )
            
            # Update progress bar
            self.progress.setValue(self.progress.maximum())

        except Exception as e:
            QMessageBox.critical(self, "Setup Error", 
                f"Error during setup: {str(e)}\n\n"
                "Please ensure you have pkexec installed and proper permissions.")

class ConfigurationPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Keyboard Configuration")
        layout = QVBoxLayout()

        # Check for KMonad installation
        try:
            subprocess.run(['kmonad', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            layout.addWidget(QLabel(
                "<b>KMonad not found!</b><br><br>"
                "Please install KMonad before continuing. "
                "You can find installation instructions at: "
                "<a href='https://github.com/kmonad/kmonad#installation'>"
                "https://github.com/kmonad/kmonad#installation</a><br><br>"
                "After installing KMonad, restart this application."
            ))
            self.setLayout(layout)
            return

        # Rest of the configuration page setup
        self.device_label = QLabel("Select your keyboard:")
        self.device_combo = QComboBox()
        self.refresh_btn = QPushButton("Refresh Devices")
        self.refresh_btn.clicked.connect(self.populate_devices)
        
        # Config file creation
        self.config_label = QLabel("kbd Configuration:")
        self.config_edit = QTextEdit()
        self.config_edit.setPlainText(self.get_default_config())
        
        layout.addWidget(self.device_label)
        layout.addWidget(self.device_combo)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.config_label)
        layout.addWidget(self.config_edit)
        self.setLayout(layout)

    def populate_devices(self):
        self.device_combo.clear()
        try:
            result = subprocess.run(['libinput', 'list-devices'], capture_output=True, text=True)
            devices = result.stdout.split('\n\n')
            keyboard_devices = [d for d in devices if 'keyboard' in d.lower()]
            
            for device in keyboard_devices:
                device_info = device.split('\n')
                name = next((line.split(':')[1].strip() for line in device_info if 'Device:' in line), None)
                path = next((line.split(':')[1].strip() for line in device_info if 'Kernel:' in line), None)
                if name and path:
                    self.device_combo.addItem(f"{name} ({path})", path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading devices: {str(e)}")

    def get_default_config(self):
        return """(defcfg
  input (device-file "DEVICE_PATH")
  output (uinput-sink "kmonad-output")
  fallthrough true
)

(defsrc
  esc  f1   f2   f3   f4   f5   f6   f7   f8   f9   f10  f11  f12
  grv  1    2    3    4    5    6    7    8    9    0    -    =    bspc
  tab  q    w    e    r    t    y    u    i    o    p    [    ]    \\
  caps a    s    d    f    g    h    j    k    l    ;    '    ret
  lsft z    x    c    v    b    n    m    ,    .    /    rsft
  lctl lmet lalt           spc            ralt rmet cmp  rctl
)

(deflayer qwerty
  esc  f1   f2   f3   f4   f5   f6   f7   f8   f9   f10  f11  f12
  grv  1    2    3    4    5    6    7    8    9    0    -    =    bspc
  tab  q    w    e    r    t    y    u    i    o    p    [    ]    \\
  caps a    s    d    f    g    h    j    k    l    ;    '    ret
  lsft z    x    c    v    b    n    m    ,    .    /    rsft
  lctl lmet lalt           spc            ralt rmet cmp  rctl
)"""

class KeyboardManager(QMainWindow):
    def __init__(self):
        super().__init__()
        # Check for existing instance first
        if not self.ensure_single_instance():
            sys.exit(1)
            
        # Initialize UI components
        self.setWindowTitle("Keyboard Manager")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Initialize text outputs
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.config_edit = QTextEdit()
        
        # Initialize settings
        self.settings = QSettings("Compyutinator", "KeyboardManager")
        self.kmonad_config_path = self.settings.value("kmonad_config_path", "")
        self.autostart_enabled = self.settings.value("autostart_enabled", False, type=bool)
        
        # Initialize state variables
        self.kmonad_process = None
        self.is_kmonad_running = False
        self.kmonad_instances = []
        self.dragging_key = None
        self.drag_start_pos = None
      
        self.layers = {
            'src': [],  # Will be populated when config is loaded
            'base': []   # Default layer
        }
        self.current_layer = 'base'

        # Special key mappings
        self.special_key_map = {
            Qt.Key.Key_Backspace: 'bspc',
            Qt.Key.Key_Return: 'ret',
            Qt.Key.Key_Enter: 'ret',
            Qt.Key.Key_Tab: 'tab',
            Qt.Key.Key_Space: 'spc',
            Qt.Key.Key_Escape: 'esc',
            Qt.Key.Key_CapsLock: 'caps',
            Qt.Key.Key_Control: 'lctl',
            Qt.Key.Key_Alt: 'lalt',
            Qt.Key.Key_Meta: 'lmet',
            Qt.Key.Key_Shift: 'lsft',
        }
        
        # Create keyboard layout widget
        self.keyboard_layout = KeyboardLayout(self)
        
        # Add widgets to layout
        main_layout.addWidget(self.keyboard_layout)
        main_layout.addWidget(self.config_edit)
        main_layout.addWidget(self.output_text)
        
        # Setup UI and timers
        if not self.settings.value("setup_complete", False, type=bool):
            self.run_setup_wizard()
        else:
            self.setup_ui()
            
        # Create layer selector
        self.create_layer_selector()
        
        # Start status check timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.check_kmonad_status)
        self.status_timer.start(5000)
        
        # Force initial config save and update
        QTimer.singleShot(500, self.initial_setup)

    def initial_setup(self):
        """Ensure config is saved and up to date on startup"""
        if self.kmonad_config_path:
            self.save_config(silent=True)
            self.refresh_keyboard_list()
            self.apply_keyboard_selection()

    def ensure_single_instance(self):
        """Ensure only one instance of the app is running"""
        try:
            self.server = QLocalServer(self)
            socket = QLocalSocket(self)
            socket.connectToServer("CompyutinatorKmonadManager")
            
            if socket.waitForConnected(500):
                QMessageBox.warning(None, "Application Running",
                                  "An instance of Keyboard Manager is already running.")
                return False
                
            self.server.listen("CompyutinatorKmonadManager")
            return True
            
        except Exception as e:
            self.output_text.append(f"Error checking for existing instance: {e}")
            return False

    def check_kmonad_status(self):
        """Periodically check if KMonad instances are running"""
        try:
            # Find all running KMonad instances
            result = subprocess.run(['pgrep', '-a', 'kmonad'], capture_output=True, text=True)
            current_instances = []
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    pid, cmd = line.split(' ', 1)
                    config_file = cmd.split()[-1]  # Get the config file path
                    current_instances.append((pid, config_file))
            
            # Update our tracking list
            self.kmonad_instances = current_instances
            
            # Check if our specific instance is running
            if self.kmonad_config_path:
                our_config = os.path.abspath(self.kmonad_config_path)  # Get full path
                self.is_kmonad_running = any(
                    os.path.abspath(cfg) == our_config 
                    for _, cfg in current_instances
                )
            else:
                self.is_kmonad_running = False
                
            # Log status changes
            if not hasattr(self, '_last_running_state'):
                self._last_running_state = self.is_kmonad_running
            elif self._last_running_state != self.is_kmonad_running:
                if self.is_kmonad_running:
                    self.output_text.append("Our KMonad instance started!")
                else:
                    self.output_text.append("Our KMonad instance stopped!")
                self._last_running_state = self.is_kmonad_running
            
            self.update_status()
                
        except Exception as e:
            if "No such file or directory" not in str(e):
                self.output_text.append(f"Error checking KMonad status: {e}")
            self.is_kmonad_running = False
            self.kmonad_instances = []
            self.update_status()

    def run_setup_wizard(self):
        wizard = SetupWizard(self)
        if wizard.exec():
            self.settings.setValue("setup_complete", True)
            QMessageBox.information(self, "Setup Complete", 
                "Setup is complete! Please log out and log back in for all changes to take effect.\n\n"
                "After logging back in, run this application again to configure your keyboard.")
            sys.exit(0)  # Exit after setup to ensure user logs out
        else:
            sys.exit(1)  # Exit if setup was cancelled

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top section for config file management and keyboard selection
        top_section = QHBoxLayout()
        
        # Left side: Config editor
        config_group = self.create_config_section()
        config_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        top_section.addWidget(config_group, stretch=2)
        
        # Right side: Keyboard selection, templates, and controls
        right_section = QVBoxLayout()
        
        # Add keyboard selection at the top of right section
        keyboard_group = self.create_keyboard_section()
        right_section.addWidget(keyboard_group)
        
        # Templates and other controls below
        templates_group = self.create_templates_section()
        right_section.addWidget(templates_group)
        
        top_section.addLayout(right_section, stretch=1)
        main_layout.addLayout(top_section)
        
        # Bottom section
        bottom_section = QVBoxLayout()
        
        # Controls row
        controls_row = QHBoxLayout()
        
        # KMonad controls
        start_btn = QPushButton("Start KMonad")
        start_btn.clicked.connect(self.start_kmonad)
        controls_row.addWidget(start_btn)
        
        stop_btn = QPushButton("Stop KMonad")
        stop_btn.clicked.connect(self.stop_kmonad)
        controls_row.addWidget(stop_btn)
        
        # Autostart checkbox
        self.autostart_checkbox = QCheckBox("Start KMonad automatically")
        self.autostart_checkbox.setChecked(self.autostart_enabled)
        self.autostart_checkbox.stateChanged.connect(self.toggle_autostart)
        controls_row.addWidget(self.autostart_checkbox)
        
        # Add the new "Terminate All KMonads" button
        terminate_all_btn = QPushButton("Terminate All KMonads")
        terminate_all_btn.clicked.connect(self.terminate_all_kmonads)
        controls_row.addWidget(terminate_all_btn)
        
        # Add stretch to push controls to the left
        controls_row.addStretch()
        
        # Clear output button
        clear_btn = QPushButton("Clear Output")
        clear_btn.clicked.connect(self.output_text.clear)
        controls_row.addWidget(clear_btn)
        
        # Layout switcher button
        layout_btn = QPushButton("Switch to US QWERTY")
        layout_btn.clicked.connect(lambda: self.switch_to_us_qwerty())
        controls_row.addWidget(layout_btn)
        
        # Add status indicator
        self.status_label = QLabel("Status: Not Running")
        self.status_label.setStyleSheet("QLabel { color: red; }")
        controls_row.addWidget(self.status_label)
        
        bottom_section.addLayout(controls_row)
        
        # Output text area
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(150)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        bottom_section.addWidget(output_group)
        
        main_layout.addLayout(bottom_section)

    def create_config_section(self):
        config_group = QGroupBox("kbd Configuration")
        config_layout = QVBoxLayout()
        
        # Add letter box view at the top
        config_layout.addWidget(self.keyboard_layout)
        
        # File selection row
        file_row = QHBoxLayout()
        self.config_path_label = QLabel(self.kmonad_config_path or "No config file selected")
        file_row.addWidget(self.config_path_label)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_config)
        file_row.addWidget(browse_btn)
        
        create_default_btn = QPushButton("Create Default Config")
        create_default_btn.clicked.connect(self.create_default_config)
        file_row.addWidget(create_default_btn)
        
        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self.save_config)
        file_row.addWidget(save_btn)
        
        config_layout.addLayout(file_row)
        
        # Config editor (should expand to fill space)
        self.config_edit = QTextEdit()
        self.config_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if self.kmonad_config_path and os.path.exists(self.kmonad_config_path):
            with open(self.kmonad_config_path, 'r') as f:
                self.config_edit.setPlainText(f.read())
        config_layout.addWidget(self.config_edit)
        
        config_group.setLayout(config_layout)
        return config_group

    def create_keyboard_section(self):
        keyboard_group = QGroupBox("Keyboard Selection")
        layout = QVBoxLayout()
        
        # Keyboard selection dropdown
        self.keyboard_combo = QComboBox()
        self.keyboard_combo.setMinimumWidth(300)
        layout.addWidget(QLabel("Select Keyboard:"))
        layout.addWidget(self.keyboard_combo)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.refresh_keyboard_list)
        buttons_layout.addWidget(refresh_btn)
        
        apply_btn = QPushButton("Apply Selection")
        apply_btn.clicked.connect(self.apply_keyboard_selection)
        buttons_layout.addWidget(apply_btn)
        
        layout.addLayout(buttons_layout)
        keyboard_group.setLayout(layout)
        
        # Initial population of keyboard list
        self.refresh_keyboard_list()
        return keyboard_group

    def refresh_keyboard_list(self):
        self.keyboard_combo.clear()
        try:
            # Get list of all input devices with event numbers
            result = subprocess.run(['ls', '-l', '/dev/input/by-id'], capture_output=True, text=True)
            
            # Also get libinput list for additional device info
            libinput_result = subprocess.run(['libinput', 'list-devices'], capture_output=True, text=True)
            libinput_devices = libinput_result.stdout.split('\n\n')
            
            # Parse the output to get keyboard devices
            keyboards = []
            for line in result.stdout.splitlines():
                if 'kbd' in line:
                    parts = line.split(' -> ')
                    if len(parts) == 2:
                        name = parts[0].split()[-1]
                        event = parts[1].split('/')[-1]  # This will be like 'event4'
                        event_num = event.replace('event', '')
                        event_path = f"/dev/input/event{event_num}"
                        
                        # Try to find additional info from libinput
                        device_info = ""
                        for device in libinput_devices:
                            if event_path in device:
                                device_info = device.split('\n')[0].replace('Device:', '').strip()
                                break
                        
                        display_name = f"{device_info or name} (event{event_num})"
                        keyboards.append((display_name, event_path, event_num))
            
            # Sort by event number
            keyboards.sort(key=lambda x: int(x[2]))
            
            # Add to combo box
            for display_name, path, _ in keyboards:
                self.keyboard_combo.addItem(display_name, path)
                self.output_text.append(f"Found keyboard: {display_name} at {path}")
            
            # Set previously selected keyboard if it exists
            saved_keyboard = self.settings.value("keyboard_device", "")
            if saved_keyboard:
                index = self.keyboard_combo.findData(saved_keyboard)
                if index >= 0:
                    self.keyboard_combo.setCurrentIndex(index)
                    self.output_text.append(f"Restored previous selection: {self.keyboard_combo.currentText()}")
        
        except Exception as e:
            self.output_text.append(f"Error refreshing keyboard list: {e}")

    def apply_keyboard_selection(self):
        current_path = self.keyboard_combo.currentData()
        current_text = self.keyboard_combo.currentText()
        if not current_path:
            self.output_text.append("ERROR: No keyboard selected!")
            return
            
        self.settings.setValue("keyboard_device", current_path)
        self.settings.setValue("keyboard_name", current_text)
        self.output_text.append(f"Selected keyboard: {current_text}")
        self.output_text.append(f"Device path: {current_path}")
        
        # Update the config content
        if hasattr(self, 'config_edit'):
            current_config = self.config_edit.toPlainText()
            
            # Extract everything after all defcfg and output sections
            import re
            
            # Remove all defcfg sections and standalone output/fallthrough/allow-cmd lines
            cleaned_config = re.sub(r'\(defcfg.*?\)', '', current_config, flags=re.DOTALL)
            cleaned_config = re.sub(r'^\s*output.*$', '', cleaned_config, flags=re.MULTILINE)
            cleaned_config = re.sub(r'^\s*fallthrough.*$', '', cleaned_config, flags=re.MULTILINE)
            cleaned_config = re.sub(r'^\s*allow-cmd.*$', '', cleaned_config, flags=re.MULTILINE)
            
            # Remove any resulting empty lines
            cleaned_config = '\n'.join(line for line in cleaned_config.split('\n') if line.strip())
            
            # Find the first actual config section (defalias, defsrc, or deflayer)
            first_section = re.search(r'\((def(?:alias|src|layer).*)', cleaned_config, re.DOTALL)
            if first_section:
                cleaned_config = first_section.group(0)
            
            # Create new config with single defcfg section
            new_config = f'''(defcfg
  input  (device-file "{current_path}")
  output (uinput-sink "kmonad-keyboard")
  fallthrough true
  allow-cmd true)

{cleaned_config}'''
            
            self.config_edit.setPlainText(new_config)
            self.output_text.append("Updated config with new keyboard device")
            
            # Save the config
            if self.kmonad_config_path:
                self.save_config()
                
            # Print the cleaned config for verification
            self.output_text.append("\nVerifying config structure:")
            self.output_text.append("------------------------")
            self.output_text.append(new_config[:200] + "...")  # Show first part of config

    def create_templates_section(self):
        templates_group = QGroupBox("KMonad Templates")
        templates_layout = QVBoxLayout()
        
        # Template categories
        categories = {
            "Basic Remapping": [
                ("Simple Key Remap", self.get_simple_remap_template),
                ("Layer Switching", self.get_layer_switch_template),
                ("Tap-Hold", self.get_tap_hold_template)
            ],
            "Advanced Features": [
                ("Multi-tap", self.get_multi_tap_template),
                ("Command Execution", self.get_command_template),
                ("Around-Modifiers", self.get_around_modifiers_template)  # Fixed name
            ],
            "Common Layouts": [
                ("Colemak", self.get_colemak_template),
                ("Gaming Layer", self.get_gaming_template)
            ]
        }

        for category, templates in categories.items():
            category_combo = QComboBox()
            category_combo.addItem(f"-- {category} --")
            for template_name, _ in templates:
                category_combo.addItem(template_name)
            
            category_combo.setProperty("templates", templates)
            category_combo.currentIndexChanged.connect(self.handle_template_selection)
            templates_layout.addWidget(category_combo)

        # Template preview
        self.template_preview = QTextEdit()
        self.template_preview.setPlaceholderText("Test, template will appear here...")
        self.template_preview.setMinimumHeight(200)
        templates_layout.addWidget(self.template_preview)

        # Insert button
        insert_btn = QPushButton("Insert Template at Cursor")
        insert_btn.clicked.connect(self.insert_template)
        templates_layout.addWidget(insert_btn)

        templates_group.setLayout(templates_layout)
        return templates_group

    def handle_template_selection(self, index):
        combo = self.sender()
        if index == 0:  # Category header
            return
            
        templates = combo.property("templates")
        template_name, template_func = templates[index - 1]  # -1 because of header
        template_text = template_func()
        self.template_preview.setText(template_text)

    def insert_template(self):
        if not hasattr(self, 'config_edit'):
            return
        
        template_text = self.template_preview.toPlainText()
        if template_text:
            cursor = self.config_edit.textCursor()
            cursor.insertText(template_text)
    
    # Template functions
    def get_simple_remap_template(self):
        return '''
;; Simple key remapping example
(defalias
  caps esc  ;; Remap Caps Lock to Escape
)

(deflayer name
  ;; Original key = New key
  caps      ;; Use the alias defined above
  @caps     ;; Another way to use the alias
)
'''

    def get_layer_switch_template(self):
        return '''
;; Layer switching example
(defalias
  num  (layer-toggle numbers)  ;; Temporarily switch to number layer while held
  sym  (layer-switch symbols)  ;; Permanently switch to symbol layer
)

(deflayer base
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _
  _    _    @num           _              @sym _    _    _
)

(deflayer numbers
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    1    2    3    4    5    6    7    8    9    0    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _              _              _    _    _    _
)
'''

     
    def _verify_kmonad_running(self):
        """Verify KMonad process is running"""
        try:
            # Check if KMonad process exists
            if self.kmonad_process and self.kmonad_process.state() == QProcess.ProcessState.Running:
                self.is_kmonad_running = True
            else:
                self.is_kmonad_running = False
            self.update_status()
        except Exception as e:
            self.output_text.append(f"Error verifying KMonad status: {e}")
            self.is_kmonad_running = False
            self.update_status()

    def handle_kmonad_output(self):
        output = self.kmonad_process.readAllStandardOutput().data().decode()
        self.output_text.append(output)

    def handle_kmonad_error(self):
        error = self.kmonad_process.readAllStandardError().data().decode()
        self.output_text.append(f"Error: {error}")
        # Add the current working directory and PATH for debugging
        self.output_text.append(f"Current directory: {os.getcwd()}")
        self.output_text.append(f"PATH: {os.environ.get('PATH', 'Not set')}")

    def handle_kmonad_finished(self, exit_code, exit_status):
        self.is_kmonad_running = False
        self.update_status()  # Update status indicator
        if exit_code != 0:
            self.output_text.append(f"KMonad process failed with exit code: {exit_code}")
            self.output_text.append("Check the output above for error messages")
            remaining_error = self.kmonad_process.readAllStandardError().data().decode()
            if remaining_error:
                self.output_text.append(f"Error output: {remaining_error}")
        else:
            self.output_text.append("KMonad process finished normally")

    def check_and_add_to_input_group(self):
        try:
            # Check if user is already in the input group
            result = subprocess.run(['groups'], capture_output=True, text=True)
            if 'input' in result.stdout:
                self.output_text.append("User is already in the input group.")
                return

            # If not, add user to the input group
            process = QProcess()
            process.start('pkexec', ['usermod', '-aG', 'input', os.environ['USER']])
            process.waitForFinished()

            if process.exitCode() == 0:
                self.output_text.append("Successfully added user to input group. Please log out and log back in for changes to take effect.")
            else:
                error = process.readAllStandardError().data().decode()
                self.output_text.append(f"Error adding user to input group: {error}")

        except Exception as e:
            self.output_text.append(f"Error checking or modifying groups: {e}")

    def save_config(self, silent=False):
        """Save config with optional silent mode"""
        if not self.kmonad_config_path:
            self.browse_config()
            if not self.kmonad_config_path:
                return
                
        try:
            with open(self.kmonad_config_path, 'w') as f:
                f.write(self.config_edit.toPlainText())
            
            # Only show message for manual saves
            if not silent and self.sender() and isinstance(self.sender(), QPushButton):
                self.output_text.append("Configuration saved successfully!")
                
            # Restart KMonad if it's running
            if self.is_kmonad_running:
                self.stop_kmonad()
                QTimer.singleShot(1000, self.start_kmonad)
                
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
            self.output_text.append(f"Error saving config: {str(e)}")

    def stop_kmonad(self):
        if not self.kmonad_process or not self.is_kmonad_running:
            self.output_text.append("KMonad is not running.")
            return

        try:
            # Try graceful termination first
            self.kmonad_process.terminate()
            
            # Wait for it to finish
            if not self.kmonad_process.waitForFinished(3000):  # 3 second timeout
                self.output_text.append("KMonad not responding to terminate signal, forcing kill...")
                self.kmonad_process.kill()
            
            # Additional cleanup
            script_path = os.path.expanduser("~/.local/share/kmonad/kmonad_starter.sh")
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except Exception as e:
                    self.output_text.append(f"Note: Could not remove starter script: {e}")
            
            self.is_kmonad_running = False
            self.output_text.append("KMonad stopped")
            
        except Exception as e:
            self.output_text.append(f"Error stopping KMonad: {e}")
            # Try force kill as last resort
            try:
                self.kmonad_process.kill()
                self.output_text.append("Forced KMonad to stop")
            except:
                self.output_text.append("Failed to force stop KMonad")
            finally:
                self.is_kmonad_running = False

    def switch_to_us_qwerty(self):
        try:
            subprocess.run(["setxkbmap", "us"], check=True)
            self.output_text.append("Successfully switched to US QWERTY layout")
            QMessageBox.information(self, "Success", "Switched to US QWERTY layout")
        except subprocess.CalledProcessError as e:
            self.output_text.append(f"Failed to switch layout: {e}")
            QMessageBox.critical(self, "Error", "Failed to switch keyboard layout")

    def update_status(self):
        """Update the status indicator with current state"""
        status_text = []
        
        # Show our instance status
        if self.is_kmonad_running:
            status_text.append("Our Instance: Running")
            status_color = "#00ff00"
            bg_color = "#002200"
        else:
            status_text.append("Our Instance: Not Running")
            status_color = "#ff0000"
            bg_color = "#220000"
        
        # Show other instances if any
        other_instances = [cfg for _, cfg in self.kmonad_instances 
                          if os.path.basename(self.kmonad_config_path) not in cfg]
        if other_instances:
            status_text.append(f"Other Instances: {len(other_instances)}")
        
        self.status_label.setText("\n".join(status_text))
        self.status_label.setStyleSheet(f"""
            QLabel {{ 
                color: {status_color};
                font-weight: bold;
                padding: 5px;
                border: 1px solid {status_color};
                border-radius: 3px;
                background-color: {bg_color};
            }}
        """)

    def mousePressEvent(self, event):
        """Handle mouse press for config editor drag and drop"""
        if self.config_edit.underMouse():
            cursor = self.config_edit.cursorForPosition(
                self.config_edit.mapFromGlobal(event.globalPosition().toPoint())
            )
            if cursor:
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                selected_text = cursor.selectedText()
                if len(selected_text) == 1:  # Only allow single letters
                    self.dragging_key = selected_text
                    self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging_key:
            # Calculate movement
            delta = event.pos() - self.drag_start_pos
            if delta.manhattanLength() > 10:  # Small threshold to start drag
                # Create drag object
                drag = QDrag(self)
                mimedata = QMimeData()
                mimedata.setText(self.dragging_key)
                drag.setMimeData(mimedata)
                
                # Optional: Create a visual drag indicator
                pixmap = QPixmap(30, 30)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                painter.drawText(0, 20, self.dragging_key)
                painter.end()
                drag.setPixmap(pixmap)
                
                # Execute drag
                drag.exec()
                self.dragging_key = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging_key = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            pos = self.config_edit.mapFromGlobal(event.position().toPoint())
            drop_pos = self.config_edit.cursorForPosition(pos)
            
            if drop_pos:
                # Get current line and find key blocks
                drop_pos.movePosition(QTextCursor.MoveOperation.StartOfLine)
                line_start = drop_pos.position()
                drop_pos.movePosition(QTextCursor.MoveOperation.EndOfLine)
                line_text = self.config_edit.document().findBlock(line_start).text()
                
                # Find key blocks in the line
                key_blocks = re.finditer(r'(\S+)\s*', line_text)
                key_positions = [(m.group(1), m.start()) for m in key_blocks]
                
                # Find insertion point
                insert_pos = pos.x() // 30  # Approximate character width
                
                # Find nearest block position
                nearest_pos = 0
                for key, pos in key_positions:
                    if pos < insert_pos:
                        nearest_pos = pos + len(key) + 1
                
                # Create new line with inserted key
                new_key = event.mimeData().text()
                new_line = (
                    line_text[:nearest_pos] + 
                    " " * (insert_pos - nearest_pos) + 
                    new_key + " " + 
                    line_text[nearest_pos:].lstrip()
                )
                
                # Replace the line
                cursor = self.config_edit.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, 
                                  QTextCursor.MoveMode.KeepAnchor)
                cursor.insertText(new_line)
                
                # Save and update
                self.save_config(silent=True)
                self.keyboard_layout.update_from_config(self.config_edit.toPlainText())
            
        self.dragging = False
        self.drag_pos = None
        self.reset_key_positions()
        event.acceptProposedAction()

    def get_expected_position(self, key):
        """Get expected position for a key based on standard layout"""
        # Define standard key positions (character count from start of line)
        key_positions = {
            'esc': 0, 'f1': 5, 'f2': 10, 'f3': 15,  # Function row
            'grv': 0, '1': 5, '2': 10, '3': 15,     # Number row
            'tab': 0, 'q': 5, 'w': 10, 'e': 15,     # QWERTY row
            'caps': 0, 'a': 5, 's': 10, 'd': 15,    # Home row
            'lsft': 0, 'z': 5, 'x': 10, 'c': 15,    # Bottom row
            'lctl': 0, 'lmet': 5, 'lalt': 10        # Modifier row
        }
        return key_positions.get(key, 0)

    def show_alignment_warning(self, current_pos, expected_pos):
        """Show subtle warning about key alignment"""
        msg = QLabel(f"Key might be misaligned (current: {current_pos}, expected: {expected_pos})")
        msg.setStyleSheet("""
            QLabel {
                background-color: #332200;
                color: #ffaa00;
                padding: 5px;
                border-radius: 3px;
            }
        """)
        
        # Create a temporary overlay for the warning
        overlay = QWidget(self)
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.addWidget(msg)
        overlay.setStyleSheet("background-color: transparent;")
        
        # Position at bottom of window
        overlay.move(10, self.height() - 50)
        overlay.show()
        
        # Auto-hide after 2 seconds
        QTimer.singleShot(2000, overlay.deleteLater)

    def keyPressEvent(self, event):
        """Handle key presses to create keys at cursor position"""
        if self.config_edit.hasFocus():
            cursor = self.config_edit.textCursor()
            key_text = None
            
            # Check for special keys first
            if event.key() in self.special_key_map:
                key_text = self.special_key_map[event.key()]
            # Then check for regular character keys
            elif event.text() and event.text().isprintable():
                key_text = event.text().lower()
            
            if key_text:
                # Insert the key at cursor position
                cursor.insertText(key_text + ' ')
                self.config_edit.setTextCursor(cursor)
                # Update the layout view
                self.keyboard_layout.update_from_config(self.config_edit.toPlainText())
                event.accept()
                return
                
        super().keyPressEvent(event)

    def parse_kbd_config(self, config_text):
        """Parse KMonad config file to extract layers"""
        try:
            # Find the defsrc layout first
            src_match = re.search(r'\(defsrc(.*?)\)', config_text, re.DOTALL)
            if src_match:
                src_layout = [key.strip() for key in src_match.group(1).split() if key.strip()]
                self.layers['src'] = src_layout
            else:
                self.layers['src'] = []  # Empty if not found
                self.output_text.append("Warning: No source layout found in config")

            # Find all deflayer sections
            layer_matches = re.finditer(r'\(deflayer\s+(\w+)(.*?)\)', config_text, re.DOTALL)
            for match in layer_matches:
                layer_name = match.group(1)
                layout_text = match.group(2).strip()
                # Convert layout text to structured data
                keys = [key.strip() for key in layout_text.split() if key.strip()]
                self.layers[layer_name] = keys

        except Exception as e:
            self.output_text.append(f"Error parsing keyboard config: {e}")
            # Ensure we have at least empty layers
            self.layers.setdefault('source', [])
            self.layers.setdefault('qwerty', [])

    def create_layer_selector(self):
        """Create layer selection toolbar"""
        toolbar = self.addToolBar("Layers")
        
        self.layer_combo = QComboBox()
        self.layer_combo.currentTextChanged.connect(self.switch_layer)
        toolbar.addWidget(QLabel("Active Layer: "))
        toolbar.addWidget(self.layer_combo)
        
        # Add edit/source toggle
        self.edit_mode = QPushButton("Edit Source")
        self.edit_mode.setCheckable(True)
        self.edit_mode.toggled.connect(self.toggle_edit_mode)
        toolbar.addWidget(self.edit_mode)

    def switch_layer(self, layer_name):
        """Switch between different keyboard layers"""
        if layer_name in self.layers:
            self.current_layer = layer_name
            self.keyboard_layout.update_from_layer(self.layers[layer_name])
            
    def toggle_edit_mode(self, checked):
        """Toggle between editing source layout and viewing layers"""
        try:
            if checked:
                self.edit_mode.setText("View Layer")
                if 'source' not in self.layers:
                    self.layers['source'] = []  # Ensure source layer exists
                self.keyboard_layout.update_from_layer(self.layers['source'])
            else:
                self.edit_mode.setText("Edit Source")
                if self.current_layer not in self.layers:
                    self.current_layer = 'qwerty'  # Fall back to default layer
                self.keyboard_layout.update_from_layer(self.layers[self.current_layer])
        except Exception as e:
            self.output_text.append(f"Error toggling edit mode: {e}")
            self.edit_mode.setChecked(False)  # Reset to unchecked state

    def start_kmonad(self):
        """Start KMonad with current configuration"""
        if self.is_kmonad_running:
            self.output_text.append("KMonad is already running")
            return

        if not self.kmonad_config_path:
            QMessageBox.warning(self, "Error", "No configuration file selected")
            return

        try:
            # Start KMonad directly using QProcess
            self.kmonad_process = QProcess(self)
            self.kmonad_process.setProgram("kmonad")
            self.kmonad_process.setArguments([self.kmonad_config_path])

            # Capture standard output and error
            self.kmonad_process.readyReadStandardOutput.connect(
                lambda: self.output_text.append(
                    str(self.kmonad_process.readAllStandardOutput(), 'utf-8')
                )
            )
            self.kmonad_process.readyReadStandardError.connect(
                lambda: self.output_text.append(
                    str(self.kmonad_process.readAllStandardError(), 'utf-8')
                )
            )

            # Connect the finished signal to handle process exit
            self.kmonad_process.finished.connect(self.handle_kmonad_exit)

            # Start the process
            self.kmonad_process.start()

            if self.kmonad_process.waitForStarted(3000):  # 3-second timeout
                self.is_kmonad_running = True
                self.output_text.append("KMonad started successfully")
            else:
                self.output_text.append("Failed to start KMonad")
                error = self.kmonad_process.errorString()
                QMessageBox.critical(self, "Error", f"Failed to start KMonad: {error}")

        except Exception as e:
            self.output_text.append(f"Error starting KMonad: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start KMonad: {str(e)}")

    def handle_kmonad_exit(self, exit_code, exit_status):
        """Handle KMonad process exit"""
        self.is_kmonad_running = False
        if exit_code != 0:
            self.output_text.append(f"KMonad exited with code {exit_code}")
            if exit_status == QProcess.ExitStatus.CrashExit:
                self.output_text.append("KMonad crashed!")
        else:
            self.output_text.append("KMonad stopped normally")

    def check_kmonad_status(self):
        """Check if KMonad is still running"""
        if self.kmonad_process:
            state = self.kmonad_process.state()
            if state == QProcess.ProcessState.NotRunning:
                self.is_kmonad_running = False
            elif state == QProcess.ProcessState.Running:
                self.is_kmonad_running = True
        self.update_status()

    def update_config_content(self, current_path):
        """Update config with new keyboard device path"""
        if hasattr(self, 'config_edit'):
            current_config = self.config_edit.toPlainText()
            
            # Extract everything after all defcfg and output sections
            import re
            
            # Remove all defcfg sections and standalone output/fallthrough/allow-cmd lines
            cleaned_config = re.sub(r'\(defcfg.*?\)', '', current_config, flags=re.DOTALL)
            cleaned_config = re.sub(r'^\s*output.*$', '', cleaned_config, flags=re.MULTILINE)
            cleaned_config = re.sub(r'^\s*fallthrough.*$', '', cleaned_config, flags=re.MULTILINE)
            cleaned_config = re.sub(r'^\s*allow-cmd.*$', '', cleaned_config, flags=re.MULTILINE)
            
            # Remove any resulting empty lines
            cleaned_config = '\n'.join(line for line in cleaned_config.split('\n') if line.strip())
            
            # Create new config with single defcfg section
            new_config = f'''(defcfg
  input  (device-file "{current_path}")
  output (uinput-sink "kmonad-keyboard")
  fallthrough true
  allow-cmd true)

{cleaned_config}'''
            
            self.config_edit.setPlainText(new_config)

    def browse_config(self):
        """Browse for or create new KMonad config file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select KMonad Config File",
            os.path.expanduser("~/.config/kmonad/"),
            "KMonad Config (*.kbd);;All Files (*.*)"
        )
        
        if file_path:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Update path
            self.kmonad_config_path = file_path
            self.config_path_label.setText(file_path)
            self.settings.setValue("kmonad_config_path", file_path)
            
            # If file doesn't exist, create it with default config
            if not os.path.exists(file_path):
                self.create_default_config()
            else:
                # Load existing config
                try:
                    with open(file_path, 'r') as f:
                        self.config_edit.setPlainText(f.read())
                    self.output_text.append(f"Loaded config from {file_path}")
                except Exception as e:
                    self.output_text.append(f"Error loading config: {e}")

    def create_default_config(self):
        """Create a default KMonad configuration"""
        if not self.kmonad_config_path:
            self.browse_config()
            if not self.kmonad_config_path:
                return
                
        default_config = f'''(defcfg
  input  (device-file "{self.keyboard_combo.currentData() or "/dev/input/by-path/platform-i8042-serio-0-event-kbd"}")
  output (uinput-sink "kmonad-keyboard")
  fallthrough true
  allow-cmd true)

(defsrc
  esc  f1   f2   f3   f4   f5   f6   f7   f8   f9   f10  f11  f12
  grv  1    2    3    4    5    6    7    8    9    0    -    =    bspc
  tab  q    w    e    r    t    y    u    i    o    p    [    ]    \\
  caps a    s    d    f    g    h    j    k    l    ;    '    ret
  lsft z    x    c    v    b    n    m    ,    .    /    rsft
  lctl lmet lalt           spc            ralt rmet rctl
)

(deflayer qwerty
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _              _              _    _    _
)'''
        
        self.config_edit.setPlainText(default_config)
        self.save_config()
        self.output_text.append("Created default configuration")

    def get_tap_hold_template(self):
        return '''
;; Tap-hold key example
(defalias
  ctl_a  (tap-hold-next-release 200 a lctl)  ;; 'a' when tapped, 'ctrl' when held
  sft_s  (tap-hold 200 s lsft)              ;; 's' when tapped, 'shift' when held
)

(deflayer name
  @ctl_a  ;; Use the tap-hold alias
  @sft_s  ;; Another tap-hold key
)
'''

    def get_multi_tap_template(self):
        return '''
;; Multi-tap key example
(defalias
  mt  (multi-tap 300 x 300 y z)  ;; Tap once for x, twice for y, thrice for z
)

(deflayer name
  @mt  ;; Use the multi-tap alias
)
'''

    def get_command_template(self):
        return '''
;; Command execution example
(defalias
  term (cmd-button "alacritty")         ;; Launch terminal
  vol+ (cmd-button "amixer set Master 5%+")  ;; Volume up
)

(deflayer name
  @term  ;; Launch terminal
  @vol+  ;; Increase volume
)
'''

    def get_around_modifiers_template(self):
        return '''
;; Around-modifier example
(defalias
  cpy (around lctl c)  ;; Ctrl+C (copy)
  pst (around lctl v)  ;; Ctrl+V (paste)
)

(deflayer name
  @cpy  ;; Use copy alias
  @pst  ;; Use paste alias
)
'''

    def get_colemak_template(self):
        return '''
;; Colemak layout
(deflayer colemak
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    q    w    f    p    g    j    l    u    y    ;    [    ]    \\
  _    a    r    s    t    d    h    n    e    i    o    '    _
  _    z    x    c    v    b    k    m    ,    .    /    _
  _    _    _              _              _    _    _
)
'''

    def get_gaming_template(self):
        return '''
;; Gaming layer (pass-through most keys)
(deflayer gaming
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    q    w    e    r    t    y    u    i    o    p    _    _    _
  _    a    s    d    f    g    h    j    k    l    _    _    _
  _    z    x    c    v    b    n    m    _    _    _    _
  _    _    _              _              _    _    _
)
'''

    def toggle_autostart(self, state):
        """Toggle automatic startup of KMonad"""
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            desktop_file = os.path.join(autostart_dir, "kmonad.desktop")
            
            if state:  # Enable autostart
                os.makedirs(autostart_dir, exist_ok=True)
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=KMonad
Comment=Keyboard remapping utility
Exec=kmonad {self.kmonad_config_path}
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true"""
                
                with open(desktop_file, 'w') as f:
                    f.write(desktop_content)
                    
                self.output_text.append("Enabled KMonad autostart")
                self.autostart_enabled = True
                
            else:  # Disable autostart
                if os.path.exists(desktop_file):
                    os.remove(desktop_file)
                self.output_text.append("Disabled KMonad autostart")
                self.autostart_enabled = False
                
            # Save setting
            self.settings.setValue("autostart_enabled", self.autostart_enabled)
            
        except Exception as e:
            self.output_text.append(f"Error toggling autostart: {e}")
            QMessageBox.critical(self, "Error", f"Failed to toggle autostart: {str(e)}")

    def terminate_all_kmonads(self):
        """Terminate all running KMonad processes"""
        try:
            # Use 'pkill' to terminate all KMonad processes
            # 'pkill' may require sudo privileges; ensure the application has the needed permissions
            subprocess.run(['pkill', '-f', 'kmonad'], check=True)
            self.output_text.append("All running KMonad processes have been terminated.")
            self.is_kmonad_running = False
            self.update_status()
        except subprocess.CalledProcessError as e:
            self.output_text.append(f"Error terminating KMonads: {e}")
            QMessageBox.critical(self, "Error", f"Failed to terminate KMonads: {e}")
        except Exception as e:
            self.output_text.append(f"Unexpected error: {e}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = KeyboardManager()
    monitor.show()
    sys.exit(app.exec())
