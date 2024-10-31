from typing import List, Dict
from datetime import datetime
from .risk import Risk
from .reward import Reward
from .resource import Resource
from .news_events import NewsItem

class DataMux:
    def __init__(self):
        self.risks: List[Risk] = []
        self.rewards: List[Reward] = []
        self.resources: List[Resource] = []
        self.news_items: List[NewsItem] = []
        self.history: List[Dict] = []
        self.org_name: str = ""
        self.categories: List[str] = []
        self.tags: List[str] = []

    def save_state(self) -> dict:
        data = {
            "version": "2.0",
            "last_updated": datetime.now().isoformat(),
            "risks": [risk.to_dict() for risk in self.risks],
            "rewards": [reward.to_dict() for reward in self.rewards],
            "resources": [resource.to_dict() for resource in self.resources],
            "news_items": [item.to_dict() for item in self.news_items],
            "history": self.history,
            "metadata": {
                "organization": self.org_name,
                "categories": self.categories,
                "tags": self.tags
            }
        }
        return data

    def load_state(self, data: dict) -> None:
        # TODO: Implement state loading
        pass
