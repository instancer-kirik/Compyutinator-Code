from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QTextEdit, QFileDialog,
                             QMessageBox, QInputDialog, QApplication, QWidget, QPlainTextEdit, QTreeWidget, QTreeWidgetItem, QListView, QTextEdit
)
from PyQt6.QtCore import QTimer, Qt, QSize, QRegularExpression, QEvent, QSize, QRect, pyqtSignal

from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QBrush, QColor, QMouseEvent, QFont, QPainter, QTextCursor, QTextFormat
import os
import sys

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
    def __init__(self):
        super().__init__()

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
        new_tab = QTextEdit()
        new_tab.setPlainText(content)
        new_tab.textChanged.connect(lambda: self.prompt_file_name(new_tab))
        new_tab.setProperty("file_path", None)
        self.tab_widget.addTab(new_tab, title)

    def close_tab(self, index):
        editor = self.tab_widget.widget(index)
        if editor.document().isModified():
            reply = QMessageBox.question(self, 'Save Changes', "The document has been modified. Do you want to save your changes?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file(editor)
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.tab_widget.removeTab(index)

    def check_for_unsaved_changes(self):
        current_editor = self.tab_widget.currentWidget()
        if current_editor and current_editor.document().isModified():
            self.save_file(current_editor)

    def save_file(self, editor=None):
        if not editor:
            editor = self.tab_widget.currentWidget()

        file_path = editor.property("file_path")
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File")
            if not file_path:
                return
            editor.setProperty("file_path", file_path)

        with open(file_path, 'w') as file:
            file.write(editor.toPlainText())
        editor.document().setModified(False)
        self.tab_widget.setTabText(self.tab_widget.indexOf(editor), os.path.basename(file_path))

    def auto_save(self):
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor.document().isModified():
                self.save_file(editor)

    def prompt_file_name(self, editor):
        if not editor.property("file_path") and editor.toPlainText():
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
        
        # Initialize the layout
        layout = QVBoxLayout(self)
        
        # Line number area
        self.lineNumberArea = LineNumberArea(self)
        
        # File outline widget
        self.file_outline_widget = FileOutlineWidget()
        
        # Text editor
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont("Courier", 10))
        
        # Connect signals
        self.text_edit.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.text_edit.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.text_edit.textChanged.connect(self.update_file_outline)
        
        # Add widgets to the layout
        layout.addWidget(self.text_edit)
        layout.addWidget(self.file_outline_widget)
        
        # Set margins for line number area
        self.updateLineNumberAreaWidth(0)
    
    def update_file_outline(self):
        text = self.text_edit.toPlainText()
        self.file_outline_widget.populate_file_outline(text)

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.text_edit.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(Qt.GlobalColor.yellow).lighter(160)
            selection.format.setBackground(lineColor)

            # Get the cursor and its current block
            cursor = self.text_edit.textCursor()
            block = cursor.block()
            block_start = block.position()  # Start position of the block
            block_end = block_start + block.length()  # End position of the block

            # Adjust the cursor to select the entire line
            cursor.setPosition(block_start)
            cursor.setPosition(block_end - 1, QTextCursor.MoveMode.KeepAnchor)  # Ensure we don't go out of range
            selection.cursor = cursor

            extraSelections.append(selection)
        
        self.text_edit.setExtraSelections(extraSelections)

    def lineNumberAreaWidth(self):
        digits = 1
        count = max(1, self.text_edit.blockCount())
        while count >= 10:
            count //= 10
            digits += 1
        space = 3 + self.text_edit.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.text_edit.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.text_edit.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def get_line_numbers(self):
        text = self.text_edit.toPlainText()
        return text.splitlines(keepends=True)  # Keeps newline characters

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)

        block = self.text_edit.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.text_edit.blockBoundingGeometry(block).translated(self.text_edit.contentOffset()).top())
        bottom = top + round(self.text_edit.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    0,  # x
                    top,  # y
                    self.lineNumberArea.width(),  # width
                    self.text_edit.fontMetrics().height(),  # height
                    Qt.AlignmentFlag.AlignRight,  # flags
                    number  # text
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.text_edit.blockBoundingRect(block).height())
            blockNumber += 1


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

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
