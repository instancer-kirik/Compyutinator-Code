import difflib
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QTextEdit, QScrollArea, QFrame, QFileDialog, QStatusBar, QCheckBox,
    QPlainTextEdit, QApplication)
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QColor, QKeySequence, QShortcut, QTextCursor, QFont, QFontInfo, QFontMetrics, QPainter
from PyQt6.QtCore import Qt, QRegularExpression, QEvent, QSize, QRect
from pygments.lexers.python import PythonLexer
from pygments.formatters import HtmlFormatter
import re
#needs scrolling fixed, synced between input editors and line of current conflict 
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.updateLineNumberAreaWidth(0)
        
    def mouseDoubleClickEvent(self, event):
        if self.toPlainText() == "":
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            self.insertPlainText(text)
        else:
            super().mouseDoubleClickEvent(event)
    def handle_double_click(self):
        # Get cursor position and line number
        cursor = self.textCursor()
        line_number = cursor.blockNumber()

        if self.toPlainText() == "":
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            self.insertPlainText(text)
        
    def lineNumberAreaWidth(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
    def get_line_numbers(self):
        text = self.toPlainText()
        return text.splitlines(keepends=True)  # Keeps newline characters
    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    0,  # x
                    top,  # y
                    self.lineNumberArea.width(),  # width
                    self.fontMetrics().height(),  # height
                    Qt.AlignmentFlag.AlignRight,  # flags
                    number  # text
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1

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
        self.initUI()
        self.diff_data = {}
        self.current_diff_index = -1

        # Scroll synchronization
        self.original_text.verticalScrollBar().valueChanged.connect(self.sync_scrolls)
        self.new_text.verticalScrollBar().valueChanged.connect(self.sync_scrolls)
        self.result_text.verticalScrollBar().valueChanged.connect(self.sync_scrolls)

    def sync_scrolls(self, value):
        """ Synchronize the scroll positions of the text editors. """
        sender = self.sender()
        if sender == self.original_text.verticalScrollBar():
            self.new_text.verticalScrollBar().setValue(value)
            self.result_text.verticalScrollBar().setValue(value)
        elif sender == self.new_text.verticalScrollBar():
            self.original_text.verticalScrollBar().setValue(value)
            self.result_text.verticalScrollBar().setValue(value)
        elif sender == self.result_text.verticalScrollBar():
            self.original_text.verticalScrollBar().setValue(value)
            self.new_text.verticalScrollBar().setValue(value)

    def initUI(self):
        self.setMinimumSize(1200, 800)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        self.conflicts_resolved = False 
        top_layout = QHBoxLayout()
        self.original_text = CodeEditor()
        self.new_text = CodeEditor()
        self.result_text = CodeEditor()

        self.original_text.highlighter = PythonHighlighter(self.original_text.document())
        self.new_text.highlighter = PythonHighlighter(self.new_text.document())
        self.result_text.highlighter = PythonHighlighter(self.result_text.document())

        top_layout.addWidget(self.create_text_input_area("Original Text", self.original_text))
        top_layout.addWidget(self.create_text_input_area("New Text", self.new_text))
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

            
        self.diff_layout = QVBoxLayout()
        diff_widget = QWidget()
        diff_widget.setLayout(self.diff_layout)
        diff_widget.setMinimumSize(600, 300)
        # Assign scroll_area to self.diff_scroll_area
        self.diff_scroll_area = QScrollArea()
        self.diff_scroll_area.setWidgetResizable(True)
        self.diff_scroll_area.setWidget(diff_widget)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.diff_scroll_area)
        self.splitter.addWidget(self.result_text)
        main_layout.addWidget(self.splitter)

        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_original_text)
        QShortcut(QKeySequence("Ctrl+N"), self, self.load_new_text)
        QShortcut(QKeySequence("Ctrl+D"), self, self.show_diff)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_result_text)

        
        # Keyboard navigation shortcuts
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
    def scroll_to_previous_diff(self):
        if self.current_diff_index > 0:
            self.current_diff_index -= 1
            self.scroll_to_diff_index(self.current_diff_index)
    
    def scroll_to_next_diff(self):
        if self.current_diff_index < len(self.diff_data) - 1:
            self.current_diff_index += 1
            self.scroll_to_diff_index(self.current_diff_index)

    def scroll_to_diff_index(self, index):
        key = list(self.diff_data.keys())[index]
        self.scroll_to_diff_key(key)
    
    def create_text_input_area(self, label, text_edit):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label))
        layout.addWidget(text_edit)
        container = QWidget()
        container.setLayout(layout)
        return container

    def load_original_text(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Original Text", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'r') as file:
                self.original_text.setText(file.read())

    def load_new_text(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load New Text", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'r') as file:
                self.new_text.setText(file.read())

    def show_diff(self):
        self.clear_diff_layout()
        original_blocks = self.extract_code_blocks(self.original_text.toPlainText())
        new_blocks = self.extract_code_blocks(self.new_text.toPlainText())

        use_original_order = self.use_original_order_checkbox.isChecked()

        all_keys = list(original_blocks.keys()) if use_original_order else list(new_blocks.keys())
        for key in all_keys:
            if key not in (set(original_blocks.keys()) | set(new_blocks.keys())):
                continue  # Skip non-existent keys
            self.compare_code_blocks(key, original_blocks.get(key, {}), new_blocks.get(key, {}))
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
            'new_end': new_block.get('end_line', 0)
        }
        self.add_diff_to_layout(key, diff)

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

                layout.addLayout(h_layout)
            else:
                print(f"Warning: line_text_label is None for line: {line}")
        frame.setLayout(layout)
        self.diff_layout.addWidget(frame)

        # Add "Next" button functionality with scrolling
        if diff_lines:
            next_button = QPushButton(f"Next")
            next_button.clicked.connect(lambda: self.scroll_to_next_conflict(key))
            layout.addWidget(next_button)

        frame.setLayout(layout)
        self.diff_layout.addWidget(frame)

    def scroll_to_next_conflict(self, current_key):
        all_keys = list(self.diff_data.keys())
        
        current_index = all_keys.index(current_key)

        for i in range(current_index + 1, len(all_keys)):
            next_key = all_keys[i]
            next_diff_data = self.diff_data[next_key]
            next_diff_lines = next_diff_data['diff']
            if any(line.startswith('- ') or line.startswith('+ ') for line in next_diff_lines):
                self.scroll_to_diff_key(next_key)
                return
        
        # If no more conflicts, scroll back to the top
        if self.diff_layout.count() > 0:
            self.diff_scroll_area.ensureWidgetVisible(self.diff_layout.itemAt(0).widget())
            self.scroll_text_editors_to_top()

    def scroll_text_editors_to_top(self):
        for editor in [self.original_text, self.new_text, self.result_text]:
            editor.verticalScrollBar().setValue(0)
    def resolve_conflict(self, key, index, choice):
        diff_data = self.diff_data[key]
        diff = diff_data['diff']
        line = diff[index]
        text = line[2:]  # Remove diff symbols ('+ ', '- ', etc.)

        if (choice == 'left' and line.startswith('- ')) or (choice == 'right' and line.startswith('+ ')):
            cursor = self.result_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)  # Move cursor to the end of the text
            cursor.insertText(text + "\n")
            
            # Select the inserted line
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            
            self.result_text.setTextCursor(cursor)  # Apply the new cursor with the selection

        self.disable_buttons_for_line(key, index)

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

        self.scroll_editor_to_line(self.original_text, original_start)
        self.scroll_editor_to_line(self.new_text, new_start)
        # For result_text, we'll scroll to the end as new content is appended
        self.scroll_editor_to_line(self.result_text, self.result_text.document().lineCount() - 1)

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
            editor = self.original_text
            color = QColor(255, 200, 200)  # Light red for deletions
        elif diff_line.startswith('+'):
            editor = self.new_text
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
            cursor = self.result_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)  # Move cursor to the end of the text
            cursor.insertText(text + "\n")
            
            # Select the inserted line
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            
            self.result_text.setTextCursor(cursor)  # Apply the new cursor with the selection

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
                file.write(self.result_text.toPlainText())
    def accept_line(self, key, index, is_new):
        diff_data = self.diff_data[key]
        diff = diff_data['diff']
        line = diff[index]
        text = line[2:]  # Remove diff symbols ('+ ', '- ', etc.)

        if is_new:
            self.result_text.append(text)
        else:
            self.result_text.append(text)

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