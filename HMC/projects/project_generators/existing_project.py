from typing import Dict, Any
from pathlib import Path
import json
import logging

class ExistingProjectGenerator:
    """Generator for adding existing projects to the system"""
    
    def __init__(self, cccore):
        self.cccore = cccore
        
    def generate(self, project_data: Dict[str, Any]) -> bool:
        """
        Add an existing project to the system
        
        Args:
            project_data: Dictionary containing project information
                - name: Project name
                - path: Project directory path
                - language: Main programming language
                - version: Language version
        """
        try:
            project_path = Path(project_data['path'])
            if not project_path.exists():
                return False
                
            # Create project configuration
            config = {
                'name': project_data['name'],
                'path': str(project_path),
                'type': 'existing',
                'language': project_data['language'],
                'version': project_data.get('version', ''),
                'build_command': '',
                'run_command': '',
                'file_extensions': ['.py', '.json', '.yml'],  # Default extensions
                'excluded_dirs': ['__pycache__', '.git', 'venv'],
                'description': project_data.get('description', ''),
                'risk_appetite': project_data.get('risk_appetite', 'moderate')
            }
            
            # Save project configuration
            config_file = project_path / 'project_config.json'
            if not config_file.exists():
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
            
            return True
            
        except Exception as e:
            logging.error(f"Error generating existing project: {e}")
            return False 