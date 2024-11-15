from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ProjectManagementConfig:
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
        }
    })

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

    activity: Dict[str, Any] = field(default_factory=lambda: {
        "changelog": [],
        "decisions": [],
        "reviews": [],
        "incidents": [],
        "metrics": {}
    })