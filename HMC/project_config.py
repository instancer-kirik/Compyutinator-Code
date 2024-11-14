from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import os
import logging
from pathlib import Path
from enum import Enum
from dataclasses import field
from .projects.project_types import ProjectType
from .system_analyzer import SystemInfo
from .projects.project_generators.existing_project import ExistingProjectGenerator
from .wings_manager import WingType, WingStatus, Wing
from .projects.project_structure import PROJECT_DIRECTORIES
from .symbol_manager import CodeSymbol

@dataclass
class ProjectConfig:
    # Required Core Fields
    name: str
    project_type: ProjectType
    path: Path
    
    # Basic Project Info
    description: str = ""
    status: str = "active"
    visibility: str = "private"
    domain: str = ""
    version: str = "0.1.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Adding missing metadata fields
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "repository_url": None,
        "documentation_url": None,
        "issue_tracker_url": None,
        "keywords": [],
        "categories": [],
        "language": None,
        "framework": None,
        "dependencies": {},
        "dev_dependencies": {},
        "contributors": [],
        "maintainers": [],
        "license": None
    })
    
    # Symbol tracking (was missing)
    symbols: Dict[Path, List['CodeSymbol']] = field(default_factory=dict)
    
    # Project Structure and Symbols
    directory_structure: Dict[str, Any] = field(default_factory=lambda: PROJECT_DIRECTORIES.copy())
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    
    # Technical Components
    wings: Dict[str, Wing] = field(default_factory=lambda: {
        "core": Wing(
            id="core",
            name="core",
            type=WingType.CORE,
            status=WingStatus.ACTIVE,
            description="Core project functionality",
            entry_points={"main": "src/main.py"}
        )
    })
    
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
        "primary_language": None,
        "languages": [],
        "frameworks": [],
        "dependencies": {},
        "dev_dependencies": {},
        "cloud_services": {},
        "databases": {},
        "apis": {},
        "tools": {}
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

    def __post_init__(self):
        """Convert path to Path object if it's a string"""
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.project_type, str):
            self.project_type = ProjectType(self.project_type)
        
        # Ensure created_at and updated_at are datetime objects
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)

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

    def get_setting(self, *keys: str, default: Any = None) -> Any:
        """Get a nested setting value safely"""
        current = self.__dict__
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def update_setting(self, *keys: str, value: Any) -> bool:
        """Update a nested setting value safely"""
        try:
            current = self.__dict__
            for key in keys[:-1]:
                current = current.setdefault(key, {})
            current[keys[-1]] = value
            self.updated_at = datetime.now()
            return True
        except Exception as e:
            logging.error(f"Error updating setting: {e}")
            return False

    def get_technical_flow(self) -> Dict[str, Any]:
        """Generate technical flow overview"""
        flow_data = {
            'project_info': {
                'name': self.name,
                'type': self.project_type.value,
                'path': str(self.path),
            },
            'structure': self._analyze_structure(),
            'dependencies': self._extract_dependencies(),
            'entry_points': self._find_entry_points(),
            'relationships': self._analyze_relationships()
        }
        return flow_data

    def _analyze_structure(self) -> Dict[str, Any]:
        """Analyze project structure"""
        structure = {}
        for file_path in self.path.rglob('*.py'):
            if any(excluded in str(file_path) for excluded in self.excluded_dirs):
                continue
            relative_path = file_path.relative_to(self.path)
            structure[str(relative_path)] = self._analyze_file(file_path)
        return structure

    def generate_technical_overview(self) -> str:
        """Generate a markdown technical overview of the project"""
        try:
            # Get system info
            sys_info = SystemInfo(
                name=self.name,
                system_type="software",
                lifecycle_stage=self.get_setting('tracking', 'lifecycle_stage', 'development'),
                root_path=self.path
            )
            
            # Project Header
            overview = f"""# {self.name} Technical Overview

## System Environment
{sys_info.to_markdown()}

## Project Information
- **Type:** {self.project_type.value}
- **Status:** {self.status}
- **Version:** {self.version}

## Development Configuration
- **Build Command:** `{self.get_setting('dev_settings', 'build_command') or 'N/A'}`
- **Run Command:** `{self.get_setting('dev_settings', 'run_command') or 'N/A'}`
- **Test Command:** `{self.get_setting('dev_settings', 'test_command') or 'N/A'}`

## Project Structure
"""
            # Add file tree with symbols
            tree_data = self._generate_file_tree()
            overview += self._format_tree_as_markdown(tree_data)
            
            return overview
            
        except Exception as e:
            logging.error(f"Error generating technical overview: {e}")
            return f"Error generating overview: {str(e)}"

    def _generate_file_tree(self) -> Dict[str, Any]:
        """Generate hierarchical file tree with symbols"""
        tree = {}
        
        try:
            for file_path in self.path.rglob('*'):
                if any(excluded in str(file_path) for excluded in self.excluded_dirs):
                    continue
                    
                relative_path = file_path.relative_to(self.path)
                parts = relative_path.parts
                
                current = tree
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                    
                if file_path.is_file() and file_path.suffix in self.file_extensions:
                    symbols = self.get_setting('tracking', 'symbols', {}).get(str(relative_path), [])
                    current[parts[-1]] = {
                        'type': 'file',
                        'symbols': [
                            {
                                'name': sym.name,
                                'type': sym.type,
                                'line': sym.line,
                                'children': [c.name for c in sym.children] if hasattr(sym, 'children') else []
                            }
                            for sym in symbols
                        ]
                    }
                else:
                    current[parts[-1]] = {'type': 'directory'}
                    
            return tree
            
        except Exception as e:
            logging.error(f"Error generating file tree: {e}")
            return {}

    def _format_tree_as_markdown(self, tree: Dict[str, Any], indent: int = 0) -> str:
        """Format file tree as markdown with symbols"""
        result = ""
        
        for name, content in sorted(tree.items()):
            prefix = "    " * indent
            
            if content.get('type') == 'file':
                result += f"{prefix}- 📄 `{name}`\n"
                
                # Add symbols if present
                symbols = content.get('symbols', [])
                for sym in symbols:
                    sym_prefix = "    " * (indent + 1)
                    icon = {
                        'class': '🔷',
                        'function': '🔶',
                        'method': '🔸',
                        'variable': '💠'
                    }.get(sym.get('type', ''), '•')
                    
                    result += f"{sym_prefix}{icon} `{sym['name']}`"
                    if sym.get('children'):
                        result += f" (contains: {', '.join(sym['children'])})"
                    result += "\n"
                    
            else:  # directory
                result += f"{prefix}- 📁 **{name}/**\n"
                if isinstance(content, dict):
                    result += self._format_tree_as_markdown(content, indent + 1)
                    
        return result

    def export_technical_overview(self, format: str = 'md') -> bool:
        """Export technical overview to file"""
        try:
            overview = self.generate_technical_overview()
            output_path = self.path / 'docs' / 'technical_overview'
            output_path.mkdir(parents=True, exist_ok=True)
            
            if format == 'md':
                with open(output_path / 'overview.md', 'w') as f:
                    f.write(overview)
            elif format == 'json':
                tree_data = self._generate_file_tree()
                with open(output_path / 'overview.json', 'w') as f:
                    json.dump(tree_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logging.error(f"Error exporting technical overview: {e}")
            return False

    def add_activity(self, activity_type: str, description: str):
        """Add new activity entry"""
        try:
            activity = {
                'type': activity_type,
                'description': description,
                'timestamp': datetime.now().isoformat()
            }
            self.tracking.setdefault('activity', []).append(activity)
            self.save()
        except Exception as e:
            logging.error(f"Error adding activity: {e}")
            
    def _setup_python_wing(self):
        """Set up Python-specific wing"""
        self.wings["python"] = {
            "id": "python",
            "type": "language",
            "status": "active",
            "config": {
                "version": "3.x",
                "package_manager": "poetry" if (self.path / "pyproject.toml").exists() else "pip",
                "virtual_env": "venv" if (self.path / "venv").exists() else None
            }
        }
        
    def _setup_mojo_wing(self):
        """Set up Mojo-specific wing"""
        self.wings["mojo"] = {
            "id": "mojo",
            "type": "language",
            "status": "active",
            "config": {
                "version": "latest",
                "package_manager": "mojo",
                "features": ["parallel", "simd"]
            }
        }
            
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
            
    def add_wing(self, wing: Wing) -> bool:
        """Add a new wing to the project"""
        try:
            if wing.id in self.wings:
                return False
            self.wings[wing.id] = wing
            self.updated_at = datetime.now()
            return True
        except Exception as e:
            logging.error(f"Error adding wing: {e}")
            return False

    def get_wing_config(self, wing_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific wing"""
        wing = self.wings.get(wing_id)
        if wing:
            return {
                "tech_stack": self.tech_stack,
                "dev_settings": self.dev_settings,
                "dev_standards": self.dev_standards,
                "wing_specific": wing.config
            }
        return None
            
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
            