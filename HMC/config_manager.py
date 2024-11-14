from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import os
import stat
import logging
import sys
from PyQt6.QtCore import QObject, pyqtSignal, QSettings
from typing import Union
from .config.types import AppConfig, WindowConfig, ApiConfig
from .projects.project_config import ProjectConfig
from HMC.config.ai_config import AIConfig
class ConfigManager(QObject):
    """Unified configuration management system"""
    
    # Signals
    config_changed = pyqtSignal(str, object)  # Key, new value
    project_config_changed = pyqtSignal(str)  # Project name
    theme_changed = pyqtSignal(dict)  # New theme
    
    def __init__(self, app_dir: Optional[Path] = None):
        super().__init__()
        
        # Initialize paths
        self.app_dir = app_dir if isinstance(app_dir, Path) else Path(app_dir) if app_dir else Path.home() / '.computinator-code'
        self.config_dir = self.app_dir / 'config'
        self.ensure_directories()
        
        # Qt Settings for UI state
        self.qsettings = QSettings("instance.select", "Computinator Code")
        
        # Configuration storage
        self.app_config = self._load_config('app_config.json', AppConfig)
        self._window_config = self.app_config.window if hasattr(self.app_config, 'window') else WindowConfig()
        
        # Projects config needs special handling since it's a dict
        try:
            self.projects_config = self._load_config('projects.json', dict, default={})
        except Exception as e:
            logging.error(f"Error loading projects config: {e}")
            self.projects_config = {}
            
        self.theme_config = self._load_config('theme.json', dict, default=self._default_theme())
        
        # Cache for frequently accessed values
        self._cache: Dict[str, Any] = {}
        
        logging.info("ConfigManager initialized")

    def ensure_directories(self):
        """Ensure required directories exist"""
        try:
            self.app_dir.mkdir(exist_ok=True)
            self.config_dir.mkdir(exist_ok=True)
            logging.info(f"Ensured config directories at {self.config_dir}")
        except Exception as e:
            logging.error(f"Failed to create config directories: {e}")
            raise

    def _load_config(self, filename: str, config_class: type, default: Any = None) -> Any:
        """Load configuration from file with proper serialization"""
        try:
            config_path = self.config_dir / filename
            if config_path.exists():
                with open(config_path) as f:
                    data = json.load(f)
                if config_class == dict:
                    return data
                return self._deserialize_config(data, config_class)
            else:
                # Create default config
                if default is not None:
                    config = default
                else:
                    config = config_class()
                    
                serialized = self._serialize_config(config)
                with open(config_path, 'w') as f:
                    json.dump(serialized, f, indent=4)
                return config
                
        except Exception as e:
            logging.error(f"Error loading config {filename}: {e}")
            return default if default is not None else config_class()

    def _serialize_config(self, obj: Any) -> dict:
        """Convert config object to JSON-serializable dict"""
        if isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dataclass_fields__'):
            result = {}
            for k, v in asdict(obj).items():
                result[k] = self._serialize_config(v)
            return result
        elif isinstance(obj, dict):
            return {k: self._serialize_config(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_config(v) for v in obj]
        return obj

    def _deserialize_config(self, data: dict, config_class: type) -> Any:
        """Convert JSON dict to config object"""
        if not data:
            return config_class()
        
        if not hasattr(config_class, '__dataclass_fields__'):
            return data
            
        field_values = {}
        for field_name, field in config_class.__dataclass_fields__.items():
            if field_name not in data:
                continue
                
            value = data[field_name]
            if field.type == Path:
                field_values[field_name] = Path(value)
            elif hasattr(field.type, '__dataclass_fields__'):
                field_values[field_name] = self._deserialize_config(value, field.type)
            else:
                field_values[field_name] = value
                
        return config_class(**field_values)

    @property
    def window(self) -> WindowConfig:
        """Get window configuration"""
        return self._window_config

    @property
    def api(self) -> ApiConfig:
        """Get API configuration"""
        return self.app_config.api

    def get_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Get configuration for a specific project"""
        if project_name not in self.projects_config:
            logging.warning(f"No config found for project: {project_name}")
            return None
        return self.projects_config[project_name]

    def update_project_config(self, project_name: str, config: Union[ProjectConfig, dict]):
        """Update configuration for a specific project"""
        try:
            if isinstance(config, dict):
                config = ProjectConfig(**config)
            self.projects_config[project_name] = config
            self._save_config(self.config_dir / 'projects.json', self.projects_config)
            self.project_config_changed.emit(project_name)
            logging.info(f"Updated config for project: {project_name}")
        except Exception as e:
            logging.error(f"Failed to update project config: {e}")

    def get_theme(self, theme_name: Optional[str] = None) -> dict:
        """Get theme configuration"""
        if theme_name and theme_name in self.theme_config.get('themes', {}):
            return self.theme_config['themes'][theme_name]
        return self.theme_config.get('current_theme', self._default_theme())

    def _default_theme(self) -> Dict[str, Any]:
        """Default theme configuration"""
        return {
            "name": "Nord Dark",
            "version": "1.0",
            "colors": {
                "main_window": "#2E3440",
                "window": "#3B4252",
                "header": "#4C566A",
                "theme": "#81A1C1",
                "sidebar": "#1E1E1E",
                "text": "#FFFFFF",
                "accent": "#007ACC"
            },
            "tab_colors": {
                "active": "#81A1C1",
                "inactive": "#88C0D0",
                "hover": "#5E81AC"
            },
            "syntax": {
                "keyword": "#81A1C1",
                "string": "#A3BE8C",
                "comment": "#616E88",
                "function": "#88C0D0",
                "variable": "#D8DEE9"
            }
        }

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get value from QSettings with caching"""
        if key not in self._cache:
            self._cache[key] = self.qsettings.value(key, default)
        return self._cache[key]

    def set_value(self, key: str, value: Any):
        """Set value in QSettings and cache"""
        self.qsettings.setValue(key, value)
        self._cache[key] = value
        self.config_changed.emit(key, value)

    def save_window_state(self, main_window):
        """Save complete window state"""
        try:
            self.set_value("geometry", main_window.saveGeometry())
            self.set_value("windowState", main_window.saveState())
            self.set_value("size", main_window.size())
            self.set_value("pos", main_window.pos())
            logging.debug("Saved window state")
        except Exception as e:
            logging.error(f"Failed to save window state: {e}")

    def restore_window_state(self, main_window):
        """Restore complete window state"""
        try:
            geometry = self.get_value("geometry")
            window_state = self.get_value("windowState")
            size = self.get_value("size")
            pos = self.get_value("pos")
            
            if geometry:
                main_window.restoreGeometry(geometry)
            if window_state:
                main_window.restoreState(window_state)
            if size:
                main_window.resize(size)
            if pos:
                main_window.move(pos)
            logging.debug("Restored window state")
        except Exception as e:
            logging.error(f"Failed to restore window state: {e}")

    def clear_cache(self):
        """Clear the configuration cache"""
        self._cache.clear()
        logging.debug("Cleared config cache")

    def _save_config(self, path: Path, data: Any):
        """Save configuration with proper security"""
        if not self._validate_path(path):
            raise ValueError(f"Invalid config path: {path}")
        if not self._validate_config_data(data):
            raise ValueError("Invalid config data")
        
        try:
            temp_path = path.with_suffix('.tmp')
            serialized_data = self._serialize_config(data)
            
            # Set secure file permissions (read/write)
            file_mode = stat.S_IRUSR | stat.S_IWUSR  # 600 permissions
            
            # Write to temporary file first with secure permissions
            fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT, file_mode)
            with os.fdopen(fd, 'w') as f:
                json.dump(serialized_data, f, indent=4, sort_keys=True)
                
            # Ensure secure permissions on the final file
            os.chmod(temp_path, file_mode)
            
            # Atomic replace
            temp_path.replace(path)
            os.chmod(path, file_mode)
            
            logging.debug(f"Saved config to {path}")
            
        except Exception as e:
            logging.error(f"Error saving config {path}: {e}")
            if temp_path.exists():
                temp_path.unlink()  # Clean up temp file
            raise

    # Add these methods for typing effect compatibility
    def get_typing_effect_enabled(self) -> bool:
        """Get typing effect enabled state"""
        return self.app_config.typing_effect.enabled

    def get_typing_effect_speed(self) -> int:
        """Get typing effect speed"""
        return self.app_config.typing_effect.speed

    def get_typing_effect_particle_count(self) -> int:
        """Get typing effect particle count"""
        return self.app_config.typing_effect.particle_count

    def set_typing_effect_enabled(self, enabled: bool):
        """Set typing effect enabled state"""
        self.app_config.typing_effect.enabled = enabled
        self._save_config(self.config_dir / 'app_config.json', self.app_config)
        self.config_changed.emit('typing_effect.enabled', enabled)

    def set_typing_effect_speed(self, speed: int):
        """Set typing effect speed"""
        self.app_config.typing_effect.speed = speed
        self._save_config(self.config_dir / 'app_config.json', self.app_config)
        self.config_changed.emit('typing_effect.speed', speed)

    def set_typing_effect_particle_count(self, count: int):
        """Set typing effect particle count"""
        self.app_config.typing_effect.particle_count = count
        self._save_config(self.config_dir / 'app_config.json', self.app_config)
        self.config_changed.emit('typing_effect.particle_count', count)

    # Add hotkey compatibility
    def get_hotkey(self, action_name: str) -> Optional[str]:
        """Get hotkey for action"""
        return self.get_value(f'hotkeys.{action_name}')

    def set_hotkey(self, action_name: str, hotkey: str):
        """Set hotkey for action"""
        self.set_value(f'hotkeys.{action_name}', hotkey)

    def get_ai_config(self) -> AIConfig:
        """Get AI configuration"""
        config_data = self._load_config('ai_config.json', dict)
        if not config_data:
            # Return default config
            return AIConfig.default_local()
        return AIConfig.from_dict(config_data)

    def save_ai_config(self, config: AIConfig):
        """Save AI configuration"""
        self._save_config(self.config_dir / 'ai_config.json', config.to_dict())
        self.config_changed.emit('ai_config', config)

    def get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key"""
        return self.get_value('openai_api_key')

    def get_anthropic_key(self) -> Optional[str]:
        """Get Anthropic API key"""
        return self.get_value('anthropic_api_key')
