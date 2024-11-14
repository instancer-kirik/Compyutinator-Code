from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QScrollArea, QFrame, QMenu, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import datetime
from typing import List, Dict
from HMC.mark_manager import Mark, MarkType
import logging

class MarkCard(QFrame):
    """Individual mark card widget"""
    clicked = pyqtSignal(int)  # Emits mark_id
    
    def __init__(self, mark: Mark, parent=None):
        super().__init__(parent)
        self.mark = mark
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            MarkCard {
                background-color: #2b2b2b;
                border-radius: 5px;
                padding: 8px;
                margin: 4px;
            }
            MarkCard:hover {
                background-color: #363636;
            }
        """)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with type icon and title
        header = QHBoxLayout()
        type_label = QLabel(self.mark.type.value)
        type_label.setStyleSheet("font-size: 16px;")
        header.addWidget(type_label)
        
        title = QLabel(self.mark.title)
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title)
        
        if self.mark.priority > 0:
            priority = QLabel("!" * self.mark.priority)
            priority.setStyleSheet("color: #ff5555;")
            header.addWidget(priority)
            
        layout.addLayout(header)
        
        # Description (if any)
        if self.mark.description:
            desc = QLabel(self.mark.description[:100] + "..." if len(self.mark.description) > 100 else self.mark.description)
            desc.setWordWrap(True)
            layout.addWidget(desc)
            
        # Footer with metadata
        footer = QHBoxLayout()
        
        if self.mark.due_date:
            due = QLabel(f"Due: {self.mark.due_date.strftime('%Y-%m-%d')}")
            due.setStyleSheet("color: #8be9fd;")
            footer.addWidget(due)
            
        if self.mark.tags:
            tags = QLabel(" ".join(f"#{tag}" for tag in self.mark.tags))
            tags.setStyleSheet("color: #50fa7b;")
            footer.addWidget(tags)
            
        layout.addLayout(footer)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.mark.id)

class MarkBoard(QWidget):
    """Kanban-style board for marks"""
    def __init__(self, mark_manager, parent=None):
        super().__init__(parent)
        self.mark_manager = mark_manager
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Add mark button
        add_btn = QPushButton("Add Mark")
        add_btn.clicked.connect(self.show_add_mark_dialog)
        toolbar.addWidget(add_btn)
        
        # Filter buttons
        for mark_type in MarkType:
            btn = QPushButton(mark_type.value)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.clicked.connect(self.refresh_board)
            toolbar.addWidget(btn)
            
        layout.addLayout(toolbar)
        
        # Scrollable board area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.board_widget = QWidget()
        self.board_layout = QGridLayout(self.board_widget)
        
        scroll.setWidget(self.board_widget)
        layout.addWidget(scroll)
        
    def refresh_board(self):
        """Refresh the mark board display"""
        try:
            # Clear existing layout
            for i in reversed(range(self.board_layout.count())): 
                self.board_layout.itemAt(i).widget().setParent(None)
            
            # Get marks and organize by type
            marks_by_type: Dict[MarkType, List[Mark]] = {}
            for mark_type in MarkType:
                marks = self.mark_manager.get_marks_by_type(mark_type)
                if marks:
                    marks_by_type[mark_type] = sorted(
                        marks,
                        key=lambda m: (m.priority, m.due_date or datetime.max),
                        reverse=True
                    )
            
            # Create columns for each type
            for col, (mark_type, marks) in enumerate(marks_by_type.items()):
                # Column header
                header = QLabel(f"{mark_type.value} {mark_type.name}")
                header.setStyleSheet("font-weight: bold; padding: 8px;")
                self.board_layout.addWidget(header, 0, col)
                
                # Add marks
                for row, mark in enumerate(marks, start=1):
                    card = MarkCard(mark)
                    card.clicked.connect(self.show_mark_details)
                    self.board_layout.addWidget(card, row, col)
                    
        except Exception as e:
            logging.error(f"Error refreshing mark board: {e}")

    def show_add_mark_dialog(self):
        """Show dialog to add new mark"""
        from GUX.dialogs.mark_dialog import AddMarkDialog
        dialog = AddMarkDialog(self.mark_manager, self)
        if dialog.exec():
            self.refresh_board()
            
    def show_mark_details(self, mark_id: int):
        """Show detailed view of a mark"""
        from GUX.dialogs.mark_dialog import MarkDetailsDialog
        mark = self.mark_manager.marks.get(mark_id)
        if mark:
            dialog = MarkDetailsDialog(mark, self.mark_manager, self)
            if dialog.exec():
                self.refresh_board() 