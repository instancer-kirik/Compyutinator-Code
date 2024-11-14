from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

# class ProjectType(Enum):
#     PYTHON = "python"
#     JAVASCRIPT = "javascript"
#     RUST = "rust"
#     UNKNOWN = "unknown"

@dataclass
class BaseConfig:
    name: str
    path: Path
    # project_type: ProjectType = ProjectType.UNKNOWN
    description: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path) 