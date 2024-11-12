from typing import List, Optional, Dict
from datetime import datetime
from .schemas import RiskUpdate, RiskCreate, RiskStatus, RiskPriority, RiskCategory
from .enums import RiskAppetite
class Risk:
    """Local risk management class"""
    def __init__(self, risk_id: int, description: str):
        self.id: int = risk_id
        self.description: str = description
        self.probability: RiskPriority = RiskPriority.LOW
        self.impact: RiskPriority = RiskPriority.LOW
        self.status: RiskStatus = RiskStatus.OPEN
        self.category_id: Optional[int] = None
        self._category: Optional[RiskCategory] = None  # Lazy loaded
        self.mitigation: str = ""
        self.date_created: datetime = datetime.now()
        self.last_updated: datetime = datetime.now()
        self.owner: str = ""
        self.dependencies: List[int] = []
        self._version: int = 1
        self.project_id: Optional[int] = None
        self.risk_appetite: RiskAppetite = RiskAppetite.CAUTIOUS  # Default value

    @property
    def category(self) -> Optional[RiskCategory]:
        """Get category details (would need to be loaded from API)"""
        return self._category

    @category.setter
    def category(self, value: RiskCategory):
        """Set category and category_id"""
        self._category = value
        self.category_id = value.id if value else None

    @property
    def priority(self) -> str:
        """Calculate priority based on impact, probability and category criteria"""
        if self.category and self.category.assessment_criteria:
            # Use category-specific assessment criteria
            return self._calculate_priority_with_criteria()
        else:
            # Fallback to default priority matrix
            return self._calculate_default_priority()

    def _calculate_priority_with_criteria(self) -> str:
        """Calculate priority using category-specific criteria"""
        if not self.category or not self.category.assessment_criteria:
            return self._calculate_default_priority()

        criteria = self.category.assessment_criteria
        prob_factors = criteria.get("probability_factors", [])
        impact_factors = criteria.get("impact_factors", [])

        # Custom priority calculation logic based on category criteria
        # This is a placeholder - implement according to your needs
        return self._calculate_default_priority()

    def _calculate_default_priority(self) -> str:
        """Default priority calculation"""
        priority_matrix = {
            (RiskPriority.CRITICAL, RiskPriority.CRITICAL): "Critical",
            (RiskPriority.CRITICAL, RiskPriority.HIGH): "Critical",
            (RiskPriority.HIGH, RiskPriority.CRITICAL): "Critical",
            (RiskPriority.HIGH, RiskPriority.HIGH): "High",
            (RiskPriority.MEDIUM, RiskPriority.HIGH): "High",
            (RiskPriority.HIGH, RiskPriority.MEDIUM): "High",
            (RiskPriority.MEDIUM, RiskPriority.MEDIUM): "Medium",
            (RiskPriority.LOW, RiskPriority.MEDIUM): "Medium",
            (RiskPriority.MEDIUM, RiskPriority.LOW): "Medium",
            (RiskPriority.LOW, RiskPriority.LOW): "Low"
        }
        return priority_matrix.get((self.impact, self.probability), "Medium")

    def to_dict(self) -> dict:
        """Convert to dict for local storage"""
        data = {
            "id": self.id,
            "description": self.description,
            "probability": self.probability.value,
            "impact": self.impact.value,
            "priority": self.priority,
            "status": self.status.value,
            "category_id": self.category_id,
            "mitigation": self.mitigation,
            "date_created": self.date_created.strftime("%Y-%m-%d"),
            "last_updated": self.last_updated.strftime("%Y-%m-%d"),
            "owner": self.owner,
            "dependencies": self.dependencies,
            "version": self._version,
            "project_id": self.project_id,
            "risk_appetite": self.risk_appetite.value
        }
        if self._category:
            data["category"] = self._category.model_dump()
        return data

    def to_update(self) -> RiskUpdate:
        """Convert to RiskUpdate for API operations"""
        return RiskUpdate(
            id=self.id,
            version=self._version,
            description=self.description,
            probability=self.probability,
            impact=self.impact,
            status=self.status,
            category=self.category,
            mitigation=self.mitigation,
            owner=self.owner,
            last_updated=self.last_updated,
            risk_appetite=self.risk_appetite
        )

    @classmethod
    def from_dict(cls, data: Dict) -> 'Risk':
        """Create from dict (local storage)"""
        risk = cls(data["id"], data["description"])
        risk.probability = RiskPriority(data["probability"])
        risk.impact = RiskPriority(data["impact"])
        risk.status = RiskStatus(data["status"])
        risk.category_id = data["category_id"]
        risk.mitigation = data["mitigation"]
        risk.date_created = datetime.strptime(data["date_created"], "%Y-%m-%d")
        risk.last_updated = datetime.strptime(data["last_updated"], "%Y-%m-%d")
        risk.owner = data["owner"]
        risk.dependencies = data["dependencies"]
        risk._version = data.get("version", 1)
        risk.project_id = data.get("project_id")
        risk.risk_appetite = RiskAppetite(data.get("risk_appetite", "cautious"))
        return risk
