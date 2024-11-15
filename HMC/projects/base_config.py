from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

class ProjectType(Enum):
    LOCAL = "local"
    RESOLVINATOR = "resolvinator"
    UNKNOWN = "unknown"

@dataclass
class BaseProjectData:
    """Base project data and metadata"""
    name: str
    path: Path
    project_type: ProjectType = ProjectType.UNKNOWN
    description: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Basic metadata
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "repository_url": None,
        "documentation_url": None,
        "issue_tracker_url": None,
        "keywords": [],
        "categories": [],
        "license": None,
        "contributors": [],
        "maintainers": []
    })

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
