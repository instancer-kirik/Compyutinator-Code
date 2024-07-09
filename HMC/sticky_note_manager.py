from PyQt6.QtWidgets import QWidget, QDockWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton
from PyQt6.QtCore import Qt
from GUX.sticky_note import StickyNoteWidget
class StickyNoteManager(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Sticky Notes", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.initUI()

    def initUI(self):
        self.container = QWidget()
        self.layout = QVBoxLayout()
        self.container.setLayout(self.layout)

        self.sticky_note_list = QListWidget()
        self.sticky_note_list.itemClicked.connect(self.load_sticky_note)
        self.layout.addWidget(self.sticky_note_list)

        self.current_note_widget = None

        self.add_button = QPushButton("Add Sticky Note")
        self.add_button.clicked.connect(self.add_sticky_note)
        self.layout.addWidget(self.add_button)

        self.setWidget(self.container)

    def add_sticky_note(self):
        note_id = self.sticky_note_list.count() + 1
        note_widget = StickyNoteWidget(note_id, parent=self)
        item = QListWidgetItem(f"Sticky Note {note_id}")
        item.setData(Qt.ItemDataRole.UserRole, note_widget)
        self.sticky_note_list.addItem(item)
        self.set_current_note_widget(note_widget)

    def load_sticky_note(self, item):
        note_widget = item.data(Qt.ItemDataRole.UserRole)
        self.set_current_note_widget(note_widget)

    def set_current_note_widget(self, note_widget):
        if self.current_note_widget is not None:
            self.layout.removeWidget(self.current_note_widget)
            self.current_note_widget.hide()

        self.current_note_widget = note_widget
        self.layout.insertWidget(1, self.current_note_widget)
        self.current_note_widget.show()

    def remove_sticky_note_widget(self, note_widget):
        self.sticky_note_list.clear()
        self.current_note_widget = None
        note_widget.hide()
