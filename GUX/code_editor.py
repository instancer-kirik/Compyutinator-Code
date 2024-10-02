from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QTextEdit, QFileDialog,
                             QMessageBox, QInputDialog, QApplication, QWidget, QPlainTextEdit, QTreeWidget, QTreeWidgetItem, QListView, QTextEdit, QHBoxLayout
)
from PyQt6.QtCore import QTimer, Qt, QSize, QRegularExpression, QEvent, QSize, QRect, pyqtSignal, QThreadPool, QThread
from NITTY_GRITTY.text_workers import LineComparisonWorker
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QBrush, QColor, QMouseEvent, QFont, QPainter, QTextCursor, QTextFormat
import os
import sys
import logging
import time
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Define formats
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QBrush(QColor(0, 0, 255)))
        keywords = ["def", "class", "import", "from", "return", "if", "else", "elif"]
        for keyword in keywords:
            pattern = rf"\b{keyword}\b"
            self.highlighting_rules.append((pattern, self.keyword_format))

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QBrush(QColor(0, 128, 0)))
        self.highlighting_rules.append((r"#.*", self.comment_format))

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QBrush(QColor(255, 0, 0)))
        self.highlighting_rules.append((r'"[^"]*"', self.string_format))
        self.highlighting_rules.append((r"'[^']*'", self.string_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

class CodeEditorWidget(QWidget):
    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.cccore = cccore

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
       
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.check_for_unsaved_changes)
        self.layout.addWidget(self.tab_widget)
        self.setAcceptDrops(True)
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(300000)  # Auto-save every 5 minutes

        self.add_tab("Untitled")
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if os.path.isfile(file_path):
                    if event.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
                        # Paste the path as text
                        self.paste_text(file_path)
                    else:
                        # Open the file
                        self.open_file(file_path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def open_file(self, file_path):
        with open(file_path, 'r') as file:
            content = file.read()
        editor = self.tab_widget.currentWidget()
        editor.setPlainText(content)
        editor.setProperty("file_path", file_path)
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(file_path))

        # Apply syntax highlighting based on file extension
        if file_path.endswith('.py'):
            self.apply_syntax_highlighter(editor)

    def paste_text(self, text):
        cursor = self.tab_widget.currentWidget().textCursor()
        cursor.insertText(text)

    def add_tab(self, title, content=""):
        new_tab = CompEditor()  # Use CompEditor instead of QTextEdit
        new_tab.text_edit.setPlainText(content)
        new_tab.text_edit.textChanged.connect(lambda: self.prompt_file_name(new_tab))
        new_tab.setProperty("file_path", None)
        self.tab_widget.addTab(new_tab, title)

    def close_tab(self, index):
        editor = self.tab_widget.widget(index)
        if editor.text_edit.document().isModified():
            reply = QMessageBox.question(self, 'Save Changes', "The document has been modified. Do you want to save your changes?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file(editor)
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.tab_widget.removeTab(index)

    def check_for_unsaved_changes(self):
        current_editor = self.tab_widget.currentWidget()
        if current_editor and current_editor.text_edit.document().isModified():
            self.save_file(current_editor)

    def save_file(self, editor):
        file_path = editor.property("file_path")
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File")
            if not file_path:
                return
            editor.setProperty("file_path", file_path)
        
        with open(file_path, 'w') as f:
            f.write(editor.text_edit.toPlainText())
        editor.text_edit.document().setModified(False)
        self.tab_widget.setTabText(self.tab_widget.indexOf(editor), os.path.basename(file_path))

    def auto_save(self):
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor.text_edit.document().isModified():
                self.save_file(editor)

    def prompt_file_name(self, editor):
        if not editor.property("file_path") and editor.text_edit.toPlainText():
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File As")
            if file_path:
                editor.setProperty("file_path", file_path)
                self.save_file(editor)

    def apply_syntax_highlighter(self, editor):
        highlighter = PythonHighlighter(editor.document())
        editor.setProperty("highlighter", highlighter)

    def eventFilter(self, obj, event):
        if obj == self.tab_widget.tabBar():
            if event.type() == QMouseEvent.Type.Enter:
                self.scroll_timer.start(20)
            elif event.type() == QMouseEvent.Type.Leave:
                self.scroll_timer.stop()
                self.scroll_speed = 1
                self.scroll_direction = None
            elif event.type() == QMouseEvent.Type.MouseMove:
                self.update_scroll_speed(event.pos())
        return super().eventFilter(obj, event)

    def update_scroll_speed(self, pos):
        bar = self.tab_widget.tabBar()
        if pos.x() < 30:
            self.scroll_direction = -1
            self.scroll_speed = max(1, 30 - pos.x())
        elif pos.x() > bar.width() - 30:
            self.scroll_direction = 1
            self.scroll_speed = max(1, pos.x() - (bar.width() - 30))
        else:
            self.scroll_speed = 1
            self.scroll_direction = None

    def scroll_tabs(self):
        if self.scroll_direction is not None:
            bar = self.tab_widget.tabBar()
            current_index = self.tab_widget.currentIndex()
            new_index = (current_index + self.scroll_direction) % self.tab_widget.count()
            if new_index < 0:
                new_index = self.tab_widget.count() - 1
            self.tab_widget.setCurrentIndex(new_index)

            bar.scroll(self.scroll_direction * self.scroll_speed, 0)

    def wrap_tabs(self):
        current_index = self.tab_widget.currentIndex()
        self.tab_widget.setCurrentIndex((current_index + self.scroll_direction) % self.tab_widget.count())

class CompEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        hbox = QHBoxLayout()
        hbox.setSpacing(0)
        layout.addLayout(hbox)
        
        self.line_number_area = LineNumberArea(self)
        hbox.addWidget(self.line_number_area)
        
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont("Courier", 10))
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        hbox.addWidget(self.text_edit)
        
        # File outline widget
        self.file_outline_widget = FileOutlineWidget()
        layout.addWidget(self.file_outline_widget)
        
        self.text_edit.blockCountChanged.connect(self.update_line_number_area_width)
        self.text_edit.updateRequest.connect(self.update_line_number_area)
        self.text_edit.cursorPositionChanged.connect(self.highlight_current_line)
        self.text_edit.textChanged.connect(self.update_file_outline)
        
        self.update_line_number_area_width(0)

        self.other_file_lines = []
        self.comparison_results = []

        self.ui_update_timer = QTimer()
        self.ui_update_timer.setSingleShot(True)
        self.ui_update_timer.timeout.connect(self.update_highlights)
       
       
        
        # Initialize start and end lines for highlighting
        self.start_line = 0
        self.end_line = 0

        self.last_update_time = 0
        self.update_interval = 100  # milliseconds

    def update_file_outline(self):
        text = self.text_edit.toPlainText()
        self.file_outline_widget.populate_file_outline(text)

    def highlight_current_line(self):
        self.start_comparison()
        extra_selections = []
        if not self.text_edit.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.GlobalColor.yellow).lighter(160)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.text_edit.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.text_edit.setExtraSelections(extra_selections)

    def start_comparison(self):
        # Create the worker
        worker = LineComparisonWorker(self.text_edit.toPlainText(), self.other_file_lines)
        worker.signals.result.connect(self.on_comparison_finished)
        
       
        
        # Submit the worker to the thread pool
        QThreadPool.globalInstance().start(worker)  

    def on_comparison_finished(self, result):
        self.comparison_results = result
        self.update_highlights()
        self.update_line_indicators(result)

    def update_highlights(self):
        cursor = QTextCursor(self.text_edit.document())
        extra_selections = self.text_edit.extraSelections()
        for i, status in self.comparison_results:
            cursor = QTextCursor(self.text_edit.document().findBlockByNumber(i))
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.cursor.select(QTextCursor.SelectionType.BlockUnderCursor)

            if status == "indentation":
                color = QColor(173, 216, 230)  # Light blue
            elif status == "different":
                color = QColor(255, 204, 203)  # Light red
            elif status == "no_match":
                color = QColor(255, 255, 204)  # Light yellow
            else:
                continue  # Skip identical lines

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setBackground(color)
            extra_selections.append(selection)

        self.text_edit.setExtraSelections(extra_selections)

    def update_line_indicators(self, diff_data):
        self.text_edit.setExtraSelections([])
        extra_selections = []

        current_line = 0
        if isinstance(diff_data, list):
            # If diff_data is a list, process it directly
            for line in diff_data:
                selection = self.create_line_selection(current_line, line)
                if selection:
                    extra_selections.append(selection)
                current_line += 1
        elif isinstance(diff_data, dict):
            # If diff_data is a dictionary, process each block
            for block_data in diff_data.values():
                diff = block_data.get('diff', [])
                for line in diff:
                    selection = self.create_line_selection(current_line, line)
                    if selection:
                        extra_selections.append(selection)
                    current_line += 1

        self.text_edit.setExtraSelections(extra_selections)

    def create_line_selection(self, line_number, line):
        selection = QTextEdit.ExtraSelection()
        cursor = QTextCursor(self.text_edit.document().findBlockByNumber(line_number))
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        selection.cursor = cursor

        if isinstance(line, tuple):
            status, text = line
        elif isinstance(line, str):
            status = line[0] if line else ' '
            text = line[2:] if len(line) > 2 else ''
        else:
            return None  # Invalid line format

        if status == '+':
            selection.format.setBackground(QColor(200, 255, 200))  # Light green for added lines
        elif status == '-':
            selection.format.setBackground(QColor(255, 200, 200))  # Light red for removed lines
        elif status == ' ':
            selection.format.setBackground(QColor(230, 230, 230))  # Light gray for matching lines
        else:
            return None  # Return None for lines that don't need highlighting

        return selection

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.text_edit.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.text_edit.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        current_time = time.time() * 1000  # Convert to milliseconds
        if current_time - self.last_update_time < self.update_interval:
            return
        
        self.last_update_time = current_time

        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.text_edit.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.text_edit.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def get_line_numbers(self):
        text = self.text_edit.toPlainText()
        return text.splitlines(keepends=True)  # Keeps newline characters

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)

        block = self.text_edit.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.text_edit.blockBoundingGeometry(block).translated(self.text_edit.contentOffset()).top())
        bottom = top + round(self.text_edit.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(0, top, self.line_number_area.width(), self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.text_edit.blockBoundingRect(block).height())
            block_number += 1

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setOpacity(0.2)
        painter.fillRect(QRect(0, self.start_line * self.fontMetrics().height(),
                               self.width(), (self.end_line - self.start_line + 1) * self.fontMetrics().height()),
                         QColor(255, 255, 0))  # Light yellow background

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class FileOutlineWidget(QTreeWidget):  # Correcting the widget type to QTreeWidget
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)  # Hide the header to make it look like an outline

    def populate_file_outline(self, text):
        self.clear()
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith('class ') or line.strip().startswith('def '):
                item = QTreeWidgetItem([f"{i + 1}: {line.strip()}"])
                self.addTopLevelItem(item)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    editor = CodeEditorWidget()
    editor.show()
    sys.exit(app.exec())
