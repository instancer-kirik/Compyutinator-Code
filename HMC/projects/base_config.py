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
    name: str
    path: Path
    project_type: ProjectType = ProjectType.UNKNOWN
    description: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path) 


class ProjectConfig(BaseProjectData)    :
    visibility: str = "private"
    domain: str = ""
    version: str = "0.1.0"
        # Adding missing metadata fields
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "repository_url": None,
        "documentation_url": None,
        "issue_tracker_url": None,
        "keywords": [],
        "categories": [],
        "language": None,
        "framework": None,
        "dependencies": {},
        "dev_dependencies": {},
        "contributors": [],
        "maintainers": [],
        "license": None,
        "primary_language": None,
        "entry_points": {"main": "src/main.py"},
        "dependencies": {},
        "dev_dependencies": {},
        "cloud_services": {},
        "databases": {},
        "apis": {},
        "tools": {}
    })
