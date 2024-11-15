from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import logging

@dataclass
class ProjectOperationsConfig:
    """Project operations, risk, and resource management configuration"""
    # Risk Management
    risk_appetite: str = "cautious"
    risk_matrix: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
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
    })

    # Resource Management
    resource_settings: Dict[str, Any] = field(default_factory=lambda: {
        "allocation_rules": {
            "max_allocation_period": "30d",
            "min_availability": 0.2
        },
        "tracking": {
            "time": True,
            "costs": True,
            "usage": True
        },
        "notifications": {
            "low_resource_threshold": 0.1,
            "overallocation_threshold": 0.9
        }
    })

    # Timeline Management
    timeline: Dict[str, Any] = field(default_factory=lambda: {
        "start_date": None,
        "target_date": None,
        "completion_date": None,
        "milestones": [],
        "dependencies": {}
    })

    def validate_risk_settings(self) -> bool:
        """Validate risk management settings"""
        try:
            valid_risk_appetites = ["averse", "minimal", "cautious", "flexible", "aggressive"]
            if self.risk_appetite not in valid_risk_appetites:
                return False
                
            # Validate dates
            if self.timeline["start_date"] and self.timeline["target_date"]:
                if self.timeline["start_date"] > self.timeline["target_date"]:
                    return False
                    
            # Validate risk matrix configuration
            if not all(isinstance(w, int) for w in self.risk_matrix["probability_weights"].values()):
                return False
            if not all(isinstance(w, int) for w in self.risk_matrix["impact_weights"].values()):
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Risk settings validation error: {e}")
            return False
            
    def validate_resource_settings(self) -> bool:
        """Validate resource management settings"""
        try:
            rules = self.resource_settings["allocation_rules"]
            if not isinstance(rules["max_allocation_period"], str):
                return False
                
            tracking = self.resource_settings["tracking"]
            if not all(isinstance(v, bool) for v in tracking.values()):
                return False
                
            notifications = self.resource_settings["notifications"]
            if not isinstance(notifications["low_resource_threshold"], (int, float)):
                return False
                
            return True
        except Exception as e:
            logging.error(f"Resource settings validation error: {e}")
            return False

    def validate(self) -> bool:
        """Validate all operations settings"""
        return all([
            self.validate_risk_settings(),
            self.validate_resource_settings()
        ])