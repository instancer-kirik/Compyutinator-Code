from dataclasses import dataclass, field
from typing import Dict, Any, List
import logging
@dataclass
class TeamConfig:
    """Team and collaboration configuration"""
    team: Dict[str, Any] = field(default_factory=lambda: {
        "roles": {
            "lead": [],
            "developers": [],
            "reviewers": [],
            "maintainers": [],
            "contributors": []
        },
        "responsibilities": {
            "code_review": {},
            "documentation": {},
            "testing": {},
            "deployment": {}
        },
        "communication": {
            "channels": [],
            "meetings": {
                "standup": {"frequency": "daily", "duration": "15m"},
                "planning": {"frequency": "weekly", "duration": "1h"},
                "review": {"frequency": "weekly", "duration": "30m"}
            },
            "tools": []
        },
        "availability": {
            "time_zones": [],
            "work_hours": {},
            "vacation_calendar": {}
        }
    })
    
    collaboration: Dict[str, Any] = field(default_factory=lambda: {
        "guidelines": {
            "code_review": [],
            "commit_messages": [],
            "branch_naming": [],
            "documentation": []
        },
        "workflows": {
            "feature_development": {},
            "bug_fixing": {},
            "release_process": {}
        },
        "tools": {
            "version_control": None,
            "issue_tracking": None,
            "documentation": None,
            "communication": []
        }
    })

    def validate(self) -> bool:
        """Validate team configuration"""
        try:
            # Validate required roles
            if not any(self.team["roles"]["lead"]):
                return False
            
            # Validate communication settings
            if not self.team["communication"]["channels"]:
                return False
            
            # Validate collaboration tools
            if not self.collaboration["tools"]["version_control"]:
                return False
                
            return True
        except Exception as e:
            logging.error(f"Team config validation error: {e}")
            return False 