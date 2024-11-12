from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from .symbol_manager import SymbolManager, CodeSymbol

class CodeManager(QObject):
    code_updated = pyqtSignal(Path)
    
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.symbol_manager = SymbolManager(cccore)  # Use the enhanced SymbolManager
        self.lexer_cache = {}  # Reuse lexers from AuraText
    
    def get_file_symbols(self, file_path: Path) -> List[CodeSymbol]:
        """Get symbols for a file using the symbol manager"""
        return self.symbol_manager.get_file_symbols(file_path)
    
    def analyze_file(self, file_path: Path):
        """Analyze a file using AuraText lexers and update symbols"""
        try:
            # Reuse AuraText's lexer functionality
            from AuraText.auratext.Core.Lexers import ColorCodeLexer
            from AuraText.auratext.Core.file_outline_widget import FileOutlineWidget
            
            # Let symbol manager handle the symbol parsing
            self.symbol_manager.parse_file(file_path)
            
            # Additional code analysis if needed...
            
            self.code_updated.emit(file_path)
            
        except Exception as e:
            self.cccore.notification_manager.show_error(f"Error analyzing file: {str(e)}")