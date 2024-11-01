from dataclasses import dataclass
from typing import Optional

@dataclass
class ApiConfig:
    """Configuration for API connections"""
    ws_url: str = "ws://localhost:4000/socket"
    api_url: str = "http://localhost:4000/api"
    auth_url: str = "http://localhost:4000/auth"
    token: Optional[str] = None 