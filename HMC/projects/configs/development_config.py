from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class DevelopmentConfig:
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
        "workspace": {
            "path": None,
            "file_extensions": [".py", ".json", ".yml", ".mojo"],
            "excluded_dirs": ["__pycache__", ".git", "venv"]
        }
    })
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
        },
        "quality": {
            "metrics": {
                "performance": {
                    "benchmarks": {},
                    "targets": {},
                    "metrics": {}
                }
            }
        }
    })