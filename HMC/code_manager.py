from pathlib import Path
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

@dataclass
class CodeSymbol:
    name: str
    type: str  # 'class', 'function', 'method', 'variable'
    line: int
    column: int
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
        self.lexer_cache = {}  # Reuse lexers from AuraText
        
    def get_file_symbols(self, file_path: Path) -> List[CodeSymbol]:
        """Get or parse symbols for a file"""
        if file_path not in self.file_symbols:
            self.parse_file(file_path)
        return self.file_symbols.get(file_path, [])
    
    def parse_file(self, file_path: Path):
        """Parse symbols using existing AuraText lexers"""
        try:
            # Reuse AuraText's lexer functionality
            from AuraText.auratext.Core.Lexers import ColorCodeLexer
            from AuraText.auratext.Core.file_outline_widget import FileOutlineWidget
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            symbols = []
            current_class = None
            
            for line_num, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                
                if stripped.startswith('class '):
                    class_name = re.match(r'class\s+(\w+)', stripped).group(1)
                    current_class = CodeSymbol(
                        name=class_name,
                        type='class',
                        line=line_num,
                        column=line.index('class')
                    )
                    symbols.append(current_class)
                    
                elif stripped.startswith('def '):
                    func_match = re.match(r'def\s+(\w+)', stripped)
                    if func_match:
                        func_name = func_match.group(1)
                        func_symbol = CodeSymbol(
                            name=func_name,
                            type='method' if current_class else 'function',
                            line=line_num,
                            column=line.index('def'),
                            parent=current_class
                        )
                        if current_class:
                            current_class.children.append(func_symbol)
                        else:
                            symbols.append(func_symbol)
            
            self.file_symbols[file_path] = symbols
            self.symbols_updated.emit(file_path)
            
        except Exception as e:
            self.cccore.notification_manager.show_error(f"Error parsing symbols: {str(e)}")