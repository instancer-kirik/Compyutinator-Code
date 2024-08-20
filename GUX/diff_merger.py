import difflib
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QTextEdit, QScrollArea, QFrame, QFileDialog, QStatusBar, QCheckBox, 
    QPlainTextEdit, QApplication)
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QColor, QKeySequence, QShortcut, QTextCursor, QFont, QFontInfo, QFontMetrics, QPainter
from PyQt6.QtCore import Qt, QRegularExpression, QEvent, QSize, QRect, pyqtSignal
import re
from GUX.code_editor import CompEditor



class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(120, 20, 170))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keyword_pattern = QRegularExpression("\\b(def|class|return|if|else|for|while|in|and|or|not|is|None|True|False)\\b")
        self.highlighting_rules.append((keyword_pattern, keyword_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor(20, 110, 100))
        self.highlighting_rules.append((QRegularExpression("\".*\""), string_format))
        self.highlighting_rules.append((QRegularExpression("'.*'"), string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(130, 130, 130))
        self.highlighting_rules.append((QRegularExpression("#[^\n]*"), comment_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)


class DiffMergerWidget(QWidget):
    key_symbols = ['def', 'class', 'import']

    def __init__(self):
        super().__init__()

        self.diff_data = {}
        self.current_diff_index = -1
        self.current_line_index = 0

        self.initUI()

    def initUI(self):
        self.setMinimumSize(1200, 800)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        self.conflicts_resolved = False 
        # Initialize text editors
        self.x_box = CompEditor()
        self.y_box = CompEditor()
        self.result_box = CompEditor()

        # Scroll synchronization
        self.x_box.text_edit.verticalScrollBar().valueChanged.connect(self.sync_scrolls)
        self.y_box.text_edit.verticalScrollBar().valueChanged.connect(self.sync_scrolls)
        self.result_box.text_edit.verticalScrollBar().valueChanged.connect(self.sync_scrolls)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.create_text_input_area("X", self.x_box))
        top_layout.addWidget(self.create_text_input_area("Y", self.y_box))

        self.x_box.highlighter = PythonHighlighter(self.x_box.text_edit.document())
        self.y_box.highlighter = PythonHighlighter(self.y_box.text_edit.document())
        self.result_box.highlighter = PythonHighlighter(self.result_box.text_edit.document())

        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)

        show_diff_button = QPushButton('Show Diff')
        show_diff_button.clicked.connect(self.show_diff)
        button_layout.addWidget(show_diff_button)

        clear_result_button = QPushButton('Clear Result')
        clear_result_button.clicked.connect(self.clear_diff_layout)
        button_layout.addWidget(clear_result_button)

        save_result_button = QPushButton('Save Result')
        save_result_button.clicked.connect(self.save_result_text)
        button_layout.addWidget(save_result_button)

        self.use_original_order_checkbox = QCheckBox("Use Original File Key Order")
        button_layout.addWidget(self.use_original_order_checkbox)

        top_layout.addLayout(button_layout)
        main_layout.addLayout(top_layout)

        # Diff layout with scroll area
        self.diff_layout = QVBoxLayout()
        diff_widget = QWidget()
        diff_widget.setLayout(self.diff_layout)
        diff_widget.setMinimumSize(600, 300)

        self.diff_scroll_area = QScrollArea()
        self.diff_scroll_area.setWidgetResizable(True)
        self.diff_scroll_area.setWidget(diff_widget)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.diff_scroll_area)
        self.splitter.addWidget(self.result_box)

        main_layout.addWidget(self.splitter)

        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_original_text)
        QShortcut(QKeySequence("Ctrl+N"), self, self.load_new_text)
        QShortcut(QKeySequence("Ctrl+D"), self, self.show_diff)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_result_text)
        QShortcut(QKeySequence("Ctrl+Up"), self, self.scroll_to_previous_diff)
        QShortcut(QKeySequence("Ctrl+Down"), self, self.scroll_to_next_diff)

        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: #E0E0E0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #3D7EAA;
                color: #FFFFFF;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5499C7;
            }
            QPushButton:pressed {
                background-color: #2980B9;
            }
            QLabel {
                font-weight: bold;
                color: #BB86FC;
            }
            QTextEdit, QPlainTextEdit {
                background-color: #3C3F41;
                color: #A9B7C6;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
            }
            QScrollBar:vertical {
                border: none;
                background: #3C3F41;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QCheckBox {
                color: #E0E0E0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #BB86FC;
                background: #2E2E2E;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #BB86FC;
                background: #BB86FC;
                border-radius: 4px;
            }
        """)
    def sync_scrolls(self, value):
        """ Synchronize the scroll positions of the text editors. """
        sender = self.sender()
        if sender == self.x_box.text_edit.verticalScrollBar():
            self.y_box.text_edit.verticalScrollBar().setValue(value)
            self.result_box.text_edit.verticalScrollBar().setValue(value)
        elif sender == self.y_box.text_edit.verticalScrollBar():
            self.x_box.text_edit.verticalScrollBar().setValue(value)
            self.result_box.text_edit.verticalScrollBar().setValue(value)
        elif sender == self.result_box.text_edit.verticalScrollBar():
            self.x_box.text_edit.verticalScrollBar().setValue(value)
            self.y_box.text_edit.verticalScrollBar().setValue(value)
    def scroll_to_previous_diff(self):
        if self.current_diff_index > 0:
            self.current_diff_index -= 1
            self.scroll_to_diff_index(self.current_diff_index)
            self.update_position_indicators()

    def scroll_to_next_diff(self):
        if self.current_diff_index < len(self.diff_data) - 1:
            self.current_diff_index += 1
            self.scroll_to_diff_index(self.current_diff_index)
            self.update_position_indicators()

    def scroll_to_diff_index(self, index):
        key = list(self.diff_data.keys())[index]
        self.scroll_to_diff_key(key)
        self.update_position_indicators()

    def load_original_text(self):
        """ Load the original text into the left text box. """
        file_dialog = QFileDialog()
        original_file, _ = file_dialog.getOpenFileName(self, "Open Original File", "", "Text Files (*.txt)")
        if original_file:
            with open(original_file, 'r') as file:
                self.x_box.text_edit.setPlainText(file.read())

    def load_new_text(self):
        """ Load the new text into the right text box. """
        file_dialog = QFileDialog()
        new_file, _ = file_dialog.getOpenFileName(self, "Open New File", "", "Text Files (*.txt)")
        if new_file:
            with open(new_file, 'r') as file:
                self.y_box.text_edit.setPlainText(file.read())

    def show_diff(self):
        self.clear_diff_layout()
        self.result_box.text_edit.clear()  # Clear the result text

        original_blocks = self.extract_code_blocks(self.x_box.text_edit.toPlainText())
        new_blocks = self.extract_code_blocks(self.y_box.text_edit.toPlainText())

        use_original_order = self.use_original_order_checkbox.isChecked()
        all_keys = list(original_blocks.keys()) if use_original_order else list(new_blocks.keys())

        for key in all_keys:
            if key not in (set(original_blocks.keys()) | set(new_blocks.keys())):
                continue  # Skip non-existent keys
            self.compare_code_blocks(key, original_blocks.get(key, {}), new_blocks.get(key, {}))

        self.current_diff_index = 0
        self.current_line_index = 0
        self.add_matching_lines_until_conflict()
        self.find_next_conflict()  # Start by finding the first conflict
        self.update_position_indicators()
    def create_text_input_area(self, label, text_edit):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label))
        layout.addWidget(text_edit)
        if label == 'X':
             
            self.add_and_next_x = QPushButton("Add and Next (X)")
            self.add_and_next_x.clicked.connect(lambda: self.on_add_and_next_clicked('left'))
            layout.addWidget(self.add_and_next_x)
        if label == 'Y':
             
            self.add_and_next_y = QPushButton("Add and Next (Y)")
            self.add_and_next_y.clicked.connect(lambda: self.on_add_and_next_clicked('right'))
            layout.addWidget(self.add_and_next_y)
        container = QWidget()
        container.setLayout(layout)
        return container

    
        
    def extract_code_blocks(self, text):
        blocks = {}
        lines = text.split('\n')
        current_block = []
        current_key = 'first'
        start_line = 0

        for i, line in enumerate(lines):
            if any(symbol in line for symbol in self.key_symbols):
                if current_block:
                    blocks[current_key] = {
                        'content': '\n'.join(current_block),
                        'start_line': start_line,
                        'end_line': i - 1
                    }
                    current_block = []
                current_key = line.strip()
                start_line = i
            current_block.append(line)

        if current_block:
            blocks[current_key] = {
                'content': '\n'.join(current_block),
                'start_line': start_line,
                'end_line': len(lines) - 1
            }
        return blocks
    
    def on_add_and_next_clicked(self, side):
        if self.current_diff_index >= len(self.diff_data):
            self.status_bar.showMessage("No more conflicts")
            return

        key = list(self.diff_data.keys())[self.current_diff_index]
        diff_data = self.diff_data[key]
        diff = diff_data['diff']
        
        # Add all lines of the chosen side until the next conflict
        i = self.current_line_index
        while i < len(diff):
            line = diff[i]
            if line.startswith('  '):  # Matching line
                self.result_box.text_edit.appendPlainText(line[2:])
            elif (side == 'left' and line.startswith('- ')) or (side == 'right' and line.startswith('+ ')):
                self.result_box.text_edit.appendPlainText(line[2:])
                self.disable_buttons_for_line(key, i)
            elif line.startswith('- ') or line.startswith('+ '):
                # We've reached a conflict for the other side, stop here
                break
            i += 1

        # Find the next conflict
        self.find_next_conflict(i + 1)

    def find_next_conflict(self, start_index=0):
        if self.current_diff_index < len(self.diff_data):
            key = list(self.diff_data.keys())[self.current_diff_index]
            diff = self.diff_data[key]['diff']

            for i in range(start_index, len(diff)):
                if diff[i].startswith('- ') or diff[i].startswith('+ '):
                    self.current_line_index = i
                    self.update_position_indicators()
                    return

            # If no more conflicts in the current diff, move to the next diff
            self.current_diff_index += 1
            self.current_line_index = 0
            self.find_next_conflict()  # Recursive call to find the next conflict

        else:
            # If we've reached this point, there are no more conflicts
            self.status_bar.showMessage("No more conflicts")


    def compare_code_blocks(self, key, original_block, new_block):
        if not original_block and not new_block:
            return

        original_lines = original_block.get('content', '').splitlines()
        new_lines = new_block.get('content', '').splitlines()

        diff = list(difflib.ndiff(original_lines, new_lines))
        self.diff_data[key] = {
            'diff': diff,
            'original_start': original_block.get('start_line', 0),
            'original_end': original_block.get('end_line', 0),
            'new_start': new_block.get('start_line', 0),
            'new_end': new_block.get('end_line', 0),
            'original_line_numbers': list(range(original_block.get('start_line', 0), original_block.get('end_line', 0) + 1)),
            'new_line_numbers': list(range(new_block.get('start_line', 0), new_block.get('end_line', 0) + 1))
        }
        self.add_diff_to_layout(key, diff)
    def update_position_indicators(self):
        if self.current_diff_index < len(self.diff_data):
            key = list(self.diff_data.keys())[self.current_diff_index]
            diff_data = self.diff_data[key]

            original_line = diff_data['original_start'] + self.current_line_index
            new_line = diff_data['new_start'] + self.current_line_index

            self.highlight_line(self.x_box, original_line)
            self.highlight_line(self.y_box, new_line)
            self.scroll_to_diff_key(key)

    def highlight_line(self, text_edit, line_number):
        cursor = text_edit.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(line_number):
            cursor.movePosition(QTextCursor.MoveOperation.Down)
        
        text_edit.text_edit.setTextCursor(cursor)
        text_edit.text_edit.ensureCursorVisible()
        
        # Highlight the line
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(255, 255, 0, 100))  # Light yellow background
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = cursor
        text_edit.text_edit.setExtraSelections([selection])

    def add_diff_to_layout(self, key, diff_lines):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout()

        key_label = QLabel(f"<b>{key}</b>")
        key_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(key_label)

        for i, line in enumerate(diff_lines):
            h_layout = QHBoxLayout()

            # Line number label
            line_number_label = QLabel(str(i + 1))
            line_number_label.setFixedWidth(30)
            h_layout.addWidget(line_number_label)

            # Diff line label
            line_text_label = QLabel(line[2:])
            if line_text_label:
                line_text_label.setWordWrap(True)
                if line.startswith('+ '):
                    line_text_label.setStyleSheet("background-color: #ccffcc; padding: 2px;")
                    side = "right"
                elif line.startswith('- '):
                    line_text_label.setStyleSheet("background-color: #ffcccc; padding: 2px;")
                    side = "left"
                else:
                    line_text_label.setStyleSheet("padding: 2px;")
                    side = None
                h_layout.addWidget(line_text_label)

                if side:
                    use_button = QPushButton(f'Use {side.capitalize()}')
                    use_button.clicked.connect(lambda _, k=key, idx=i, s=side: self.resolve_conflict(k, idx, s))
                    h_layout.addWidget(use_button)

                # Add hover event for scrolling
                frame.installEventFilter(self)
                frame.hover_data = (key, i)  # Store key and line index in hover_data attribute

                layout.addLayout(h_layout)
            else:
                print(f"Warning: line_text_label is None for line: {line}")
        frame.setLayout(layout)
        self.diff_layout.addWidget(frame)

        # Add "Next" button functionality with scrolling
        if diff_lines:
            next_button = QPushButton(f"Next")
            next_button.clicked.connect(lambda: self.scroll_to_next_diff)
            layout.addWidget(next_button)

        frame.setLayout(layout)
        self.diff_layout.addWidget(frame)

    def on_add_and_next_button_clicked(self):
        # Add the selected side to the result text
        self.add_selected_side_to_result()

        # Move to the next conflict
        self.go_to_next_conflict()

    def add_selected_side_to_result(self):
        # Logic to add the selected side (left or right) to the result text
        if self.is_left_side_selected():
            self.add_left_side_to_result()
        elif self.is_right_side_selected():
            self.add_right_side_to_result()

    def go_to_next_conflict(self):
        # Logic to navigate to the next conflict
        next_conflict_index = self.current_diff_index
        if next_conflict_index is not None:
            self.scroll_to_next_diff()
            self.update_ui_for_next_conflict(next_conflict_index)
    def scroll_text_editors_to_top(self):
        for editor in [self.x_box.text_edit, self.y_box.text_edit, self.result_box.text_edit]:
            editor.verticalScrollBar().setValue(0)
    def on_add_and_next_button_clicked(self):
        self.add_all_to_result_until_next_conflict()
        self.scroll_to_next_diff()

    def add_all_to_result_until_next_conflict(self):
        """Add all resolved lines from the current diff index to the next conflict to the result text."""
        while self.current_diff_index < len(self.diff_data) - 1:
            key = list(self.diff_data.keys())[self.current_diff_index]
            diff = self.diff_data[key]['diff']

            for i, line in enumerate(diff):
                if line.startswith('- '):
                    # This line was removed from the original, so add it to the result
                    self.resolve_conflict(key, i, 'left')
                elif line.startswith('+ '):
                    # This line was added in the new version, so add it to the result
                    self.resolve_conflict(key, i, 'right')

            self.current_diff_index += 1
            if self.has_conflict_at_index(self.current_diff_index):
                break
    def add_matching_lines_until_conflict(self):
        for key in self.diff_data:
            diff_lines = self.diff_data[key]['diff']
            for line in diff_lines:
                if line.startswith('  '):  # Matching line
                    self.result_box.text_edit.appendPlainText(line[2:])
                elif line.startswith('- ') or line.startswith('+ '):  # Conflict found
                    return
    def has_conflict_at_index(self, index):
        """Check if there is a conflict at the given diff index."""
        key = list(self.diff_data.keys())[index]
        diff = self.diff_data[key]['diff']
        return any(line.startswith('- ') or line.startswith('+ ') for line in diff)

    def scroll_to_next_diff(self):
        if self.current_diff_index < len(self.diff_data) - 1:
            self.current_diff_index += 1
            self.scroll_to_diff_index(self.current_diff_index)
        else:
            self.status_bar.showMessage("Reached the end of differences")
    def resolve_conflict(self, key, index, choice):
        diff_data = self.diff_data[key]
        diff = diff_data['diff']
        line = diff[index]
        text = line[2:]  # Remove diff symbols ('+ ', '- ', etc.)

        if (choice == 'left' and line.startswith('- ')) or (choice == 'right' and line.startswith('+ ')):
            cursor = self.result_box.text_edit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)  # Move cursor to the end of the text
            cursor.insertText(text + "\n")
            
            # Select the inserted line
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            
            self.result_box.text_edit.setTextCursor(cursor)  # Apply the new cursor with the selection

        self.disable_buttons_for_line(key, index)

        # Find and scroll to the next conflict
        self.find_next_conflict()

    def find_next_conflict(self, start_index=None):
        if start_index is None:
            start_index = self.current_line_index + 1

        # Check if there are more conflicts in the current diff
        current_key = list(self.diff_data.keys())[self.current_diff_index]
        current_diff = self.diff_data[current_key]['diff']
        
        for i in range(start_index, len(current_diff)):
            line = current_diff[i]
            if line.startswith('- ') or line.startswith('+ '):
                self.current_line_index = i
                self.scroll_to_current_conflict()
                return

        # If no more conflicts in current diff, move to the next diff
        for i in range(self.current_diff_index + 1, len(self.diff_data)):
            next_key = list(self.diff_data.keys())[i]
            next_diff = self.diff_data[next_key]['diff']
            for j, line in enumerate(next_diff):
                if line.startswith('- ') or line.startswith('+ '):
                    self.current_diff_index = i
                    self.current_line_index = j
                    self.scroll_to_current_conflict()
                    return

        # If no more conflicts found
        self.status_bar.showMessage("No more conflicts found")

    def scroll_to_current_conflict(self):
        key = list(self.diff_data.keys())[self.current_diff_index]
        self.scroll_to_diff_key(key)
        self.update_position_indicators()

    def scroll_to_diff_key(self, key):
        # Scroll the diff list
        for i in range(self.diff_layout.count()):
            widget = self.diff_layout.itemAt(i).widget()
            if widget and widget.layout().itemAt(0).widget().text() == f"<b>{key}</b>":
                self.diff_scroll_area.ensureWidgetVisible(widget)
                break

        # Scroll the text editors
        diff_data = self.diff_data.get(key, {})
        original_start = diff_data.get('original_start', 0)
        new_start = diff_data.get('new_start', 0)

        self.scroll_editor_to_line(self.x_box.text_edit, original_start)
        self.scroll_editor_to_line(self.y_box.text_edit, new_start)
        # For result_text, we'll scroll to the end as new content is appended
        self.scroll_editor_to_line(self.result_box.text_edit, self.result_box.text_edit.document().lineCount() - 1)

    def scroll_editor_to_line(self, editor, line_number):
        block = editor.document().findBlockByLineNumber(line_number)
        cursor = QTextCursor(block)
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()

    
    def next_diff(self):
        if not self.diff_data:
            return

        self.current_diff_index += 1
        if self.current_diff_index >= len(self.diff_data):
            self.current_diff_index = 0

        while self.current_diff_index < len(self.diff_data):
            line = self.diff_data[self.current_diff_index]
            if line.startswith('-') or line.startswith('+'):
                self.highlight_diff(line)
                break
            self.current_diff_index += 1

    def highlight_diff(self, diff_line):
        if diff_line.startswith('-'):
            editor = self.x_box.text_edit
            color = QColor(255, 200, 200)  # Light red for deletions
        elif diff_line.startswith('+'):
            editor = self.y_box.text_edit
            color = QColor(200, 255, 200)  # Light green for additions
        else:
            return

        # Find the line in the editor
        content = editor.toPlainText()
        lines = content.split('\n')
        line_number = -1
        for i, line in enumerate(lines):
            if line == diff_line[1:]:  # Remove the first character (+ or -)
                line_number = i
                break

        if line_number != -1:
            # Highlight the line
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(line_number):
                cursor.movePosition(QTextCursor.MoveOperation.Down)
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = cursor
            editor.setExtraSelections([selection])
            
            # Scroll to the line
            editor.setTextCursor(cursor)
            editor.ensureCursorVisible()

    def resolve_conflict(self, key, index, choice):
        diff_data = self.diff_data[key]
        diff = diff_data['diff']
        line = diff[index]
        text = line[2:]  # Remove diff symbols ('+ ', '- ', etc.)

        if (choice == 'left' and line.startswith('- ')) or (choice == 'right' and line.startswith('+ ')):
            cursor = self.result_box.text_edit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)  # Move cursor to the end of the text
            cursor.insertText(text + "\n")
            
            # Select the inserted line
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            
            self.result_box.text_edit.setTextCursor(cursor)  # Apply the new cursor with the selection

        self.disable_buttons_for_line(key, index)

    def disable_buttons_for_line(self, key, index):
        for i in range(self.diff_layout.count()):
            widget = self.diff_layout.itemAt(i).widget()
            if widget:
                layout = widget.layout()
                if isinstance(layout, QVBoxLayout):
                    for j in range(layout.count()):
                        h_layout = layout.itemAt(j).layout()
                        if h_layout and isinstance(h_layout.itemAt(0).widget(), QLabel):
                            line_number_label = h_layout.itemAt(0).widget()
                            if line_number_label and line_number_label.text() == str(index + 1):
                                for k in range(h_layout.count()):
                                    button = h_layout.itemAt(k).widget()
                                    if isinstance(button, QPushButton):
                                        button.setEnabled(False)


    def clear_diff_layout(self):
        while self.diff_layout.count():
            item = self.diff_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def save_result_text(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Result", "", "Text Files (*.txt);;Python Files (*.py);;All Files (*)")
        if file_name:
            with open(file_name, 'w') as file:
                file.write(self.result_box.text_edit.toPlainText())
    def accept_line(self, key, index, is_new):
        diff_data = self.diff_data[key]
        diff = diff_data['diff']
        line = diff[index]
        text = line[2:]  # Remove diff symbols ('+ ', '- ', etc.)

        if is_new:
            self.result_box.text_edit.append(text)
        else:
            self.result_box.text_edit.append(text)

    def reject_line(self, key, index, is_new):
        # If rejected, simply do nothing (or alternatively, you can remove a line from result_text if it exists)
        pass
    def switch_key_order(self):
            if not self.conflicts_resolved:
                self.left_key_order = not self.left_key_order
                self.show_diff()
            else:
                # Handle case where conflicts are resolved (e.g., show a message)
                pass