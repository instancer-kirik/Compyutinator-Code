from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QTimer, Qt
from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtWidgets import QApplication
import logging
from typing import Dict, Optional

class CursorPointerManager(QObject):
    """Manages mouse cursor/pointer behavior and animations."""
    
    cursor_changed = pyqtSignal(str)  # Emitted when cursor type changes
    position_changed = pyqtSignal(QPoint)  # Emitted when cursor moves
    
    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.current_cursor = "default"
        self.tracking_enabled = False
        self.custom_cursors: Dict[str, QCursor] = {}
        
        # Initialize cursor types
        self._init_cursor_types()
        
        # Setup position tracking
        self.track_timer = QTimer()
        self.track_timer.timeout.connect(self._track_position)
        self.last_position = QCursor.pos()
        
        # Initialize special cursors
        self._init_special_cursors()
    
    def _init_cursor_types(self):
        """Initialize standard cursor mappings."""
        self.cursor_types = {
            "default": Qt.CursorShape.ArrowCursor,
            "text": Qt.CursorShape.IBeamCursor,
            "wait": Qt.CursorShape.WaitCursor,
            "crosshair": Qt.CursorShape.CrossCursor,
            "size_ver": Qt.CursorShape.SizeVerCursor,
            "size_hor": Qt.CursorShape.SizeHorCursor,
            "size_all": Qt.CursorShape.SizeAllCursor,
            "forbidden": Qt.CursorShape.ForbiddenCursor,
            "pointing_hand": Qt.CursorShape.PointingHandCursor,
            "split_ver": Qt.CursorShape.SplitVCursor,
            "split_hor": Qt.CursorShape.SplitHCursor,
            "whats_this": Qt.CursorShape.WhatsThisCursor,
            "busy": Qt.CursorShape.BusyCursor,
            "open_hand": Qt.CursorShape.OpenHandCursor,
            "closed_hand": Qt.CursorShape.ClosedHandCursor,
        }
    
    def _init_special_cursors(self):
        """Initialize special cursor types like transparent."""
        # Create transparent cursor
        transparent_pixmap = QPixmap(1, 1)
        transparent_pixmap.fill(Qt.GlobalColor.transparent)
        self.custom_cursors["transparent"] = QCursor(transparent_pixmap)
        
        # Add other special cursors here as needed
    
    def start_tracking(self, interval: int = 50):
        """Start tracking cursor position."""
        self.tracking_enabled = True
        self.track_timer.start(interval)
        logging.debug("Cursor tracking started")
    
    def stop_tracking(self):
        """Stop tracking cursor position."""
        self.tracking_enabled = False
        self.track_timer.stop()
        logging.debug("Cursor tracking stopped")
    
    def _track_position(self):
        """Track and emit cursor position changes."""
        if self.tracking_enabled:
            current_pos = QCursor.pos()
            if current_pos != self.last_position:
                self.position_changed.emit(current_pos)
                self.last_position = current_pos
    
    def set_cursor(self, cursor_type: str):
        """Set the cursor type."""
        try:
            if cursor_type in self.cursor_types:
                QApplication.setOverrideCursor(self.cursor_types[cursor_type])
                self.current_cursor = cursor_type
                self.cursor_changed.emit(cursor_type)
                logging.debug(f"Cursor changed to: {cursor_type}")
            elif cursor_type in self.custom_cursors:
                QApplication.setOverrideCursor(self.custom_cursors[cursor_type])
                self.current_cursor = cursor_type
                self.cursor_changed.emit(cursor_type)
                logging.debug(f"Custom cursor set: {cursor_type}")
            else:
                logging.warning(f"Unknown cursor type: {cursor_type}")
        except Exception as e:
            logging.error(f"Error setting cursor: {str(e)}")
    
    def restore_cursor(self):
        """Restore the default cursor."""
        QApplication.restoreOverrideCursor()
        self.current_cursor = "default"
        self.cursor_changed.emit("default")
        logging.debug("Cursor restored to default")
    
    def register_custom_cursor(self, name: str, pixmap: QPixmap):
        """Register a custom cursor from a pixmap."""
        self.custom_cursors[name] = QCursor(pixmap)
        logging.debug(f"Registered custom cursor: {name}")
    
    def get_position(self) -> QPoint:
        """Get current cursor position."""
        return QCursor.pos()
    
    def set_position(self, pos: QPoint):
        """Set cursor position."""
        QCursor.setPos(pos)
        logging.debug(f"Cursor moved to: {pos}")
    
    def move_relative(self, dx: int, dy: int):
        """Move cursor relative to current position."""
        current_pos = self.get_position()
        new_pos = current_pos + QPoint(dx, dy)
        self.set_position(new_pos)
    
    def hide_cursor(self):
        """Hide the cursor (make it transparent)."""
        self.set_cursor("transparent")
    
    def show_cursor(self):
        """Show the cursor (restore default)."""
        self.restore_cursor()
    
    def get_current_type(self) -> str:
        """Get current cursor type."""
        return self.current_cursor
    
    def get_current_cursor_pos(self) -> QPoint:
        """Alias for get_position() for backward compatibility."""
        return self.get_position()
    
    def get_current_pos(self) -> QPoint:
        """Another alias for get_position() for backward compatibility."""
        return self.get_position()