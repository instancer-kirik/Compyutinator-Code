from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import jinja2
import yaml
import logging

import json
from riskkit.enums import WingType, WingStatus

class TemplateError(Exception):
    """Base class for template errors"""
    pass

class TemplateValidationError(TemplateError):
    """Raised when template validation fails"""
    pass

class TemplateGenerationError(TemplateError):
    """Raised when wing generation fails"""
    pass

@dataclass
class TemplateValidationResult:
    """Result of template validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class WingTemplate:
    """Template for creating new wings"""
    # Core Template Info
    name: str
    type: WingType
    description: str
    version: str = "0.1.0"
    
    # Template Structure
    structure: Dict[str, str] = field(default_factory=dict)  # Directory structure
    files: Dict[str, str] = field(default_factory=dict)      # File templates
    
    # Template Configuration
    config_template: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "settings": {},
        "build": {
            "command": None,
            "args": [],
            "env": {}
        },
        "run": {
            "command": None,
            "args": [],
            "env": {}
        }
    })
    
    # Dependencies and Requirements
    requirements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "author": "",
        "tags": [],
        "category": "",
        "visibility": "private",
        "documentation": "",
        "examples": []
    })

class WingTemplateManager:
    """Manages wing templates and generation"""
    def __init__(self, cccore):
        self.cccore = cccore
        self.templates: Dict[str, WingTemplate] = {}
        self.template_path = Path(cccore.config_manager.get_config_path()) / "wing_templates"
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_path)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True
        )
        self.load_templates()

    def get_template(self, template_name: str) -> Optional[WingTemplate]:
        """Get a template by name"""
        return self.templates.get(template_name)

    def list_templates(self, wing_type: Optional[WingType] = None) -> List[str]:
        """List available templates, optionally filtered by type"""
        if wing_type:
            return [name for name, template in self.templates.items() 
                   if template.type == wing_type]
        return list(self.templates.keys())

    def validate_template(self, template: WingTemplate) -> bool:
        """Validate a template's structure and requirements"""
        try:
            # Check required fields
            if not template.name or not template.type:
                return False
                
            # Validate file templates
            for content in template.files.values():
                self.jinja_env.from_string(content)
                
            return True
            
        except Exception as e:
            logging.error(f"Template validation error: {e}")
            return False

    def generate_wing(self, template_name: str, wing_data: dict) -> Optional[Path]:
        """Generate a new wing from template"""
        try:
            template = self.get_template(template_name)
            if not template or not self.validate_template(template):
                raise ValueError(f"Invalid template: {template_name}")

            # Create wing directory structure
            wing_path = self.cccore.project_manager.get_wings_path() / wing_data['id']
            wing_path.mkdir(parents=True)

            # Create directory structure
            for dir_name, description in template.structure.items():
                (wing_path / dir_name).mkdir(parents=True, exist_ok=True)

            # Generate files from templates
            for file_name, content in template.files.items():
                file_path = wing_path / file_name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                template = self.jinja_env.from_string(content)
                rendered = template.render(
                    wing=wing_data,
                    project=self.cccore.project_manager.get_current_project()
                )
                
                with open(file_path, 'w') as f:
                    f.write(rendered)

            # Create wing configuration
            config_path = wing_path / "wing.json"
            with open(config_path, 'w') as f:
                json.dump({
                    **wing_data,
                    "config": template.config_template,
                    "metadata": template.metadata
                }, f, indent=2)

            return wing_path

        except Exception as e:
            logging.error(f"Error generating wing from template: {e}")
            return None