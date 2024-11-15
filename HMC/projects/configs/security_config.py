from dataclasses import dataclass, field
from typing import Dict, Any
import logging
@dataclass
class SecurityConfig:
   
    """Security and compliance configuration"""
    authentication: Dict[str, Any] = field(default_factory=lambda: {
        "providers": [],
        "methods": ["password", "2fa"],
        "policies": {
            "password_strength": "high",
            "session_timeout": "30m",
            "max_attempts": 3,
            "lockout_period": "1h",
            "ip_blacklist": [],
            "suspicious_patterns": []
        },
        "honeypot": {  # Trap endpoints/credentials
            "enabled": True,
            "fake_endpoints": ["/admin-backup", "/config.php", "/wp-login"],
            "decoy_credentials": {},
            "alert_on_access": True
        }
    })
    
    
    authorization: Dict[str, Any] = field(default_factory=lambda: {
        "roles": {
            "admin": {"permissions": []},
            "developer": {"permissions": []},
            "viewer": {"permissions": []}
        },
        "access_control": {
            "resources": {},
            "policies": {}
        }
    })
    
    compliance: Dict[str, Any] = field(default_factory=lambda: {
        "standards": [],
        "certifications": [],
        "audit_schedule": "quarterly",
        "data_retention": {
            "policies": {},
            "periods": {}
        }
    })
    
    scanning: Dict[str, Any] = field(default_factory=lambda: {
        "vulnerability": {
            "schedule": "weekly",
            "tools": [],
            "severity_thresholds": {}
        },
        "dependency": {
            "schedule": "daily",
            "policies": {}
        },
        "code": {
            "sast": True,
            "dast": False,
            "tools": []
        }
    }) 

    monitoring: Dict[str, Any] = field(default_factory=lambda: {
        "intrusion_detection": {
            "enabled": True,
            "patterns": {
                "sql_injection": [],
                "xss_attempts": [],
                "path_traversal": [],
                "unusual_requests": []
            },
            "rate_limiting": {
                "enabled": True,
                "threshold": 100,
                "period": "1m"
            },
            "ip_tracking": {
                "enabled": True,
                "suspicious_behavior": [],
                "auto_block": True
            }
        },
        "deception": {  # Misleading responses
            "fake_errors": {
                "enabled": True,
                "templates": {
                    "404": "System Error: Contact administrator",
                    "403": "Loading..."
                }
            },
            "delayed_responses": {
                "enabled": True,
                "suspicious_ips": True,
                "delay_ms": 2000
            }
        }
    })
    
    countermeasures: Dict[str, Any] = field(default_factory=lambda: {
        "active_defense": {
            "enabled": True,
            "responses": {
                "port_scan": "blacklist",
                "brute_force": "challenge",
                "injection_attempt": "redirect",
                "suspicious_traffic": "slow_down"
            },
            "traps": {
                "honeypots": [],
                "tarpits": [],  # Slow down attackers
                "blackholes": []  # Dead-end routes
            }
        },
        "deception": {
            "fake_data": {
                "enabled": True,
                "decoy_records": True,
                "canary_tokens": []
            },
            "misdirection": {
                "fake_services": [],
                "decoy_ports": [],
                "false_responses": {}
            }
        },
        "alerts": {
            "channels": ["email", "slack"],
            "thresholds": {
                "attempts": 5,
                "interval": "5m"
            },
            "response_team": []
        }
    })