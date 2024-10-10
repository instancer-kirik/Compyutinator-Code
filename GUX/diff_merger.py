import difflib
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QTextEdit, QScrollArea, QFrame, QFileDialog, QStatusBar, QCheckBox, 
    QPlainTextEdit, QApplication, QDialog)
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QColor, QKeySequence, QShortcut, QTextCursor, QFont, QFontInfo, QFontMetrics, QPainter
from PyQt6.QtCore import Qt, QRegularExpression, QEvent, QSize, QRect, pyqtSignal
import re
from GUX.code_editor import CompEditor
from AuraText.auratext.Core.CodeEditor import CodeEditor
import logging
import os
class DiffHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor(33, 33, 3))  # Light yellow background

    def highlightBlock(self, text):
        if text.startswith('+'):
            self.setFormat(0, len(text), QColor(0, 255, 0, 50))  # Light green background
        elif text.startswith('-'):
            self.setFormat(0, len(text), QColor(255, 0, 0, 50))  # Light red background
        elif text.startswith('?'):
            self.setFormat(0, len(text), QColor(0, 0, 255, 50))  # Light blue background
class InlineDiffWidget(QWidget):
    def __init__(self, mm, original_text, suggested_text):
        super().__init__()
        self.mm = mm
        self.original_text = original_text
        self.suggested_text = suggested_text
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        layout.addWidget(self.editor)

        button_layout = QHBoxLayout()
        self.accept_button = QPushButton("Accept Change")
        self.reject_button = QPushButton("Reject Change")
        button_layout.addWidget(self.accept_button)
        button_layout.addWidget(self.reject_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.show_diff()

    def show_diff(self):
        diff = difflib.ndiff(self.original_text.splitlines(True), 
                             self.suggested_text.splitlines(True))
        
        html = []
        for line in diff:
            if line.startswith('+ '):
                html.append(f'<span style="background-color: #e6ffe6">{line[2:]}</span>')
            elif line.startswith('- '):
                html.append(f'<span style="background-color: #ffe6e6"> {line[2:]}</span>')
            elif line.startswith('? '):
                continue
            else:
                html.append(line[2:])
        
        self.editor.setHtml(''.join(html))

    def apply_changes(self):
        # Logic to apply accepted changes
        pass
class DiffMergerWidget(QDialog):  # Change QWidget to QDialog
    key_symbols = ['def', 'class', 'import']

    def __init__(self, mm, original_text="", suggested_text="", file_path=None):
        super().__init__()  # No parent widget for a dialog
        self.mm = mm
        self.file_path = file_path
        self.original_text = original_text
        self.suggested_text = suggested_text
        self.isFullScreen = False  # Start as a normal window
        self.diff_data = {}
        self.current_diff_index = -1
        self.current_line_index = 0
        self.diff_layout = QVBoxLayout()
        self.setLayout(self.diff_layout)
        self.initUI()
        
        # Set initial content
        self.x_box.text_edit.setPlainText(original_text)
        self.y_box.text_edit.setPlainText(suggested_text)
        self.apply_button = QPushButton("Apply Changes", self)
        self.apply_button.clicked.connect(self.apply_changes)
        self.layout().addWidget(self.apply_button)
        
    def initUI(self):
        self.setMinimumSize(1200, 800)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # Initialize text editors
        self.x_box = CodeEditor(self.mm)
        self.y_box = CodeEditor(self.mm)
        self.result_box = CodeEditor(self.mm)

        # Add these lines to set a minimum width for the text editors
        self.x_box.setMinimumWidth(400)
        self.y_box.setMinimumWidth(400)
        self.result_box.setMinimumWidth(400)

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

        # Apply syntax highlighting to the text editors
        self.x_highlighter = DiffHighlighter(self.x_box.text_edit.document())
        self.y_highlighter = DiffHighlighter(self.y_box.text_edit.document())
        self.result_highlighter = DiffHighlighter(self.result_box.text_edit.document())

        if self.file_path:
            self.setWindowTitle(f"Diff Merger - {os.path.basename(self.file_path)}")

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
        self.current_line_index = 0  # Reset the line index when scrolling to a new diff
        self.update_position_indicators()

    def scroll_to_diff_key(self, key):
        self.current_diff_index = list(self.diff_data.keys()).index(key)
        diff_data = self.diff_data[key]
        
        # Use get() method with default value of 0
        start_line_x = diff_data['original'].get('start_line', 0)
        start_line_y = diff_data['new'].get('start_line', 0)

        self.ensure_conflict_visible(self.x_box.text_edit, start_line_x)
        self.ensure_conflict_visible(self.y_box.text_edit, start_line_y)

        self.current_line_index = 0  # Reset the line index when scrolling to a new diff
        self.update_position_indicators()

    def ensure_conflict_visible(self, text_edit, line_index):
        block = text_edit.document().findBlockByLineNumber(line_index)
        cursor = text_edit.textCursor()
        cursor.setPosition(block.position())
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()

    def update_position_indicators(self):
        if self.current_diff_index < len(self.all_keys):
            key = self.all_keys[self.current_diff_index]
            diff_data = self.diff_data[key]
            self.highlight_current_conflict(diff_data)

    def highlight_current_conflict(self, diff_data):
        self.x_box.update_line_indicators(diff_data['diff'])
        self.y_box.update_line_indicators(diff_data['diff'])

        # Ensure the current conflict is visible
        start_line_x = diff_data['original'].get('start_line', 0)
        start_line_y = diff_data['new'].get('start_line', 0)
        self.ensure_conflict_visible(self.x_box.text_edit, start_line_x)
        self.ensure_conflict_visible(self.y_box.text_edit, start_line_y)

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
        self.result_box.text_edit.clear()  # Clear the result box
        self.diff_data.clear()  # Clear previous diff data

        self.original_blocks = self.extract_code_blocks(self.x_box.text_edit.toPlainText())
        self.new_blocks = self.extract_code_blocks(self.y_box.text_edit.toPlainText())

        use_original_order = self.use_original_order_checkbox.isChecked()
        self.all_keys = list(self.original_blocks.keys()) if use_original_order else list(self.new_blocks.keys())

        for key in self.all_keys:
            self.compare_code_blocks(key, self.original_blocks.get(key, {}), self.new_blocks.get(key, {}))

        self.current_diff_index = 0
        
        # Add all non-conflicting blocks at the start until the first conflict
        self.add_non_conflicting_blocks_until_conflict()
        
        # Ensure the diff view is updated
        self.diff_scroll_area.widget().update()

    def add_non_conflicting_blocks_until_conflict(self):
        for i, key in enumerate(self.all_keys):
            if key in self.diff_data and self.is_conflict(self.diff_data[key]['diff']):
                self.current_diff_index = i
                break
            self.add_block(key)

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
        current_key = 'global'
        start_line = 0

        for i, line in enumerate(lines):
            if line.strip().startswith(tuple(self.key_symbols)):
                if current_block:
                    blocks[current_key] = {
                        'content': '\n'.join(current_block),
                        'start_line': start_line,
                        'end_line': i - 1
                    }
                current_key = line.strip()
                current_block = [line]
                start_line = i
            else:
                current_block.append(line)

        if current_block:
            blocks[current_key] = {
                'content': '\n'.join(current_block),
                'start_line': start_line,
                'end_line': len(lines) - 1
            }
        return blocks

    def on_add_and_next_clicked(self, side):
        if self.current_diff_index >= len(self.all_keys):
            self.status_bar.showMessage("No more conflicts")
            return

        while self.current_diff_index < len(self.all_keys):
            current_key = self.all_keys[self.current_diff_index]
            
            if current_key in self.diff_data and self.is_conflict(self.diff_data[current_key]['diff']):
                self.add_selected_side(self.diff_data[current_key]['diff'], side)
                self.current_diff_index += 1
                break
            else:
                self.add_block(current_key)
                self.current_diff_index += 1

        if self.current_diff_index >= len(self.all_keys):
            self.status_bar.showMessage("All conflicts resolved")
            # Add any remaining non-conflicting blocks at the end
            self.add_remaining_blocks(side)
        else:
            self.status_bar.showMessage(f"Next conflict: {self.all_keys[self.current_diff_index]}")

        # Ensure the result box scrolls to show the latest added content
        self.result_box.text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.result_box.text_edit.ensureCursorVisible()

    def add_selected_side(self, diff, side):
        lines_to_add = []
        for line in diff:
            if line.startswith(' '):  # Matching line
                lines_to_add.append(line[2:])
            elif (side == 'left' and line.startswith('-')) or (side == 'right' and line.startswith('+')):
                lines_to_add.append(line[2:])
        self.result_box.text_edit.insertPlainText('\n'.join(lines_to_add) + '\n')

    def add_remaining_blocks(self, side):
        for i in range(self.current_diff_index, len(self.all_keys)):
            key = self.all_keys[i]
            if key in self.diff_data and self.is_conflict(self.diff_data[key]['diff']):
                self.add_selected_side(self.diff_data[key]['diff'], side)
            else:
                self.add_block(key)
         # Get the current text content
         #################################################TO REMOVE THE LAST NEWLINE
        text = self.result_box.text_edit.toPlainText()

        # Find the index of the last newline character
        last_newline_index = text.rfind('\n')

        # If there's a newline, remove everything from the last newline to the end
        if last_newline_index != -1:
            new_text = text[:last_newline_index]
            self.result_box.text_edit.setText(new_text)

    def add_block(self, key):
        block = self.new_blocks.get(key) or self.original_blocks.get(key)
        if block:
            self.result_box.text_edit.insertPlainText(block['content'] + '\n')

    def is_conflict(self, diff):
        return any(line.startswith('- ') or line.startswith('+ ') for line in diff)

    def compare_code_blocks(self, key, original_block, new_block):
        original_lines = original_block.get('content', '').split('\n')
        new_lines = new_block.get('content', '').split('\n')

        diff = list(difflib.ndiff(original_lines, new_lines))
        is_conflict = any(line.startswith('- ') or line.startswith('+ ') for line in diff)

        self.diff_data[key] = {
            'original': original_block,
            'new': new_block,
            'diff': diff
        }

        if is_conflict:
            self.add_diff_key_to_layout(key)

    def add_diff_key_to_layout(self, key):
        button = QPushButton(f'Conflict: {key}', self)
        button.clicked.connect(lambda _, k=key: self.scroll_to_diff_key(k))
        self.diff_layout.addWidget(button)

    def clear_diff_layout(self):
        """Clear the layout and reset the diff data."""
        for i in reversed(range(self.diff_layout.count())):
            widget_to_remove = self.diff_layout.itemAt(i).widget()
            logging.info(f"Removing widget: {widget_to_remove}")
            if widget_to_remove is not None and widget_to_remove in self.diff_layout.children():
                self.diff_layout.removeWidget(widget_to_remove)
                widget_to_remove.deleteLater()
            
        self.diff_data.clear()

    def save_result_text(self):
        file_dialog = QFileDialog()
        save_file, _ = file_dialog.getSaveFileName(self, "Save Result", "", "Text Files (*.txt)")
        if save_file:
            with open(save_file, 'w') as file:
                file.write(self.result_box.text_edit.toPlainText())
    def analyze_change_context(self, diff):
           # Analyze the surrounding code to understand the context of the change
           pass

    def suggest_merge_based_on_context(self):
           # Use the analyzed context to make a more informed merge decision
        pass
    def get_ai_merge_suggestion(self, conflict):
           # Use AI to generate a merge suggestion
           pass

    def apply_ai_suggestion(self):
        # Apply the AI-generated suggestion to the current conflict
        pass
    
    class MergeTestingManager:
       def run_tests_on_merged_code(self, merged_file_path):
           # Run automated tests on the merged code
           pass

       def report_test_results(self):
        # Generate a report of the test results after merging
        pass
    def apply_changes(self):
        merged_content = self.result_box.text_edit.toPlainText()
        if self.file_path:
            self.mm.editor_manager.update_editor_content(self.file_path, merged_content)
        else:
            self.mm.editor_manager.update_current_editor_content(merged_content)
        self.accept()  # Close the dialog and return QDialog.Accepted
class DiffMergerDialog(QDialog):
    def __init__(self, mm, original_text, suggested_text, file_path=None):
        super().__init__()
        self.mm = mm
        self.file_path = file_path
        self.original_text = original_text
        self.suggested_text = suggested_text
        self.merged_content = ""
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        
        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        layout.addWidget(self.diff_view)

        self.result_view = QTextEdit()
        layout.addWidget(self.result_view)

        button_layout = QHBoxLayout()
        self.accept_button = QPushButton("Accept Changes")
        self.accept_button.clicked.connect(self.accept)
        self.reject_button = QPushButton("Reject Changes")
        self.reject_button.clicked.connect(self.reject)
        button_layout.addWidget(self.accept_button)
        button_layout.addWidget(self.reject_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.show_diff()

    def show_diff(self):
        diff = difflib.unified_diff(
            self.original_text.splitlines(keepends=True),
            self.suggested_text.splitlines(keepends=True),
            fromfile='Original',
            tofile='Suggested'
        )
        self.diff_view.setPlainText(''.join(diff))
        self.result_view.setPlainText(self.suggested_text)

    def get_merged_content(self):
        return self.result_view.toPlainText()
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = DiffMergerWidget()
    window.show()
    sys.exit(app.exec())
