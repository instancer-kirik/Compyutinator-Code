import re
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QPushButton
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QMimeData, QTimer
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QPen, QColor

class KeyboardLayout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(4)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.dragging = False
        self.drag_source = None
        self.drag_source_row = None
        self.active_row = None
        self.row_states = {}  # Store current state of each row
        self.setAcceptDrops(True)
        
        # Remove duplicate offset toggle initialization
        self.offset_toggle = None
        
        self.create_keyboard_layout()
        
        # Add warning label
        self.warning_label = QLabel(self)
        self.warning_label.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                background-color: #2a2a2a;
                border: 1px solid #ff6b6b;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        self.warning_label.hide()
        
        # Warning fade timer
        self.warning_timer = QTimer(self)
        self.warning_timer.setSingleShot(True)
        self.warning_timer.timeout.connect(self.hide_warning)

    def toggle_standard_offset(self):
        """Toggle between standard and custom key offsets"""
        self.standard_offset = self.offset_toggle.isChecked()
        if self.standard_offset:
            self.apply_standard_offset()
        else:
            self.reset_offset()
        self.update()

    def apply_standard_offset(self):
        """Apply standard keyboard row offsets"""
        standard_offsets = {
            "Number": 0,
            "QWERTY": 25,  # Quarter key offset
            "Home": 37,    # Third key + bit more
            "Shift": 50,   # Half key offset
            "Control": 0
        }
        
        for i in range(self.layout.count()):
            row_widget = self.layout.itemAt(i).widget()
            if row_widget:
                row_name = row_widget.property("row_name")
                if row_name in standard_offsets:
                    row_widget.setContentsMargins(standard_offsets[row_name], 0, 0, 0)

    def reset_offset(self):
        """Reset all row offsets"""
        for i in range(self.layout.count()):
            row_widget = self.layout.itemAt(i).widget()
            if row_widget:
                row_widget.setContentsMargins(0, 0, 0, 0)

    
    def update_row_state(self, row_widget):
        """Update stored state for a row"""
        if not isinstance(row_widget, QWidget):
            return
            
        row_name = row_widget.property("row_name")
        if not row_name:
            return
            
        row_layout = row_widget.layout()
        keys = []
        positions = {}
        
        # Store only non-empty keys
        for i in range(row_layout.count() - 1):  # Exclude stretch
            widget = row_layout.itemAt(i).widget()
            if isinstance(widget, KeyBlock) and widget.key.strip():
                keys.append(widget.key)
                positions[widget.key] = widget.pos()
        
        self.row_states[row_name] = {
            'keys': keys,
            'positions': positions
        }

    def update_layout(self, keys, is_source=False):
        """Update layout with new keys"""
        if not keys:
            return
            
        # Split keys into rows based on our layout structure
        current_idx = 0
        for i, (length, _) in enumerate(self.row_lengths):
            if current_idx >= len(keys):
                break
                
            row_widget = self.layout.itemAt(i).widget()
            if row_widget:
                row_layout = row_widget.layout()
                
                # Update keys in this row
                for j in range(min(length, row_layout.count())):
                    if current_idx < len(keys):
                        widget = row_layout.itemAt(j).widget()
                        if isinstance(widget, KeyBlock):
                            widget.update_key(keys[current_idx])
                            widget.update_style(is_active=(not is_source))
                            current_idx += 1

    def update_from_config(self, config_text):
        """Update layout from KMonad config"""
        # Find the defsrc section
        src_match = re.search(r'\(defsrc(.*?)\)', config_text, re.DOTALL)
        if src_match:
            layout_text = src_match.group(1).strip()
            keys = [key.strip() for key in layout_text.split() if key.strip()]
            self.update_layout(keys, is_source=True)

    def update_from_layer(self, layer_keys):
        """Update layout from a specific layer"""
        self.update_layout(layer_keys, is_source=False)

    def update_config_from_layout(self):
        """Generate config text from current layout"""
        config_lines = []
        # Skip the last widget (toggle button)
        for i in range(self.layout.count() - 1):
            row_widget = self.layout.itemAt(i).widget()
            if not isinstance(row_widget, QWidget):
                continue
                
            row_layout = row_widget.layout()
            if not row_layout:
                continue
                
            row_keys = []
            # Skip the stretch at the end
            for j in range(row_layout.count() - 1):
                widget = row_layout.itemAt(j).widget()
                if isinstance(widget, KeyBlock) and widget.key.strip():
                    row_keys.append(widget.key)
                    
            if row_keys:  # Only add non-empty rows
                config_lines.append(" ".join(row_keys))
        
        # Update parent's config if it exists
        if hasattr(self.parent(), 'config_edit'):
            config_text = self.parent().config_edit.toPlainText()
            new_layout = "\n  ".join(config_lines)
            
            # Replace content between defsrc parentheses
            config_text = re.sub(
                r'\(defsrc.*?\)', 
                f'(defsrc\n  {new_layout}\n)', 
                config_text, 
                flags=re.DOTALL
            )
            
            self.parent().config_edit.setPlainText(config_text)
            self.parent().save_config(silent=True)

    def dropEvent(self, event):
        if not (event.mimeData().hasText() and self.drag_source):
            return
            
        drop_pos = event.position().toPoint()
        dest_row_layout = None
        
        # Find destination row
        for i in range(self.layout.count() - 1):
            row_widget = self.layout.itemAt(i).widget()
            if not isinstance(row_widget, QWidget):
                continue
                
            if row_widget.geometry().contains(drop_pos):
                dest_row_layout = row_widget.layout()
                break
        
        if not dest_row_layout:
            return
            
        # Handle the move
        source_row = self.drag_source_row
        source_index = source_row.indexOf(self.drag_source)
        
        # Calculate target slot
        local_x = drop_pos.x() - row_widget.geometry().left()
        key_width = 50
        spacing = dest_row_layout.spacing()
        total_width = key_width + spacing
        target_slot = int((local_x + total_width/2) // total_width)
        target_slot = max(0, min(target_slot, dest_row_layout.count() - 1))
        
        if dest_row_layout == source_row:
            # Same row - just reorder without creating blank space
            source_row.removeWidget(self.drag_source)
            dest_row_layout.insertWidget(target_slot, self.drag_source)
        else:
            # Different rows - replace source with blank space
            source_row.removeWidget(self.drag_source)
            blank_key = KeyBlock(" ", self)
            source_row.insertWidget(source_index, blank_key)
            
            # Insert at new position
            dest_row_layout.insertWidget(target_slot, self.drag_source)
        
        # Update states and cleanup
        self.update_row_state(row_widget)
        if dest_row_layout != source_row:
            self.update_row_state(source_row.parentWidget())
        
        self.update_config_from_layout()
        
        # Reset state
        self.dragging = False
        self.drag_source = None
        self.drag_source_row = None
        self.active_row = None
        self.reset_key_positions()
        event.acceptProposedAction()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            # Store the source key and row
            source_widget = event.source()
            if isinstance(source_widget, KeyBlock):
                self.drag_source = source_widget
                # Find the source row
                parent_widget = source_widget.parent()
                if parent_widget and parent_widget.layout():
                    self.drag_source_row = parent_widget.layout()
                    # Compress the source row immediately to prevent gaps
                    self.compress_row(self.drag_source_row)
            
            event.acceptProposedAction()
            self.dragging = True
            self.update_drag_position(event.position().toPoint())

    def dragMoveEvent(self, event):
        if not self.dragging:
            return
            
        drop_pos = event.position().toPoint()
        found_row = False
        
        # Find current row
        for i in range(self.layout.count() - 1):  # Skip toggle button
            row_widget = self.layout.itemAt(i).widget()
            if not isinstance(row_widget, QWidget):
                continue
                
            if row_widget.geometry().contains(drop_pos):
                found_row = True
                dest_row_layout = row_widget.layout()
                expected_length = row_widget.property("max_length")
                
                # Show warning if exceeding expected length
                if (dest_row_layout.count() - 1 >= expected_length and 
                    dest_row_layout != self.drag_source_row):
                    self.show_warning(row_widget, f"Expected {expected_length} keys")
                else:
                    self.hide_warning()
                
                # Update active row and positions
                if self.active_row != row_widget:
                    if self.active_row:
                        self.reset_row_positions(self.active_row.layout())
                        self.compress_row(self.active_row.layout())
                    self.active_row = row_widget
                    
                self.update_drag_position(drop_pos)
                break
        
        # Reset if not over any row
        if not found_row:
            if self.active_row:
                self.reset_row_positions(self.active_row.layout())
                self.compress_row(self.active_row.layout())
                self.active_row = None
            # Also ensure source row stays compressed
            if self.drag_source_row:
                self.compress_row(self.drag_source_row)
        
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """Reset positions when drag leaves a row"""
        self.dragging = False
        if self.active_row and self.active_row.layout():
            self.reset_row_positions(self.active_row.layout())
            self.compress_row(self.active_row.layout())  # Add this to remove gaps
        self.active_row = None

    def reset_row_positions(self, row_layout):
        """Reset positions for a specific row, maintaining standard offset if enabled"""
        if not row_layout:
            return
            
        # Get row's current offset
        row_widget = row_layout.parentWidget()
        current_margins = row_widget.contentsMargins()
        left_offset = current_margins.left()
        
        # Reset each key position while maintaining offset
        for i in range(row_layout.count() - 1):  # Exclude stretch
            widget = row_layout.itemAt(i).widget()
            if isinstance(widget, KeyBlock):
                key_width = widget.width()
                spacing = row_layout.spacing()
                new_pos = QPoint(left_offset + (i * (key_width + spacing)), widget.y())
                widget.animate_to(new_pos)

    def reset_key_positions(self):
        """Reset all key positions to original state"""
        for i in range(self.layout.count() - 1):  # Skip the toggle button
            row_widget = self.layout.itemAt(i).widget()
            if row_widget and row_widget.layout():  # Check if layout exists
                self.reset_row_positions(row_widget.layout())

    def compress_row(self, row_layout):
        """Remove gaps in row by shifting remaining keys"""
        if not row_layout:
            return
            
        # Get row's current offset
        row_widget = row_layout.parentWidget()
        if not row_widget:
            return
            
        current_margins = row_widget.contentsMargins()
        left_offset = current_margins.left()
        
        # Collect all non-empty keys and one blank space at the end if needed
        keys = []
        blank_key = None
        for i in range(row_layout.count() - 1):  # Exclude stretch
            widget = row_layout.itemAt(i).widget()
            if isinstance(widget, KeyBlock):
                if widget.key.strip() and widget != self.drag_source:
                    keys.append(widget)
                elif widget.key.strip() == " " and not blank_key:
                    blank_key = widget
        
        # Add blank key at the end if we have room
        max_length = row_widget.property("max_length")
        if len(keys) < max_length and blank_key:
            keys.append(blank_key)
        
        # Reposition keys without gaps
        key_width = 50
        spacing = row_layout.spacing()
        for i, key in enumerate(keys):
            new_pos = QPoint(left_offset + (i * (key_width + spacing)), key.y())
            key.animate_to(new_pos)

    def shift_keys_in_row(self, row_layout, x_pos):
        """Animate keys in a row to make space, with snapping behavior"""
        if not row_layout:
            return
            
        key_width = 50
        spacing = row_layout.spacing()
        total_width = key_width + spacing
        
        # Get row's current offset
        row_widget = row_layout.parentWidget()
        current_margins = row_widget.contentsMargins()
        left_offset = current_margins.left()
        
        # Calculate target slot based on x position
        target_slot = int((x_pos - left_offset + total_width/2) // total_width)
        target_slot = max(0, min(target_slot, row_layout.count() - 1))
        
        # Shift all keys as a unit
        for i in range(row_layout.count() - 1):  # Exclude stretch
            widget = row_layout.itemAt(i).widget()
            if isinstance(widget, KeyBlock) and widget != self.drag_source:
                if i < target_slot:
                    new_pos = QPoint(left_offset + (i * total_width), widget.y())
                else:
                    new_pos = QPoint(left_offset + ((i + 1) * total_width), widget.y())
                widget.animate_to(new_pos)

    def update_drag_position(self, pos):
        """Update key positions based on drag position with snapping"""
        if not self.dragging:
            return
            
        # Find which row we're hovering over
        for i in range(self.layout.count()):
            row_widget = self.layout.itemAt(i).widget()
            if row_widget and row_widget.geometry().contains(pos):
                if self.active_row != row_widget:
                    # Reset previous row if we moved to a new one
                    if self.active_row:
                        self.reset_row_positions(self.active_row.layout())
                    self.active_row = row_widget
                
                # Calculate relative x position in row
                local_x = pos.x() - row_widget.geometry().left()
                self.shift_keys_in_row(row_widget.layout(), local_x)
                return

        # If we're not over any row, reset positions
        if self.active_row:
            self.reset_row_positions(self.active_row.layout())
            self.active_row = None

    def paintEvent(self, event):
        """Draw grid lines for visual feedback"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.DotLine))
        
        key_width = 50
        spacing = 2
        total_width = key_width + spacing
        
        # Skip the last widget (toggle button) in layout
        for row_idx in range(self.layout.count() - 1):
            row_widget = self.layout.itemAt(row_idx).widget()
            if not isinstance(row_widget, QWidget):
                continue
                
            row_rect = row_widget.geometry()
            max_length = row_widget.property("max_length")
            if max_length is None:
                continue
            
            # Draw vertical lines for each key position
            for i in range(max_length + 1):
                x = row_rect.left() + i * total_width
                painter.drawLine(x, row_rect.top(), x, row_rect.bottom())
            
            # Draw horizontal lines
            width = max_length * total_width
            painter.drawLine(row_rect.left(), row_rect.top(), 
                           row_rect.left() + width, row_rect.top())
            painter.drawLine(row_rect.left(), row_rect.bottom(), 
                           row_rect.left() + width, row_rect.bottom())

    def create_keyboard_layout(self):
        """Create initial empty keyboard layout"""
        # Define row configurations with explicit max lengths
        self.row_configs = [
            {"name": "Function", "length": 13, "keys": ["esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"]},
            {"name": "Number", "length": 14, "keys": ["grv", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "bspc"]},
            {"name": "QWERTY", "length": 14, "keys": ["tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"]},
            {"name": "Home", "length": 13, "keys": ["caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "ret"]},
            {"name": "Shift", "length": 12, "keys": ["lsft", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "rsft"]},
            {"name": "Control", "length": 8, "keys": ["lctl", "lmet", "lalt", "spc", "ralt", "rmet", "menu", "rctl"]}
        ]
        
        # Create rows
        for config in self.row_configs:
            row_widget = QWidget()
            row_widget.setProperty("row_name", config["name"])
            row_widget.setProperty("max_length", config["length"])
            row_layout = QHBoxLayout(row_widget)
            row_layout.setSpacing(2)
            row_layout.setContentsMargins(2, 2, 2, 2)
            
            # Initialize row state
            self.row_states[config["name"]] = {
                'keys': config["keys"].copy(),
                'positions': {}
            }
            
            # Create key blocks
            for i in range(config["length"]):
                key = config["keys"][i] if i < len(config["keys"]) else " "
                key_block = KeyBlock(key, self)
                row_layout.addWidget(key_block)
            
            row_layout.addStretch()
            self.layout.addWidget(row_widget)
        
        # Add toggle button at the end (remove duplicate initialization)
        if not self.offset_toggle:
            self.offset_toggle = QPushButton("Toggle Standard Offset", self)
            self.offset_toggle.setCheckable(True)
            self.offset_toggle.clicked.connect(self.toggle_standard_offset)
            self.layout.addWidget(self.offset_toggle)

    def show_warning(self, row_widget, message):
        """Show subtle warning near the row"""
        self.warning_label.setText(message)
        
        # Position warning next to row
        row_rect = row_widget.geometry()
        warning_pos = QPoint(
            row_rect.right() - self.warning_label.sizeHint().width() - 10,
            row_rect.top() + (row_rect.height() - self.warning_label.sizeHint().height()) // 2
        )
        self.warning_label.move(warning_pos)
        
        # Show with fade effect
        self.warning_label.show()
        
        # Reset and start fade timer
        self.warning_timer.stop()
        self.warning_timer.start(2000)  # Hide after 2 seconds

    def hide_warning(self):
        """Hide the warning label"""
        self.warning_label.hide()

class KeyBlock(QLabel):
    def __init__(self, key, parent=None):
        super().__init__(parent)
        self.key = key
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(50, 50)
        
        # Add delete button for blank spaces
        self.delete_button = QPushButton("×", self)
        self.delete_button.setFixedSize(16, 16)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        self.delete_button.clicked.connect(self.delete_key)
        self.delete_button.hide()  # Initially hidden
        
        # Position delete button in top-right corner
        self.delete_button.move(self.width() - self.delete_button.width() - 2, 2)
        
        # Enable animation
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Initial setup
        self.update_key(key)
        self.update_style()

    def update_key(self, new_key):
        """Update key value and display"""
        self.key = new_key if new_key else " "
        display_text = self.key
        
        # Special key display mappings
        key_display = {
            "bspc": "⌫",
            "ret": "⏎",
            "spc": "␣",
            "tab": "⇥",
            "caps": "⇪",
            "lsft": "⇧",
            "rsft": "⇧",
            "lctl": "Ctrl",
            "rctl": "Ctrl",
            "lalt": "Alt",
            "ralt": "Alt",
            "lmet": "⌘",
            "rmet": "⌘",
            "_": " ",
            " ": " "
        }
        
        if self.key in key_display:
            display_text = key_display[self.key]
        elif len(self.key) == 1:
            display_text = self.key.upper()
            
        self.setText(display_text)
        
        # Show/hide delete button based on key type
        if hasattr(self, 'delete_button'):  # Check if button exists
            self.delete_button.setVisible(self.key.strip() == " ")

    def delete_key(self):
        """Remove this key block"""
        parent_layout = self.parent().layout()
        if parent_layout:
            parent_layout.removeWidget(self)
            self.deleteLater()
            
            # Find KeyboardLayout parent to update state
            keyboard_layout = None
            parent = self.parent()
            while parent:
                if isinstance(parent, KeyboardLayout):
                    keyboard_layout = parent
                    break
                parent = parent.parent()
            
            if keyboard_layout:
                keyboard_layout.compress_row(parent_layout)
                keyboard_layout.update_row_state(parent_layout.parentWidget())
                keyboard_layout.update_config_from_layout()

    def enterEvent(self, event):
        """Show delete button on hover for blank spaces"""
        super().enterEvent(event)
        if hasattr(self, 'delete_button') and self.key.strip() == " ":
            self.delete_button.show()
            self.delete_button.raise_()  # Ensure button is on top

    def leaveEvent(self, event):
        """Hide delete button when mouse leaves"""
        super().leaveEvent(event)
        if hasattr(self, 'delete_button'):
            self.delete_button.hide()

    def update_style(self, is_active=False):
        """Update visual style based on state"""
        self.setStyleSheet("""
            QLabel {
                background-color: %s;
                color: %s;
                border: 1px solid %s;
                border-radius: 4px;
                padding: 8px;
                min-width: 30px;
                min-height: 30px;
                margin: 1px;
            }
            QLabel:hover {
                background-color: %s;
                border-color: %s;
            }
        """ % (
            "#2a4a2a" if is_active else "#2a2a2a",
            "#90ff90" if is_active else "white",
            "#3a5a3a" if is_active else "#3a3a3a",
            "#3a5a3a" if is_active else "#3a3a3a",
            "#4a6a4a" if is_active else "#4a4a4a"
        ))

    def mousePressEvent(self, event):
        """Handle drag initiation"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Find the KeyboardLayout parent
            keyboard_layout = None
            parent = self.parent()
            while parent:
                if isinstance(parent, KeyboardLayout):
                    keyboard_layout = parent
                    break
                parent = parent.parent()
            
            if not keyboard_layout:
                return
            
            # Don't create blank key immediately - let dropEvent handle it
            parent_layout = self.parent().layout()
            if parent_layout:
                parent_layout.removeWidget(self)
            
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.key)
            drag.setMimeData(mime)
            
            # Create drag pixmap
            pixmap = QPixmap(self.size())
            pixmap.fill(Qt.GlobalColor.transparent)
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width()//2, pixmap.height()//2))
            
            # Store current layout state
            row_widget = self.parent()
            if row_widget:
                keyboard_layout.update_row_state(row_widget)
            
            drag.exec()

    def animate_to(self, new_pos):
        """Animate the key to a new position"""
        if self.pos() == new_pos:
            return
            
        self.animation.stop()
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(new_pos)
        self.animation.start()



