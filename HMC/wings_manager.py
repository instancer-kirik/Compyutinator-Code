from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pathlib import Path
import logging
from datetime import datetime
import json
from .wing_template import WingTemplateManager
from HMC.projects.project import Project
from HMC.projects.project_config import ProjectConfig
from HMC.projects.project_types import ProjectType, WingStatus, WingType
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
class Wing:
    """Represents a project wing/extension"""
    id: str
    name: str
    type: WingType
    description: str = ""
    version: str = "0.1.0"
    status: WingStatus = WingStatus.DEVELOPMENT
    
    # Wing Structure
    entry_points: Dict[str, str] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    
    # Metadata
    path: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert wing to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "conflicts": self.conflicts,
            "entry_points": self.entry_points,
            "config": self.config,
            "path": str(self.path) if self.path else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.author,
            "tags": self.tags,
            "metadata": self.metadata
        }

class WingsManager:
    """Manages project wings/extensions"""
    def __init__(self, cccore):
        self.cccore = cccore
        self.config_manager = cccore.config_manager
        self.current_project = None
        self.projects: Dict[str, Project] = {}
        self.wings: Dict[str, Wing] = {}
        self.template_manager = WingTemplateManager(self)

    def load_project_from_folder(self, folder_path: Union[str, Path]) -> Optional[Project]:
        """Load project from folder"""
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists():
                logging.error(f"Project folder does not exist: {folder_path}")
                return None
                
            # Create project config
            config = ProjectConfig(
                name=folder_path.name,
                path=folder_path,
                project_type=ProjectType.LOCAL  # Default to Python project
            )
            
            # Create project
            project = Project(
                name=folder_path.name,
                path=folder_path,
                project_type=ProjectType.LOCAL,
                config=config
            )
            
            return project
            
        except Exception as e:
            logging.error(f"Error loading project from folder: {e}")
            return None

    def create_wing(self, name: str, wing_type: WingType, description: str = "", 
                   config: Dict[str, Any] = None) -> Optional[Wing]:
        """Create a new wing"""
        try:
            wing_id = f"{name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            wing = Wing(
                id=wing_id,
                name=name,
                type=wing_type,
                description=description,
                config=config or {}
            )
            
            # Generate wing structure from template
            wing_path = self.template_manager.generate_wing(
                f"{wing_type.value}_wing",
                wing.to_dict()
            )
            
            if wing_path:
                wing.path = wing_path
                if self.cccore.project_config.add_wing(wing):
                    self.save_wing_config(wing)
                    return wing
            
            return None

        except Exception as e:
            logging.error(f"Error creating wing {name}: {e}")
            return None

    def save_wing_config(self, wing: Wing):
        """Save wing configuration to file"""
        try:
            if not wing.path:
                return

            config_path = wing.path / "wing.json"
            with open(config_path, 'w') as f:
                json.dump(wing.to_dict(), f, indent=4)

        except Exception as e:
            logging.error(f"Error saving wing config for {wing.name}: {e}")

    def get_wing(self, wing_id: str) -> Optional[Wing]:
        """Get wing by ID"""
        return self.wings.get(wing_id)

    def get_wings_by_type(self, wing_type: WingType) -> List[Wing]:
        """Get all wings of a specific type"""
        return [w for w in self.wings.values() if w.type == wing_type]

    def get_active_wings(self) -> List[Wing]:
        """Get all active wings"""
        return [w for w in self.wings.values() if w.status == WingStatus.ACTIVE]

    def enable_wing(self, wing_id: str) -> bool:
        """Enable a wing"""
        wing = self.get_wing(wing_id)
        if wing:
            wing.status = WingStatus.ACTIVE
            self.save_wing_config(wing)
            return True
        return False

    def disable_wing(self, wing_id: str) -> bool:
        """Disable a wing"""
        wing = self.get_wing(wing_id)
        if wing:
            wing.status = WingStatus.DISABLED
            self.save_wing_config(wing)
            return True
        return False

    def check_dependencies(self, wing_id: str) -> List[str]:
        """Check wing dependencies"""
        wing = self.get_wing(wing_id)
        if not wing:
            return []
            
        missing = []
        for dep in wing.dependencies:
            if dep not in self.wings:
                missing.append(dep)
        return missing

    def get_dependent_wings(self, wing_id: str) -> List[Wing]:
        """Get wings that depend on the specified wing"""
        return [w for w in self.wings.values() if wing_id in w.dependencies] 