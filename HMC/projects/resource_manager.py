from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from datetime import datetime
from pathlib import Path
import logging
from HMC.projects.project_types import BaseProjectData

@dataclass
class ResourceManager:
    project: BaseProjectData
    allocations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def allocate(self, resource_id: str, allocation: Dict[str, Any]) -> bool:
        """Allocate resource with validation"""
        try:
            if not self._validate_allocation(resource_id, allocation):
                return False
                
            self.allocations[resource_id] = {
                **allocation,
                'timestamp': datetime.now().isoformat(),
                'status': 'active'
            }
            return True
        except Exception as e:
            logging.error(f"Resource allocation error: {e}")
            return False
            
    def get_allocation(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get resource allocation details"""
        return self.allocations.get(resource_id)
        
    def _validate_allocation(self, resource_id: str, allocation: Dict[str, Any]) -> bool:
        """Validate resource allocation"""
        try:
            # Check resource exists
            if resource_id not in self.project.resources:
                return False
                
            resource = self.project.resources[resource_id]
            
            # Check quantity available
            if allocation.get('quantity', 0) > resource.quantity:
                return False
                
            # Check allocation period
            start = datetime.fromisoformat(allocation.get('start_date', ''))
            end = datetime.fromisoformat(allocation.get('end_date', ''))
            if start > end:
                return False
                
            return True
        except Exception as e:
            logging.error(f"Allocation validation error: {e}")
            return False

    def list_allocations(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List resource allocations with optional filtering"""
        try:
            allocations = list(self.allocations.values())
            if not filters:
                return allocations
                
            return [
                alloc for alloc in allocations
                if all(alloc.get(k) == v for k, v in filters.items())
            ]
        except Exception as e:
            logging.error(f"Error listing allocations: {e}")
            return [] 