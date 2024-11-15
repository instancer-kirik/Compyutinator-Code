from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from riskkit.enums import WingType, WingStatus
from .wing_config import WingConfig

@dataclass
class Wing:
    """Represents a project wing/extension"""
    id: str
    name: str
    type: WingType
    description: str = ""
    version: str = "0.1.0"
    status: WingStatus = WingStatus.DEVELOPMENT
    config: WingConfig = field(default_factory=WingConfig)
    path: Optional[Path] = None
    entry_points: List[str] = field(default_factory=list)
    def __post_init__(self):
        if self.path:
            # Load existing config if available
            loaded_config = WingConfig.load(self.path)
            if loaded_config:
                self.config = loaded_config
                
    def save_config(self) -> bool:
        """Save wing configuration"""
        if not self.path:
            return False
        return self.config.save(self.path)

    def to_dict(self) -> dict:
        """Convert wing to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "conflicts": self.conflicts,
            "entry_points": self.entry_points,
            "config": self.config.to_dict(),
            "path": str(self.path) if self.path else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.author,
            "tags": self.tags,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Wing':
        if 'path' in data and data['path']:
            data['path'] = Path(data['path'])
        data['type'] = WingType(data['type'])
        data['status'] = WingStatus(data['status'])
        if 'config' in data:
            data['config'] = WingConfig.from_dict(data['config'])
        return cls(**data)