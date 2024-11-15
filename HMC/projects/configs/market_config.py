from dataclasses import dataclass, field
from typing import Dict, Any, List
import logging
@dataclass
class MarketConfig:
    """Market and audience configuration"""
    target_audience: Dict[str, Any] = field(default_factory=lambda: {
        "primary": {
            "description": "",
            "demographics": {},
            "needs": [],
            "pain_points": [],
            "user_stories": [],
            "use_cases": []
        },
        "secondary": {
            "description": "",
            "demographics": {},
            "needs": [],
            "pain_points": [],
            "user_stories": [],
            "use_cases": []
        },
        "market_segment": "",
        "user_personas": [],
        "accessibility_requirements": []
    })
    
    market_analysis: Dict[str, Any] = field(default_factory=lambda: {
        "competitors": [],
        "market_size": {
            "total": None,
            "addressable": None,
            "serviceable": None
        },
        "trends": [],
        "opportunities": [],
        "threats": []
    })
    
    product_positioning: Dict[str, Any] = field(default_factory=lambda: {
        "value_proposition": "",
        "unique_selling_points": [],
        "pricing_strategy": {
            "model": "",
            "tiers": {},
            "pricing_factors": []
        },
        "distribution_channels": [],
        "marketing_channels": []
    })
    
    feedback_collection: Dict[str, Any] = field(default_factory=lambda: {
        "methods": [],
        "metrics": {
            "satisfaction": {},
            "usage": {},
            "retention": {}
        },
        "feedback_sources": [],
        "improvement_tracking": []
    })

    def validate(self) -> bool:
        """Validate market configuration"""
        try:
            # Validate primary audience
            if not self.target_audience["primary"]["description"]:
                return False
            
            # Validate market analysis
            if not any([
                self.market_analysis["competitors"],
                self.market_analysis["trends"],
                self.market_analysis["opportunities"]
            ]):
                return False
            
            # Validate product positioning
            if not self.product_positioning["value_proposition"]:
                return False
            
            return True
        except Exception as e:
            logging.error(f"Market config validation error: {e}")
            return False 