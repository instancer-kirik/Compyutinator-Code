from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

class ProjectType(Enum):
    LOCAL = "local"
    RESOLVINATOR = "resolvinator"
    UNKNOWN = "unknown"

class WingType(Enum):
    CORE = "core"
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    TOOL = "tool"
    SERVICE = "service"
    THEME = "theme"
    DATA = "data"
    UTILITY = "utility"
    CUSTOM = "custom"

class WingStatus(Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEVELOPMENT = "development"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"

@dataclass
class ProjectSettings:
    """Core project settings"""
    tracking: Dict[str, Any] = field(default_factory=lambda: {
        "activity": [],
        "lifecycle_stage": "development",
        "symbols": {}
    })

@dataclass
class BaseProjectData:
    """Base project data structure"""
    name: str
    path: Path
    project_type: ProjectType = ProjectType.UNKNOWN
    description: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    settings: ProjectSettings = field(default_factory=ProjectSettings)

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)

@dataclass
class Resource:
    """Project resource configuration"""
    id: str
    name: str
    type: str = ""  # Financial/Human/Material/Technical
    value: float = 0.0
    quantity: float = 0.0
    unit: str = ""  # Currency/Hours/Units/etc
    status: str = "Available"
    allocation: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "value": self.value,
            "quantity": self.quantity,
            "unit": self.unit,
            "status": self.status,
            "allocation": self.allocation,
            "metadata": self.metadata
        }