from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QProcess, Qt
import os
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QSplitter
from PyQt6.QtCore import Qt
from AuraText.auratext.Core.powershell import TerminalEmulator
class TerminalWidget(QWidget):
    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.cccore = cccore
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(self)
        self.layout.addWidget(self.splitter)

        self.add_terminal()
    
        self.setup_shortcuts()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Shift+H"), self, self.split_horizontal)
        QShortcut(QKeySequence("Ctrl+Shift+V"), self, self.split_vertical)
        QShortcut(QKeySequence("Ctrl+Shift+W"), self, self.close_current_terminal)

    def add_terminal(self):
        terminal = TerminalEmulator(self, mm=self.cccore)
        if self.cccore and hasattr(self.cccore, 'input_manager'):
            terminal.keyPressed.connect(self.cccore.input_manager.update_typing_speed)
        self.splitter.addWidget(terminal)
        return terminal

    def split_horizontal(self):
        current_terminal = self.splitter.widget(self.splitter.count() - 1)
        new_terminal = self.add_terminal()
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter.insertWidget(self.splitter.count() - 1, new_terminal)
        self.splitter.setStretchFactor(self.splitter.count() - 1, 1)
        new_terminal.setFocus()

    def split_vertical(self):
        current_terminal = self.splitter.widget(self.splitter.count() - 1)
        new_terminal = self.add_terminal()
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.insertWidget(self.splitter.count() - 1, new_terminal)
        self.splitter.setStretchFactor(self.splitter.count() - 1, 1)
        new_terminal.setFocus()

    def close_current_terminal(self):
        current_terminal = self.splitter.widget(self.splitter.count() - 1)
        if self.splitter.count() > 1:
            current_terminal.setParent(None)
            current_terminal.deleteLater()
        else:
            self.parent().close()  # Close the entire widget if it's the last terminal

    def execute_command(self):
        command = self.input.text()
        self.process.write(command.encode() + b'\n')
        self.input.clear()

    def update_output(self):
        output = self.process.readAllStandardOutput().data().decode()
        self.output.append(output)
        error_output = self.process.readAllStandardError().data().decode()
        if error_output:
            self.output.append(error_output)

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        split_h_action = QAction("Split Horizontally", self)
        split_v_action = QAction("Split Vertically", self)
        close_action = QAction("Close Terminal", self)

        split_h_action.triggered.connect(self.split_horizontal)
        split_v_action.triggered.connect(self.split_vertical)
        close_action.triggered.connect(self.close_current_terminal)

        context_menu.addAction(split_h_action)
        context_menu.addAction(split_v_action)
        context_menu.addAction(close_action)

        context_menu.exec(event.globalPos())

    def copy_text(self):
        cursor = self.output.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            QApplication.clipboard().setText(selected_text)

    def clear_output(self):
        self.output.clear()

    def closeEvent(self, event):
        self.process.terminate()
        self.process.waitForFinished()
        super().closeEvent(event)
