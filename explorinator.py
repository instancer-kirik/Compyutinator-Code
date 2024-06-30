import sys
import os
import signal
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileSystemModel, QTreeView, QVBoxLayout, QWidget, QLabel, QStyle
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtCore import Qt, QUrl, QTimer

class FileExplorer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Explorer")
        self.setGeometry(300, 100, 800, 600)

        self.model = QFileSystemModel()
        self.model.setRootPath('')

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(''))
        self.tree.doubleClicked.connect(self.on_double_click)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tree)

        self.loading_label = QLabel("Loading...", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("QLabel { background-color : black; color : white; }")
        self.loading_label.hide()

        self.layout.addWidget(self.loading_label)

        self.container = QWidget()
        self.container.setLayout(self.layout)

        self.setCentralWidget(self.container)

        self.player = QMediaPlayer()
        self.player.setVolume(50)
        self.player.mediaStatusChanged.connect(self.media_status_changed)

        self.current_index = -1

        self.setStyleSheet(self.get_dark_red_style())

    def get_dark_red_style(self):
        return """
        QMainWindow {
            background-color: #2E2E2E;
            color: #FFFFFF;
        }
        QTreeView {
            background-color: #1C1C1C;
            alternate-background-color: #3C3C3C;
            color: #FFFFFF;
            selection-background-color: #8B0000;
            selection-color: #FFFFFF;
        }
        QTreeView::item:hover {
            background-color: #551A1A;
        }
        QTreeView::item:selected {
            background-color: #8B0000;
        }
        QTreeView::branch:closed:has-children {
            border-image: none;
            image: none;
        }
        QTreeView::branch:open:has-children {
            border-image: none;
            image: none;
        }
        QTreeView::branch:has-children:!has-siblings:closed,
        QTreeView::branch:closed:has-children:has-siblings {
            border-image: none;
            qproperty-icon: url(:/images/branch_closed.png);
        }
        QTreeView::branch:open:has-children:!has-siblings,
        QTreeView::branch:open:has-children:has-siblings {
            border-image: none;
            qproperty-icon: url(:/images/branch_open.png);
        }
        QHeaderView::section {
            background-color: #1C1C1C;
            color: #FFFFFF;
        }
        QScrollBar:vertical {
            background: #2E2E2E;
            width: 15px;
        }
        QScrollBar::handle:vertical {
            background: grey;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: #2E2E2E;
        }
        QScrollBar:horizontal {
            background: #2E2E2E;
            height: 15px;
        }
        QScrollBar::handle:horizontal {
            background: grey;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            background: #2E2E2E;
        }
        QHeaderView::section {
            background-color: #1C1C1C;
            color: #FFFFFF;
        }
        """

    def on_double_click(self, index):
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path) and (file_path.endswith('.mp3') or file_path.endswith('.wav')):
            self.play_audio(file_path)

    def play_audio(self, file_path):
        self.loading_label.show()
        self.player.setMedia(QUrl.fromLocalFile(file_path))
        self.player.play()

    def media_status_changed(self, status):
        if status == QMediaPlayer.LoadedMedia:
            QTimer.singleShot(500, self.hide_loading_label)

    def hide_loading_label(self):
        self.loading_label.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up or event.key() == Qt.Key_Down:
            current_index = self.tree.currentIndex()
            if event.key() == Qt.Key_Up:
                next_index = self.tree.indexAbove(current_index)
            else:
                next_index = self.tree.indexBelow(current_index)
                
            if next_index.isValid():
                self.tree.setCurrentIndex(next_index)
                file_path = self.model.filePath(next_index)
                if os.path.isfile(file_path) and (file_path.endswith('.mp3') or file_path.endswith('.wav')):
                    self.play_audio(file_path)

def handle_sigint(signal, frame):
    print("Exiting...")
    QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Handle SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, handle_sigint)

    file_explorer = FileExplorer()
    file_explorer.show()
    sys.exit(app.exec_())
