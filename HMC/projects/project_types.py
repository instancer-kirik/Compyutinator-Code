from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

class ProjectType(Enum):
    LOCAL = "local"
    RESOLVINATOR = "resolvinator"
    UNKNOWN = "unknown"
class WingStatus(Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEVELOPMENT = "development"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"

class WingType(Enum):
    CORE = "core"           # Project core functionality
    LANGUAGE = "language"   # Language-specific support
    FRAMEWORK = "framework" # Framework integration
    TOOL = "tool"          # Development tools
    SERVICE = "service"     # External services
    THEME = "theme"        # UI/UX components
    DATA = "data"          # Data processing
    UTILITY = "utility"    # Helper functions
    CUSTOM = "custom"      # User-defined

@dataclass
class BaseProjectData:
    name: str
    path: Path
    project_type: ProjectType = ProjectType.UNKNOWN
    description: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict) 