from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import psutil
import subprocess
import platform
import os
import json
import logging

@dataclass
class SystemInfo:
    # Core system info
    name: str
    system_type: str = "software"  # software/hardware/infrastructure/service/hybrid
    lifecycle_stage: str = "development"  # concept/development/testing/production/maintenance/eol
    environment_type: str = "development"  # development/staging/production/testing
    
    # System details
    os_info: Dict[str, str] = field(default_factory=dict)
    technical_stack: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    root_path: Path = None
    
    # Runtime metrics
    health_metrics: Dict[str, float] = field(default_factory=lambda: {
        "availability": 0.0,
        "reliability": 0.0,
        "performance": 0.0,
        "security_score": 0.0,
        "maintainability": 0.0
    })
    
    # System resources
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    network_connections: List[Dict[str, Any]] = field(default_factory=list)
    active_services: List[Dict[str, str]] = field(default_factory=list)
    
    # Environment
    environment_variables: Dict[str, str] = field(default_factory=dict)
    filesystem_config: Dict[str, Any] = field(default_factory=lambda: {
        "paths": {
            "data": None,
            "logs": None,
            "config": None,
            "temp": None,
            "backup": None
        },
        "permissions": {
            "owner": None,
            "group": None,
            "mode": None
        },
        "mount_points": [],
        "storage_quotas": {
            "max_size": None,
            "warning_threshold": None
        }
    })

    def to_markdown(self) -> str:
        """Generate markdown report of system info"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""# System Overview - {self.name}
Generated at: {now}

## System Information
- **Type:** {self.system_type}
- **Lifecycle Stage:** {self.lifecycle_stage}
- **Environment:** {self.environment_type}

## Operating System
- **System:** {self.os_info.get('system', 'Unknown')}
- **Release:** {self.os_info.get('release', 'Unknown')}
- **Version:** {self.os_info.get('version', 'Unknown')}
- **Machine:** {self.os_info.get('machine', 'Unknown')}

## Resource Usage
- **CPU Usage:** {self.resource_usage.get('cpu_percent', 0)}%
- **Memory Usage:** {self.resource_usage.get('memory_percent', 0)}%
- **Disk Usage:** {self.resource_usage.get('disk_percent', 0)}%

## Active Services: {len(self.active_services)}
{self._format_services()}

## Network Connections: {len(self.network_connections)}
{self._format_connections()}

## Technical Stack
{self._format_list(self.technical_stack)}

## Dependencies
{self._format_list(self.dependencies)}

## Health Metrics
{self._format_dict(self.health_metrics)}

## Filesystem Configuration
{self._format_dict(self.filesystem_config, depth=1)}
"""

    def _format_services(self) -> str:
        return "\n".join(
            f"- **{service['name']}** - {service['status']}"
            for service in self.active_services
        )

    def _format_connections(self) -> str:
        return "\n".join(
            f"- {conn['process']} ({conn['status']}) - {conn['local_addr']} → {conn['remote_addr']}"
            for conn in self.network_connections
        )

    def _format_list(self, items: List[str], indent: int = 0) -> str:
        prefix = "  " * indent
        return "\n".join(f"{prefix}- {item}" for item in items) or f"{prefix}- None"

    def _format_dict(self, d: Dict[str, Any], depth: int = 0) -> str:
        lines = []
        prefix = "  " * depth
        
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}- **{key}:**")
                lines.append(self._format_dict(value, depth + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}- **{key}:**")
                lines.append(self._format_list(value, depth + 1))
            else:
                lines.append(f"{prefix}- **{key}:** {value}")
                
        return "\n".join(lines)

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary"""
        return {
            "name": self.name,
            "system_type": self.system_type,
            "lifecycle_stage": self.lifecycle_stage,
            "environment_type": self.environment_type,
            "os_info": self.os_info,
            "technical_stack": self.technical_stack,
            "dependencies": self.dependencies,
            "root_path": str(self.root_path) if self.root_path else None,
            "health_metrics": self.health_metrics,
            "resource_usage": self.resource_usage,
            "network_connections": self.network_connections,
            "active_services": self.active_services,
            "environment_variables": self.environment_variables,
            "filesystem_config": self.filesystem_config
        } 