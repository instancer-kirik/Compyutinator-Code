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
        font = self.font()
        painter.setFont(font)

        # Adjust for line number width (assuming fixed width)
        line_number_width = 30  

        # Calculate area for line numbers
        rect = QRect(0, 0, line_number_width, self.lineNumberArea.height())

        # Get line numbers based on your implementation
        line_numbers = self.get_line_numbers()

        # Loop through each line number
        for i, line_number in enumerate(line_numbers):
            # Adjust y-coordinate based on line spacing
            
            font_info = QFontInfo(font)
            y = i * font.pixelSize() + (QFontMetrics(font).height() // 2)
            # Call drawText with the rectangle and line number string
            painter.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, line_number)

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
        
    def initUI(self):
        self.setMinimumSize(1000, 600)  # Set minimum size
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
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(diff_widget)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(scroll_area)
        self.splitter.addWidget(self.result_text)
        main_layout.addWidget(self.splitter)

        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_original_text)
        QShortcut(QKeySequence("Ctrl+N"), self, self.load_new_text)
        QShortcut(QKeySequence("Ctrl+D"), self, self.show_diff)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_result_text)

        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                color: #333;
                font-family: Arial, sans-serif;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLabel {
                font-weight: bold;
            }
            QTextEdit, QPlainTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
    
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
            self.compare_code_blocks(key, original_blocks.get(key, ''), new_blocks.get(key, ''))
    def extract_code_blocks(self, text):
        blocks = {}
        lines = text.split('\n')
        current_block = []
        current_key = 'first'

        for line in lines:
            if any(symbol in line for symbol in self.key_symbols):
                if current_block:
                    blocks[current_key] = '\n'.join(current_block)
                    current_block = []
                current_key = line.strip()
            current_block.append(line)

        if current_block:
            blocks[current_key] = '\n'.join(current_block)
        return blocks

    def compare_code_blocks(self, key, original_block, new_block):
        if not original_block and not new_block:
            return

        original_lines = original_block.splitlines()
        new_lines = new_block.splitlines()

        diff = list(difflib.ndiff(original_lines, new_lines))
        self.diff_data[key] = diff
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
    def resolve_until_next_conflict(self, key, side):
        all_keys = list(self.diff_data.keys())
        start_index = all_keys.index(key)
        
        for i in range(start_index, len(all_keys)):
            current_key = all_keys[i]
            diff_lines = self.diff_data[current_key]
            
            for j, line in enumerate(diff_lines):
                if side == "left" and line.startswith('- '):
                    self.resolve_conflict(current_key, j, side)
                elif side == "right" and line.startswith('+ '):
                    self.resolve_conflict(current_key, j, side)
                elif line.startswith('? '):  # Assuming '?' indicates a conflict marker
                    return  # Stop when the next conflict is encountered
    def scroll_to_diff_key(self, key):
        # Find the widget containing the diff for the given key
        for i in range(self.diff_layout.count()):
            widget = self.diff_layout.itemAt(i).widget()
            if widget and widget.layout().itemAt(0).widget().text() == f"<b>{key}</b>":
                # Scroll the diff list to make the widget visible
                self.scroll.ensureWidgetVisible(widget)
                break

    def scroll_to_next_conflict(self, current_key):
        all_keys = list(self.diff_data.keys())
        current_index = all_keys.index(current_key)

        # Find the next key with a conflict
        for i in range(current_index + 1, len(all_keys)):
            next_key = all_keys[i]
            next_diff_lines = self.diff_data.get(next_key, [])
            if any(line.startswith('- ') or line.startswith('+ ') for line in next_diff_lines):
                self.scroll_to_diff_key(next_key)
                return

    def resolve_conflict(self, key, index, choice):
        diff = self.diff_data[key]
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
        diff = self.diff_data[key]
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