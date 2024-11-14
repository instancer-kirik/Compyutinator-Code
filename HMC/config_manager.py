from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import os
import logging
import sys
from PyQt6.QtCore import QObject, pyqtSignal, QSettings

from .config.types import AppConfig, WindowConfig, ApiConfig

class ConfigManager(QObject):
    """Unified configuration management"""
    
    config_changed = pyqtSignal(str, object)
    
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        
        # Qt Settings for UI state (migrated from SettingsManager)
        self.qsettings = QSettings("instance.select", "Computinator Code")
        
        # Load configurations
        self.app_config = self._load_config('app_config.json', AppConfig())
        self.projects_config = self._load_config('projects.json', {})
        self.theme_config = self._load_config('theme.json', self._default_theme())
    @property
    def window(self) -> WindowConfig:
        return self.app_config.window

    @property
    def api(self) -> ApiConfig:
        return self.app_config.api

    def get_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Get configuration for a specific project"""
        return self.projects_config.get(project_name)

    def _default_theme(self) -> Dict[str, Any]:
        """Default theme configuration"""
        return {
            "main_window_color": "#2E3440",
            "window_color": "#3B4252",
            "header_color": "#4C566A",
            "theme_color": "#81A1C1",
            "sidebar_bg": "#1E1E1E",
            "text_color": "#FFFFFF",
            "accent_color": "#007ACC",
            "tab_colors": {
                "0": "#81A1C1",
                "1": "#88C0D0",
                "2": "#5E81AC"
            }
        }

    def _load_config(self, path: Path, defaults: Any) -> Dict:
        """Load configuration with defaults"""
        try:
            if path.exists():
                with open(path, 'r') as f:
                    loaded = json.load(f)
                    if isinstance(defaults, dict):
                        return {**defaults, **loaded}
                    return loaded
            self._save_config(path, defaults)
            return defaults if isinstance(defaults, dict) else asdict(defaults)
        except Exception as e:
            logging.error(f"Error loading config {path}: {e}")
            return defaults if isinstance(defaults, dict) else asdict(defaults)

    def _save_config(self, path: Path, data: Any):
        """Save configuration safely"""
        try:
            temp_path = path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data if isinstance(data, dict) else asdict(data), 
                         f, indent=4)
            temp_path.replace(path)  # Atomic replace
        except Exception as e:
            logging.error(f"Error saving config {path}: {e}") 

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get value from QSettings"""
        return self.qsettings.value(key, default)

    def set_value(self, key: str, value: Any):
        """Set value in QSettings"""
        self.qsettings.setValue(key, value)
        self.config_changed.emit(key, value)

    def save_layout(self, main_window):
        """Save window layout"""
        self.set_value("geometry", main_window.saveGeometry())
        self.set_value("windowState", main_window.saveState())

    def load_layout(self, main_window):
        """Load window layout"""
        geometry = self.get_value("geometry")
        window_state = self.get_value("windowState")
        if geometry:
            main_window.restoreGeometry(geometry)
        if window_state:
            main_window.restoreState(window_state)
