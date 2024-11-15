# New file: BigLinks/HMC/projects/project_registry.py
from typing import Dict, Optional
from pathlib import Path
import json
import logging
from .project import Project

class ProjectRegistry:
    """Central registry for managing multiple projects"""
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.projects: Dict[str, Project] = {}
        self.active_project: Optional[str] = None
        self._load_registry()
    
    def _load_registry(self):
        try:
            if self.registry_path.exists():
                with open(self.registry_path) as f:
                    data = json.load(f)
                for project_data in data['projects']:
                    project = Project.from_dict(project_data)
                    self.projects[project.id] = project
                self.active_project = data.get('active_project')
        except Exception as e:
            logging.error(f"Error loading project registry: {e}")

    def save_registry(self):
        try:
            data = {
                'projects': [p.to_dict() for p in self.projects.values()],
                'active_project': self.active_project
            }
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving project registry: {e}")