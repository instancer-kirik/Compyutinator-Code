from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Any
import re
import os
import logging
from .symbol_manager import CodeSymbol

class TechnicalAnalyzer:
    def __init__(self, cccore):
        self.cccore = cccore
        
    def analyze_project(self, project_name: str) -> Dict[str, Any]:
        """Generate comprehensive technical analysis of project"""
        try:
            project_path = self.cccore.project_manager.get_project_path(project_name)
            if not project_path:
                return {}
                
            return {
                'project_info': self._get_project_info(project_name, project_path),
                'structure': self._analyze_structure(project_path),
                'dependencies': self._analyze_dependencies(project_path),
                'entry_points': self._find_entry_points(project_path),
                'relationships': self._analyze_relationships(project_path),
                'environment': self._get_environment_info()
            }
            
        except Exception as e:
            logging.error(f"Error analyzing project: {e}")
            return {}

    def _get_project_info(self, name: str, path: Path) -> Dict[str, Any]:
        """Get basic project information"""
        return {
            'name': name,
            'type': self.cccore.project_manager.get_project_type(name),
            'path': str(path),
            'vault_info': self._get_vault_info()
        }

    def _get_vault_info(self) -> Dict[str, Any]:
        """Get current vault information"""
        vault = self.cccore.vault_manager.current_vault
        return {
            'name': vault.name if vault else None,
            'path': str(self.cccore.vault_manager.get_current_vault_path())
        }

    def _analyze_structure(self, project_path: Path) -> Dict[str, Dict]:
        """Analyze project structure including symbols"""
        structure = {}
        
        for file_path in project_path.rglob('*.py'):
            relative_path = file_path.relative_to(project_path)
            
            # Get or parse symbols
            symbols = self._get_file_symbols(file_path)
            structure[str(relative_path)] = {
                'symbols': self._format_symbols(symbols),
                'metadata': self._get_file_metadata(file_path)
            }
            
        return structure

    def _get_file_symbols(self, file_path: Path) -> List[CodeSymbol]:
        """Get symbols from file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return self._parse_file_symbols(content, file_path)
        except Exception as e:
            logging.error(f"Error parsing symbols from {file_path}: {e}")
            return []

    def _format_symbols(self, symbols: List[CodeSymbol]) -> List[Dict]:
        """Format symbols for output"""
        return [{
            'name': sym.name,
            'type': sym.type,
            'line': sym.line,
            'column': sym.column,
            'parent': sym.parent.name if sym.parent else None,
            'children': [child.name for child in sym.children]
        } for sym in symbols]

    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get file metadata from vault index"""
        vault = self.cccore.vault_manager.current_vault
        if not vault:
            return {}
            
        file_info = vault.get_index().get('files', {}).get(str(file_path), {})
        return {
            'type': file_info.get('type'),
            'size': file_info.get('size'),
            'created': file_info.get('created'),
            'modified': file_info.get('modified'),
            'tags': file_info.get('tags', []),
            'links': file_info.get('links', [])
        }

    def _analyze_dependencies(self, project_path: Path) -> List[str]:
        """Analyze project dependencies"""
        dependencies = set()
        
        for file_path in project_path.rglob('*.py'):
            with open(file_path, 'r') as f:
                content = f.read()
            dependencies.update(self._extract_dependencies(content))
            
        return list(dependencies)

    def _get_environment_info(self) -> Dict[str, Any]:
        """Get environment configuration"""
        return {
            'nix_enabled': bool(self.cccore.vault_manager.get_nix_store_path()),
            'nix_store_path': str(self.cccore.vault_manager.get_nix_store_path() or ''),
            'knowledge_graph': self._get_knowledge_graph()
        }

    def _get_knowledge_graph(self) -> Dict[str, List]:
        """Get knowledge graph information"""
        vault = self.cccore.vault_manager.current_vault
        if not vault:
            return {}
            
        return {
            'tags': list(vault.get_all_tags()),
            'references': list(vault.get_all_references()),
            'backlinks': list(vault.get_all_backlinks())
        } 