from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
import json
import os
import logging

@dataclass
class ProjectConfig:
    name: str
    project_type: str  # "local" or "resolvinator"
    path: str
    description: Optional[str] = None
    status: Optional[str] = None
    risk_appetite: Optional[float] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    websocket_enabled: bool = False
    symbols: Dict[str, List[Dict]] = None  # Add symbol tracking
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = {}
    
    @classmethod
    def load(cls, project_path: str) -> 'ProjectConfig':
        config_path = os.path.join(project_path, 'project_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        return None

    def save(self):
        config_path = os.path.join(self.path, 'project_config.json')
        # Convert symbols to serializable format
        serializable_symbols = {}
        for file_path, symbols in self.symbols.items():
            serializable_symbols[str(file_path)] = [
                {
                    'name': s.name,
                    'type': s.type,
                    'line': s.line,
                    'column': s.column,
                    'parent': s.parent.name if s.parent else None
                }
                for s in symbols
            ]
        
        data = {**self.__dict__, 'symbols': serializable_symbols}
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2, default=str) 