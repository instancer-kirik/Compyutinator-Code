from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
                            QGraphicsItem, QGraphicsItemGroup, QGraphicsEllipseItem, QGraphicsLineItem)
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter
import sys
import os
from pathlib import Path
import math
from dataclasses import dataclass
from typing import List, Dict, Optional
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QGraphicsPathItem, QStyleOptionGraphicsItem)
from PyQt6.QtGui import QPainterPath, QGradient
from HMC.symbol_manager import CodeSymbol
from HMC.project_manager import Project

@dataclass
class FSNode:
    """
    Class representing a node in the file structure.

    Attributes:
    - path: The path of the file/directory.
    - x, y: Coordinates of the node.
    - radius: Radius of the node.
    - velocity_x, velocity_y: Velocities in x and y directions.
    - expanded: Boolean indicating if the node is expanded.
    - parent: Parent node.
    - children: List of child nodes.
    - symbols: List of symbols associated with the node.
    - project: Reference to the project associated with the node.
    """
    path: Path
    x: float
    y: float
    radius: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    expanded: bool = False
    parent: Optional['FSNode'] = None
    children: List['FSNode'] = None
    symbols: List['CodeSymbol'] = None
    project: Optional['Project'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.symbols is None:
            self.symbols = []
        self.name = self.path.name or str(self.path)
 
    # Add more methods and comments here
class FileNode(QGraphicsEllipseItem):
    def __init__(self, node: FSNode, scene_node: 'FileSystemScene'):
        super().__init__(0, 0, node.radius * 2, node.radius * 2)
        self.node = node
        self.scene_node = scene_node
        self.setPos(node.x, node.y)
        self.setAcceptHoverEvents(True)
        
        # Visual settings
        self.default_color = self._get_node_color()
        self.setBrush(QBrush(self.default_color))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        
        # Add to scene first
        scene_node.addItem(self)
        
        # Add text label
        self.label = scene_node.addSimpleText(node.name)
        self.update_label_position()

    def _get_node_color(self) -> QColor:
        # First check for symbols
        if self.node.symbols:
            symbol_type = self.node.symbols[0].type
            return {
                'class': QColor(255, 87, 34),    # Deep Orange
                'function': QColor(33, 150, 243), # Blue
                'method': QColor(0, 150, 136),    # Teal
            }.get(symbol_type, QColor(200, 200, 200))
        
        # Then check file type
        if self.node.path.is_dir():
            return QColor(100, 149, 237)  # Cornflower blue
            
        ext = self.node.path.suffix.lower()
        return {
            '.py': QColor(106, 176, 76),
            '.rs': QColor(255, 132, 0),
            '.cpp': QColor(249, 168, 212),
            '.js': QColor(241, 224, 90),
            '.md': QColor(158, 158, 158),
        }.get(ext, QColor(200, 200, 200))

    def update_label_position(self):
        if self.label:
            self.label.setPos(
                self.pos().x() + self.node.radius * 2 + 5,
                self.pos().y()
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.node.path.is_dir():
                self.node.expanded = not self.node.expanded
                self.scene_node.update_nodes()
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(self.default_color.lighter(150)))
        self.scene_node.status_bar.showMessage(str(self.node.path))

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(self.default_color))
        self.scene_node.status_bar.clearMessage()

class TreeConnection(QGraphicsPathItem):
    """Stylized connection between nodes using curved paths"""
    def __init__(self, start_pos: QPointF, end_pos: QPointF):
        super().__init__()
        
        # Create curved path
        path = QPainterPath()
        path.moveTo(start_pos)
        
        # Calculate control points for curve
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        ctrl1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
        ctrl2 = QPointF(end_pos.x() - dx * 0.5, end_pos.y())
        
        path.cubicTo(ctrl1, ctrl2, end_pos)
        
        # Set path and style
        self.setPath(path)
        pen = QPen(QColor(100, 100, 100, 150), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)

class FSNodeItem(QGraphicsItemGroup):
    """Enhanced node visualization with risk information"""
    ICONS = {
        'folder': '''
            <svg width="24" height="24" viewBox="0 0 24 24">
                <path fill="#FFA000" d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
        ''',
        'file': '''
            <svg width="24" height="24" viewBox="0 0 24 24">
                <path fill="#90CAF9" d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/>
            </svg>
        ''',
        'class': '''
            <svg width="24" height="24" viewBox="0 0 24 24">
                <path fill="#FF5722" d="M12 2L2 7v10l10 5 10-5V7L12 2z"/>
            </svg>
        ''',
        'function': '''
            <svg width="24" height="24" viewBox="0 0 24 24">
                <path fill="#2196F3" d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2z"/>
            </svg>
        ''',
        'risk_high': '''<svg width="24" height="24">
            <path fill="#FF5252" d="M12 2L1 21h22L12 2zm0 3l7.53 13H4.47L12 5zm-1 5v4h2v-4h-2zm0 6v2h2v-2h-2z"/>
        </svg>''',
        'risk_medium': '''<svg width="24" height="24">
            <path fill="#FFC107" d="M12 2L1 21h22zm0 3l7.53 13H4.47L12 5z"/>
        </svg>'''
    }

    def __init__(self, node: FSNode, scene: 'FileSystemScene'):
        super().__init__()
        self.node = node
        self.scene = scene
        self.setPos(node.x, node.y)
        self.setAcceptHoverEvents(True)
        
        # Create base circle
        self.circle = QGraphicsEllipseItem(0, 0, node.radius * 2, node.radius * 2, self)
        self.default_color = self._get_node_color()
        self.circle.setBrush(QBrush(self.default_color))
        self.circle.setPen(QPen(Qt.GlobalColor.black, 1))
        
        # Add risk indicator if applicable
        if self._has_risks():
            self._add_risk_indicator()
        
        # Add main icon
        icon = self._create_svg_item(self.ICONS[self._get_icon_type()])
        icon.setParentItem(self)
        icon.setPos(node.radius/2, node.radius/2)
        
        # Add label
        self.label = scene.addSimpleText(self._get_display_name())
        self.update_label_position()

    def _has_risks(self) -> bool:
        """Check if node has associated risks"""
        if hasattr(self.node, 'risks'):
            return bool(self.node.risks)
        return False

    def _get_risk_priority(self) -> Optional[str]:
        """Get highest risk priority"""
        if not self._has_risks():
            return None
        priorities = [risk.priority for risk in self.node.risks]
        if RiskPriority.CRITICAL in priorities or RiskPriority.HIGH in priorities:
            return 'high'
        if RiskPriority.MEDIUM in priorities:
            return 'medium'
        return None

    def _add_risk_indicator(self):
        """Add risk indicator to node"""
        priority = self._get_risk_priority()
        if priority:
            indicator = self._create_svg_item(self.ICONS[f'risk_{priority}'])
            indicator.setParentItem(self)
            indicator.setPos(node.radius * 1.5, -node.radius/2)
            indicator.setScale(0.7)

    def _get_display_name(self) -> str:
        """Get node display name with risk count"""
        name = self.node.name
        if self._has_risks():
            name = f"{name} ({len(self.node.risks)})"
        return name

    def hoverEnterEvent(self, event):
        """Show detailed info on hover"""
        if self._has_risks():
            tooltip = self._build_risk_tooltip()
            self.setToolTip(tooltip)
        super().hoverEnterEvent(event)

    def _build_risk_tooltip(self) -> str:
        """Build detailed risk tooltip"""
        lines = ["<b>Risks:</b>"]
        for risk in self.node.risks:
            impact_score = max([impact.impact_score for impact in risk.impacts]) if risk.impacts else 0
            lines.append(f"• {risk.description} (Priority: {risk.priority}, Impact: {impact_score})")
        return "<br>".join(lines)

class FileSystemScene(QGraphicsScene):
    def __init__(self, root_path: Path, status_bar, project_manager=None, parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self.status_bar = status_bar
        self.project_manager = project_manager
        
        self.nodes: Dict[Path, FSNode] = {}
        self.node_items: Dict[Path, FSNodeItem] = {}
        self.connections: List[TreeConnection] = []
        
        # Visual settings
        self.node_spacing = 150  # Horizontal spacing between nodes
        self.level_spacing = 100  # Vertical spacing between levels
        
        # Initialize root node
        self.root_node = FSNode(
            path=root_path,
            x=0,
            y=0,
            radius=20
        )
        self.nodes[root_path] = self.root_node
        
        # Initial scene setup
        self.update_nodes()

    def update_nodes(self):
        """Update the node structure and visual elements"""
        # Clear existing nodes except root
        old_nodes = set(self.nodes.keys())
        old_nodes.discard(self.root_path)
        for path in old_nodes:
            self.nodes.pop(path, None)
        
        # Update node structure
        self._update_node_structure(self.root_node)
        
        # Layout nodes
        self._layout_nodes(self.root_node)
        
        # Update visuals
        self._update_visual_elements()

    def _update_visual_elements(self):
        # Clear existing items
        for conn in self.connections:
            self.removeItem(conn)
        self.connections.clear()
        
        # Update/create node visuals
        for path, node in self.nodes.items():
            if path not in self.node_items:
                node_item = FSNodeItem(node, self)
                self.node_items[path] = node_item
            else:
                self.node_items[path].setPos(node.x, node.y)
            
            # Create connections to parent
            if node.parent:
                start_pos = QPointF(node.parent.x + 20, node.parent.y + 12)
                end_pos = QPointF(node.x, node.y + 12)
                conn = TreeConnection(start_pos, end_pos)
                self.addItem(conn)
                self.connections.append(conn)

    def _layout_nodes(self, node: FSNode, level: int = 0, offset: float = 0):
        """Position nodes in a tree layout"""
        node.y = level * self.level_spacing
        
        if node.children:
            total_width = len(node.children) * self.node_spacing
            start_x = offset - total_width / 2
            
            for i, child in enumerate(node.children):
                child_x = start_x + i * self.node_spacing
                child.x = child_x
                self._layout_nodes(child, level + 1, child_x)
                
    def _update_node_symbols(self, node: FSNode):
        if self.project_manager:
            project = self.project_manager.get_current_project()
            if project:
                node.symbols = project.symbols.get(node.path, [])

class FileSystemView(QGraphicsView):
    def __init__(self, scene: FileSystemScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(factor, factor)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Filesystem Explorer")
        self.setMinimumSize(800, 600)
        
        # Create status bar
        self.status_bar = self.statusBar()
        
        # Create scene and view
        self.scene = FileSystemScene(Path.home(), self.status_bar)
        self.view = FileSystemView(self.scene)
        self.setCentralWidget(self.view)
        
        # Set initial view bounds
        self.view.setSceneRect(QRectF(-2000, -2000, 4000, 4000))

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
