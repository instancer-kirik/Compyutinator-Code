from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
import logging

@dataclass
class WingConfig:
    """Configuration for a project wing"""
    build: Dict[str, Any] = field(default_factory=lambda: {
        "command": None,
        "args": [],
        "env": {},
        "dependencies": [],
        "scripts": {}
    })
    runtime: Dict[str, Any] = field(default_factory=lambda: {
        "entry_points": {},
        "environment": {},
        "requirements": []
    })
    development: Dict[str, Any] = field(default_factory=lambda: {
        "tools": [],
        "linters": [],
        "formatters": [],
        "test_framework": None
    })
    
    # Integration Settings
    integration: Dict[str, Any] = field(default_factory=lambda: {
        "dependencies": [],
        "conflicts": [],
        "optional_features": []
    })
    
    def save(self, path: Path) -> bool:
        """Save configuration to file"""
        try:
            with open(path / "wing_config.json", 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error saving wing config: {e}")
            return False
    
    @classmethod
    def load(cls, path: Path) -> Optional['WingConfig']:
        """Load configuration from file"""
        try:
            with open(path / "wing_config.json", 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            logging.error(f"Error loading wing config: {e}")
            return None
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "build": self.build,
            "runtime": self.runtime,
            "development": self.development,
            "integration": self.integration
        } 