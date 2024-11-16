
import logging
from typing import Dict, Any
from HMC.system_analyzer import SystemInfo
from HMC.projects.project_types import BaseProjectData
import json
class TechnicalOverviewGenerator:
    def __init__(self, config: BaseProjectData):
        self.config = config

    def generate(self) -> str:
        try:
            sys_info = self._get_system_info()
            overview = self._generate_header()
            overview += self._generate_system_section(sys_info)
            overview += self._generate_project_info()
            overview += self._generate_structure()
            return overview
        except Exception as e:
            logging.error(f"Error generating technical overview: {e}")
            return f"Error generating overview: {str(e)}"

    def _generate_file_tree(self) -> Dict[str, Any]:
        tree = {}
        try:
            for file_path in self.config.path.rglob('*'):
                if self._should_skip_file(file_path):
                    continue
                self._add_to_tree(tree, file_path)
            return tree
        except Exception as e:
            logging.error(f"Error generating file tree: {e}")
            return {}

    def _generate_file_tree(self) -> Dict[str, Any]:
        """Generate hierarchical file tree with symbols"""
        tree = {}
        
        try:
            for file_path in self.path.rglob('*'):
                if any(excluded in str(file_path) for excluded in self.excluded_dirs):
                    continue
                    
                relative_path = file_path.relative_to(self.path)
                parts = relative_path.parts
                
                current = tree
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                    
                if file_path.is_file() and file_path.suffix in self.file_extensions:
                    symbols = self.get_setting('tracking', 'symbols', {}).get(str(relative_path), [])
                    current[parts[-1]] = {
                        'type': 'file',
                        'symbols': [
                            {
                                'name': sym.name,
                                'type': sym.type,
                                'line': sym.line,
                                'children': [c.name for c in sym.children] if hasattr(sym, 'children') else []
                            }
                            for sym in symbols
                        ]
                    }
                else:
                    current[parts[-1]] = {'type': 'directory'}
                    
            return tree
            
        except Exception as e:
            logging.error(f"Error generating file tree: {e}")
            return {}

    def _format_tree_as_markdown(self, tree: Dict[str, Any], indent: int = 0) -> str:
        """Format file tree as markdown with symbols"""
        result = ""
        
        for name, content in sorted(tree.items()):
            prefix = "    " * indent
            
            if content.get('type') == 'file':
                result += f"{prefix}- 📄 `{name}`\n"
                
                # Add symbols if present
                symbols = content.get('symbols', [])
                for sym in symbols:
                    sym_prefix = "    " * (indent + 1)
                    icon = {
                        'class': '🔷',
                        'function': '🔶',
                        'method': '🔸',
                        'variable': '💠'
                    }.get(sym.get('type', ''), '•')
                    
                    result += f"{sym_prefix}{icon} `{sym['name']}`"
                    if sym.get('children'):
                        result += f" (contains: {', '.join(sym['children'])})"
                    result += "\n"
                    
            else:  # directory
                result += f"{prefix}- 📁 **{name}/**\n"
                if isinstance(content, dict):
                    result += self._format_tree_as_markdown(content, indent + 1)
                    
        return result
    def get_technical_flow(self) -> Dict[str, Any]:
        """Generate technical flow overview"""
        flow_data = {
            'project_info': {
                'name': self.name,
                'type': self.project_type.value,
                'path': str(self.path),
            },
            'structure': self._analyze_structure(),
            'dependencies': self._extract_dependencies(),
            'entry_points': self._find_entry_points(),
            'relationships': self._analyze_relationships()
        }
        return flow_data

    def _analyze_structure(self) -> Dict[str, Any]:
        """Analyze project structure"""
        structure = {}
        for file_path in self.path.rglob('*.py'):
            if any(excluded in str(file_path) for excluded in self.excluded_dirs):
                continue
            relative_path = file_path.relative_to(self.path)
            structure[str(relative_path)] = self._analyze_file(file_path)
        return structure

    def generate_technical_overview(self) -> str:
        """Generate a markdown technical overview of the project"""
        try:
            # Get system info
            sys_info = SystemInfo(
                name=self.name,
                system_type="software",
                lifecycle_stage=self.get_setting('tracking', 'lifecycle_stage', 'development'),
                root_path=self.path
            )
            
            # Project Header
            overview = f"""# {self.name} Technical Overview

## System Environment
{sys_info.to_markdown()}

## Project Information
- **Type:** {self.project_type.value}
- **Status:** {self.status}
- **Version:** {self.version}

## Development Configuration
- **Build Command:** `{self.get_setting('dev_settings', 'build_command') or 'N/A'}`
- **Run Command:** `{self.get_setting('dev_settings', 'run_command') or 'N/A'}`
- **Test Command:** `{self.get_setting('dev_settings', 'test_command') or 'N/A'}`

## Project Structure
"""
            # Add file tree with symbols
            tree_data = self._generate_file_tree()
            overview += self._format_tree_as_markdown(tree_data)
            
            return overview
            
        except Exception as e:
            logging.error(f"Error generating technical overview: {e}")
            return f"Error generating overview: {str(e)}"

    def export_technical_overview(self, format: str = 'md') -> bool:
        """Export technical overview to file"""
        try:
            overview = self.generate_technical_overview()
            output_path = self.path / 'docs' / 'technical_overview'
            output_path.mkdir(parents=True, exist_ok=True)
            
            if format == 'md':
                with open(output_path / 'overview.md', 'w') as f:
                    f.write(overview)
            elif format == 'json':
                tree_data = self._generate_file_tree()
                with open(output_path / 'overview.json', 'w') as f:
                    json.dump(tree_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logging.error(f"Error exporting technical overview: {e}")
            return False
