from dataclasses import dataclass, field
from typing import Dict, Any
import logging
@dataclass
class QualityConfig:
    """Quality assurance and testing configuration"""
    testing: Dict[str, Any] = field(default_factory=lambda: {
        "unit": {
            "framework": "pytest",
            "coverage_target": 80,
            "patterns": []
        },
        "integration": {
            "framework": None,
            "environments": []
        },
        "performance": {
            "benchmarks": {},
            "thresholds": {}
        },
        "e2e": {
            "framework": None,
            "scenarios": []
        }
    })
    
    code_quality: Dict[str, Any] = field(default_factory=lambda: {
        "linting": {
            "tools": [],
            "rules": {},
            "ignore_patterns": []
        },
        "formatting": {
            "style": "black",
            "line_length": 88,
            "rules": {}
        },
        "metrics": {
            "complexity": {
                "max": 10,
                "tools": []
            },
            "maintainability": {
                "index_threshold": 20,
                "tools": []
            }
        }
    })
    
    documentation: Dict[str, Any] = field(default_factory=lambda: {
        "api": {
            "format": "openapi",
            "version": "3.0",
            "tools": []
        },
        "code": {
            "style": "google",
            "coverage_target": 70,
            "tools": []
        },
        "user": {
            "formats": ["md", "html"],
            "sections": ["setup", "usage", "api"]
        }
    }) 