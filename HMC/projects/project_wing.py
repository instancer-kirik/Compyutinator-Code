from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from riskkit.enums import WingType, WingStatus

@dataclass
class Wing:
    """Represents a project wing/extension"""
    id: str
    name: str
    type: WingType
    description: str = ""
    version: str = "0.1.0"
    status: WingStatus = WingStatus.DEVELOPMENT
    
    # Wing Structure
    entry_points: Dict[str, str] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    
    # Metadata
    path: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

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
            "config": self.config,
            "path": str(self.path) if self.path else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.author,
            "tags": self.tags,
            "metadata": self.metadata
        }