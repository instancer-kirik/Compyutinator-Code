from typing import List
from datetime import datetime

class Reward:
    def __init__(self, reward_id: int, description: str):
        self.id: int = reward_id
        self.description: str = description
        self.type: str = ""        # Revenue/Cost Saving/Strategic Value
        self.value: float = 0.0    # Estimated monetary value
        self.probability: str = "Low" # Low/Medium/High
        self.timeline: str = "Short"  # Short/Medium/Long term
        self.dependencies: List[int] = []  # Related risks or resources
        self.status: str = "Potential"  # Potential/In Progress/Realized

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type,
            "value": self.value,
            "probability": self.probability,
            "timeline": self.timeline,
            "dependencies": self.dependencies,
            "status": self.status
        }
