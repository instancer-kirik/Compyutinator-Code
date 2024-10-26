import sys
import os
import subprocess
import tempfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QComboBox, QTextEdit, QLabel, 
                            QFileDialog, QMessageBox, QGroupBox, QCheckBox,
                            QWizard, QWizardPage, QProgressBar, QSizePolicy)
from PyQt6.QtCore import QProcess, QSettings, QTimer

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

class KmonadMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.setWindowTitle("Keyboard Manager")
        # Initialize settings
        self.settings = QSettings("Compyutinator", "KeyboardManager")
        self.kmonad_config_path = self.settings.value("kmonad_config_path", "")
        self.autostart_enabled = self.settings.value("autostart_enabled", False, type=bool)
        self.kmonad_process = None
        self.is_kmonad_running = False
        
        # Check if first run or if setup was incomplete
        if not self.settings.value("setup_complete", False, type=bool):
            self.run_setup_wizard()
        else:
            self.setup_ui()

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
        
        # Add stretch to push controls to the left
        controls_row.addStretch()
        
        # Clear output button
        clear_btn = QPushButton("Clear Output")
        clear_btn.clicked.connect(self.output_text.clear)
        controls_row.addWidget(clear_btn)
        
        # Add layout switcher button to controls_row
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
  _    _    _    _    _    _    _    _    _    _    _    _    _
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

    def get_tap_hold_template(self):
        return '''
;; Tap-hold configuration example
(defalias
  sft  (tap-hold 200 a lsft)  ;; Tap for 'a', hold for left shift
  ctl  (tap-hold-next 200 s lctl)  ;; Tap for 's', hold for left control
  alt  (tap-hold-next-release 200 d lalt)  ;; Tap for 'd', hold for left alt
)

(deflayer tap-hold
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    @sft @ctl @alt _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _              _              _    _    _    _
)
'''

    def get_multi_tap_template(self):
        return '''
;; Multi-tap configuration example
(defalias
  mt  (multi-tap 300 a 300 b 300 c d)  ;; Tap 1=a, 2=b, 3=c, 4+=d
)

(deflayer multi-tap
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    @mt  _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _              _              _    _    _    _
)
'''

    def get_command_template(self):
        return '''
;; Command execution example
(defalias
  term (cmd-button "alacritty")  ;; Launch terminal
  lock (cmd-button "loginctl lock-session")  ;; Lock screen
)

(deflayer commands
  _     _     _     _     _     _     _     _     _     _     _     _     _
  _     _     _     _     _     _     _     _     _     _     _     _     _     _
  _     _     _     @term _     _     _     _     _     _     _     _     _     _
  _     _     _     _     _     _     _     _     _     _     _     _     _
  _     _     _     _     _     _     _     _     _     _     @lock  _
  _     _     _               _               _     _     _     _
)
'''

    def get_colemak_template(self):
        return '''
;; Colemak layout
(deflayer colemak
  esc  f1   f2   f3   f4   f5   f6   f7   f8   f9   f10  f11  f12
  grv  1    2    3    4    5    6    7    8    9    0    -    =    bspc
  tab  q    w    f    p    g    j    l    u    y    ;    [    ]    \\
  bspc a    r    s    t    d    h    n    e    i    o    '    ret
  lsft z    x    c    v    b    k    m    ,    .    /    rsft
  lctl lmet lalt           spc            ralt rmet cmp  rctl
)
'''

    def get_gaming_template(self):
        return '''
;; Gaming layer (standard QWERTY with some extra bindings)
(defalias
  inv  (tap-hold 200 i tab)    ;; Tap for inventory (i), hold for tab
  map  (tap-hold 200 m ret)    ;; Tap for map (m), hold for enter
)

(deflayer gaming
  esc  f1   f2   f3   f4   f5   f6   f7   f8   f9   f10  f11  f12
  grv  1    2    3    4    5    6    7    8    9    0    -    =    bspc
  tab  q    w    e    r    t    y    u    @inv o    p    [    ]    \\
  caps a    s    d    f    g    h    j    k    l    ;    '    ret
  lsft z    x    c    v    b    n    @map ,    .    /    rsft
  lctl lmet lalt           spc            ralt rmet cmp  rctl
)
'''

    def get_around_modifiers_template(self):
        return '''
;; Around-modifier configuration example
(defalias
  ;; Press shift, then press keys, then release shift
  caps (around lsft (layer-toggle capslock))
  
  ;; Hold both shift and control while pressing key
  sel  (around-next lsft lctl)
  
  ;; Press and hold control, press shift, press key, release all
  meh  (around lctl (around-next lsft lalt))
)

(deflayer modifiers
  _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  _    _    _    _    _    _    _    _    _    _    _    _    _    _
  @cps _    @sel _    _    _    _    _    _    _    _    _    _
  _    _    _    @meh _    _    _    _    _    _    _    _
  _    _    _              _              _    _    _    _
)
'''

    def toggle_autostart(self, state):
        self.autostart_enabled = bool(state)
        self.settings.setValue("autostart_enabled", self.autostart_enabled)
        self.update_autostart_entry()  # Update the autostart file

    def update_autostart_entry(self):
        autostart_dir = os.path.expanduser('~/.config/autostart')
        autostart_file = os.path.join(autostart_dir, 'keyboard-manager.desktop')
        
        if self.autostart_enabled:
            os.makedirs(autostart_dir, exist_ok=True)
            with open(autostart_file, 'w') as f:
                f.write(f"""[Desktop Entry]
Type=Application
Name=Keyboard Manager
Exec={sys.executable} {os.path.abspath(__file__)}
X-GNOME-Autostart-enabled=true
""")
        else:
            if os.path.exists(autostart_file):
                os.remove(autostart_file)

    def switch_layout(self, layout_name):
        if self.is_kmonad_running:
            self.stop_kmonad()
            # Use a timer to delay the restart
            QTimer.singleShot(1000, lambda: self._complete_layout_switch(layout_name))
        else:
            self._complete_layout_switch(layout_name)

    def _complete_layout_switch(self, layout_name):
        # Update the KMonad config to use the new layout
        if self.kmonad_config_path:
            try:
                # Read the current config
                with open(self.kmonad_config_path, 'r') as f:
                    config = f.read()
                
                # Update the layout in the config (you'll need to adjust this based on your KMonad config structure)
                # This is a placeholder - adjust the regex pattern to match your config format
                import re
                config = re.sub(r'\(layout\s+[^\)]+\)', f'(layout {layout_name})', config)
                
                # Write the updated config
                with open(self.kmonad_config_path, 'w') as f:
                    f.write(config)
                
                # Restart KMonad with the new config
                self.start_kmonad()
                self.output_text.append(f"Switched to layout: {layout_name}")
                
            except Exception as e:
                self.output_text.append(f"Error updating KMonad config: {e}")
        else:
            self.output_text.append("No KMonad config file selected")

    def closeEvent(self, event):
        # Properly cleanup KMonad process before closing
        if self.kmonad_process and self.is_kmonad_running:
            self.stop_kmonad()
        event.accept()

    def list_input_devices(self):
        try:
            # Try using libinput first
            result = subprocess.run(['libinput', 'list-devices'], capture_output=True, text=True)
            self.output_text.append("Available input devices:")
            self.output_text.append(result.stdout)
            
            # Also show event devices
            result = subprocess.run(['ls', '-l', '/dev/input/by-id'], capture_output=True, text=True)
            self.output_text.append("\nInput device links:")
            self.output_text.append(result.stdout)
            
        except Exception as e:
            self.output_text.append(f"Error listing input devices: {e}")

    def browse_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select KMonad Config File",
            os.path.expanduser("~"),  # Start in home directory
            "KMonad Config (*.kbd);;All Files (*.*)"
        )
        if file_path:
            self.kmonad_config_path = file_path
            self.config_path_label.setText(file_path)
            self.settings.setValue("kmonad_config_path", file_path)
            
            # Load the selected config file
            try:
                with open(file_path, 'r') as f:
                    self.config_edit.setPlainText(f.read())
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load configuration: {str(e)}")

    def create_default_config(self):
        default_config_dir = os.path.expanduser("~/.config/kmonad")
        os.makedirs(default_config_dir, exist_ok=True)
        default_config_path = os.path.join(default_config_dir, "default.kbd")
        
        if not os.path.exists(default_config_path):
            with open(default_config_path, 'w') as f:
                f.write("""(defcfg
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
)""")
            
            self.kmonad_config_path = default_config_path
            self.config_path_label.setText(default_config_path)
            self.settings.setValue("kmonad_config_path", default_config_path)
            return default_config_path

    def identify_keyboard_device(self):
        # Use the saved keyboard device instead of auto-detecting
        device_path = self.settings.value("keyboard_device", "")
        if not device_path:
            self.output_text.append("No keyboard device selected. Please select a keyboard from the dropdown.")
            return False
        
        self.output_text.append(f"Using keyboard device: {device_path}")
        return True

    def update_kmonad_config(self, device_path):
        if not self.kmonad_config_path:
            self.output_text.append("No KMonad config file selected.")
            return
        
        try:
            with open(self.kmonad_config_path, 'r') as f:
                config = f.read()
            
            # Update the input device in the config
            import re
            config = re.sub(r'\(device-file\s+"[^"]*"\)', f'(device-file "{device_path}")', config)
            
            with open(self.kmonad_config_path, 'w') as f:
                f.write(config)
            
            self.output_text.append("Updated KMonad config with correct device path.")
        except Exception as e:
            self.output_text.append(f"Error updating KMonad config: {e}")

    def check_qwerty_layout(self):
        try:
            current_layout = subprocess.check_output(["setxkbmap", "-query"]).decode()
            layout = [line.split(':')[1].strip() for line in current_layout.split('\n') if line.startswith('layout:')][0]
            variant = [line.split(':')[1].strip() for line in current_layout.split('\n') if line.startswith('variant:')]
            
            if layout.lower() != 'us' or (variant and variant[0].lower() != 'qwerty'):
                message = f"Current layout is {layout}"
                if variant:
                    message += f" with variant {variant[0]}"
                message += ". It's recommended to set it to US QWERTY before running KMonad."
                
                msgBox = QMessageBox(self)
                msgBox.setWindowTitle('Layout Warning')
                msgBox.setText(message)
                msgBox.setInformativeText("What would you like to do?")
                
                # Add custom buttons
                switchButton = msgBox.addButton("Switch to US QWERTY", QMessageBox.ButtonRole.ActionRole)
                continueButton = msgBox.addButton("Continue Anyway", QMessageBox.ButtonRole.AcceptRole)
                cancelButton = msgBox.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                
                msgBox.exec()
                
                if msgBox.clickedButton() == switchButton:
                    try:
                        subprocess.run(["setxkbmap", "us"], check=True)
                        self.output_text.append("Successfully switched to US QWERTY layout")
                        return True
                    except subprocess.CalledProcessError as e:
                        self.output_text.append(f"Failed to switch layout: {e}")
                        return False
                elif msgBox.clickedButton() == continueButton:
                    return True
                else:  # Cancel was clicked
                    return False
            
            return True
        except Exception as e:
            self.output_text.append(f"Error checking current layout: {e}")
            return False

    def start_kmonad(self):
        if not self.kmonad_config_path:
            self.output_text.append("No KMonad config file selected.")
            return
        
        if not os.path.exists(self.kmonad_config_path):
            self.output_text.append(f"Config file not found: {self.kmonad_config_path}")
            return
        
        # Check keyboard layout first
        if not self.check_qwerty_layout():
            self.output_text.append("Cancelled startup due to keyboard layout concerns.")
            return
        
        if self.is_kmonad_running:
            self.stop_kmonad()  # Stop existing process before starting new one
            QTimer.singleShot(1000, self._start_kmonad_process)  # Wait a second before restarting
            return
        
        self._start_kmonad_process()

    def _start_kmonad_process(self):
        try:
            # Verify keyboard selection first
            if not self.keyboard_combo.currentData():
                self.output_text.append("ERROR: No keyboard selected! Please select a keyboard from the dropdown.")
                return
            
            device_path = self.keyboard_combo.currentData()
            self.output_text.append(f"Using keyboard: {self.keyboard_combo.currentText()}")
            self.output_text.append(f"Device path: {device_path}")
            
            # Verify the device exists
            if not os.path.exists(device_path):
                self.output_text.append(f"ERROR: Device {device_path} does not exist!")
                return
            
            # Verify config file
            if not os.path.exists(self.kmonad_config_path):
                self.output_text.append(f"ERROR: Config file {self.kmonad_config_path} does not exist!")
                return
            
            # Create script in a more persistent location
            script_dir = os.path.expanduser("~/.local/share/kmonad")
            os.makedirs(script_dir, exist_ok=True)
            script_path = os.path.join(script_dir, "kmonad_starter.sh")
            
            script_content = f"""#!/bin/bash
set -e  # Exit on any error

# Debug info
echo "Starting KMonad setup..."
echo "Device path: {device_path}"
echo "Config path: {os.path.abspath(self.kmonad_config_path)}"

# Ensure uinput is loaded
if ! lsmod | grep -q "uinput"; then
    echo "Loading uinput module..."
    modprobe uinput || {{ echo "Failed to load uinput module"; exit 1; }}
fi

# Set up uinput permissions
if [ -e /dev/uinput ]; then
    echo "Setting up uinput permissions..."
    chmod 0660 /dev/uinput
    chown root:input /dev/uinput
fi

# Verify device permissions
if [ ! -r "{device_path}" ]; then
    echo "ERROR: Cannot read keyboard device!"
    ls -l "{device_path}"
    exit 1
fi

echo "Starting KMonad daemon..."
exec kmonad "{os.path.abspath(self.kmonad_config_path)}" &

# Wait a moment for KMonad to start
sleep 2

# Check if KMonad is running
if pgrep -f "kmonad.*{os.path.basename(self.kmonad_config_path)}"; then
    echo "KMonad daemon is running"
else
    echo "ERROR: KMonad failed to start or exited immediately"
    exit 1
fi

# Keep the script running to maintain the pkexec session
while pgrep -f "kmonad.*{os.path.basename(self.kmonad_config_path)}" > /dev/null; do
    sleep 1
done
"""
            # Write the script
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make the script executable
            os.chmod(script_path, 0o755)

            self.kmonad_process = QProcess(self)
            self.kmonad_process.readyReadStandardOutput.connect(self.handle_kmonad_output)
            self.kmonad_process.readyReadStandardError.connect(self.handle_kmonad_error)
            self.kmonad_process.finished.connect(self.handle_kmonad_finished)
            
            # Run the script with pkexec
            self.output_text.append("Starting KMonad daemon...")
            self.kmonad_process.start("pkexec", [script_path])
            
            # Wait for process to start
            if not self.kmonad_process.waitForStarted(5000):  # 5 second timeout
                raise Exception("Failed to start KMonad process (timeout)")
            
            # Set running flag
            QTimer.singleShot(2000, self._verify_kmonad_running)

        except Exception as e:
            self.output_text.append(f"Error starting KMonad: {str(e)}")
            self.is_kmonad_running = False
            self.update_status()  # Update status indicator

    def _verify_kmonad_running(self):
        try:
            # Check if KMonad process exists
            result = subprocess.run(['pgrep', '-f', f'kmonad.*{os.path.basename(self.kmonad_config_path)}'], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                self.is_kmonad_running = True
                self.output_text.append("KMonad daemon is running")
                # Get the actual KMonad process ID
                kmonad_pid = result.stdout.strip()
                self.output_text.append(f"KMonad process ID: {kmonad_pid}")
                self.update_status()  # Update status indicator
            else:
                self.is_kmonad_running = False
                self.output_text.append("ERROR: KMonad is not running!")
                
        except Exception as e:
            self.output_text.append(f"Error verifying KMonad status: {e}")
            self.is_kmonad_running = False

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

    def save_config(self):
        if not self.kmonad_config_path:
            self.browse_config()
            if not self.kmonad_config_path:
                return
                
        try:
            # Backup the existing config first
            if os.path.exists(self.kmonad_config_path):
                backup_path = f"{self.kmonad_config_path}.backup"
                import shutil
                shutil.copy2(self.kmonad_config_path, backup_path)
                self.output_text.append(f"Created backup at: {backup_path}")
            
            with open(self.kmonad_config_path, 'w') as f:
                f.write(self.config_edit.toPlainText())
            QMessageBox.information(self, "Success", "Configuration saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")

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
        if self.is_kmonad_running:
            self.status_label.setText("Status: Running")
            self.status_label.setStyleSheet("QLabel { color: green; }")
        else:
            self.status_label.setText("Status: Not Running")
            self.status_label.setStyleSheet("QLabel { color: red; }")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = KmonadMonitor()
    monitor.show()
    sys.exit(app.exec())
