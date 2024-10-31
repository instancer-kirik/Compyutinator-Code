from typing import List, Optional, Dict, Set, Union
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime, timedelta
from enum import Enum
import re

class RiskCategory(str, Enum):
    TECHNICAL = "Technical"
    FINANCIAL = "Financial"
    OPERATIONAL = "Operational"
    STRATEGIC = "Strategic"
    COMPLIANCE = "Compliance"
    SECURITY = "Security"

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
    status: RiskStatus
    category: RiskCategory
    tags: List[str] = Field(default_factory=list, max_items=10)
    due_date: Optional[datetime] = None
    budget: Optional[float] = Field(None, ge=0)
    owner: Optional[str] = None
    
    @validator('description')
    def description_must_be_meaningful(cls, v):
        words = v.split()
        if len(words) < 3:
            raise ValueError('Description must be meaningful (at least 3 words)')
        if not re.search(r'[.!?]$', v):
            raise ValueError('Description must end with proper punctuation')
        return v.strip()

    @validator('tags')
    def validate_tags(cls, v):
        if not v:
            return v
        # Ensure tags are unique and properly formatted
        unique_tags = set()
        for tag in v:
            tag = tag.lower().strip()
            if not re.match(r'^[a-z0-9-_]{2,30}$', tag):
                raise ValueError(f'Invalid tag format: {tag}')
            unique_tags.add(tag)
        return sorted(list(unique_tags))

    @validator('due_date')
    def due_date_must_be_future(cls, v):
        if v and v < datetime.now():
            raise ValueError('Due date must be in the future')
        return v

class RiskCreate(RiskBase):
    """Fields specific to risk creation"""
    mitigation: Optional[str] = Field(None, min_length=10, max_length=1000)
    dependencies: List[int] = Field(default_factory=list)
    resource_requirements: Dict[str, float] = Field(default_factory=dict)
    
    @validator('mitigation')
    def mitigation_required_for_status(cls, v, values):
        if values.get('status') in [RiskStatus.MITIGATED, RiskStatus.CLOSED] and not v:
            raise ValueError('Mitigation plan required for mitigated or closed risks')
        return v

    @root_validator
    def validate_dependencies(cls, values):
        """Validate that dependencies form a valid graph"""
        deps = values.get('dependencies', [])
        if values.get('id') in deps:
            raise ValueError('Risk cannot depend on itself')
        return values

class RiskUpdate(RiskBase):
    """Fields specific to risk updates"""
    id: int
    version: int  # For optimistic locking
    last_updated: datetime
    change_reason: str = Field(..., min_length=10, max_length=500)
    previous_status: Optional[RiskStatus] = None
    
    @validator('change_reason')
    def validate_change_reason(cls, v, values):
        if 'status' in values and values.get('previous_status'):
            if values['status'] != values['previous_status'] and len(v) < 20:
                raise ValueError('Status changes require detailed explanation (min 20 chars)')
        return v
    
    @root_validator
    def validate_status_transition(cls, values):
        """Validate that status transitions are legal"""
        current = values.get('status')
        previous = values.get('previous_status')
        
        if previous and current:
            valid_transitions = {
                RiskStatus.OPEN: [RiskStatus.IN_PROGRESS, RiskStatus.ACCEPTED],
                RiskStatus.IN_PROGRESS: [RiskStatus.MITIGATED, RiskStatus.ACCEPTED],
                RiskStatus.MITIGATED: [RiskStatus.CLOSED],
                RiskStatus.ACCEPTED: [RiskStatus.CLOSED],
                RiskStatus.CLOSED: []  # Cannot transition from CLOSED
            }
            
            if current not in valid_transitions.get(previous, []):
                raise ValueError(f'Invalid status transition: {previous} -> {current}')
        
        return values

class ResourceBase(BaseModel):
    """Base Resource fields"""
    name: str = Field(..., min_length=3, max_length=100)
    type: str = Field(..., regex="^(Financial|Human|Material|Technical)$")
    value: float = Field(..., ge=0)
    quantity: float = Field(..., ge=0)
    unit: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    
    @validator('name')
    def name_must_be_meaningful(cls, v):
        if not re.match(r'^[A-Za-z0-9\s\-_]+$', v):
            raise ValueError('Name must contain only letters, numbers, spaces, hyphens, and underscores')
        return v.strip()

class ResourceCreate(ResourceBase):
    """Fields specific to resource creation"""
    availability_schedule: Optional[Dict[str, List[datetime]]] = None
    dependencies: List[int] = Field(default_factory=list)
    
    @validator('availability_schedule')
    def validate_schedule(cls, v):
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
    
    @root_validator
    def validate_quantity_change(cls, values):
        """Validate quantity changes"""
        current = values.get('quantity')
        previous = values.get('previous_quantity')
        
        if current is not None and previous is not None:
            if current < 0:
                raise ValueError('Quantity cannot be negative')
            if current < previous and not values.get('change_reason'):
                raise ValueError('Quantity reduction requires change reason')
        
        return values

class ResourceRequirement(BaseModel):
    resource_id: int
    amount: float = Field(..., gt=0)
    start_date: datetime
    end_date: datetime
    
    @validator('end_date')
    def end_date_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class RiskRelationship(BaseModel):
    source_id: int
    target_id: int
    relationship_type: str = Field(..., regex="^(depends_on|blocks|relates_to)$")
    strength: float = Field(..., ge=0, le=1)
    
    @validator('source_id', 'target_id')
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
    
    @root_validator
    def validate_batch(cls, values):
        risks = values.get('risks', [])
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
        
        return values

class BatchValidationResult(BaseModel):
    """Enhanced validation result for batch operations"""
    valid: bool
    errors: Dict[str, List[str]] = Field(default_factory=dict)
    warnings: Dict[str, List[str]] = Field(default_factory=dict)
    item_results: Dict[int, ValidationResult] = Field(default_factory=dict)
    resource_impacts: Dict[str, float] = Field(default_factory=dict)
    dependency_graph: Optional[Dict] = None