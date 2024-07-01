from PyQt6.QtWidgets import QWidget, QVBoxLayout

from PyQt6.QtGui import QFileSystemModel
from custom_tree_view import CustomTreeView
from audio_handler import AudioHandler

class FileExplorerWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.model = QFileSystemModel()
        self.model.setRootPath('')

        self.tree = CustomTreeView(self, self)
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(''))

        self.audio_handler = AudioHandler()

        self.layout.addWidget(self.tree)

    def play_audio(self, file_path):
        self.audio_handler.play(file_path)

    def play_current_audio(self):
        index = self.tree.currentIndex()
        if index.isValid():
            file_path = self.model.filePath(index)
            if os.path.isfile(file_path):
                self.play_audio(file_path)
