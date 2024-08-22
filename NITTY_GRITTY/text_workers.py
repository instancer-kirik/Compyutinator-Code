#text_workers.py

from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject

class WorkerSignals(QObject):
    finished = pyqtSignal(list)  # Signal to emit the comparison results

class LineComparisonWorker(QRunnable):
    def __init__(self, text, other_file_lines):
        super().__init__()
        self.text = text
        self.other_file_lines = other_file_lines
        self.signals = WorkerSignals()

    def run(self):
        result = []
        text = self.text
        lines = text.split('\n')
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
        self.signals.finished.emit(result)