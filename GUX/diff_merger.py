# diff_merger.py

import difflib
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSplitter, QTextEdit, QScrollArea, QFrame, QInputDialog, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt

class DiffMergerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)

        self.new_text = QTextEdit()
        self.new_text.setReadOnly(True)

        self.result_text = QTextEdit()
        
        self.diff_result = QScrollArea()
        self.diff_result.setWidgetResizable(True)
        self.diff_widget = QWidget()
        self.diff_layout = QVBoxLayout()

        self.diff_widget.setLayout(self.diff_layout)
        self.diff_result.setWidget(self.diff_widget)

        self.splitter.addWidget(self.original_text)
        self.splitter.addWidget(self.new_text)
        self.splitter.addWidget(self.diff_result)

        load_original_button = QPushButton('Load Original Text')
        load_original_button.clicked.connect(self.load_original_text)

        load_new_button = QPushButton('Load New Text')
        load_new_button.clicked.connect(self.load_new_text)

        show_diff_button = QPushButton('Show Diff')
        show_diff_button.clicked.connect(self.show_diff)

        clear_result_button = QPushButton('Clear Result')
        clear_result_button.clicked.connect(self.clear_result_text)

        save_result_button = QPushButton('Save Result')
        save_result_button.clicked.connect(self.save_result_text)

        layout.addWidget(load_original_button)
        layout.addWidget(load_new_button)
        layout.addWidget(self.splitter)
        layout.addWidget(QLabel("Resulting Merged Text"))
        layout.addWidget(self.result_text)
        layout.addWidget(show_diff_button)
        layout.addWidget(clear_result_button)
        layout.addWidget(save_result_button)
        self.setLayout(layout)

    def load_original_text(self):
        text, ok = QInputDialog.getMultiLineText(self, 'Load Original Text', 'Enter the original text:')
        if ok:
            self.original_text.setPlainText(text)

    def load_new_text(self):
        text, ok = QInputDialog.getMultiLineText(self, 'Load New Text', 'Enter the new text:')
        if ok:
            self.new_text.setPlainText(text)

    def show_diff(self):
        original_lines = self.original_text.toPlainText().splitlines()
        new_lines = self.new_text.toPlainText().splitlines()
        diff = list(difflib.ndiff(original_lines, new_lines))

        self.diff_layout = QVBoxLayout()
        self.diff_widget.setLayout(self.diff_layout)
        self.diff_lines = diff

        self.result_lines = original_lines.copy()

        for i, line in enumerate(diff):
            h_layout = QHBoxLayout()
            line_label = QLabel()
            line_label.setTextFormat(Qt.TextFormat.RichText)
            line_label.setWordWrap(True)

            if line.startswith('-'):
                line_label.setText(f'<span style="background-color: #ffcccc;">{line}</span>')
                merge_button = QPushButton('Accept Original')
                merge_button.setToolTip('Accept this line from the original text')
                merge_button.clicked.connect(lambda _, idx=i: self.accept_original(idx))
                h_layout.addWidget(line_label)
                h_layout.addWidget(merge_button)
            elif line.startswith('+'):
                line_label.setText(f'<span style="background-color: #ccffcc;">{line}</span>')
                merge_button = QPushButton('Accept New')
                merge_button.setToolTip('Accept this line from the new text')
                merge_button.clicked.connect(lambda _, idx=i: self.accept_new(idx))
                h_layout.addWidget(line_label)
                h_layout.addWidget(merge_button)
            else:
                line_label.setText(line)
                h_layout.addWidget(line_label)

            frame = QFrame()
            frame.setLayout(h_layout)
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            self.diff_layout.addWidget(frame)

    def accept_original(self, index):
        if self.diff_lines[index].startswith('-'):
            self.result_lines.append(self.diff_lines[index][2:])
            self.update_result_text()

    def accept_new(self, index):
        if self.diff_lines[index].startswith('+'):
            self.result_lines.append(self.diff_lines[index][2:])
            self.update_result_text()

    def update_result_text(self):
        self.result_text.setPlainText('\n'.join(self.result_lines))

        self.diff_layout = QVBoxLayout()
        self.diff_widget.setLayout(self.diff_layout)

        for i, line in enumerate(self.diff_lines):
            h_layout = QHBoxLayout()
            line_label = QLabel()
            line_label.setTextFormat(Qt.TextFormat.RichText)
            line_label.setWordWrap(True)

            if line.startswith('-'):
                line_label.setText(f'<span style="background-color: #ffcccc;">{line}</span>')
                merge_button = QPushButton('Accept Original')
                merge_button.setToolTip('Accept this line from the original text')
                merge_button.clicked.connect(lambda _, idx=i: self.accept_original(idx))
                h_layout.addWidget(line_label)
                h_layout.addWidget(merge_button)
            elif line.startswith('+'):
                line_label.setText(f'<span style="background-color: #ccffcc;">{line}</span>')
                merge_button = QPushButton('Accept New')
                merge_button.setToolTip('Accept this line from the new text')
                merge_button.clicked.connect(lambda _, idx=i: self.accept_new(idx))
                h_layout.addWidget(line_label)
                h_layout.addWidget(merge_button)
            else:
                line_label.setText(line)
                h_layout.addWidget(line_label)

            frame = QFrame()
            frame.setLayout(h_layout)
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            self.diff_layout.addWidget(frame)

    def clear_result_text(self):
        self.result_text.clear()
        self.result_lines.clear()

    def save_result_text(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Resulting Text", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'w') as file:
                    file.write(self.result_text.toPlainText())
                QMessageBox.information(self, "Success", "File saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
