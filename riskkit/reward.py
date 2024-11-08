from typing import List, Dict, Optional
from datetime import datetime
from .enums import (
    RewardType, RiskProbability, ImpactTimeframe, 
    RewardStatus, RewardTier
)
from .reward_protocol import BaseReward

class Reward(BaseReward):
    """Base reward class for all reward types"""
    def __init__(self, reward_id: str, description: str):
        super().__init__(reward_id, description)
        self.status: RewardStatus = RewardStatus.PENDING
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.metadata: Dict = {}
        self.tags: List[str] = []

    def to_dict(self) -> dict:
        return {
            "reward_id": self.reward_id,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Reward':
        reward = cls(
            reward_id=data['reward_id'],
            description=data['description']
        )
        reward.status = RewardStatus(data.get('status', 'pending'))
        reward.created_at = datetime.fromisoformat(data['created_at'])
        reward.updated_at = datetime.fromisoformat(data['updated_at'])
        reward.metadata = data.get('metadata', {})
        reward.tags = data.get('tags', [])
        return reward

class RiskReward(Reward):
    """Reward associated with risk management"""
    def __init__(self, reward_id: str, description: str):
        super().__init__(reward_id, description)
        self.type: RewardType = RewardType.OTHER
        self.probability: RiskProbability = RiskProbability.POSSIBLE
        self.timeline: ImpactTimeframe = ImpactTimeframe.SHORT_TERM
        self.dependencies: List[int] = []
        
    def to_dict(self) -> dict:
        base_dict = super().to_dict()
        base_dict.update({
            "type": self.type.value,
            "probability": self.probability.value,
            "timeline": self.timeline.value,
            "dependencies": self.dependencies,
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> 'RiskReward':
        reward = super().from_dict(data)
        reward.type = RewardType(data['type'])
        reward.probability = RiskProbability(data['probability'])
        reward.timeline = ImpactTimeframe(data['timeline'])
        reward.dependencies = data['dependencies']
        return reward

class AchievementReward(Reward):
    """Reward representing an achievement/badge"""
    def __init__(self, reward_id: str, name: str):
        super().__init__(reward_id, "")
        self.name: str = name
        self.reward_type: RewardType = RewardType.BADGE
        self.tier: RewardTier = RewardTier.BRONZE
        self.criteria: Dict = {}
        self.achievement_date: Optional[datetime] = None
        self.expiry_date: Optional[datetime] = None
        self.project_id: Optional[str] = None
        self.achiever_id: Optional[str] = None
        self.creator_id: Optional[str] = None
        
    def to_dict(self) -> dict:
        base_dict = super().to_dict()
        base_dict.update({
            "name": self.name,
            "reward_type": self.reward_type.value,
            "tier": self.tier.value,
            "criteria": self.criteria,
            "achievement_date": self.achievement_date.isoformat() if self.achievement_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "project_id": self.project_id,
            "achiever_id": self.achiever_id,
            "creator_id": self.creator_id
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> 'AchievementReward':
        reward = super().from_dict(data)
        reward.name = data['name']
        reward.reward_type = RewardType(data.get('reward_type', 'badge'))
        reward.tier = RewardTier(data.get('tier', 'bronze'))
        reward.criteria = data.get('criteria', {})
        if data.get('achievement_date'):
            reward.achievement_date = datetime.fromisoformat(data['achievement_date'])
        if data.get('expiry_date'):
            reward.expiry_date = datetime.fromisoformat(data['expiry_date'])
        reward.project_id = data.get('project_id')
        reward.achiever_id = data.get('achiever_id')
        reward.creator_id = data.get('creator_id')
        return reward

class IntegrationReward(Reward):
    """Reward for completing integration testing milestones"""
    def __init__(self, reward_id: str, description: str):
        super().__init__(reward_id, description)
        self.milestone_type: str = ""
        self.completion_percentage: float = 0.0
        self.risk_score: float = 0.0
        self.completion_date: Optional[datetime] = None
        self.verified_by: Optional[str] = None
        self.test_results: Dict = {}
        
    def to_dict(self) -> dict:
        base_dict = super().to_dict()
        base_dict.update({
            "milestone_type": self.milestone_type,
            "completion_percentage": self.completion_percentage,
            "risk_score": self.risk_score,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "verified_by": self.verified_by,
            "test_results": self.test_results
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> 'IntegrationReward':
        reward = super().from_dict(data)
        reward.milestone_type = data.get('milestone_type', '')
        reward.completion_percentage = float(data.get('completion_percentage', 0.0))
        reward.risk_score = float(data.get('risk_score', 0.0))
        if data.get('completion_date'):
            reward.completion_date = datetime.fromisoformat(data['completion_date'])
        reward.verified_by = data.get('verified_by')
        reward.test_results = data.get('test_results', {})
        return reward
