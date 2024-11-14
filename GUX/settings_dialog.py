from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QSlider, QCheckBox, QPushButton, QTabWidget,
                           QTableWidget, QTableWidgetItem, QKeySequenceEdit, QWidget, QGroupBox, QDialogButtonBox, QMessageBox)
from PyQt6.QtCore import Qt
import logging

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
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Typing Effect Settings
        typing_group = QGroupBox("Typing Effect")
        typing_layout = QVBoxLayout()
        
        self.typing_effect_checkbox = QCheckBox("Enable Typing Effect")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.particle_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_slider.setRange(0, 20)
        
        typing_layout.addWidget(self.typing_effect_checkbox)
        typing_layout.addWidget(QLabel("Effect Speed:"))
        typing_layout.addWidget(self.speed_slider)
        typing_layout.addWidget(QLabel("Particle Count:"))
        typing_layout.addWidget(self.particle_slider)
        typing_group.setLayout(typing_layout)
        
        layout.addWidget(typing_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_settings(self):
        """Load settings from ConfigManager"""
        app_config = self.config_manager.app_config
        self.typing_effect_checkbox.setChecked(app_config.typing_effect_enabled)
        self.speed_slider.setValue(app_config.typing_effect_speed)
        self.particle_slider.setValue(app_config.typing_effect_particle_count)

    def save_settings(self):
        """Save settings using ConfigManager"""
        try:
            self.config_manager.app_config.typing_effect_enabled = self.typing_effect_checkbox.isChecked()
            self.config_manager.app_config.typing_effect_speed = self.speed_slider.value()
            self.config_manager.app_config.typing_effect_particle_count = self.particle_slider.value()
            
            # Save to disk
            self.config_manager._save_config(
                self.config_manager.config_dir / 'app_config.json',
                self.config_manager.app_config
            )
            
            # Emit change signal
            self.config_manager.config_changed.emit('app_config', self.config_manager.app_config)
            
            self.accept()
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")