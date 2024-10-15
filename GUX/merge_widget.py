from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt6.QtGui import QFont, QColor, QPainter, QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal
from GUX.widget_vault import DiffHighlighter
from difflib import unified_diff

class MergeTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = QFont("Courier")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setOpacity(0.2)
        document = self.document()
        for block in document:
            if block.text().startswith('-'):
                layout = block.layout()
                line_rect = layout.lineAt(0).rect()
                painter.fillRect(line_rect, QColor(100, 100, 100))

class MergeWidget(QDialog):
    merge_accepted = pyqtSignal(str)
    merge_rejected = pyqtSignal()

    def __init__(self, file_path, original_content, new_content, language=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Changes")
        self.file_path = file_path
        self.original_content = original_content
        self.new_content = new_content
        self.language = language
        self.is_diff = self.check_if_diff(new_content)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.context_label = QLabel(f"Editing: {self.file_path}")
        layout.addWidget(self.context_label)

        self.merge_edit = MergeTextEdit()
        self.highlighter = DiffHighlighter(self.merge_edit.document())
        layout.addWidget(self.merge_edit)

        button_layout = QHBoxLayout()
        self.accept_button = QPushButton("Accept Changes")
        self.accept_button.clicked.connect(self.accept_changes)
        self.reject_button = QPushButton("Reject Changes")
        self.reject_button.clicked.connect(self.reject_changes)
        button_layout.addWidget(self.accept_button)
        button_layout.addWidget(self.reject_button)
        layout.addLayout(button_layout)

        self.show_content()

    def check_if_diff(self, content):
        lines = content.splitlines()
        return any(line.startswith(('+++', '---', '@@')) for line in lines[:10])

    def show_content(self):
        if self.is_diff:
            self.merge_edit.setPlainText(self.new_content)
        else:
            diff_content = self.generate_diff()
            self.merge_edit.setPlainText(diff_content)
        self.merge_edit.setReadOnly(True)

    def generate_diff(self):
        diff = list(unified_diff(
            self.original_content.splitlines(keepends=True),
            self.new_content.splitlines(keepends=True),
            fromfile=self.file_path,
            tofile=f"{self.file_path} (modified)",
            lineterm='',
        ))
        return ''.join(diff)

    def accept_changes(self):
        if self.is_diff:
            final_content = self.apply_diff(self.original_content, self.new_content)
        else:
            final_content = self.new_content
        
        self.merge_accepted.emit(final_content)
        self.accept()

    def apply_diff(self, original, diff):
        lines = original.splitlines()
        diff_lines = diff.splitlines()
        result = []
        i = 0
        for line in diff_lines:
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                continue
            elif line.startswith('+'):
                result.append(line[1:])
            elif line.startswith('-'):
                i += 1
            else:
                result.append(lines[i])
                i += 1
        return '\n'.join(result)

    def reject_changes(self):
        self.merge_rejected.emit()
        self.reject()

def show_merge(file_path, original_content, new_content, language=None, editor_widget=None):
    merge_widget = MergeWidget(file_path, original_content, new_content, language)
    if editor_widget:
        merge_widget.merge_accepted.connect(lambda content: editor_widget.setPlainText(content))
        merge_widget.merge_rejected.connect(lambda: editor_widget.setPlainText(original_content))
    return merge_widget.exec()
