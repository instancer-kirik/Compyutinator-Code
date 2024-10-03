# settings_manager.py
from PyQt6.QtCore import QSettings
import os

from PyQt6.QtCore import QSettings
import os

class SettingsManager:
    def __init__(self):
        self.settings =  QSettings("instance.select", "Computinator Code")
        self.ensure_app_data_dir()
        self.ensure_vault_path()
        self.ensure_typing_effect_settings()

    def get_value(self, key, default=None):
        return self.settings.value(key, default)  # Changed from getValue to value

    def set_value(self, key, value):
        self.settings.setValue(key, value)

    def save_layout(self, main_window):
        self.set_value("geometry", main_window.saveGeometry())
        self.set_value("windowState", main_window.saveState())

    def load_layout(self, main_window):
        geometry = self.get_value("geometry")
        window_state = self.get_value("windowState")
        if geometry:
            main_window.restoreGeometry(geometry)
        if window_state:
            main_window.restoreState(window_state)

    def get_vault_path(self):
        return self.get_value("vault_path", "")

    def set_vault_path(self, path):
        self.set_value("vault_path", path)

    def ensure_vault_path(self):
        vault_path = self.get_vault_path()
        if not vault_path:
            # Set a default vault path if not set
            default_vault_path = os.path.join(os.path.expanduser("~"), "ComputinatorVault")
            self.set_value("vault_path", default_vault_path)
            vault_path = default_vault_path
        if not os.path.exists(vault_path):
            os.makedirs(vault_path)

    def ensure_typing_effect_settings(self):
        if not self.get_value("typing_effect_enabled"):
            self.set_value("typing_effect_enabled", True)
        if not self.get_value("typing_effect_speed"):
            self.set_value("typing_effect_speed", 100)  # milliseconds
        if not self.get_value("typing_effect_particle_count"):
            self.set_value("typing_effect_particle_count", 10)

    def get_typing_effect_enabled(self):
        return self.get_value("typing_effect_enabled", True)

    def set_typing_effect_enabled(self, enabled):
        self.set_value("typing_effect_enabled", enabled)

    def get_typing_effect_speed(self):
        return self.get_value("typing_effect_speed", 100)

    def set_typing_effect_speed(self, speed):
        self.set_value("typing_effect_speed", speed)

    def get_typing_effect_particle_count(self):
        return self.get_value("typing_effect_particle_count", 10)

    def set_typing_effect_particle_count(self, count):
        self.set_value("typing_effect_particle_count", count)

    def get_settings(self):
        return self.settings
    # Add other settings-related methods as needed

    def ensure_app_data_dir(self):
        app_data_dir = self.get_value("app_data_dir")
        if not app_data_dir:
            default_app_data_dir = os.path.join(os.path.expanduser("~"), ".computinator_code")
            self.set_value("app_data_dir", default_app_data_dir)
        if not os.path.exists(self.get_value("app_data_dir")):
            os.makedirs(self.get_value("app_data_dir"))