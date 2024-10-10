import sys
import os
import networkx as nx
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QSlider, QLabel, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSlot
import pyqtgraph as pg
import re

class VaultGraphView(QMainWindow):
    def __init__(self, vault_manager, vault_name, lsp_manager):
        super().__init__()
        self.vault_manager = vault_manager
        self.vault = self.vault_manager.get_vault(vault_name)
        self.lsp_manager = lsp_manager
        self.graph = nx.Graph()
        self.initUI()
        self.build_graph()

    def initUI(self):
        self.setWindowTitle('Vault Graph View')
        self.setGeometry(100, 100, 1000, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Graph widget
        self.graph_widget = pg.PlotWidget()
        main_layout.addWidget(self.graph_widget)

        # Controls
        controls_layout = QHBoxLayout()

        # Node size control
        self.node_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.node_size_slider.setRange(5, 30)
        self.node_size_slider.setValue(10)
        self.node_size_slider.valueChanged.connect(self.update_graph)
        controls_layout.addWidget(QLabel("Node Size:"))
        controls_layout.addWidget(self.node_size_slider)

        # Edge width control
        self.edge_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.edge_width_slider.setRange(1, 10)
        self.edge_width_slider.setValue(1)
        self.edge_width_slider.valueChanged.connect(self.update_graph)
        controls_layout.addWidget(QLabel("Edge Width:"))
        controls_layout.addWidget(self.edge_width_slider)

        # Tag filter
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("All Tags")
        self.tag_filter.addItems(self.vault.knowledge_graph.get_all_tags())
        self.tag_filter.currentTextChanged.connect(self.update_graph)
        controls_layout.addWidget(QLabel("Filter by Tag:"))
        controls_layout.addWidget(self.tag_filter)

        # Culling control
        self.cull_checkbox = QCheckBox("Cull Isolated Nodes")
        self.cull_checkbox.stateChanged.connect(self.update_graph)
        controls_layout.addWidget(self.cull_checkbox)

        # Refresh button
        self.refresh_button = QPushButton("Refresh Graph")
        self.refresh_button.clicked.connect(self.refresh_graph)
        controls_layout.addWidget(self.refresh_button)

        # Add a checkbox for showing/hiding classes and functions
        self.show_symbols_checkbox = QCheckBox("Show Classes and Functions")
        self.show_symbols_checkbox.stateChanged.connect(self.update_graph)
        controls_layout.addWidget(self.show_symbols_checkbox)

        main_layout.addLayout(controls_layout)

    def build_graph(self):
        self.graph.clear()
        index = self.vault.get_index()
        for file_info in index['files']:
            if file_info['type'] == 'document':
                file_path = file_info['path']
                self.graph.add_node(file_path, type='file')
                if self.show_symbols_checkbox.isChecked():
                    self.request_symbols(file_path)

        for source, targets in self.vault.knowledge_graph.links.items():
            for target in targets:
                self.graph.add_edge(source, target)

        self.update_graph()

    def request_symbols(self, file_path):
        file_uri = f"file://{os.path.join(self.vault.path, file_path)}"
        self.lsp_manager.request_document_symbols(file_uri)
        self.lsp_manager.symbolsReceived.connect(self.handle_symbols)

    @pyqtSlot(list)
    def handle_symbols(self, symbols):
        for symbol in symbols:
            if symbol['kind'] in [5, 6]:  # 5 is class, 6 is method/function
                symbol_name = f"{os.path.basename(symbol['location']['uri'])}::{symbol['name']}"
                self.graph.add_node(symbol_name, type='symbol')
                self.graph.add_edge(symbol['location']['uri'], symbol_name)

        self.update_graph()

    def update_graph(self):
        pos = nx.spring_layout(self.graph)
        
        self.graph_widget.clear()
        
        node_size = self.node_size_slider.value()
        edge_width = self.edge_width_slider.value()
        selected_tag = self.tag_filter.currentText()
        cull_isolated = self.cull_checkbox.isChecked()

        # Filter nodes based on tag
        nodes_to_draw = self.graph.nodes()
        if selected_tag != "All Tags":
            nodes_to_draw = [node for node in self.graph.nodes() if selected_tag in self.vault.knowledge_graph.tags.get(node, [])]

        # Cull isolated nodes if checkbox is checked
        if cull_isolated:
            nodes_to_draw = [node for node in nodes_to_draw if self.graph.degree(node) > 0]

        # Draw edges
        for edge in self.graph.edges():
            if edge[0] in nodes_to_draw and edge[1] in nodes_to_draw:
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                line = pg.PlotDataItem([x0, x1], [y0, y1], pen=pg.mkPen(color=(100, 100, 100), width=edge_width))
                self.graph_widget.addItem(line)
        
        # Draw nodes
        for node in nodes_to_draw:
            x, y = pos[node]
            if self.graph.nodes[node]['type'] == 'file':
                brush = pg.mkBrush(0, 255, 0, 120)
            else:
                brush = pg.mkBrush(255, 0, 0, 120)
            scatter = pg.ScatterPlotItem([x], [y], size=node_size, pen=pg.mkPen(None), brush=brush)
            self.graph_widget.addItem(scatter)
            text = pg.TextItem(os.path.basename(node), anchor=(0.5, 0.5))
            text.setPos(x, y)
            self.graph_widget.addItem(text)

    def refresh_graph(self):
        self.vault.update_index()
        self.build_graph()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # You'll need to replace these with actual VaultManager and vault name
   # vault_manager = VaultManager()
    vault_name = "Your Vault Name"
    ex = QLabel("VaultGraphView(vault_manager, vault_name)")
    ex.show()
    sys.exit(app.exec())