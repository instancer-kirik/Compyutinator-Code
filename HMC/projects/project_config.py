from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import os
import logging
from pathlib import Path
from enum import Enum
from dataclasses import field
from HMC.system_analyzer import SystemInfo
from HMC.projects.project_structure import PROJECT_DIRECTORIES
from HMC.symbol_manager import CodeSymbol
from HMC.projects.project_wing import Wing

from HMC.projects.wings_manager import WingsManager
from .project_types import (
    BaseProjectData, ProjectType, WingType, WingStatus, TechnicalConfig,
    DevelopmentConfig, TeamConfig, RiskManagement
)

from .wing_config import WingConfig
from .technical_overview_generator import TechnicalOverviewGenerator

@dataclass
class ProjectConfig(BaseProjectData):
    """Project configuration and settings management"""
    # Core configs
    technical: TechnicalConfig = field(default_factory=TechnicalConfig)
    development: DevelopmentConfig = field(default_factory=DevelopmentConfig)
    team: TeamConfig = field(default_factory=TeamConfig)
    risk: RiskManagement = field(default_factory=RiskManagement)
    
    # Project Structure
    directory_structure: Dict[str, Any] = field(default_factory=lambda: PROJECT_DIRECTORIES.copy())
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    symbols: Dict[Path, List['CodeSymbol']] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.project_type, str):
            self.project_type = ProjectType(self.project_type)

    def validate(self) -> bool:
        """Validate project configuration"""
        return all([
            self.name and self.path,
            self.technical.validate(),
            self.development.validate(),
            self.team.validate(),
            self.risk.validate()
        ])

    def get_setting(self, *path: str, default: Any = None) -> Any:
        """Get setting using dot notation"""
        current = self.__dict__
        for key in path:
            if not isinstance(current, dict):
                return default
            current = current.get(key, default)
        return current

    def update_setting(self, *path: str, value: Any) -> bool:
        """Update setting value using dot notation"""
        try:
            current = self.settings
            for key in path[:-1]:
                current = current.setdefault(key, {})
            current[path[-1]] = value
            return True
        except Exception as e:
            logging.error(f"Error updating setting: {e}")
            return False

    def validate(self) -> bool:
        return all([
            self.name and self.path,
            self.settings["development"]["code_style"].validate(),
            self.settings["development"]["testing"].validate(),
            self.settings["development"]["security"].validate(),
            self.settings["team"]["roles"].validate(),
            self.settings["team"]["communication"].validate(),
            self.settings["team"]["documentation"].validate(),
            self.settings["technical"]["languages"].validate(),
            self.settings["technical"]["frameworks"].validate(),
            self.settings["technical"]["entry_points"].validate(),
            self.settings["technical"]["dependencies"].validate(),
            self.dev_standards.validate(),
          
            self.risk_management.validate(),
            self.tech_stack.validate(),
            self.components.validate(),
            self.dev_environment.validate()
        ])

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

    # Symbol tracking (was missing)
    symbols: Dict[Path, List['CodeSymbol']] = field(default_factory=dict)
   
    # Project Structure and Symbols
    directory_structure: Dict[str, Any] = field(default_factory=lambda: PROJECT_DIRECTORIES.copy())
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    
    
    # Technical Components
    components: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "languages": {},    # Language configurations
        "frameworks": {},   # Framework settings
        "services": {},     # External services
        "databases": {},    # Database connections
        "apis": {},         # API configurations
        "tools": {}         # Development tools
    })
    
    # Technical Stack
    tech_stack: Dict[str, Any] = field(default_factory=lambda: {
        "languages": [],
        "frameworks": [],
        "primary_language": None,
        "entry_points": {"main": "src/main.py"}
    })
    
    # Development Environment
    dev_settings: Dict[str, Any] = field(default_factory=lambda: {
        "environment": {
            "variables": {},
            "virtual_env": None,
            "required_tools": [],
            "tool_versions": {},
            "workspace_path": None,
            "file_extensions": [".py", ".json", ".yml"],
            "excluded_dirs": ["__pycache__", ".git", "venv"]
        },
        "commands": {
            "build": None,
            "run": None,
            "test": None,
            "lint": None,
            "deploy": None
        },
        "scripts": [],
        "workspace": {
            "path": None,
            "file_extensions": [".py", ".json", ".yml", ".mojo"],
            "excluded_dirs": ["__pycache__", ".git", "venv"]
        }
    })
    
    # Development Standards
    dev_standards: Dict[str, Any] = field(default_factory=lambda: {
        "code_style": {
            "style_guide": "pep8",
            "max_complexity": 10,
            "formatters": [],
            "linters": []
        },
        "testing": {
            "framework": "pytest",
            "coverage_target": 80,
            "strategies": ["unit", "integration"],
            "performance_benchmarks": {}
        },
        "documentation": {
            "required_sections": ["API", "Setup", "Usage"],
            "format": "markdown",
            "tools": []
        },
        "security": {
            "requirements": [],
            "scan_frequency": "weekly",
            "vulnerability_threshold": "high"
        }
    })
    
    # Team and Collaboration
    team: Dict[str, Any] = field(default_factory=lambda: {
        "roles": {
            "owners": [],
            "maintainers": [],
            "contributors": [],
            "reviewers": []
        },
        "communication": {
            "primary_channel": None,
            "meetings": {
                "schedule": [],
                "templates": {}
            }
        },
        "documentation": {
            "wiki": None,
            "api_docs": None,
            "architecture": None
        }
    })
    
    # Project Management
    management: Dict[str, Any] = field(default_factory=lambda: {
        "issue_tracking": {
            "provider": None,
            "project_url": None,
            "labels": ["bug", "feature", "enhancement"],
            "templates": {}
        },
        "ci_cd": {
            "provider": None,
            "config_path": None,
            "triggers": [],
            "environments": ["dev", "staging", "prod"]
        },
        "review_process": {
            "required_approvals": 1,
            "review_checklist": [],
            "automated_checks": []
        },
        "risk": {
            "matrix_config": {
                "probability_weights": {
                    "rare": 1,
                    "unlikely": 2,
                    "possible": 3,
                    "likely": 4,
                    "certain": 5
                },
                "impact_weights": {
                    "negligible": 1,
                    "minor": 2,
                    "moderate": 3,
                    "major": 4,
                    "severe": 5
                }
            },
            "notification_preferences": {
                "high_risk_threshold": 12,
                "review_period_days": 30,
                "alert_channels": [],
                "monitoring_intervals": {
                    "risk_review": "30d",
                    "dependency_check": "7d",
                    "security_scan": "14d"
                }
            }
        }
    })
    
    # Target Audience and Market
    target_audience: Dict[str, Any] = field(default_factory=lambda: {
        "primary": {
            "description": "",
            "demographics": {},
            "needs": [],
            "pain_points": []
        },
        "secondary": {
            "description": "",
            "demographics": {},
            "needs": [],
            "pain_points": []
        },
        "market_segment": "",
        "user_personas": [],
        "accessibility_requirements": []
    })
    
    # Integration and Security
    integrations: Dict[str, Any] = field(default_factory=lambda: {
        "services": {
            "websocket": {"enabled": False},
            "webhooks": [],
            "apis": {},
            "cloud_services": {}
        },
        "ci_cd": {
            "provider": None,
            "config_path": None,
            "triggers": []
        },
        "security": {
            "auth_providers": [],
            "secret_management": None,
            "compliance": []
        },
        "notifications": {
            "channels": [],
            "preferences": {
                "high_risk_threshold": 12,
                "review_period_days": 30
            }
        }
    })
    # Activity and History
    activity: Dict[str, Any] = field(default_factory=lambda: {
        "changelog": [],
        "decisions": [],
        "reviews": [],
        "incidents": [],
        "metrics": {}
    })
    
    # Monitoring and Analytics
    monitoring: Dict[str, Any] = field(default_factory=lambda: {
        "metrics": {
            "performance": {},
            "usage": {},
            "errors": {}
        },
        "alerts": {
            "thresholds": {},
            "notifications": {}
        },
        "logging": {
            "level": "INFO",
            "handlers": [],
            "retention": "30d"
        }
    })
    # Quality and Risk Management
    quality_metrics: Dict[str, Any] = field(default_factory=lambda: {
        "testing": {
            "coverage_target": 80,
            "framework": "pytest"
        },
        "code_quality": {
            "max_complexity": 10,
            "style_guide": "pep8"
        },
        "performance": {
            "benchmarks": {},
            "targets": {},
            "metrics": {}
        }
    })
    
    # Risk Management (add these)
    risk_appetite: str = "cautious"
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
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
        """Add a new wing to the project"""
        return self.wings_manager.create_wing(name, wing_type, description, config)

   
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
            # Validate core requirements
            if not self.name or not self.path:
                return False
                
            # Validate wings
            for wing in self.wings.values():
                if not self._validate_wing(wing):
                    return False
                    
            # Validate technical stack
            if self.tech_stack["primary_language"] and \
               self.tech_stack["primary_language"] not in self.tech_stack["languages"]:
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Configuration validation error: {e}")
            return False
            
    
    def validate_risk_settings(self) -> bool:
        """Validate risk management settings"""
        try:
            valid_risk_appetites = ["averse", "minimal", "cautious", "flexible", "aggressive"]
            if self.risk_appetite not in valid_risk_appetites:
                return False
                
            # Validate dates
            if self.start_date and self.target_date:
                if self.start_date > self.target_date:
                    return False
                    
            # Validate risk matrix configuration
            risk_config = self.management.get("risk", {}).get("matrix_config", {})
            if not all(isinstance(w, int) for w in risk_config.get("probability_weights", {}).values()):
                return False
            if not all(isinstance(w, int) for w in risk_config.get("impact_weights", {}).values()):
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Risk settings validation error: {e}")
            return False
            
    def validate_resource_settings(self) -> bool:
        """Validate resource management settings"""
        try:
            rules = self.resource_settings.get("allocation_rules", {})
            if not isinstance(rules.get("max_allocation_period"), str):
                return False
                
            tracking = self.resource_settings.get("tracking", {})
            if not all(isinstance(v, bool) for v in tracking.values()):
                return False
                
            notifications = self.resource_settings.get("notifications", {})
            if not isinstance(notifications.get("low_resource_threshold"), (int, float)):
                return False
                
            return True
        except Exception as e:
            logging.error(f"Resource settings validation error: {e}")
            return False
