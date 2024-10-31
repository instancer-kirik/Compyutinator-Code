from typing import Dict, Optional, List
from datetime import datetime

class Resource:
    def __init__(self, resource_id: int, name: str):
        self.id: int = resource_id
        self.type: str = ""       # Financial/Human/Material/Technical
        self.name: str = name
        self.value: float = 0.0   # Current value
        self.quantity: float = 0.0
        self.unit: str = ""       # Currency/Hours/Units/etc
        self.status: str = "Available"  # Available/Allocated/Depleted
        self.allocation: Dict[int, float] = {}  # Risk ID -> amount allocated

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "quantity": self.quantity,
            "unit": self.unit,
            "status": self.status,
            "allocation": self.allocation
        }

class FinancialResource(Resource):
    def __init__(self, resource_id: int, name: str):
        super().__init__(resource_id, name)
        self.currency: str = "USD"
        self.liquid: bool = True
        self.vesting_schedule: Optional[Dict] = None

    def to_dict(self) -> dict:
        base_dict = super().to_dict()
        base_dict.update({
            "currency": self.currency,
            "liquid": self.liquid,
            "vesting_schedule": self.vesting_schedule
        })
        return base_dict

class MaterialResource(Resource):
    def __init__(self, resource_id: int, name: str):
        super().__init__(resource_id, name)
        self.location: str = ""
        self.expiry: Optional[datetime] = None
        self.supplier: str = ""

    def to_dict(self) -> dict:
        base_dict = super().to_dict()
        base_dict.update({
            "location": self.location,
            "expiry": self.expiry.isoformat() if self.expiry else None,
            "supplier": self.supplier
        })
        return base_dict
