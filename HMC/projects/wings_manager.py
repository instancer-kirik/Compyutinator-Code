from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from datetime import datetime
import json
from .project_types import WingType, WingStatus
from .project_wing import Wing
from .wing_config import WingConfig
from .wings.language_wing_factory import LanguageWingFactory
from .project_types import ProjectType
class WingsManager:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.wings: Dict[str, Wing] = {}
        self.language_factory = LanguageWingFactory(project_path)
        
    def create_wing(self, name: str, wing_type: WingType, 
                   description: str = "", config: Optional[WingConfig] = None) -> Optional[Wing]:
        try:
            wing_id = f"{name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            wing_path = self.project_path / "wings" / wing_id
            
            wing = Wing(
                id=wing_id,
                name=name,
                type=wing_type,
                description=description,
                status=WingStatus.ACTIVE,
                config=config or WingConfig(),
                path=wing_path
            )
            
            # Create wing directory and save config
            wing_path.mkdir(parents=True, exist_ok=True)
            if wing.save_config():
                self.wings[wing_id] = wing
                return wing
            return None
            
        except Exception as e:
            logging.error(f"Error creating wing: {e}")
            return None
            
    def update_wing_config(self, wing_id: str, updates: Dict[str, Any]) -> bool:
        """Update wing configuration"""
        wing = self.get_wing(wing_id)
        if not wing:
            return False
            
        try:
            for section, values in updates.items():
                if hasattr(wing.config, section):
                    current = getattr(wing.config, section)
                    current.update(values)
            
            return wing.save_config()
            
        except Exception as e:
            logging.error(f"Error updating wing config: {e}")
            return False

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
    def _validate_wing(self, wing: Wing) -> bool:
        """Validate a wing configuration"""
        try:
            # Check required fields
            if not wing.id or not wing.name or not wing.type:
                return False
                
            # Check dependencies
            for dep in wing.dependencies:
                if dep not in self.wings:
                    return False
                    
            return True
            
        except Exception as e:
            logging.error(f"Wing validation error: {e}")
            return False
            
    def initialize_wings(self, project_type: ProjectType):
        """Initialize wings based on project type"""
        # Create core wing
        core_wing = self.create_wing(
            name="core",
            wing_type=WingType.CORE,
            description="Core project functionality"
        )
        if core_wing:
            self.wings[core_wing.id] = core_wing

        # Auto-detect and create language wings
        for language in self.language_factory.detect_languages():
            wing = self.language_factory.create_wing(language)
            if wing:
                self.wings[wing.id] = wing
            