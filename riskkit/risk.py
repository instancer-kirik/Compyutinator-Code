from typing import List
from datetime import datetime

class Risk:
    def __init__(self, risk_id: int, description: str):
        self.id: int = risk_id
        self.description: str = description
        self.probability: str = "Low"  # Low/Medium/High/Critical
        self.impact: str = "Low"      # Low/Medium/High/Critical
        self.priority: str = "Low"    # Calculated
        self.status: str = "Open"     # Open/Mitigated/Closed
        self.mitigation: str = ""
        self.date_created: str = datetime.now().strftime("%Y-%m-%d")
        self.last_updated: str = datetime.now().strftime("%Y-%m-%d")
        self.owner: str = ""          # Add ownership
        self.category: str = ""       # Technical/Financial/Operational/Strategic
        self.dependencies: List[int] = []  # IDs of related risks

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "probability": self.probability,
            "impact": self.impact,
            "priority": self.priority,
            "status": self.status,
            "mitigation": self.mitigation,
            "date_created": self.date_created,
            "last_updated": self.last_updated,
            "owner": self.owner,
            "category": self.category,
            "dependencies": self.dependencies
        }
