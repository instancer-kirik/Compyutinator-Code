from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from PyQt6.Qsci import QsciLexer
import threading

@dataclass
class CachedLexer:
    lexer: QsciLexer
    timestamp: datetime
    ttl: timedelta = timedelta(minutes=30)

    @property
    def is_expired(self) -> bool:
        return datetime.now() - self.timestamp > self.ttl

class LexerCache:
    def __init__(self):
        self._cache: Dict[Path, CachedLexer] = {}
        self._lock = threading.Lock()

    def get(self, file_path: Path) -> Optional[QsciLexer]:
        """Get lexer from cache if not expired"""
        with self._lock:
            if cached := self._cache.get(file_path):
                if not cached.is_expired:
                    cached.timestamp = datetime.now()  # Update timestamp
                    return cached.lexer
                del self._cache[file_path]
            return None

    def set(self, file_path: Path, lexer: QsciLexer):
        """Add lexer to cache"""
        with self._lock:
            self._cache[file_path] = CachedLexer(
                lexer=lexer,
                timestamp=datetime.now()
            )

    def cleanup(self):
        """Remove expired entries"""
        with self._lock:
            expired = [path for path, cached in self._cache.items() 
                      if cached.is_expired]
            for path in expired:
                del self._cache[path] 