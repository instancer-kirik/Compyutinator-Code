from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
from riskkit.enums import ProjectType
from .project_config import ProjectConfig
import logging
from .wings_manager import WingsManager
from HMC.code_manager import CodeManager
from HMC.projects.project_wing import Wing
from riskkit.enums import WingType, WingStatus

@dataclass
class Project:
    name: str
    path: Path
    type: ProjectType
    config: ProjectConfig
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.type, str):
            self.type = ProjectType(self.type)
        
        # Initialize managers
        self.wings_manager = WingsManager(self.config)
        self.code_manager = CodeManager(self.cccore)
        
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
            type=project_type,
            config=config
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'path': str(self.path),
            'type': self.type.value if isinstance(self.type, ProjectType) else self.type,
            'config': {
                'name': self.config.name,
                'project_type': self.config.project_type.value,
                'path': str(self.config.path),
                'description': self.config.description,
                'status': self.config.status,
                'relationships': self.config.relationships,
                'created_at': self.config.created_at.isoformat(),
                'updated_at': self.config.updated_at.isoformat(),
                'directory_structure': self.config.directory_structure,
                'dev_settings': self.config.dev_settings,
                'integrations': self.config.integrations,
                'tracking': self.config.tracking,
                'metadata': self.config.metadata,
                'quality_metrics': self.config.quality_metrics
            }
        }
        
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
        