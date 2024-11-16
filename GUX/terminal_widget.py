from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QMenu, QApplication, QLabel
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QProcess, Qt
import os
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QSplitter
from PyQt6.QtCore import Qt
from AuraText.auratext.Core.powershell import TerminalEmulator
import logging

class TerminalWidget(QWidget):
    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.cccore = cccore
        self.setLayout(QVBoxLayout())
        self.terminals = []  # Keep track of terminals
        self.add_terminal()

    def add_terminal(self):
        try:
            terminal = TerminalEmulator(self, mm=self.cccore)
            self.terminals.append(terminal)
            self.layout().addWidget(terminal)
            return terminal
        except Exception as e:
            logging.error(f"Error creating terminal: {e}")
            error_label = QLabel("Failed to initialize terminal. Check logs for details.")
            error_label.setStyleSheet("color: red;")
            self.layout().addWidget(error_label)
            return None

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Shift+H"), self, self.split_horizontal)
        QShortcut(QKeySequence("Ctrl+Shift+V"), self, self.split_vertical)
        QShortcut(QKeySequence("Ctrl+Shift+W"), self, self.close_current_terminal)

    def split_horizontal(self):
        current_terminal = self.layout().itemAt(self.layout().count() - 1).widget()
        new_terminal = self.add_terminal()
        self.layout().setOrientation(Qt.Orientation.Vertical)
        self.layout().insertWidget(self.layout().count() - 1, new_terminal)
        self.layout().setStretchFactor(self.layout().count() - 1, 1)
        new_terminal.setFocus()

    def split_vertical(self):
        current_terminal = self.layout().itemAt(self.layout().count() - 1).widget()
        new_terminal = self.add_terminal()
        self.layout().setOrientation(Qt.Orientation.Horizontal)
        self.layout().insertWidget(self.layout().count() - 1, new_terminal)
        self.layout().setStretchFactor(self.layout().count() - 1, 1)
        new_terminal.setFocus()

    def close_current_terminal(self):
        current_terminal = self.layout().itemAt(self.layout().count() - 1).widget()
        if self.layout().count() > 1:
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
        """Clean up terminals before closing"""
        try:
            for terminal in self.terminals:
                if terminal:
                    terminal.cleanup()
        except Exception as e:
            logging.error(f"Error cleaning up terminals: {e}")
        super().closeEvent(event)
