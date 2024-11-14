from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .base_config import ProjectType
from .project_config import ProjectConfig
import logging
from .wings_manager import WingsManager

from HMC.projects.project_wing import Wing
from .project_types import WingType, WingStatus
import uuid
@dataclass
class Project:
    name: str
    path: Path
    project_type: ProjectType
    config: ProjectConfig
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cccore: Any = field(default=None)
    wings: Dict[str, Wing] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.project_type, str):
            self.project_type = ProjectType(self.project_type)
            
        # Initialize wings from config
        if hasattr(self.config, 'wings'):
            self.wings = self.config.wings
        else:
            self.wings = {}
            
        # Initialize managers
        self.wings_manager = WingsManager(self.config)
        if self.cccore:
            self.code_manager = self.cccore.code_manager
        else:
            self.code_manager = None
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create Project instance from dictionary"""
        return cls(
            name=data.get('name', ''),
            path=Path(data.get('path', '')),
            project_type=data.get('project_type', ProjectType.LOCAL),
            config=ProjectConfig(**data.get('config', {})) if data.get('config') else None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Project to dictionary"""
        return {
            'name': self.name,
            'path': str(self.path),
            'project_type': self.project_type,
            'config': asdict(self.config) if self.config else None
        }   
    def add_wing(self, name: str, wing_type: WingType, description: str = "", 
                config: Dict[str, Any] = None) -> Optional[Wing]:
        """Add a new wing to the project"""
        return self.wings_manager.create_wing(name, wing_type, description, config)
        
    @classmethod
    def create(cls, name: str, path: str | Path, project_type: ProjectType = ProjectType.LOCAL) -> 'Project':
        """Create a new project instance with automatic wing detection"""
        path = Path(path)
        
        # Create base config
        config = ProjectConfig(
            name=name,
            project_type=project_type,
            path=path
        )
        
        # Initialize wings manager
        wing_manager = WingsManager(config)
        
        # Auto-detect and set up language wings
        detected_wings = []
        
        # Python detection
        if list(path.glob("*.py")) or (path / "pyproject.toml").exists():
            detected_wings.append(("python", WingType.LANGUAGE))
            
        # Mojo detection
        if list(path.glob("*.mojo")):
            detected_wings.append(("mojo", WingType.LANGUAGE))
            
        # Create detected wings
        for wing_name, wing_type in detected_wings:
            wing_manager.create_wing(
                name=wing_name,
                wing_type=wing_type,
                description=f"{wing_name.title()} language support"
            )
        
        return cls(
            name=name,
            path=path,
            project_type=project_type,
            config=config
        )
        
    def calculate_risk_score(self, probability: str, impact: str) -> int:
        """Calculate risk score based on probability and impact"""
        try:
            risk_config = self.config.management.get("risk", {}).get("matrix_config", {})
            p_weight = risk_config.get("probability_weights", {}).get(probability, 1)
            i_weight = risk_config.get("impact_weights", {}).get(impact, 1)
            return p_weight * i_weight
        except Exception as e:
            logging.error(f"Error calculating risk score: {e}")
            return 1

    def needs_risk_review(self, last_review_date: datetime) -> bool:
        """Check if risk needs review based on configuration"""
        try:
            review_period = int(self.config.management.get("risk", {})
                              .get("notification_preferences", {})
                              .get("review_period_days", 30))
            days_since_review = (datetime.now() - last_review_date).days
            return days_since_review >= review_period
        except Exception as e:
            logging.error(f"Error checking risk review: {e}")
            return True
        
    @classmethod
    def from_config(cls, config: ProjectConfig) -> 'Project':
        return cls(
            name=config.name,
            path=config.path,
            project_type=config.project_type,
            config=config
        )
        