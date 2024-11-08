from pathlib import Path
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal
import logging

@dataclass
class CodeSymbol:
    name: str
    type: str  # 'class', 'function', 'method', 'variable'
    line: int
    column: int
    file_path: Path
    parent: Optional['CodeSymbol'] = None
    children: List['CodeSymbol'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

class SymbolManager(QObject):
    symbols_updated = pyqtSignal(Path)
    
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.file_symbols: Dict[Path, List[CodeSymbol]] = {}
        self.vault_symbols: Dict[str, Dict[Path, List[CodeSymbol]]] = {}
        
    def update_vault_symbols(self, vault_name: str):
        """Update symbols for all code files in a vault"""
        vault = self.cccore.vault_manager.vaults.get(vault_name)
        if not vault:
            return
            
        self.vault_symbols[vault_name] = {}
        
        # Use existing vault index to find code files
        index = vault.get_index()
        for rel_path, file_info in index['files'].items():
            if file_info['type'] == 'code':
                full_path = vault.path / rel_path
                self.parse_file(full_path, vault_name)
    
    def parse_file(self, file_path: Path, vault_name: Optional[str] = None):
        """Parse symbols from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            symbols = []
            current_class = None
            
            for line_num, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                
                # Class definition
                if stripped.startswith('class '):
                    class_match = re.match(r'class\s+(\w+)', stripped)
                    if class_match:
                        class_name = class_match.group(1)
                        current_class = CodeSymbol(
                            name=class_name,
                            type='class',
                            line=line_num,
                            column=line.index('class'),
                            file_path=file_path
                        )
                        symbols.append(current_class)
                
                # Function/method definition
                elif stripped.startswith('def '):
                    func_match = re.match(r'def\s+(\w+)', stripped)
                    if func_match:
                        func_name = func_match.group(1)
                        func_symbol = CodeSymbol(
                            name=func_name,
                            type='method' if current_class else 'function',
                            line=line_num,
                            column=line.index('def'),
                            file_path=file_path,
                            parent=current_class
                        )
                        if current_class:
                            current_class.children.append(func_symbol)
                        else:
                            symbols.append(func_symbol)
            
            self.file_symbols[file_path] = symbols
            if vault_name:
                if vault_name not in self.vault_symbols:
                    self.vault_symbols[vault_name] = {}
                self.vault_symbols[vault_name][file_path] = symbols
            
            self.symbols_updated.emit(file_path)
            
        except Exception as e:
            logging.error(f"Error parsing symbols from {file_path}: {str(e)}")
            return []