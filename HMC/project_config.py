from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
import json
import os
import logging

@dataclass
class ProjectConfig:
    name: str
    project_type: str  # "local" or "resolvinator"
    path: str
    description: Optional[str] = None
    status: Optional[str] = None
    risk_appetite: Optional[float] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    websocket_enabled: bool = False
    
    @classmethod
    def load(cls, project_path: str) -> 'ProjectConfig':
        config_path = os.path.join(project_path, 'project_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        return None

    def save(self):
        config_path = os.path.join(self.path, 'project_config.json')
        with open(config_path, 'w') as f:
            json.dump(self.__dict__, f, indent=2, default=str) 