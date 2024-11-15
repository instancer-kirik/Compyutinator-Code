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
    risk_appetite: str = "cautious"
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    tracking: Dict[str, Any] = field(default_factory=lambda: {
        "activity": [],
        "lifecycle_stage": "development",
        "symbols": {}
    })

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
    settings: ProjectSettings = field(default_factory=ProjectSettings)

@dataclass
class DevelopmentStandards:
    """Development standards and practices configuration"""
    code_style: Dict[str, Any] = field(default_factory=lambda: {
        "guide": "pep8",
        "max_complexity": 10,
        "formatters": [],
        "linters": []
    })
    testing: Dict[str, Any] = field(default_factory=lambda: {
        "framework": "pytest",
        "coverage_target": 80,
        "strategies": ["unit", "integration"]
    })
    security: Dict[str, Any] = field(default_factory=lambda: {
        "scan_frequency": "weekly",
        "vulnerability_threshold": "high"
    })

@dataclass
class RiskManagement:
    """Risk management configuration"""
    risk_appetite: str = "cautious"
    matrix_config: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "probability_weights": {
            "rare": 1,
            "unlikely": 2,
            "possible": 3,
            "likely": 4,
            "certain": 5
        },
        "impact_weights": {
            "negligible": 1,
            "minor": 2,
            "moderate": 3,
            "major": 4,
            "severe": 5
        }
    })
    notification_preferences: Dict[str, Any] = field(default_factory=lambda: {
        "review_period_days": 30,
        "high_risk_threshold": 12
    })

    def calculate_risk_score(self, probability: str, impact: str) -> int:
        """Calculate risk score based on probability and impact"""
        p_weight = self.matrix_config["probability_weights"].get(probability, 1)
        i_weight = self.matrix_config["impact_weights"].get(impact, 1)
        return p_weight * i_weight

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
@dataclass
class TechnicalConfig:
    """Technical configuration management"""
    tech_stack: Dict[str, Any] = field(default_factory=lambda: {
        "languages": [],
        "frameworks": [],
        "primary_language": None,
        "entry_points": {"main": "src/main.py"}
    })
    components: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "languages": {},
        "frameworks": {},
        "services": {},
        "databases": {},
        "apis": {},
        "tools": {}
    })

    def validate(self) -> bool:
        if self.tech_stack["primary_language"] and \
           self.tech_stack["primary_language"] not in self.tech_stack["languages"]:
            return False
        return True
@dataclass
class DevelopmentConfig:
    """Development environment and standards"""
    dev_settings: Dict[str, Any] = field(default_factory=lambda: {
        "environment": {
            "variables": {},
            "virtual_env": None,
            "required_tools": [],
            "tool_versions": {},
            "workspace_path": None,
            "file_extensions": [".py", ".json", ".yml"],
            "excluded_dirs": ["__pycache__", ".git", "venv"]
        },
        "commands": {
            "build": None,
            "run": None,
            "test": None,
            "lint": None,
            "deploy": None
        }
    })
    dev_standards: Dict[str, Any] = field(default_factory=lambda: {
        "code_style": {
            "style_guide": "pep8",
            "max_complexity": 10,
            "formatters": [],
            "linters": []
        },
        "testing": {
            "framework": "pytest",
            "coverage_target": 80,
            "strategies": ["unit", "integration"]
        }
    })
@dataclass
class TeamConfig:
    """Team and collaboration settings"""
    team: Dict[str, Any] = field(default_factory=lambda: {
        "roles": {
            "owners": [],
            "maintainers": [],
            "contributors": [],
            "reviewers": []
        },
        "communication": {
            "primary_channel": None,
            "meetings": {"schedule": [], "templates": {}}
        },
        "documentation": {
            "wiki": None,
            "api_docs": None,
            "architecture": None
        }
    })