from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import os
import logging
import sys

logger = logging.getLogger(__name__)

@dataclass
class ApiConfig:
    """Unified API configuration"""
    base_url: str = "http://localhost:4000"
    api_key: Optional[str] = None
    org_id: Optional[str] = None
    socket_url: Optional[str] = None
    cache_dir: Optional[Path] = None
    max_retries: int = 3
    offline_mode: bool = False
    auth_url: Optional[str] = None
    token: Optional[str] = None

    def __post_init__(self):
        if not self.socket_url:
            self.socket_url = f"ws://{self.base_url.split('://')[-1]}/socket"
        if not self.auth_url:
            self.auth_url = f"{self.base_url}/auth"
        if not self.cache_dir:
            self.cache_dir = Path.home() / ".riskkit" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

class ConfigManager:
    """Unified configuration management"""
    def __init__(self, app_name: str = "Compyutinator"):
        # Platform-specific config directory
        if sys.platform == "win32":
            self.config_dir = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~"))) / app_name
        elif sys.platform == "darwin":
            self.config_dir = Path.home() / "Library" / "Application Support" / app_name
        else:
            self.config_dir = Path.home() / ".local" / "share" / app_name
            
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = self.config_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Config files
        self.main_config = self.data_dir / "config.json"
        self.theme_config = self.data_dir / "theme.json"
        self.workspace_config = self.data_dir / "workspace.json"
        
        # Load configs
        self.config = self._load_config(self.main_config, self.get_default_config())
        self.theme = self._load_config(self.theme_config, self.get_default_theme())
        self.workspace = self._load_config(self.workspace_config, {})

    def get_api_config(self) -> ApiConfig:
        """Get API configuration from settings"""
        return ApiConfig(
            base_url=self.get("api_url", "http://localhost:4000"),
            api_key=self.get("api_key"),
            org_id=self.get("org_id"),
            socket_url=self.get("websocket_url"),
            cache_dir=self.data_dir / "cache",
            max_retries=self.get("max_retries", 3),
            offline_mode=self.get("offline_mode", False)
        )

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "api_url": "http://localhost:4000",
            "websocket_url": "ws://localhost:4000/socket",
            "api_key": None,
            "org_id": None,
            "offline_mode": False,
            "max_retries": 3,
            "max_history_length": 10,
            "splash": True,
            "terminal_tips": True,
            "explorer_default_open": True,
            "open_last_file": False,
            "subscribe_to_all_channels": True
        }

    def _load_config(self, path: Path, defaults: Dict) -> Dict:
        """Load config with fallback to defaults"""
        try:
            if path.exists():
                with open(path, 'r') as f:
                    return {**defaults, **json.load(f)}
            else:
                self._save_config(path, defaults)
                return defaults
        except Exception as e:
            logger.error(f"Error loading config {path}: {e}")
            return defaults

    def _save_config(self, path: Path, data: Dict):
        """Save config safely"""
        try:
            temp_path = path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=4)
            temp_path.replace(path)  # Atomic replace
        except Exception as e:
            logger.error(f"Error saving config {path}: {e}")

    def get_default_theme(self) -> Dict[str, Any]:
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

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value with optional default"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set config value and save"""
        self.config[key] = value
        self._save_config(self.main_config, self.config)

    def get_theme(self, key: str, default: Any = None) -> Any:
        """Get theme value with optional default"""
        return self.theme.get(key, default)

    def set_theme(self, key: str, value: Any):
        """Set theme value and save"""
        self.theme[key] = value
        self._save_config(self.theme_config, self.theme)

    def save_workspace_state(self, workspace: str, state: Dict):
        """Save workspace-specific state"""
        self.workspace[workspace] = state
        self._save_config(self.workspace_config, self.workspace)

    def get_workspace_state(self, workspace: str) -> Optional[Dict]:
        """Get workspace-specific state"""
        return self.workspace.get(workspace)

    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user-specific preferences"""
        return self.get("preferences", {})

    def set_user_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences"""
        self.set("preferences", preferences)

    def get_recent_files(self) -> List[str]:
        """Get list of recently opened files"""
        return self.get("recent_files", [])

    def add_recent_file(self, filepath: str, max_entries: int = 10):
        """Add file to recent files list"""
        recent = self.get_recent_files()
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        self.set("recent_files", recent[:max_entries])