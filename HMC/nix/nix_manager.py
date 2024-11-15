from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import subprocess
import logging
from enum import Enum
import json
from datetime import datetime

class NixCommandError(Exception):
    """Custom exception for Nix command failures"""
    pass

class NixStore(Enum):
    SYSTEM = "system"
    USER = "user"
    PROJECT = "project"

@dataclass
class NixPackage:
    name: str
    version: str
    path: Path
    size: int
    modified: datetime
    dependencies: List[str] = field(default_factory=list)
    referrers: List[str] = field(default_factory=list)

class NixManager:
    def __init__(self):
        self.nix_available = self._check_nix_available()
        self._stores: Dict[NixStore, Dict[str, NixPackage]] = {
            store: {} for store in NixStore
        }
        
    def _check_nix_available(self) -> bool:
        """Check if Nix is installed and available"""
        try:
            subprocess.run(['nix', '--version'], capture_output=True)
            return True
        except FileNotFoundError:
            return False
            
    def run_command(self, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a Nix command safely"""
        if not self.nix_available:
            raise NixCommandError("Nix is not installed")
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
            if result.returncode != 0:
                raise NixCommandError(f"Command failed: {result.stderr}")
            return result
        except Exception as e:
            raise NixCommandError(f"Error running command: {e}")
            
    def get_store_items(self, store: NixStore) -> Dict[str, NixPackage]:
        """Get items from specified Nix store"""
        try:
            result = self.run_command(['nix-store', '--gc', '--print-live'])
            items = {}
            
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                    
                path = Path(line.strip())
                size = self._get_item_size(path)
                modified = datetime.fromtimestamp(path.stat().st_mtime)
                
                pkg = NixPackage(
                    name=path.name,
                    version=self._get_version(path),
                    path=path,
                    size=size,
                    modified=modified
                )
                items[path.name] = pkg
                
            self._stores[store] = items
            return items
            
        except Exception as e:
            logging.error(f"Error getting store items: {e}")
            return {}
            
    def _get_item_size(self, path: Path) -> int:
        """Get size of store item in bytes"""
        try:
            result = self.run_command(['nix-store', '--query', '--size', str(path)])
            return int(result.stdout.strip())
        except:
            return 0
            
    def _get_version(self, path: Path) -> str:
        """Extract version from store path"""
        try:
            parts = path.name.split('-')
            return parts[1] if len(parts) > 1 else "unknown"
        except:
            return "unknown"
            
    def get_dependencies(self, path: Path) -> List[str]:
        """Get dependencies of a store item"""
        try:
            result = self.run_command(['nix-store', '--query', '--references', str(path)])
            return result.stdout.strip().split('\n')
        except:
            return []
            
    def get_referrers(self, path: Path) -> List[str]:
        """Get items that depend on this store item"""
        try:
            result = self.run_command(['nix-store', '--query', '--referrers', str(path)])
            return result.stdout.strip().split('\n')
        except:
            return []
            
    def delete_item(self, path: Path) -> bool:
        """Delete a store item"""
        try:
            self.run_command(['nix-store', '--delete', str(path)])
            return True
        except:
            return False 