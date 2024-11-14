from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

@dataclass
class WindowConfig:
    """Window configuration"""
    title: str = "Computinator Code"
    geometry: List[int] = field(default_factory=lambda: [100, 100, 800, 600])
    
    # Window behavior
    enable_snap: bool = True
    snap_threshold: int = 20
    enable_fade: bool = True
    fade_opacity: float = 0.85
    save_state: bool = True
    animation_duration: int = 200
    default_opacity: float = 1.0
    
    # Layout
    default_docks: List[str] = field(default_factory=lambda: [
        "File Explorer", "Code Editor", "Terminal",
        "AI Chat", "Symbolic Linker", "Sticky Notes",
        "Process Manager", "Vaults Manager", "Projects Manager"
    ])
    
    layout: Dict[str, List[str]] = field(default_factory=lambda: {
        "left": ["File Explorer", "Symbolic Linker"],
        "right": ["Code Editor", "Sticky Notes"],
        "bottom": ["Terminal", "Process Manager"]
    })

@dataclass
class ApiConfig:
    """API configuration"""
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
        if not self.socket_url and self.base_url:
            self.socket_url = f"ws://{self.base_url.split('://')[-1]}/socket"
        if not self.auth_url and self.base_url:
            self.auth_url = f"{self.base_url}/auth"
        if not self.cache_dir:
            self.cache_dir = Path.home() / ".computinator" / "cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)

@dataclass
class AppConfig:
    """Application configuration"""
    app_data_dir: Path = field(default_factory=lambda: Path.home() / ".computinator")
    vault_path: Path = field(default_factory=lambda: Path.home() / "ComputinatorVault")
    
    # Features
    typing_effect_enabled: bool = True
    typing_effect_speed: int = 100
    typing_effect_particle_count: int = 10
    
    # System
    offline_mode: bool = False
    show_notifications: bool = True
    max_reconnect_attempts: int = 5
    reconnect_interval: int = 5000
    
    # Integrations
    api: ApiConfig = field(default_factory=ApiConfig)
    window: WindowConfig = field(default_factory=WindowConfig)

    def __post_init__(self):
        self.app_data_dir = Path(self.app_data_dir)
        self.vault_path = Path(self.vault_path)
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.vault_path.mkdir(parents=True, exist_ok=True) 