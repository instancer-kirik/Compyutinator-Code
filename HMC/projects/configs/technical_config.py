from dataclasses import dataclass, field
from typing import Dict, Any
import logging

@dataclass
class TechnicalConfig:
    tech_stack: Dict[str, Any] = field(default_factory=lambda: {
        "primary_language": None,
        "languages": [],
        "frameworks": [],
        "libraries": [],
        "tools": []
    })
    
    components: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "core": {
            "modules": [],
            "services": [],
            "dependencies": []
        },
        "frontend": {
            "framework": None,
            "components": [],
            "assets": [],
            "routes": []
        },
        "backend": {
            "services": [],
            "apis": [],
            "databases": [],
            "middleware": []
        },
        "application": {
            "databases": [],
            "caching": [],
            "storage": [],
            "messaging": []
        },
        "integrations": {
            "external_apis": [],
            "third_party": [],
            "plugins": []
        }
    })
    
    dependencies: Dict[str, Any] = field(default_factory=lambda: {
        "production": {},
        "development": {},
        "optional": {}
    })
    
    integrations: Dict[str, Any] = field(default_factory=lambda: {
        "services": {
            "websocket": {"enabled": False},
            "webhooks": [],
            "apis": {},
            "cloud_services": {}
        },
        "notifications": {
            "channels": [],
            "preferences": {
                "high_risk_threshold": 12,
                "review_period_days": 30
            }
        }
    })

    def validate(self) -> bool:
        """Validate technical configuration"""
        try:
            # Validate tech stack
            if self.tech_stack["primary_language"] and \
               self.tech_stack["primary_language"] not in self.tech_stack["languages"]:
                return False
            
            # Validate components
            required_components = ["core", "backend", "application"]
            if not all(comp in self.components for comp in required_components):
                return False
            
            # Validate core components
            if not self.components["core"]["modules"]:
                return False
            
            # Validate integrations
            if self.integrations["services"]["websocket"]["enabled"] and \
               not self.integrations["services"]["apis"]:
                return False
            
            return True
        except Exception as e:
            logging.error(f"Technical config validation error: {e}")
            return False