import threading
import concurrent.futures
import psutil
import time

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
