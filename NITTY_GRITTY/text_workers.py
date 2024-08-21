#text_workers.py
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class LineComparisonWorker(QObject):
    finished = pyqtSignal(list)  # Signal to emit the result of the comparison

    def __init__(self, text, other_file_lines):
        super().__init__()
        self.text = text
        self.other_file_lines = other_file_lines

    def run(self):
        result = []
        lines = self.text.splitlines()
        for i, line in enumerate(lines):
            if i < len(self.other_file_lines):
                other_line = self.other_file_lines[i]
                if line.strip() == other_line.strip():
                    result.append((i, "indentation"))
                elif line != other_line:
                    result.append((i, "different"))
                else:
                    result.append((i, "identical"))
            else:
                result.append((i, "no_match"))
        self.finished.emit(result)