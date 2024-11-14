from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QSlider, QCheckBox, QPushButton, QTabWidget,
                           QTableWidget, QTableWidgetItem, QKeySequenceEdit, QWidget)
from PyQt6.QtCore import Qt

class HotkeyEditor(QTableWidget):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setup_ui()

    def setup_ui(self):
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self.horizontalHeader().setStretchLastSection(True)
        
        # Get current hotkeys
        hotkeys = self.settings_manager.get_value("hotkeys", 
                                                self.settings_manager.default_settings["hotkeys"])
        
        # Populate table
        self.setRowCount(len(hotkeys))
        for i, (action, shortcut) in enumerate(hotkeys.items()):
            self.setItem(i, 0, QTableWidgetItem(action))
            
            # Use QKeySequenceEdit for shortcut editing
            shortcut_edit = QKeySequenceEdit()
            shortcut_edit.setKeySequence(shortcut)
            shortcut_edit.editingFinished.connect(
                lambda e=shortcut_edit, a=action: self.update_shortcut(a, e.keySequence().toString())
            )
            self.setCellWidget(i, 1, shortcut_edit)

    def update_shortcut(self, action, shortcut):
        self.settings_manager.set_hotkey(action, shortcut)

class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # General settings tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Add existing settings to general tab
        self.typing_effect_checkbox = QCheckBox("Enable Typing Effect")
        self.typing_effect_checkbox.setChecked(self.settings_manager.get_typing_effect_enabled())
        general_layout.addWidget(self.typing_effect_checkbox)
        
        # Typing effect speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Typing Effect Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 500)
        self.speed_slider.setValue(self.settings_manager.get_typing_effect_speed())
        speed_layout.addWidget(self.speed_slider)
        general_layout.addLayout(speed_layout)
        
        # Particle count
        particle_layout = QHBoxLayout()
        particle_layout.addWidget(QLabel("Particle Count:"))
        self.particle_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_slider.setRange(1, 50)
        self.particle_slider.setValue(self.settings_manager.get_typing_effect_particle_count())
        particle_layout.addWidget(self.particle_slider)
        general_layout.addLayout(particle_layout)
        
        # Hotkeys tab
        hotkeys_tab = HotkeyEditor(self.settings_manager)
        
        # Add tabs
        tab_widget.addTab(general_tab, "General")
        tab_widget.addTab(hotkeys_tab, "Hotkeys")
        
        layout.addWidget(tab_widget)
        
        # Save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def save_settings(self):
        # Save existing settings
        self.settings_manager.set_typing_effect_enabled(self.typing_effect_checkbox.isChecked())
        self.settings_manager.set_typing_effect_speed(self.speed_slider.value())
        self.settings_manager.set_typing_effect_particle_count(self.particle_slider.value())
        
        # Hotkeys are saved immediately when edited
        self.accept()