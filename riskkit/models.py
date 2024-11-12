# from datetime import datetime
# from typing import Dict, Optional
# from .state_machine import RiskStateMachine

# class Risk:
#     def __init__(self, risk_id: int, description: str):
#         self.id: int = risk_id
#         self.description: str = description
#         self.probability: str = "Low"
#         self.impact: str = "Low"
#         self.priority: str = "Low"
#         self.status: str = "Open"
#         self.mitigation: str = ""
#         self.date_created: str = datetime.now().strftime("%Y-%m-%d")
#         self.last_updated: str = datetime.now().strftime("%Y-%m-%d")
#         self.owner: str = ""
#         self.category: str = ""
#         self.state_machine = RiskStateMachine()
        
#     def transition_to(self, new_state: str, context: Dict) -> bool:
#         try:
#             context = self.state_machine.transition(self.status, new_state, context)
#             self.status = new_state
#             self.last_updated = datetime.now().strftime("%Y-%m-%d")
#             return True
#         except ValueError as e:
#             return False

#     def can_transition_to(self, new_state: str, context: Dict) -> bool:
#         return self.state_machine.can_transition(self.status, new_state, context)

#     def to_dict(self) -> Dict:
#         return {
#             "id": self.id,
#             "description": self.description,
#             "probability": self.probability,
#             "impact": self.impact,
#             "priority": self.priority,
#             "status": self.status,
#             "mitigation": self.mitigation,
#             "date_created": self.date_created,
#             "last_updated": self.last_updated,
#             "owner": self.owner,
#             "category": self.category
#         }

#     @classmethod
#     def from_dict(cls, data: Dict) -> 'Risk':
#         risk = cls(data["id"], data["description"])
#         for key, value in data.items():
#             if hasattr(risk, key):
#                 setattr(risk, key, value)
#         return risk 