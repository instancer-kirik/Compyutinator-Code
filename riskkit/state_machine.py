from enum import Enum
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Transition:
    from_state: str
    to_state: str
    conditions: List[Callable]
    side_effects: List[Callable]
    required_fields: Set[str]
    permission_level: str = "normal"

class StateMachine:
    def __init__(self):
        self.transitions: Dict[str, Dict[str, Transition]] = {}
        self.current_state: str = None
        self.history: List[Dict] = []
        
    def add_transition(self, transition: Transition):
        if transition.from_state not in self.transitions:
            self.transitions[transition.from_state] = {}
        self.transitions[transition.from_state][transition.to_state] = transition
    
    def can_transition(self, from_state: str, to_state: str, context: Dict) -> bool:
        if from_state not in self.transitions:
            return False
        
        transition = self.transitions[from_state].get(to_state)
        if not transition:
            return False
            
        # Check required fields
        missing_fields = transition.required_fields - set(context.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
            
        # Check conditions
        return all(condition(context) for condition in transition.conditions)
    
    def transition(self, from_state: str, to_state: str, context: Dict) -> Dict:
        if not self.can_transition(from_state, to_state, context):
            raise ValueError(f"Invalid transition: {from_state} -> {to_state}")
            
        transition = self.transitions[from_state][to_state]
        
        # Execute side effects
        for effect in transition.side_effects:
            effect(context)
            
        # Record history
        self.history.append({
            "from_state": from_state,
            "to_state": to_state,
            "timestamp": datetime.now(),
            "context": context
        })
        
        return context

class RiskStateMachine(StateMachine):
    def __init__(self):
        super().__init__()
        self.setup_transitions()
    
    def setup_transitions(self):
        # Validation conditions
        def has_mitigation(context: Dict) -> bool:
            return bool(context.get("mitigation"))
            
        def has_owner(context: Dict) -> bool:
            return bool(context.get("owner"))
            
        def has_approval(context: Dict) -> bool:
            return bool(context.get("approved_by"))
            
        def resources_allocated(context: Dict) -> bool:
            return all(r["allocated"] for r in context.get("resources", []))
        
        # Side effects
        def notify_owner(context: Dict):
            # Implementation for notification system
            pass
            
        def update_resource_allocation(context: Dict):
            # Implementation for resource management
            pass
            
        def log_mitigation_complete(context: Dict):
            # Implementation for audit logging
            pass
        
        # Define transitions
        self.add_transition(Transition(
            from_state="Open",
            to_state="In Progress",
            conditions=[has_owner, resources_allocated],
            side_effects=[notify_owner, update_resource_allocation],
            required_fields={"owner", "resources", "start_date"}
        ))
        
        self.add_transition(Transition(
            from_state="In Progress",
            to_state="Mitigated",
            conditions=[has_mitigation],
            side_effects=[log_mitigation_complete],
            required_fields={"mitigation", "completion_date"}
        ))
        
        self.add_transition(Transition(
            from_state="In Progress",
            to_state="Accepted",
            conditions=[has_approval],
            side_effects=[notify_owner],
            required_fields={"approved_by", "acceptance_rationale"}
        ))
        
        self.add_transition(Transition(
            from_state="Mitigated",
            to_state="Closed",
            conditions=[has_approval],
            side_effects=[notify_owner],
            required_fields={"approved_by", "closure_notes"}
        ))

class ResourceStateMachine(StateMachine):
    def __init__(self):
        super().__init__()
        self.setup_transitions()
    
    def setup_transitions(self):
        def has_sufficient_quantity(context: Dict) -> bool:
            return context.get("quantity", 0) > 0
            
        def is_fully_allocated(context: Dict) -> bool:
            return context.get("allocated_quantity", 0) >= context.get("quantity", 0)
            
        def has_valid_schedule(context: Dict) -> bool:
            return bool(context.get("availability_schedule"))
        
        # Side effects
        def update_availability(context: Dict):
            pass
            
        def notify_resource_manager(context: Dict):
            pass
        
        # Define transitions
        self.add_transition(Transition(
            from_state="Available",
            to_state="Allocated",
            conditions=[has_sufficient_quantity, has_valid_schedule],
            side_effects=[update_availability, notify_resource_manager],
            required_fields={"quantity", "allocation_details"}
        ))
        
        self.add_transition(Transition(
            from_state="Allocated",
            to_state="In Use",
            conditions=[is_fully_allocated],
            side_effects=[notify_resource_manager],
            required_fields={"start_date", "assigned_to"}
        ))

# Usage in the Risk/Resource classes: 