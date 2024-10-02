import threading
import concurrent.futures
import psutil
import time
import subprocess
from PyQt6.QtCore import QThreadPool, QObject, pyqtSignal
from NITTY_GRITTY.ThreadTrackers import SafeQRunnable
#maybe>?? not implmented
import logging

class ProcessController:
    def __init__(self):
        self.processes = []
        self.ollama_process = None

    def launch_process(self, command):
        process = subprocess.Popen(command, shell=True)
        self.processes.append(process)
        return process

    def get_running_processes(self):
        return [p for p in self.processes if p.poll() is None]

    def terminate_process(self, process):
        process.terminate()

    def launch_ollama(self, command="ollama serve"):
        if self.ollama_process is None or self.ollama_process.poll() is not None:
            self.ollama_process = subprocess.Popen(command, shell=True)
        return self.ollama_process

class ThreadController(QObject):
    thread_finished = pyqtSignal(object)

    def __init__(self, max_threads=None):
        super().__init__()
        self.max_threads = max_threads or psutil.cpu_count() * 2
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(self.max_threads)
        self.active_runnables = []

    def submit(self, runnable: SafeQRunnable):
        logging.debug(f"Submitting new runnable: {runnable}")
        runnable.setAutoDelete(False)
        runnable.signals = WorkerSignals()
        runnable.signals.finished.connect(self.on_thread_finished)
        self.active_runnables.append(runnable)
        self.thread_pool.start(runnable)

    def on_thread_finished(self):
        runnable = self.sender().parent()
        logging.debug(f"Thread finished: {runnable}")
        if runnable in self.active_runnables:
            self.active_runnables.remove(runnable)
        self.thread_finished.emit(runnable)

    def shutdown(self):
        logging.info("Shutting down ThreadController")
        self.thread_pool.clear()
        for runnable in self.active_runnables:
            if hasattr(runnable, 'stop') and callable(runnable.stop):
                runnable.stop()
        self.thread_pool.waitForDone(5000)  # Wait up to 5 seconds
        self.active_runnables.clear()
        logging.info("ThreadController shutdown complete")

class WorkerSignals(QObject):
    finished = pyqtSignal()

# Example task
def example_task(duration):
    time.sleep(duration)
    return f"Task with duration {duration} seconds completed"

class ThreadController2:
    def __init__(self, max_threads=None):
        self.max_threads = max_threads or psutil.cpu_count() * 5
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(self.max_threads)
        self.active_runnables = []

    def submit(self, runnable: SafeQRunnable):
        self.thread_pool.start(runnable)
        self.active_runnables.append(runnable)

    def available_threads(self):
        return self.max_threads - len(self.active_runnables)

    def running_threads(self):
        return [r for r in self.active_runnables if r.isFinished() == False]

    def shutdown(self):
        self.thread_pool.clear()
