from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class InfrastructureConfig:
    """Infrastructure and deployment configuration"""
    environments: Dict[str, Any] = field(default_factory=lambda: {
        "development": {
            "resources": {
                "compute": [],
                "storage": [],
                "networking": []
            },
            "variables": {},
            "services": {},
            "security": {}
        },
        "staging": {
            "resources": {
                "compute": [],
                "storage": [],
                "networking": []
            },
            "variables": {},
            "services": {},
            "security": {}
        },
        "production": {
            "resources": {
                "compute": [],
                "storage": [],
                "networking": []
            },
            "variables": {},
            "services": {},
            "security": {}
        }
    })
    
    deployment: Dict[str, Any] = field(default_factory=lambda: {
        "strategy": "rolling",
        "automation": {
            "ci_cd": {
                "provider": None,
                "config_path": None,
                "pipelines": [],
                "triggers": []
            },
            "scripts": {},
            "artifacts": {}
        },
        "rollback": {
            "strategy": "automatic",
            "conditions": [],
            "verification": []
        }
    })
    
    scaling: Dict[str, Any] = field(default_factory=lambda: {
        "auto_scaling": {
            "enabled": False,
            "rules": {},
            "limits": {},
            "metrics": []
        },
        "load_balancing": {
            "enabled": False,
            "strategy": "round-robin",
            "health_checks": {}
        }
    })
    
    monitoring: Dict[str, Any] = field(default_factory=lambda: {
        "metrics": {
            "collection": {
                "providers": [],
                "custom_metrics": []
            },
            "storage": {
                "provider": None,
                "retention": "30d"
            },
            "visualization": {
                "dashboards": [],
                "tools": []
            }
        },
        "logging": {
            "levels": ["INFO", "WARNING", "ERROR"],
            "storage": {
                "provider": None,
                "retention": "30d"
            },
            "aggregation": {
                "enabled": False,
                "strategy": None
            }
        },
        "alerting": {
            "rules": {},
            "channels": [],
            "escalation": {
                "levels": [],
                "contacts": []
            }
        }
    })
    
    security_measures: Dict[str, Any] = field(default_factory=lambda: {
        "network": {
            "honeynets": {  # Fake network segments
                "enabled": True,
                "segments": [],
                "monitoring": True
            },
            "traffic_analysis": {
                "enabled": True,
                "suspicious_patterns": [],
                "action_on_detect": "block"
            }
        },
        "deception": {
            "decoy_services": {
                "ssh": {"port": 22222, "banner": "OpenSSH_4.3"},
                "ftp": {"port": 21212, "banner": "vsFTPd 2.3.4"},
                "telnet": {"port": 23232}
            },
            "fake_vulnerabilities": {  # Trap attackers looking for specific vulns
                "enabled": True,
                "responses": {}
            }
        }
    })