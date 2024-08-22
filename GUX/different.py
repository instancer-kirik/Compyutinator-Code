import difflib
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QTextEdit, QScrollArea, QFrame, QFileDialog, QStatusBar, QCheckBox, 
    QPlainTextEdit, QApplication)
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QColor, QKeySequence, QShortcut, QTextCursor, QFont, QFontInfo, QFontMetrics, QPainter
from PyQt6.QtCore import Qt, QRegularExpression, QEvent, QSize, QRect, pyqtSignal
import re
from GUX.code_editor import CompEditor
class DiffMergerWidget(QWidget):
    key_symbols = ['def', 'class', 'import']

    def __init__(self):
        super().__init__()
        self.isFullScreen = True
        self.diff_data = {}
        self.current_diff_index = -1
        self.current_line_index = 0
        
        self.initUI()

    def initUI(self):
        self.setMinimumSize(1200, 800)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # Initialize text editors
        self.x_box = CompEditor()
        self.y_box = CompEditor()
        self.result_box = CompEditor()

        # Create a fullscreen button
        self.fullscreen_button = QPushButton("Fullscreen", self)
        self.fullscreen_button.setMaximumWidth(100)
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)

        # Add the button to the layout
        main_layout.addWidget(self.fullscreen_button)

        # Scroll synchronization
        self.x_box.text_edit.verticalScrollBar().valueChanged.connect(self.sync_scrolls)
        self.y_box.text_edit.verticalScrollBar().valueChanged.connect(self.sync_scrolls)
        self.result_box.text_edit.verticalScrollBar().valueChanged.connect(self.sync_scrolls)

        # Top layout for editors and buttons
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.create_text_input_area("X", self.x_box))
        top_layout.addWidget(self.create_text_input_area("Y", self.y_box))

        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addWidget(QPushButton('Show Diff', clicked=self.show_diff))
        button_layout.addWidget(QPushButton('Clear Result', clicked=self.clear_diff_layout))
        button_layout.addWidget(QPushButton('Save Result', clicked=self.save_result_text))

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
        self.setup_shortcuts()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_original_text)
        QShortcut(QKeySequence("Ctrl+N"), self, self.load_new_text)
        QShortcut(QKeySequence("Ctrl+D"), self, self.show_diff)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_result_text)
        QShortcut(QKeySequence("Ctrl+Up"), self, self.scroll_to_previous_diff)
        QShortcut(QKeySequence("Ctrl+Down"), self, self.scroll_to_next_diff)

    def toggle_fullscreen(self):
        main_window = self.window()
        if main_window.isFullScreen():
            main_window.showNormal()
            self.fullscreen_button.setText("Fullscreen")
        else:
            main_window.showFullScreen()
            self.fullscreen_button.setText("Exit Fullscreen")

    def sync_scrolls(self, value):
        """Synchronize the scroll positions of the text editors."""
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
        file_dialog = QFileDialog()
        original_file, _ = file_dialog.getOpenFileName(self, "Open Original File", "", "Text Files (*.txt)")
        if original_file:
            with open(original_file, 'r') as file:
                self.x_box.text_edit.setPlainText(file.read())

    def load_new_text(self):
        file_dialog = QFileDialog()
        new_file, _ = file_dialog.getOpenFileName(self, "Open New File", "", "Text Files (*.txt)")
        if new_file:
            with open(new_file, 'r') as file:
                self.y_box.text_edit.setPlainText(file.read())

    def show_diff(self):
        self.clear_diff_layout()
        self.result_box.text_edit.clear()

        original_blocks = self.extract_code_blocks(self.x_box.text_edit.toPlainText())
        new_blocks = self.extract_code_blocks(self.y_box.text_edit.toPlainText())

        use_original_order = self.use_original_order_checkbox.isChecked()
        all_keys = list(original_blocks.keys()) if use_original_order else list(new_blocks.keys())

        for key in all_keys:
            if key not in (set(original_blocks.keys()) | set(new_blocks.keys())):
                continue
            self.compare_code_blocks(key, original_blocks.get(key, {}), new_blocks.get(key, {}))

        self.current_diff_index = 0
        self.current_line_index = 0
        self.add_matching_lines_until_conflict()  # Add this line
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
        current_key = ''
        start_line = 0

        for i, line in enumerate(lines):
            if line.strip().startswith(tuple(self.key_symbols)):
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

        # Add the key (function or class definition) to the result
        self.result_box.text_edit.appendPlainText(key)

        # Add all lines of the chosen side until the next conflict
        i = 0
        while i < len(diff):
            line = diff[i]
            if line.startswith('  '):  # Matching line
                self.result_box.text_edit.appendPlainText(line[2:])
            elif (side == 'left' and line.startswith('- ')) or (side == 'right' and line.startswith('+ ')):
                self.result_box.text_edit.appendPlainText(line[2:])
            elif line.startswith('- ') or line.startswith('+ '):
                # We've reached a conflict for the other side, stop here
                break
            i += 1

        # Update the current line index
        self.current_line_index = i

        # Find the next conflict
        self.find_next_conflict()

    def find_next_conflict(self):
        while self.current_diff_index < len(self.diff_data):
            key = list(self.diff_data.keys())[self.current_diff_index]
            diff_data = self.diff_data[key]
            diff = diff_data['diff']

            while self.current_line_index < len(diff):
                line = diff[self.current_line_index]
                if line.startswith('- ') or line.startswith('+ '):
                    self.update_position_indicators()
                    self.scroll_to_diff_key(key)
                    return
                self.current_line_index += 1

            self.current_diff_index += 1
            self.current_line_index = 0

        self.status_bar.showMessage("No more conflicts")

    def compare_code_blocks(self, key, original_block, new_block):
        # Combine the clarity of unified_diff with the detail of ndiff:
        diff_lines = list(difflib.unified_diff(
            original_block.get('content', '').splitlines(keepends=True),
            new_block.get('content', '').splitlines(keepends=True)))

        # Store the diff data
        self.diff_data[key] = {
            'original_block': original_block,
            'new_block': new_block,
            'diff': diff_lines
        }

        # Create and add the diff item to the UI
        self.add_diff_item_to_ui(key)

    def scroll_to_diff_key(self, key):
        if key not in self.diff_data:
            return

        original_block = self.diff_data[key]['original_block']
        new_block = self.diff_data[key]['new_block']

        x_box_scroll_value = self.x_box.text_edit.verticalScrollBar().maximum() * original_block['start_line'] / len(self.x_box.text_edit.toPlainText().splitlines())
        y_box_scroll_value = self.y_box.text_edit.verticalScrollBar().maximum() * new_block['start_line'] / len(self.y_box.text_edit.toPlainText().splitlines())

        self.x_box.text_edit.verticalScrollBar().setValue(int(x_box_scroll_value))
        self.y_box.text_edit.verticalScrollBar().setValue(int(y_box_scroll_value))

    def add_diff_item_to_ui(self, key):
        # Add diff key to the UI list
        diff_item = QWidget()
        layout = QHBoxLayout()

        key_label = QLabel(key)
        layout.addWidget(key_label)

        add_left_button = QPushButton('Use Left')
        add_left_button.clicked.connect(lambda: self.on_add_button_clicked('left', key))
        layout.addWidget(add_left_button)

        add_right_button = QPushButton('Use Right')
        add_right_button.clicked.connect(lambda: self.on_add_button_clicked('right', key))
        layout.addWidget(add_right_button)

        diff_item.setLayout(layout)
        self.diff_layout.addWidget(diff_item)

    def update_position_indicators(self):
        self.status_bar.showMessage(f"Diff {self.current_diff_index + 1}/{len(self.diff_data)}")
        self.x_box.update_line_indicator(self.current_diff_index)
        self.y_box.update_line_indicator(self.current_diff_index)
        self.result_box.update_line_indicator(self.current_diff_index)

    def clear_diff_layout(self):
        for i in reversed(range(self.diff_layout.count())):
            widget = self.diff_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
    def save_result_text(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Result", "", "Text Files (*.txt);;Python Files (*.py);;All Files (*)")
        if file_name:
            with open(file_name, 'w') as file:
                file.write(self.result_box.text_edit.toPlainText())


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

