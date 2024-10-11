from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
import json

class KnowledgeGraphView(QWidget):
    def __init__(self, vault, parent=None):
        super().__init__(parent)
        self.vault = vault
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # Load a simple HTML file with JavaScript for graph visualization
        # You can use libraries like vis.js or cytoscape.js for more advanced visualizations
        html_path = "path/to/graph_visualization.html"
        self.web_view.load(QUrl.fromLocalFile(html_path))

    def update_graph(self):
        graph_data = self.generate_graph_data()
        self.web_view.page().runJavaScript(f"updateGraph({json.dumps(graph_data)});")

    def generate_graph_data(self):
        nodes = []
        edges = []
        for file in self.vault.index['files']:
            file_path = file['path']
            nodes.append({"id": file_path, "label": file_path, "group": "file"})
            
            for linked_file in self.vault.knowledge_graph.links[file_path]:
                edges.append({"from": file_path, "to": linked_file, "label": "link"})
            
            for tag in self.vault.knowledge_graph.tags[file_path]:
                tag_id = f"tag_{tag}"
                if tag_id not in [node['id'] for node in nodes]:
                    nodes.append({"id": tag_id, "label": f"#{tag}", "group": "tag"})
                edges.append({"from": file_path, "to": tag_id, "label": "tag"})
            
            for ref in self.vault.knowledge_graph.references[file_path]:
                ref_id = f"ref_{ref}"
                if ref_id not in [node['id'] for node in nodes]:
                    nodes.append({"id": ref_id, "label": f"@{ref}", "group": "reference"})
                edges.append({"from": file_path, "to": ref_id, "label": "reference"})
            
            # Add fileset connections
            for fileset in self.vault.knowledge_graph.get_filesets_for_file(file_path):
                fileset_id = f"fileset_{fileset}"
                if fileset_id not in [node['id'] for node in nodes]:
                    nodes.append({"id": fileset_id, "label": fileset, "group": "fileset"})
                edges.append({"from": file_path, "to": fileset_id, "label": "belongs_to"})

        return {"nodes": nodes, "edges": edges}