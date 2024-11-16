from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import os
import logging
from pathlib import Path
from dataclasses import field
from HMC.system_analyzer import SystemInfo
from HMC.projects.project_structure import PROJECT_DIRECTORIES
from HMC.symbol_manager import CodeSymbol
from HMC.projects.project_wing import Wing, WingType
from HMC.projects.wings_manager import WingsManager
from .project_types import BaseProjectData, ProjectType

from .configs.technical_config import TechnicalConfig
from .configs.development_config import DevelopmentConfig
from .configs.project_management_config import ProjectManagementConfig
from .configs.project_operations_config import ProjectOperationsConfig
from .configs.team_config import TeamConfig
from .configs.security_config import SecurityConfig
from .configs.infrastructure_config import InfrastructureConfig
from .configs.quality_config import QualityConfig
from .configs.market_config import MarketConfig
from .wing_config import WingConfig

from .validators.config_validators import InfrastructureValidator, SecurityValidator

@dataclass
class ProjectConfig(BaseProjectData):
    """Project configuration and settings management"""
    # Add these fields
    visibility: str = "private"
    domain: str = ""
    version: str = "0.1.0"
    
    # Core configs
    technical: TechnicalConfig = field(default_factory=TechnicalConfig)
    development: DevelopmentConfig = field(default_factory=DevelopmentConfig)
    team: TeamConfig = field(default_factory=TeamConfig)
    operations: ProjectOperationsConfig = field(default_factory=ProjectOperationsConfig)
    project_management: ProjectManagementConfig = field(default_factory=ProjectManagementConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    infrastructure: InfrastructureConfig = field(default_factory=InfrastructureConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    
    # Project Structure
    directory_structure: Dict[str, Any] = field(default_factory=lambda: PROJECT_DIRECTORIES.copy())
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    symbols: Dict[Path, List['CodeSymbol']] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.project_type, str):
            self.project_type = ProjectType(self.project_type)

    def get_setting(self, *path: str, default: Any = None) -> Any:
        """Get setting using dot notation"""
        try:
            current = self.__dict__
            for key in path:
                if not isinstance(current, dict):
                    if hasattr(current, key):
                        current = getattr(current, key)
                    else:
                        return default
                else:
                    current = current.get(key, default)
            return current
        except Exception as e:
            logging.error(f"Error getting setting: {e}")
            return default

    def update_setting(self, *path: str, value: Any) -> bool:
        """Update setting value using dot notation"""
        try:
            current = self
            for key in path[:-1]:
                if hasattr(current, key):
                    current = getattr(current, key)
                else:
                    return False
            setattr(current, path[-1], value)
            return True
        except Exception as e:
            logging.error(f"Error updating setting: {e}")
            return False

    
    @property
    def wings(self) -> Dict[str, Wing]:
        # This should reference the Project's wings_manager
        if hasattr(self, '_project') and hasattr(self._project, 'wings_manager'):
            return self._project.wings_manager.wings
        return {}
    
    def add_wing(self, name: str, wing_type: WingType, description: str = "", 
                config: Optional[WingConfig] = None) -> Optional[Wing]:
        """Delegate wing management to Project"""
        if hasattr(self, '_project'):
            return self._project.add_wing(name, wing_type, description, config)
        return None

    @classmethod
    def from_folder(cls, folder_path: str, project_name: str) -> 'ProjectConfig':
        path = Path(folder_path)
        project_type = cls._detect_project_type(path)
        
        config = cls(
            name=project_name,
            path=path,
            project_type=project_type
        )
        
        # Auto-detect wings
        if (path / 'setup.py').exists() or list(path.glob('*.py')):
            wing = config.wings_manager.create_wing('python', WingType.LANGUAGE)
            if wing:
                config.wings[wing.id] = wing
                
        if (path / 'package.json').exists():
            wing = config.wings_manager.create_wing('javascript', WingType.LANGUAGE)
            if wing:
                config.wings[wing.id] = wing
                
        return config
    @classmethod
    def from_folder(cls, folder_path: str | Path, project_name: str) -> 'ProjectConfig':
        """Create a new ProjectConfig instance from a folder path"""
        logging.debug(f"Creating ProjectConfig from folder: {folder_path}")
        try:
            path = Path(folder_path)
            
            # Detect languages and frameworks
            languages = {}
            frameworks = {}
            
            # Python detection
            if list(path.glob("*.py")) or (path / "pyproject.toml").exists():
                languages["python"] = {
                    "version": "3.x",
                    "package_manager": "poetry" if (path / "pyproject.toml").exists() else "pip",
                    "virtual_env": "venv" if (path / "venv").exists() else None
                }
            
            # JavaScript/Node detection
            if (path / "package.json").exists():
                languages["javascript"] = {
                    "runtime": "node",
                    "package_manager": "yarn" if (path / "yarn.lock").exists() else "npm"
                }
            
            # Rust detection
            if (path / "Cargo.toml").exists():
                languages["rust"] = {
                    "package_manager": "cargo"
                }
            
            # Framework detection
            if (path / "requirements.txt").exists():
                with open(path / "requirements.txt") as f:
                    reqs = f.read()
                    if "django" in reqs.lower():
                        frameworks["django"] = {"version": "latest"}
                    if "flask" in reqs.lower():
                        frameworks["flask"] = {"version": "latest"}
            
            # Create instance
            instance = cls(
                name=project_name,
                project_type=ProjectType.LOCAL,
                path=path,
                description=f"Project created from folder: {folder_path}",
                status="active"
            )
            
            # Update components and metadata
            instance.tech_stack["languages"] = languages
            instance.tech_stack["frameworks"] = frameworks
            instance.tech_stack["primary_language"] = list(languages.keys())[0] if languages else None
            
            # Git detection
            if (path / ".git").is_dir():
                try:
                    import git
                    repo = git.Repo(path)
                    instance.metadata["repository_url"] = repo.remotes.origin.url
                except Exception as e:
                    logging.debug(f"Git repository detection failed: {e}")
            
            logging.debug(f"Successfully created ProjectConfig instance for {project_name}")
            return instance
            
        except Exception as e:
            logging.error(f"Error creating ProjectConfig from folder: {e}")
            raise

    # Delegate wing management to WingsManager
    def add_wing(self, name: str, wing_type: WingType, description: str = "", 
                config: Optional[WingConfig] = None) -> Optional[Wing]:
        """Delegate wing management to Project"""
        if hasattr(self, '_project'):
            return self._project.add_wing(name, wing_type, description, config)
        logging.error("Project instance not found, cannot add wing")
        return None

   
    @classmethod
    def load(cls, path: Path) -> Optional['ProjectConfig']:
        """Load ProjectConfig from a config file"""
        try:
            config_path = path / "project_config.json"
            if not config_path.exists():
                return None
                
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            # Convert datetime strings back to datetime objects
            if 'created_at' in data:
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'updated_at' in data:
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                
            return cls(**data)
            
        except Exception as e:
            logging.error(f"Error loading project config: {e}")
            return None
            
    def save(self) -> bool:
        """Save ProjectConfig to file"""
        try:
            config_path = self.path / "project_config.json"
            with open(config_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
            return True
        except Exception as e:
            logging.error(f"Error saving project config: {e}")
            return False

    def add_activity(self, activity_type: str, description: str):
        """Add new activity entry"""
        try:
            activity = {
                'type': activity_type,
                'description': description,
                'timestamp': datetime.now().isoformat()
            }
            self.settings.tracking["activity"].append(activity)
            self.save()
        except Exception as e:
            logging.error(f"Error adding activity: {e}")
            
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        """Create ProjectConfig from dictionary"""
        # Convert string dates to datetime objects
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            
        # Ensure path is Path object
        if 'path' in data and isinstance(data['path'], str):
            data['path'] = Path(data['path'])
            
        return cls(**data)
   
    def validate(self) -> bool:
        """Validate project configuration"""
        try:
            # Core validation
            if not all([self.name, self.path]):
                return False
            
            # Config component validation
            if not all([
                self.technical.validate(),
                self.development.validate(),
                self.team.validate(),
                self.operations.validate(),
                self.project_management.validate()
            ]):
                return False
               
            # Validate using separate validators
            if not InfrastructureValidator.validate_infrastructure(self.infrastructure):
                return False
                
            if not SecurityValidator.validate_security(self.security):
                return False
                
            # Validate wings
            for wing in self.wings.values():
                if not self._validate_wing(wing):
                    return False
            
            return True
        except Exception as e:
            logging.error(f"Configuration validation error: {e}")
            return False
   
    @property
    def tech_stack(self) -> Dict[str, Any]:
        return self.technical.tech_stack

    @property
    def components(self) -> Dict[str, Dict[str, Any]]:
        return self.technical.components

    @property
    def dev_settings(self) -> Dict[str, Any]:
        return self.development.dev_settings

    @property
    def dev_standards(self) -> Dict[str, Any]:
        return self.development.dev_standards

    @property
    def team_settings(self) -> Dict[str, Any]:
        return self.team.team

    @property
    def risk_settings(self) -> Dict[str, Any]:
        return self.operations.risk_matrix

    @property
    def resource_settings(self) -> Dict[str, Any]:
        return self.operations.resource_settings

    @property
    def timeline(self) -> Dict[str, Any]:
        return self.operations.timeline
