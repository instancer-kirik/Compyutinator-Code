from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QStyle
from typing import Dict, List
from pathlib import Path
from HMC.symbol_manager import CodeSymbol

class FileOutlineWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Symbol", "Type", "Location"])
        self.setColumnCount(3)
        self.setColumnWidth(0, 200)  # Name column
        self.setColumnWidth(1, 100)  # Type column
    
    def populate_project_outline(self, flow_map: Dict[Path, List[CodeSymbol]]):
        self.clear()
        for file_path, symbols in flow_map.items():
            file_item = QTreeWidgetItem([
                file_path.name,  # Show only filename
                "file",
                str(file_path.parent)  # Show parent directory
            ])
            self.addTopLevelItem(file_item)
            
            for symbol in symbols:
                if not symbol.parent:  # Only add top-level symbols
                    self._add_symbol_item(symbol, file_item)
    
    def _add_symbol_item(self, symbol: CodeSymbol, parent_item: QTreeWidgetItem):
        item = QTreeWidgetItem([
            symbol.name,
            symbol.type,
            f"Line {symbol.line}"
        ])
        
        # Store symbol and file path for reference
        item.symbol = symbol
        item.file_path = parent_item.file_path
        
        # Add icon based on symbol type
        if symbol.type == 'class':
            item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        elif symbol.type in ('function', 'method'):
            item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            
        parent_item.addChild(item)
        
        # Recursively add children
        for child in symbol.children:
            self._add_symbol_item(child, item)
