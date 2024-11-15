from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .base_config import ProjectType
from .project_config import ProjectConfig
import logging
from .wings_manager import WingsManager
from .resource_manager import ResourceManager

from HMC.projects.project_wing import Wing
from .project_types import (
    DevelopmentStandards,
    RiskManagement,
    Resource,
    ProjectType,
    WingType,
    WingStatus
)
import uuid
@dataclass
class Project:
    name: str
    path: Path
    project_type: ProjectType
    config: ProjectConfig
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cccore: Any = field(default=None, repr=False)
    resources: Dict[str, 'Resource'] = field(default_factory=dict)
    wings_manager: Optional[WingsManager] = None
    
    def __post_init__(self):
        self.path = Path(self.path) if isinstance(self.path, str) else self.path
        self.project_type = ProjectType(self.project_type) if isinstance(self.project_type, str) else self.project_type
        
        self.wings_manager = WingsManager(self.config)
        self.code_manager = self.cccore.code_manager if self.cccore else None
        self.resource_manager = ResourceManager(self)
        
        self.config._project = self

    @property
    def risk_manager(self) -> RiskManagement:
        return self.config.risk_management

    @property
    def dev_standards(self) -> DevelopmentStandards:
        return self.config.dev_standards

    def calculate_risk_score(self, probability: str, impact: str) -> int:
        return self.risk_manager.calculate_risk_score(probability, impact)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create Project from dictionary"""
        wings_data = data.pop('wings', {})
        project = cls(
            name=data['name'],
            path=Path(data['path']),
            project_type=ProjectType(data['project_type']),
            config=ProjectConfig.from_dict(data['config']) if data.get('config') else None,
            id=data.get('id')
        )
        # Restore wings
        for wing_id, wing_data in wings_data.items():
            project.wings_manager.wings[wing_id] = Wing.from_dict(wing_data)
        return project

    def to_dict(self) -> Dict[str, Any]:
        """Convert Project to dictionary"""
        return {
            'name': self.name,
            'path': str(self.path),
            'project_type': self.project_type.value,
            'config': self.config.to_dict() if self.config else None,
            'id': self.id,
            'wings': {k: v.to_dict() for k, v in self.wings_manager.wings.items()}
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
        
        # Create project instance (WingsManager will be initialized in __post_init__)
        project = cls(
            name=name,
            path=path,
            project_type=project_type,
            config=config
        )
        
        return project
        
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
        
    def allocate_resource(self, resource_id: str, allocation: Dict[str, Any]) -> bool:
        """Allocate resource to project"""
        try:
            return self.resource_manager.allocate(resource_id, allocation)
        except Exception as e:
            logging.error(f"Error allocating resource: {e}")
            return False

    def get_resource_allocation(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get resource allocation details"""
        return self.resource_manager.get_allocation(resource_id)
        
    def get_technical_overview(self) -> str:
        """Generate technical overview"""
        generator = TechnicalOverviewGenerator(self.config)
        return generator.generate()
        