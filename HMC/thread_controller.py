import threading
import concurrent.futures
import psutil
import time
import subprocess
from PyQt6.QtCore import QRunnable, QThreadPool
#maybe>?? not implmented
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

class ThreadController:
    def __init__(self, max_workers=None):
        self.max_workers = max_workers or psutil.cpu_count() * 5  # Default to 5 times the number of CPUs
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self.active_threads = set()
        self.lock = threading.Lock()

    def submit(self, fn, *args, **kwargs):
        future = self.executor.submit(fn, *args, **kwargs)
        with self.lock:
            self.active_threads.add(future)
        future.add_done_callback(self._thread_done_callback)
        return future

    def _thread_done_callback(self, future):
        with self.lock:
            self.active_threads.discard(future)

    def available_threads(self):
        with self.lock:
            return self.max_workers - len(self.active_threads)

    def shutdown(self):
        self.executor.shutdown(wait=True)

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

    def submit(self, runnable: QRunnable):
        self.thread_pool.start(runnable)
        self.active_runnables.append(runnable)

    def available_threads(self):
        return self.max_threads - len(self.active_runnables)

    def running_threads(self):
        return [r for r in self.active_runnables if r.isFinished() == False]

    def shutdown(self):
        self.thread_pool.clear()
