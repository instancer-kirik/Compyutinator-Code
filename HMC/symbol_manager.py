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
    references: List['SymbolReference'] = None  # Add references field
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.references is None:
            self.references = []

@dataclass
class SymbolReference:
    """Represents a reference to a symbol from another location"""
    symbol: CodeSymbol
    file_path: Path
    line: int
    column: int
    reference_type: str  # 'import', 'call', 'inheritance', 'assignment'
    context: str  # The line of code containing the reference

class SymbolManager(QObject):
    symbols_updated = pyqtSignal(Path)
    
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.file_symbols: Dict[Path, List[CodeSymbol]] = {}
        self.vault_symbols: Dict[str, Dict[Path, List[CodeSymbol]]] = {}
        self.symbol_index: Dict[str, CodeSymbol] = {}  # Quick lookup by name
    
    def parse_file(self, file_path: Path, vault_name: Optional[str] = None):
        """Parse symbols from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            symbols = []
            current_class = None
            
            # First pass: collect symbols
            for line_num, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                
                # Class definition
                if stripped.startswith('class '):
                    class_match = re.match(r'class\s+(\w+)(?:\((.*?)\))?:', stripped)
                    if class_match:
                        class_name = class_match.group(1)
                        bases = class_match.group(2)
                        current_class = CodeSymbol(
                            name=class_name,
                            type='class',
                            line=line_num,
                            column=line.index('class'),
                            file_path=file_path
                        )
                        symbols.append(current_class)
                        self.symbol_index[class_name] = current_class
                        
                        # Handle inheritance references
                        if bases:
                            for base in bases.split(','):
                                base = base.strip()
                                if base in self.symbol_index:
                                    current_class.references.append(SymbolReference(
                                        symbol=self.symbol_index[base],
                                        file_path=file_path,
                                        line=line_num,
                                        column=line.index(base),
                                        reference_type='inheritance',
                                        context=line.strip()
                                    ))
                
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
                        self.symbol_index[func_name] = func_symbol
            
            # Second pass: find references
            for line_num, line in enumerate(content.splitlines(), 1):
                self._find_references(line, line_num, file_path, symbols)
            
            self.file_symbols[file_path] = symbols
            if vault_name:
                if vault_name not in self.vault_symbols:
                    self.vault_symbols[vault_name] = {}
                self.vault_symbols[vault_name][file_path] = symbols
            
            self.symbols_updated.emit(file_path)
            
        except Exception as e:
            logging.error(f"Error parsing symbols from {file_path}: {str(e)}")
            return []
    
    def _find_references(self, line: str, line_num: int, file_path: Path, symbols: List[CodeSymbol]):
        """Find references to symbols in a line of code"""
        # Import references
        import_match = re.match(r'^from\s+(\w+)\s+import\s+(.+)$', line.strip())
        if import_match:
            module, imports = import_match.groups()
            for imp in imports.split(','):
                imp = imp.strip()
                if imp in self.symbol_index:
                    self.symbol_index[imp].references.append(SymbolReference(
                        symbol=self.symbol_index[imp],
                        file_path=file_path,
                        line=line_num,
                        column=line.index(imp),
                        reference_type='import',
                        context=line.strip()
                    ))
        
        # Function/method calls
        for symbol in symbols:
            if symbol.name + '(' in line:
                col = line.index(symbol.name)
                symbol.references.append(SymbolReference(
                    symbol=symbol,
                    file_path=file_path,
                    line=line_num,
                    column=col,
                    reference_type='call',
                    context=line.strip()
                ))
        
        # Variable assignments
        for symbol in symbols:
            if re.match(rf'\b{symbol.name}\s*=', line):
                col = line.index(symbol.name)
                symbol.references.append(SymbolReference(
                    symbol=symbol,
                    file_path=file_path,
                    line=line_num,
                    column=col,
                    reference_type='assignment',
                    context=line.strip()
                ))
    
    def get_symbol_references(self, symbol_name: str) -> List[SymbolReference]:
        """Get all references to a symbol across files"""
        symbol = self.symbol_index.get(symbol_name)
        if symbol:
            return symbol.references
        return []
    
    def get_file_references(self, file_path: Path) -> Dict[str, List[SymbolReference]]:
        """Get all symbol references in a file"""
        references = {}
        for symbol in self.file_symbols.get(file_path, []):
            if symbol.references:
                references[symbol.name] = symbol.references
        return references
    
    def get_relevant_symbols(self, prompt: str) -> List[CodeSymbol]:
        """Find symbols relevant to the prompt"""
        relevant_symbols = []
        
        # Check for direct symbol name mentions
        for symbol_name, symbol in self.symbol_index.items():
            if symbol_name.lower() in prompt.lower():
                relevant_symbols.append(symbol)
                
                # Include related symbols
                if symbol.parent:
                    relevant_symbols.append(symbol.parent)
                relevant_symbols.extend(symbol.children)
                
                # Include referenced symbols
                for ref in symbol.references:
                    if ref.symbol not in relevant_symbols:
                        relevant_symbols.append(ref.symbol)