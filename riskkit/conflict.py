from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Any

@dataclass
class Change:
    field: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    user: str

class ConflictResolver:
    def __init__(self):
        self.resolution_strategies = {
            "last_write_wins": self._last_write_wins,
            "merge_fields": self._merge_fields,
            "manual": self._manual_resolution
        }

    def _last_write_wins(self, local: Dict, remote: Dict) -> Dict:
        """Simple last-write-wins strategy"""
        if local["version"] > remote["version"]:
            return local
        return remote

    def _merge_fields(self, local: Dict, remote: Dict) -> Dict:
        """Merge non-conflicting fields, flag conflicts for manual resolution"""
        merged = remote.copy()
        conflicts = {}

        for key, local_value in local.items():
            remote_value = remote.get(key)
            if key not in remote or local_value == remote_value:
                merged[key] = local_value
            else:
                conflicts[key] = {
                    "local": local_value,
                    "remote": remote_value,
                    "timestamp_local": local.get("last_updated"),
                    "timestamp_remote": remote.get("last_updated")
                }

        if conflicts:
            merged["_conflicts"] = conflicts

        return merged

    def _manual_resolution(self, local: Dict, remote: Dict) -> Dict:
        """Return both versions for manual resolution"""
        return {
            "local": local,
            "remote": remote,
            "requires_manual": True
        }

    def resolve(self, local: Dict, remote: Dict, strategy: str = "merge_fields") -> Dict:
        """Resolve conflicts between local and remote versions"""
        resolver = self.resolution_strategies.get(strategy, self._merge_fields)
        return resolver(local, remote) 