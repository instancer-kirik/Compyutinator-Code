from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path
import logging
from datetime import datetime
import json
from .wing_template import WingTemplateManager

from HMC.projects.project_config import ProjectConfig
from HMC.projects.project_wing import Wing, WingType, WingStatus
class WingsManager:
    """Manages project wings/extensions"""
    def __init__(self, project_config: ProjectConfig):
        self.project_config = project_config
        self.wings: Dict[str, Wing] = project_config.wings
        self.template_manager = WingTemplateManager(self)

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
                if self.project_config.add_wing(wing):
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