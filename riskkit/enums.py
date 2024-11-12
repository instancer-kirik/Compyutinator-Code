from enum import Enum

class EventPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Risk-related enums
class RiskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
class RiskAppetite(Enum):
    AVERSE = "averse"
    MINIMAL = "minimal"
    CAUTIOUS = "cautious"
    FLEXIBLE = "flexible"
    AGGRESSIVE = "aggressive"

class RiskStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    CLOSED = "closed"
    REJECTED = "rejected"
    ARCHIVED = "archived"
class RiskProbability(str, Enum):
    RARE = "rare"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    CERTAIN = "certain"

# Impact-related enums
class ImpactSeverity(str, Enum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ImpactArea(Enum):
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    REPUTATIONAL = "reputational"
    REGULATORY = "regulatory"
    TECHNICAL = "technical"
    STRATEGIC = "strategic"
    FUNCTIONALITY = "functionality"

class ImpactTimeframe(Enum):
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"

# Relationship enums
class RelationshipType(str, Enum):
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    RELATES_TO = "relates_to"

class RewardType(str, Enum):
    OPTIMIZATION = "optimization"      # Instead of cost_saving
    REVENUE = "revenue"
    EFFICIENCY = "efficiency"
    QUALITY = "quality"
    STRATEGIC = "strategic"
    OPPORTUNITY = "opportunity"
    BADGE = "badge"
    ACHIEVEMENT = "achievement"
    MILESTONE = "milestone"
    RECOGNITION = "recognition"

    RISK = "risk"
    OTHER = "other"

class RewardStatus(Enum):
    PENDING = "pending"
    ACHIEVED = "achieved"
    EXPIRED = "expired"
    REVOKED = "revoked"

class RewardTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

class RewardClaimStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# Value mapping dictionaries
SEVERITY_VALUES = {
    ImpactSeverity.LOW: 1,
    ImpactSeverity.MEDIUM: 2,
    ImpactSeverity.HIGH: 3,
    ImpactSeverity.CRITICAL: 4
}

PRIORITY_VALUES = {
    RiskPriority.LOW: 1,
    RiskPriority.MEDIUM: 2,
    RiskPriority.HIGH: 3,
    RiskPriority.CRITICAL: 4
}

# Status transition mapping
VALID_STATUS_TRANSITIONS = {
    RiskStatus.OPEN: {
        RiskStatus.IN_PROGRESS: "Risk mitigation started",
        RiskStatus.ACCEPTED: "Risk accepted without mitigation"
    },
    RiskStatus.IN_PROGRESS: {
        RiskStatus.MITIGATED: "Risk successfully mitigated",
        RiskStatus.ACCEPTED: "Risk accepted during mitigation"
    },
    RiskStatus.MITIGATED: {
        RiskStatus.CLOSED: "Risk fully mitigated and verified"
    },
    RiskStatus.ACCEPTED: {
        RiskStatus.CLOSED: "Accepted risk now closed"
    },
    RiskStatus.CLOSED: {}  # Cannot transition from CLOSED
}

class ResourceType(str, Enum):
    FINANCIAL = "financial"
    HUMAN = "human"
    MATERIAL = "material"
    TECHNICAL = "technical"
    TIME = "time"
    INFORMATION = "information"
    OTHER = "other"
