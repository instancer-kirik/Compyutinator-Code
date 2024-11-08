from typing import Protocol, List, Dict, Optional
from datetime import datetime
from .enums import (
    RewardType, RiskProbability, ImpactTimeframe, 
    RewardStatus, RewardTier
)

class RewardProtocol(Protocol):
    """Protocol defining the interface for reward objects"""
    id: str
    description: str
    value: float
    status: RewardStatus
    
    def to_dict(self) -> dict:
        """Convert reward to dictionary format"""
        ...
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RewardProtocol':
        """Create reward from dictionary data"""
        ...

class BaseReward:
    """Base implementation of common reward functionality"""
    def __init__(self, reward_id: str, description: str):
        self.id: str = reward_id
        self.description: str = description
        self.value: float = 0.0
        self.status: RewardStatus = RewardStatus.PENDING

    def to_dict(self) -> dict:
        """Base dictionary representation"""
        return {
            "id": self.id,
            "description": self.description,
            "value": self.value,
            "status": self.status.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'BaseReward':
        """Create base reward from dictionary"""
        reward = cls(data['id'], data.get('description', ''))
        reward.value = data.get('value', 0.0)
        reward.status = RewardStatus(data.get('status', 'pending'))
        return reward