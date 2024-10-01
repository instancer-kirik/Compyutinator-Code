from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton
from PyQt6.QtCore import Qt
from GUX.sticky_note import StickyNoteWidget
import logging

class StickyNoteManager(QWidget):
    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.cccore = cccore
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.sticky_note_list = QListWidget()
        self.sticky_note_list.itemClicked.connect(self.load_sticky_note)
        self.layout.addWidget(self.sticky_note_list)

        self.current_note_widget = None

        self.add_button = QPushButton("Add Sticky Note")
        self.add_button.clicked.connect(self.add_sticky_note)
        self.layout.addWidget(self.add_button)

    def add_sticky_note(self, content=""):
        note_id = self.sticky_note_list.count() + 1
        note_widget = StickyNoteWidget(note_id, note_content=content, parent=self)
        item = QListWidgetItem(f"Sticky Note {note_id}")
        item.setData(Qt.ItemDataRole.UserRole, note_widget)
        self.sticky_note_list.addItem(item)
        self.set_current_note_widget(note_widget)

    def load_sticky_note(self, item):
        note_widget = item.data(Qt.ItemDataRole.UserRole)
        self.set_current_note_widget(note_widget)

    def set_current_note_widget(self, note_widget):
        if self.current_note_widget is not None:
            logging.debug(f"Removing current note widget: {self.current_note_widget}")
            self.layout.removeWidget(self.current_note_widget)
            self.current_note_widget.hide()

        self.current_note_widget = note_widget
        if self.current_note_widget is not None:
            logging.debug(f"Setting new current note widget: {self.current_note_widget}")
            self.layout.insertWidget(1, self.current_note_widget)
            self.current_note_widget.show()

    def remove_sticky_note_widget(self, note_widget):
        if note_widget is not None and self.layout.count() > 1:
            logging.debug(f"Removing note widget: {note_widget}")
            self.layout.removeWidget(note_widget)
            note_widget.hide()
        self.sticky_note_list.clear()
        self.current_note_widget = None
