from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List
from pathlib import Path
import re
import logging

class AtomStore(Enum):
    GIT = "git"
    S3 = "s3"
    NIX = "nix"
    LOCAL = "local"

@dataclass
class AtomIdentifier:
    scheme: Optional[str]
    user: Optional[str]
    password: Optional[str]
    url_alias: Optional[str]
    url_fragment: Optional[str]
    atom_id: str
    version: Optional[str]

    @classmethod
    def parse(cls, uri: str) -> 'AtomIdentifier':
        """Parse an Atom URI into components"""
        try:
            # Basic pattern: scheme:user:pass@alias#fragment::id@version
            pattern = r"(?:(?P<scheme>[^:]+):)?(?:(?P<auth>[^@]+)@)?(?:(?P<alias>[^#]+)(?:#(?P<fragment>[^:]+))?::)?(?P<id>[^@]+)(?:@(?P<version>.+))?"
            match = re.match(pattern, uri)
            if not match:
                raise ValueError(f"Invalid Atom URI format: {uri}")
                
            auth_parts = match.group('auth').split(':') if match.group('auth') else [None, None]
            return cls(
                scheme=match.group('scheme'),
                user=auth_parts[0],
                password=auth_parts[1] if len(auth_parts) > 1 else None,
                url_alias=match.group('alias'),
                url_fragment=match.group('fragment'),
                atom_id=match.group('id'),
                version=match.group('version')
            )
        except Exception as e:
            logging.error(f"Error parsing Atom URI: {e}")
            raise

class AtomManager:
    def __init__(self, nix_manager):
        self.nix_manager = nix_manager
        self.stores: Dict[AtomStore, Dict] = {}
        self._setup_stores()
        
    def _setup_stores(self):
        """Initialize store backends"""
        self.stores[AtomStore.NIX] = self._create_nix_store()
        
    def _create_nix_store(self) -> Dict:
        """Create Nix store implementation"""
        return {
            'resolve': self._resolve_nix_atom,
            'publish': self._publish_nix_atom,
            'get_deps': self._get_nix_atom_deps
        }
        
    def get_atom_deps(self, path: str) -> List[str]:
        """Get atom dependencies"""
        return self.nix_manager.get_dependencies(Path(path))
        
    def get_atom_reverse_deps(self, path: str) -> List[str]:
        """Get reverse dependencies"""
        return self.nix_manager.get_referrers(Path(path))
        
    def get_atom_build_log(self, path: str) -> str:
        """Get build log for an atom"""
        result = self.nix_manager.run_command(['nix', 'log', path])
        return result.stdout.strip()
        
    def get_atom_uri(self, path: str) -> str:
        """Generate Atom URI from path"""
        match = re.search(r'/nix/store/[^-]+-([^/]+)', path)
        if not match:
            raise ValueError("Could not extract Atom name from path")
        return f"nix:{match.group(1)}"
        
    def generate_lock_file(self, path: str) -> str:
        """Generate lock file for an atom"""
        result = self.nix_manager.run_command(['nix', 'generate-lock-file', path])
        return result.stdout.strip()