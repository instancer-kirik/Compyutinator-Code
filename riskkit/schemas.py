from typing import List, Optional, Dict, Set, Union
from pydantic import BaseModel, Field, model_validator, field_validator, computed_field
from datetime import datetime, timedelta
from enum import Enum
import re

class RiskCategoryBase(BaseModel):
    """Base fields for risk categories"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    color: str = Field(..., pattern="^#[0-9a-fA-F]{6}$")  # Hex color
    assessment_criteria: Dict = Field(default_factory=lambda: {
        "probability_factors": [],
        "impact_factors": [],
        "mitigation_guidelines": [],
        "review_frequency_days": 30
    })
    project_id: int
    hidden: bool = False
    hidden_at: Optional[datetime] = None
    hidden_by_id: Optional[int] = None

class RiskCategory(RiskCategoryBase):
    """Full risk category model"""
    id: int
    creator_id: int
    created_at: datetime
    updated_at: datetime

class RiskStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    MITIGATED = "Mitigated"
    CLOSED = "Closed"
    ACCEPTED = "Accepted"

class RiskPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class RiskBase(BaseModel):
    """Base Risk fields shared between Create and Update"""
    description: str = Field(..., min_length=10, max_length=1000)
    probability: RiskPriority
    impact: RiskPriority
    status: RiskStatus = Field(default=RiskStatus.OPEN)
    category_id: Optional[int] = None
    tags: List[str] = Field(default_factory=list, max_items=10)
    due_date: Optional[datetime] = None
    budget: Optional[float] = Field(None, ge=0)
    owner: Optional[str] = None
    project_id: int = Field(..., description="Project ID this risk belongs to")
    
    @field_validator('description')
    @classmethod
    def description_must_be_meaningful(cls, v: str) -> str:
        words = v.split()
        if len(words) < 3:
            raise ValueError('Description must be meaningful (at least 3 words)')
        if not re.search(r'[.!?]$', v):
            raise ValueError('Description must end with proper punctuation')
        return v.strip()

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        if not v:
            return v
        unique_tags = set()
        for tag in v:
            tag = tag.lower().strip()
            if not re.match(r'^[a-z0-9-_]{2,30}$', tag):
                raise ValueError(f'Invalid tag format: {tag}')
            unique_tags.add(tag)
        return sorted(list(unique_tags))

    @field_validator('due_date')
    @classmethod
    def due_date_must_be_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v < datetime.now():
            raise ValueError('Due date must be in the future')
        return v

    @computed_field
    @property
    def risk_score(self) -> float:
        priority_values = {
            RiskPriority.LOW: 1,
            RiskPriority.MEDIUM: 2,
            RiskPriority.HIGH: 3,
            RiskPriority.CRITICAL: 4
        }
        return priority_values[self.impact] * priority_values[self.probability]

class RiskCreate(RiskBase):
    """Fields specific to risk creation"""
    mitigation: Optional[str] = Field(None, min_length=10, max_length=1000)
    dependencies: List[int] = Field(default_factory=list)
    resource_requirements: Dict[str, float] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_mitigation_and_deps(self) -> 'RiskCreate':
        # Validate mitigation requirement
        if self.status in [RiskStatus.MITIGATED, RiskStatus.CLOSED] and not self.mitigation:
            raise ValueError('Mitigation plan required for mitigated or closed risks')
            
        # Validate dependencies
        if hasattr(self, 'id') and self.id in self.dependencies:
            raise ValueError('Risk cannot depend on itself')
            
        return self

    @model_validator(mode='after')
    def project_id_required(self) -> 'RiskCreate':
        """Ensure project_id is provided for new risks"""
        if not self.project_id:
            raise ValueError("project_id is required when creating a risk")
        return self

class RiskUpdate(RiskBase):
    """Fields specific to risk updates"""
    id: int
    version: int
    last_updated: datetime
    change_reason: str = Field(..., min_length=10, max_length=500)
    previous_status: Optional[RiskStatus] = None
    
    @field_validator('version')
    @classmethod
    def version_required(cls, v: Optional[int]) -> int:
        """Ensure version is provided for updates"""
        if not v:
            raise ValueError("version is required when updating a risk")
        return v

    @field_validator('change_reason')
    @classmethod
    def validate_change_reason(cls, v: str, info) -> str:
        """Validate change reason, especially for status changes"""
        # Get the current values from the validation context
        values = info.data
        if ('status' in values and 
            'previous_status' in values and 
            values['status'] != values['previous_status'] and 
            len(v) < 20):
            raise ValueError('Status changes require detailed explanation (min 20 chars)')
        return v

    @model_validator(mode='after')
    def validate_status_transition(self) -> 'RiskUpdate':
        """Validate that status transitions are legal"""
        if not self.previous_status or not self.status:
            return self

        valid_transitions = {
            RiskStatus.OPEN: {
                RiskStatus.IN_PROGRESS: "Can transition to in progress",
                RiskStatus.ACCEPTED: "Can be accepted without mitigation"
            },
            RiskStatus.IN_PROGRESS: {
                RiskStatus.MITIGATED: "Mitigation complete",
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

        if self.status not in valid_transitions.get(self.previous_status, {}):
            allowed = valid_transitions.get(self.previous_status, {}).keys()
            raise ValueError(
                f'Invalid status transition: {self.previous_status} -> {self.status}. '
                f'Allowed transitions: {", ".join(str(s) for s in allowed)}'
            )

        # Additional validation for specific transitions
        if self.status in [RiskStatus.MITIGATED, RiskStatus.CLOSED]:
            if not hasattr(self, 'mitigation') or not self.mitigation:
                raise ValueError(f'Mitigation plan required when transitioning to {self.status}')

        if self.status == RiskStatus.ACCEPTED:
            if len(self.change_reason) < 50:
                raise ValueError('Accepting a risk requires detailed justification (min 50 chars)')

        return self
    @field_validator('version')
    @classmethod
    def version_required(cls, v: Optional[int]) -> int:
        """Ensure version is provided for updates"""
        if not v:
            raise ValueError("version is required when updating a risk")
        return v
    @computed_field
    @property
    def has_status_changed(self) -> bool:
        """Indicates whether the status has changed in this update"""
        return bool(
            self.previous_status and 
            self.status and 
            self.previous_status != self.status
        )

    @computed_field
    @property
    def transition_message(self) -> Optional[str]:
        """Returns a human-readable message about the status transition"""
        if not self.has_status_changed:
            return None

        messages = {
            (RiskStatus.OPEN, RiskStatus.IN_PROGRESS): "Risk mitigation started",
            (RiskStatus.OPEN, RiskStatus.ACCEPTED): "Risk accepted without mitigation",
            (RiskStatus.IN_PROGRESS, RiskStatus.MITIGATED): "Risk successfully mitigated",
            (RiskStatus.IN_PROGRESS, RiskStatus.ACCEPTED): "Risk accepted during mitigation",
            (RiskStatus.MITIGATED, RiskStatus.CLOSED): "Mitigated risk verified and closed",
            (RiskStatus.ACCEPTED, RiskStatus.CLOSED): "Accepted risk closed"
        }
        
        return messages.get((self.previous_status, self.status))

class ResourceBase(BaseModel):
    """Base Resource fields"""
    name: str = Field(..., min_length=3, max_length=100)
    type: str = Field(..., pattern="^(Financial|Human|Material|Technical)$")
    value: float = Field(..., ge=0)
    quantity: float = Field(..., ge=0)
    unit: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    
    @field_validator('name')
    @classmethod
    def name_must_be_meaningful(cls, v: str) -> str:
        if not re.match(r'^[A-Za-z0-9\s\-_]+$', v):
            raise ValueError('Name must contain only letters, numbers, spaces, hyphens, and underscores')
        return v.strip()

class ResourceCreate(ResourceBase):
    """Fields specific to resource creation"""
    availability_schedule: Optional[Dict[str, List[datetime]]] = None
    dependencies: List[int] = Field(default_factory=list)
    
    @field_validator('availability_schedule')
    @classmethod
    def validate_schedule(cls, v: Optional[Dict[str, List[datetime]]]) -> Optional[Dict[str, List[datetime]]]:
        if v:
            now = datetime.now()
            for timeframes in v.values():
                for dt in timeframes:
                    if dt < now:
                        raise ValueError('Schedule cannot contain past dates')
        return v

class ResourceUpdate(ResourceBase):
    """Fields specific to resource updates"""
    id: int
    version: int
    last_updated: datetime
    change_reason: str = Field(..., min_length=10, max_length=500)
    previous_quantity: float
    
    @model_validator(mode='after')
    def validate_quantity_change(self) -> 'ResourceUpdate':
        """Validate quantity changes"""
        current = self.quantity
        previous = self.previous_quantity
        
        if current is not None and previous is not None:
            if current < 0:
                raise ValueError('Quantity cannot be negative')
            if current < previous and not self.change_reason:
                raise ValueError('Quantity reduction requires change reason')
        
        return self

class ResourceRequirement(BaseModel):
    resource_id: int
    amount: float = Field(..., gt=0)
    start_date: datetime
    end_date: datetime
    
    @field_validator('end_date')
    def end_date_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class RiskRelationship(BaseModel):
    source_id: int
    target_id: int
    relationship_type: str = Field(..., pattern="^(depends_on|blocks|relates_to)$")
    strength: float = Field(..., ge=0, le=1)
    
    @field_validator('source_id', 'target_id')
    def ids_must_be_different(cls, v, values):
        if 'source_id' in values and v == values['source_id']:
            raise ValueError('Source and target must be different')
        return v

class ValidationResult(BaseModel):
    valid: bool
    errors: Dict[str, List[str]] = Field(default_factory=dict)
    warnings: Dict[str, List[str]] = Field(default_factory=dict)

class BatchRiskCreate(BaseModel):
    risks: List[RiskCreate]
    
    @model_validator(mode='after')
    def validate_batch(self) -> 'BatchRiskCreate':
        risks = self.risks
        if not risks:
            raise ValueError('Batch cannot be empty')
        if len(risks) > 100:
            raise ValueError('Batch size cannot exceed 100 items')
        
        # Check for duplicate descriptions
        descriptions = [r.description for r in risks]
        if len(descriptions) != len(set(descriptions)):
            raise ValueError('Duplicate risk descriptions found in batch')
        
        # Validate dependency graph
        all_ids = {r.id for r in risks if hasattr(r, 'id')}
        for risk in risks:
            invalid_deps = set(risk.dependencies) - all_ids
            if invalid_deps:
                raise ValueError(f'Invalid dependencies found: {invalid_deps}')
        
        return self

class BatchValidationResult(BaseModel):
    """Enhanced validation result for batch operations"""
    valid: bool
    errors: Dict[str, List[str]] = Field(default_factory=dict)
    warnings: Dict[str, List[str]] = Field(default_factory=dict)
    item_results: Dict[int, ValidationResult] = Field(default_factory=dict)
    resource_impacts: Dict[str, float] = Field(default_factory=dict)
    dependency_graph: Optional[Dict] = None