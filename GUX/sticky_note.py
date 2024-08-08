from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag
#these probably don't save yet
class StickyNoteWidget(QWidget):
    def __init__(self, note_id, note_content="", parent=None):
        super().__init__(parent)
        self.note_id = note_id
        self.initUI(note_content)

    def initUI(self, note_content):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.header = QLabel(f"Sticky Note {self.note_id} - Doesn't save yet, add path selection")
        self.layout.addWidget(self.header)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(note_content)
        self.layout.addWidget(self.text_edit)

        self.setAcceptDrops(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.text_edit.toPlainText())
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.MoveAction)
        super().mousePressEvent(event)

    def get_content(self):
        return self.text_edit.toPlainText()

    def set_content(self, content):
        self.text_edit.setPlainText(content)
