from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QHBoxLayout
from PyQt6.QtCore import QProcess

class TerminalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.layout.addWidget(self.output)

        self.input = QLineEdit()
        self.input.returnPressed.connect(self.execute_command)
        self.layout.addWidget(self.input)

        if os.name == 'nt':
            # Windows
            self.process.start("cmd.exe")
        else:
            # Unix-like
            self.process.start("/bin/bash")

        self.process.readyReadStandardOutput.connect(self.update_output)
        self.process.readyReadStandardError.connect(self.update_output)

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
