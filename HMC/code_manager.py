from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from .symbol_manager import SymbolManager
import ast
import networkx as nx
import logging
import threading
from PyQt6.Qsci import QsciLexer

class CodeAnalyzer:
    def __init__(self):
        self.ast_parser = ast.parse
        self.dependency_graph = nx.DiGraph()
        
    async def analyze_code(self, content: str):
        """Analyze code using AST and LangChain tools"""
        tree = self.ast_parser(content)
        analysis = {
                'imports': self.extract_imports(tree),
                'functions': self.extract_functions(tree),
               # 'classes': self.extract_classes(tree),
               # 'dependencies': self.build_dependency_graph(tree)
            }
        return analysis    
        
    def extract_imports(self, tree: ast.AST) -> List[Dict]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend([n.name for n in node.names])
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module}.{node.names[0].name}")
        return imports
        
    def extract_functions(self, tree: ast.AST) -> List[Dict]:
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'returns': getattr(node, 'returns', None)
                })
        return functions

class CodeManager:
    """Non-QObject singleton for code management"""
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, cccore=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(cccore)
        return cls._instance
    
    def __init__(self, cccore=None):
        if CodeManager._instance is not None:
            raise Exception("CodeManager is a singleton!")
            
        self.cccore = cccore
        self.symbol_manager = SymbolManager(cccore)
        self.code_analyzer = CodeAnalyzer()
        self.lexer_cache = {}
        self._state = "active"
        logging.debug("CodeManager singleton initialized")

    def get_lexer(self, file_path: Path) -> Optional[QsciLexer]:
        """Get lexer for file with caching"""
        try:
            with self._lock:
                cache_key = str(file_path)
                if cache_key in self.lexer_cache:
                    return self.lexer_cache[cache_key]
                    
                extension = file_path.suffix.lower()
                lexer = self._create_lexer(extension)
                if lexer:
                    self.lexer_cache[cache_key] = lexer
                return lexer
                
        except Exception as e:
            logging.error(f"Error getting lexer: {e}")
            return None

    def cleanup_lexer_cache(self):
        """Clean lexer cache"""
        try:
            with self._lock:
                self.lexer_cache.clear()
                logging.debug("Lexer cache cleaned")
        except Exception as e:
            logging.error(f"Error cleaning lexer cache: {e}")

    def _create_lexer(self, extension: str) -> Optional[QsciLexer]:
        """Create appropriate lexer for file extension"""
        try:
            from AuraText.auratext.Core.Lexers import LexerManager
            lexer_manager = LexerManager(self)
            language = lexer_manager.get_language_from_extension(extension)
            return lexer_manager.get_lexer(language)
        except Exception as e:
            logging.error(f"Error creating lexer: {e}")
            return None
            