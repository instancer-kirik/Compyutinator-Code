#text_workers.py

from PyQt6.QtCore import QThreadPool, pyqtSignal, QObject
from NITTY_GRITTY.ThreadTrackers import SafeQRunnable
import difflib

class WorkerSignals(QObject):
    result = pyqtSignal(object)

class LineComparisonWorker(SafeQRunnable):
    def __init__(self, text1, text2):
        super().__init__(target=self.run)
        self.text1 = text1
        self.text2 = text2
        self.signals = WorkerSignals()

    def run(self):
        # Ensure both inputs are lists of strings
        lines1 = self.text1.splitlines() if isinstance(self.text1, str) else self.text1
        lines2 = self.text2 if isinstance(self.text2, list) else self.text2.splitlines()
        
        diff = list(difflib.ndiff(lines1, lines2))
        self.signals.result.emit(diff)