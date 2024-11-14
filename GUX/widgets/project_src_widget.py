from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                           QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
                           QGraphicsView, QGraphicsScene, QMenu, QFileDialog,
                           QComboBox, QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPen, QPainterPath, QColor, QBrush, QPainter
from pathlib import Path
from typing import Dict, List, Optional
from HMC.symbol_manager import CodeSymbol
from GUX.widgets.file_outline_widget import FileOutlineWidget
import logging
import math
from HMC.project_config import ProjectConfig

class SymbolNode:
    def __init__(self, symbol: CodeSymbol, file_path: Path):
        self.symbol = symbol
        self.file_path = file_path
        self.references: List['SymbolNode'] = []
        self.x = 0
        self.y = 0
        
    def add_reference(self, ref: 'SymbolNode'):
        if ref not in self.references:
            self.references.append(ref)

class ProjectSourceWidget(QWidget):
    symbol_selected = pyqtSignal(CodeSymbol, Path)
    
    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.symbol_nodes: Dict[str, SymbolNode] = {}
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_view)
        toolbar.addWidget(self.refresh_btn)
        
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["Hierarchical", "Circular", "Force-Directed"])
        self.layout_combo.currentTextChanged.connect(self.update_layout)
        toolbar.addWidget(self.layout_combo)
        
        layout.addLayout(toolbar)
        
        # Main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: File outline
        self.outline = FileOutlineWidget()
        self.outline.itemClicked.connect(self.on_symbol_selected)
        splitter.addWidget(self.outline)
        
        # Right: Reference view
        ref_widget = QWidget()
        ref_layout = QVBoxLayout(ref_widget)
        
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_in = QPushButton("+")
        zoom_out = QPushButton("-")
        fit = QPushButton("Fit")
        zoom_in.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        zoom_out.clicked.connect(lambda: self.view.scale(0.8, 0.8))
        fit.clicked.connect(self.fit_view)
        zoom_layout.addWidget(zoom_in)
        zoom_layout.addWidget(zoom_out)
        zoom_layout.addWidget(fit)
        
        ref_layout.addLayout(zoom_layout)
        ref_layout.addWidget(self.view)
        
        splitter.addWidget(ref_widget)
        layout.addWidget(splitter)
        
    def refresh_view(self):
        """Refresh the entire view"""
        try:
            project = self.cccore.project_manager.get_current_project()
            if not project:
                return
                
            # Get all symbols
            symbols = self.cccore.symbol_manager.get_project_symbols(project.name)
            
            # Update outline
            self.outline.populate_project_outline(symbols)
            
            # Build reference graph
            self.build_reference_graph(symbols)
            
            # Update visualization
            self.update_reference_view()
            
        except Exception as e:
            logging.error(f"Error refreshing source view: {e}")

    def update_layout(self, layout_type: str):
        """Update the layout of the reference view"""
        if not self.symbol_nodes:
            return
            
        if layout_type == "Hierarchical":
            self._apply_hierarchical_layout()
        elif layout_type == "Circular":
            self._apply_circular_layout()
        else:
            self._apply_force_directed_layout()
            
        self.update_reference_view()

    def _apply_hierarchical_layout(self):
        """Apply hierarchical layout to nodes"""
        level_map = {}
        visited = set()
        
        def process_node(node: SymbolNode, level: int):
            if node in visited:
                return
            visited.add(node)
            
            if level not in level_map:
                level_map[level] = []
            level_map[level].append(node)
            
            for ref in node.references:
                process_node(ref, level + 1)
        
        # Process all root nodes
        roots = [node for node in self.symbol_nodes.values() if not any(node in n.references for n in self.symbol_nodes.values())]
        for root in roots:
            process_node(root, 0)
            
        # Position nodes
        max_nodes_per_level = max(len(nodes) for nodes in level_map.values())
        level_height = 100
        node_width = 150
        
        for level, nodes in level_map.items():
            y = level * level_height
            total_width = (len(nodes) - 1) * node_width
            start_x = -total_width / 2
            
            for i, node in enumerate(nodes):
                node.x = start_x + (i * node_width)
                node.y = y

    def _apply_circular_layout(self):
        """Apply circular layout to nodes"""
        nodes = list(self.symbol_nodes.values())
        count = len(nodes)
        if count == 0:
            return
            
        radius = count * 20
        angle_step = 2 * math.pi / count
        
        for i, node in enumerate(nodes):
            angle = i * angle_step
            node.x = radius * math.cos(angle)
            node.y = radius * math.sin(angle)

    def _apply_force_directed_layout(self):
        """Apply force-directed layout to nodes"""
        # Simple force-directed layout implementation
        iterations = 50
        k = 100  # Optimal distance
        
        for _ in range(iterations):
            # Calculate repulsive forces
            for node1 in self.symbol_nodes.values():
                dx = dy = 0
                for node2 in self.symbol_nodes.values():
                    if node1 != node2:
                        dx_temp = node1.x - node2.x
                        dy_temp = node1.y - node2.y
                        dist = math.sqrt(dx_temp**2 + dy_temp**2)
                        if dist < 1: dist = 1
                        
                        force = k**2 / dist
                        dx += (dx_temp / dist) * force
                        dy += (dy_temp / dist) * force
                
                # Apply attractive forces for references
                for ref in node1.references:
                    dx_temp = node1.x - ref.x
                    dy_temp = node1.y - ref.y
                    dist = math.sqrt(dx_temp**2 + dy_temp**2)
                    if dist < 1: dist = 1
                    
                    force = dist**2 / k
                    dx -= (dx_temp / dist) * force
                    dy -= (dy_temp / dist) * force
                
                # Update position
                node1.x += dx
                node1.y += dy

    def _draw_reference_graph(self):
        """Draw the reference graph"""
        # Draw edges first
        for node in self.symbol_nodes.values():
            for ref in node.references:
                path = QPainterPath()
                path.moveTo(node.x, node.y)
                path.lineTo(ref.x, ref.y)
                
                edge = self.scene.addPath(path, 
                    QPen(QColor("#666666"), 1, Qt.PenStyle.SolidLine))
                edge.setZValue(0)
        
        # Draw nodes
        for node in self.symbol_nodes.values():
            color = self._get_symbol_color(node.symbol)
            ellipse = self.scene.addEllipse(
                node.x - 5, node.y - 5, 10, 10,
                QPen(Qt.GlobalColor.black),
                QBrush(color)
            )
            ellipse.setZValue(1)
            
            # Add label
            text = self.scene.addText(node.symbol.name)
            text.setPos(node.x - text.boundingRect().width()/2,
                       node.y + 10)
            text.setZValue(1)
            
            # Add tooltip and make clickable
            ellipse.setToolTip(
                f"{node.symbol.name}\n"
                f"Type: {node.symbol.type}\n"
                f"File: {node.file_path.name}"
            )
            ellipse.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            ellipse.setData(0, node)

    def _get_symbol_color(self, symbol: CodeSymbol) -> QColor:
        """Get color for symbol type"""
        colors = {
            'class': QColor("#4CAF50"),
            'function': QColor("#2196F3"),
            'method': QColor("#03A9F4"),
            'variable': QColor("#9C27B0"),
            'module': QColor("#FF9800")
        }
        return colors.get(symbol.type, QColor("#757575"))

    def fit_view(self):
        """Fit view to content"""
        self.view.fitInView(
            self.scene.itemsBoundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio
        )

    def on_symbol_selected(self, item: QTreeWidgetItem, column: int):
        """Handle symbol selection in outline"""
        if hasattr(item, 'symbol'):
            self.symbol_selected.emit(item.symbol, item.file_path)
            
            # Highlight in reference view
            node_id = f"{item.file_path}:{item.symbol.name}"
            if node_id in self.symbol_nodes:
                self.highlight_symbol_references(self.symbol_nodes[node_id])

    def highlight_symbol_references(self, node: SymbolNode):
        """Highlight selected symbol and its references"""
        # Reset previous highlighting
        for item in self.scene.items():
            if isinstance(item, QGraphicsEllipseItem):
                item.setPen(QPen(Qt.GlobalColor.black))
            elif isinstance(item, QGraphicsPathItem):
                item.setPen(QPen(QColor("#666666"), 1))
        
        # Highlight selected node
        for item in self.scene.items():
            if isinstance(item, QGraphicsEllipseItem):
                item_node = item.data(0)
                if item_node == node:
                    item.setPen(QPen(Qt.GlobalColor.red, 2))
                elif item_node in node.references:
                    item.setPen(QPen(Qt.GlobalColor.blue, 2))

    def build_reference_graph(self, symbols: Dict[Path, List[CodeSymbol]]):
        """Build the reference graph from symbols"""
        self.symbol_nodes.clear()
        
        # First pass: Create nodes
        for file_path, file_symbols in symbols.items():
            for symbol in file_symbols:
                node_id = f"{file_path}:{symbol.name}"
                self.symbol_nodes[node_id] = SymbolNode(symbol, file_path)
        
        # Second pass: Build references
        for file_path, file_symbols in symbols.items():
            for symbol in file_symbols:
                node_id = f"{file_path}:{symbol.name}"
                node = self.symbol_nodes[node_id]
                
                # Add parent-child relationships
                if symbol.parent:
                    parent_id = f"{file_path}:{symbol.parent.name}"
                    if parent_id in self.symbol_nodes:
                        node.add_reference(self.symbol_nodes[parent_id])
                
                # Add references from symbol tracking
                if hasattr(symbol, 'references'):
                    for ref in symbol.references:
                        ref_id = f"{file_path}:{ref.name}"
                        if ref_id in self.symbol_nodes:
                            node.add_reference(self.symbol_nodes[ref_id])

    def update_reference_view(self):
        """Update the reference visualization"""
        self.scene.clear()
        
        if not self.symbol_nodes:
            return
        
        # Apply current layout
        layout_type = self.layout_combo.currentText()
        if layout_type == "Hierarchical":
            self._apply_hierarchical_layout()
        elif layout_type == "Circular":
            self._apply_circular_layout()
        else:
            self._apply_force_directed_layout()
        
        # Draw the graph
        self._draw_reference_graph()
        
        # Fit view
        self.fit_view()

    def set_project(self, project_config: ProjectConfig):
        """Set current project and refresh view"""
        self.project_config = project_config
        self.refresh_view()