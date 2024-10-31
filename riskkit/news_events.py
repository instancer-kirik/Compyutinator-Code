from typing import List
from datetime import datetime

class NewsItem:
    def __init__(self, news_id: int, title: str):
        self.id: int = news_id
        self.title: str = title
        self.content: str = ""
        self.source: str = ""
        self.date: datetime = datetime.now()
        self.category: str = ""    # Market/Technical/Regulatory/etc
        self.impact_areas: List[str] = []  # Risks/Resources affected
        self.priority: str = "Info"  # Info/Warning/Critical

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "date": self.date.isoformat(),
            "category": self.category,
            "impact_areas": self.impact_areas,
            "priority": self.priority
        }
