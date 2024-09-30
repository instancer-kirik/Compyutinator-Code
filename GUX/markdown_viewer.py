import os
import markdown
from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtGui import QImage, QTextDocument
import re
class MarkdownViewer(QTextBrowser):
    def __init__(self, vault_path):
        super().__init__()
        self.vault_path = vault_path
        self.image_map = {}
        if self.vault_path:
            self.index_vault()

    def index_vault(self):
        if not self.vault_path:
            return
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    self.image_map[file] = os.path.join(root, file)

    def load_markdown(self, md_file):
        with open(md_file, 'r') as f:
            md_content = f.read()
        
        # Custom image syntax handling
        def image_handler(match):
            image_name = match.group(1)
            if image_name in self.image_map:
                return f'<img src="{self.image_map[image_name]}">'
            return match.group(0)

        md_content = re.sub(r'!\[\[(.*?)\]\]', image_handler, md_content)
        
        html_content = markdown.markdown(md_content)
        self.setHtml(html_content)

    def loadResource(self, type, name):
        if type == QTextDocument.ResourceType.ImageResource:
            image = QImage(name.toString())
            if not image.isNull():
                return image
        return super().loadResource(type, name)

    def set_vault_path(self, new_vault_path):
        self.vault_path = new_vault_path
        self.image_map = {}
        if self.vault_path:
            self.index_vault()