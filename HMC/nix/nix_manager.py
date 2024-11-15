from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
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
            subprocess.run(['nix', '--version'], capture_output=True, check=True)
            return True
        except FileNotFoundError:
            return False
            
    def run_command(self, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a Nix command safely"""
        if not self.nix_available:
            raise NixCommandError("Nix is not installed")
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, **kwargs)
            return result
        except subprocess.CalledProcessError as e:
            raise NixCommandError(f"Command failed: {e.stderr.strip()}")
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
        except Exception as e:
            logging.error(f"Error getting item size: {e}")
            return 0
            
    def _get_version(self, path: Path) -> str:
        """Extract version from store path"""
        try:
            parts = path.name.split('-')
            return parts[1] if len(parts) > 1 else "unknown"
        except Exception as e:
            logging.error(f"Error extracting version: {e}")
            return "unknown"
            
    def get_dependencies(self, path: Path) -> List[str]:
        """Get dependencies of a store item"""
        try:
            result = self.run_command(['nix-store', '--query', '--references', str(path)])
            return result.stdout.strip().split('\n')
        except Exception as e:
            logging.error(f"Error getting dependencies: {e}")
            return []
            
    def get_referrers(self, path: Path) -> List[str]:
        """Get items that depend on this store item"""
        try:
            result = self.run_command(['nix-store', '--query', '--referrers', str(path)])
            return result.stdout.strip().split('\n')
        except Exception as e:
            logging.error(f"Error getting referrers: {e}")
            return []
            
    def delete_item(self, path: Path) -> bool:
        """Delete a store item"""
        try:
            self.run_command(['nix-store', '--delete', str(path)])
            return True
        except Exception as e:
            logging.error(f"Error deleting item: {e}")
            return False
            
    def get_package_info(self, package_name: str) -> str:
        """Get detailed information about a specific Nix package"""
        try:
            result = self.run_command(['nix', 'path-info', '--json', package_name])
            return result.stdout.strip()
        except Exception as e:
            logging.error(f"Error fetching package info: {e}")
            return f"Error fetching package info: {e}"

    # New methods for handling flakes
    def update_flake(self, flake_path: str) -> bool:
        """Update a Nix flake"""
        try:
            self.run_command(['nix', 'flake', 'update', flake_path])
            logging.info(f"Flake updated: {flake_path}")
            return True
        except Exception as e:
            logging.error(f"Error updating flake: {e}")
            return False

    def build_flake(self, flake_path: str) -> bool:
        """Build a Nix flake"""
        try:
            self.run_command(['nix', 'build', flake_path])
            logging.info(f"Flake built: {flake_path}")
            return True
        except Exception as e:
            logging.error(f"Error building flake: {e}")
            return False

    def get_flake_info(self, flake_path: str) -> str:
        """Get information about a Nix flake"""
        try:
            result = self.run_command(['nix', 'flake', 'show', flake_path])
            return result.stdout.strip()
        except Exception as e:
            logging.error(f"Error fetching flake info: {e}")
            return f"Error fetching flake info: {e}"

    def get_installed_packages(self) -> Dict[str, NixPackage]:
        """Get a list of installed packages in the Nix store."""
        installed_packages = {}
        for store in self._stores.values():
            installed_packages.update(store)
        return installed_packages

    def check_for_upgrades(self) -> Dict[str, Tuple[NixPackage, str]]:
        """Check for available upgrades for installed packages."""
        upgrades = {}
        installed_packages = self.get_installed_packages()

        for package_name, package in installed_packages.items():
            latest_version = self._get_latest_version(package_name)
            if latest_version and latest_version != package.version:
                upgrades[package_name] = (package, latest_version)

        return upgrades

    def _get_latest_version(self, package_name: str) -> Optional[str]:
        """Get the latest version available for a package."""
        try:
            result = self.run_command(['nix', 'search', package_name])
            # Parse the output to find the latest version
            for line in result.stdout.splitlines():
                if package_name in line:
                    parts = line.split()
                    if len(parts) > 1:
                        return parts[1]  # Assuming version is the second part
        except Exception as e:
            logging.error(f"Error fetching latest version for {package_name}: {e}")
        return None

    def upgrade_package(self, package_name: str) -> bool:
        """Upgrade a specific package to the latest version."""
        try:
            self.run_command(['nix', 'upgrade', package_name])
            logging.info(f"Package upgraded: {package_name}")
            return True
        except Exception as e:
            logging.error(f"Error upgrading package {package_name}: {e}")
            return False

    def upgrade_all_packages(self) -> List[str]:
        """Upgrade all packages that have available upgrades."""
        upgrades = self.check_for_upgrades()
        upgraded_packages = []

        for package_name, (package, latest_version) in upgrades.items():
            if self.upgrade_package(package_name):
                upgraded_packages.append(package_name)

        return upgraded_packages
            