import threading
import logging
from PyQt6.QtCore import QThread
import traceback
import logging

class SafeQThread(QThread):
    def run(self):
        try:
            super().run()
        except Exception as e:
            logging.critical(f"Uncaught exception in QThread {self.objectName()}:", exc_info=True)
            logging.exception(e)
            traceback.print_exc()
from PyQt6.QtCore import QRunnable, pyqtSlot

class SafeQRunnable(QRunnable):
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        try:
            self.target(*self.args, **self.kwargs)
        except Exception as e:
            logging.critical(f"Uncaught exception in QRunnable:")
            logging.exception(e)
            traceback.print_exc()
# Replace all QThread usages with SafeQThread in your application
class ThreadTracker:
    def __init__(self):
        self.threads = {}
        self.lock = threading.Lock()

    def register_thread(self, thread):
        with self.lock:
            self.threads[thread.ident] = thread
            logging.debug(f"Registered thread: {thread.name} (ID: {thread.ident})")

    def unregister_thread(self, thread_id):
        with self.lock:
            if thread_id in self.threads:
                thread = self.threads.pop(thread_id)
                logging.debug(f"Unregistered thread: {thread.name} (ID: {thread_id})")
            else:
                logging.debug(f"Attempted to unregister unknown thread ID: {thread_id}")
    def dump_thread_info(self):
        print("Active Threads:")
        for thread_id, thread_info in self.active_threads.items():
            print(f"Thread ID: {thread_id}, Name: {thread_info['name']}, Start Time: {thread_info['start_time']}")
    def is_thread_registered(self, thread_id):
        with self.lock:
            return thread_id in self.threads

    def get_active_threads(self):
        with self.lock:
            return list(self.threads.values())

global_thread_tracker = ThreadTracker()

# Monkey-patch threading.Thread
original_thread_init = threading.Thread.__init__
original_thread_run = threading.Thread.run

def patched_thread_init(self, *args, **kwargs):
    original_thread_init(self, *args, **kwargs)
    global_thread_tracker.register_thread(self)

def patched_thread_run(self):
    try:
        original_thread_run(self)
    finally:
        if global_thread_tracker.is_thread_registered(self.ident):
            global_thread_tracker.unregister_thread(self.ident)
        else:
            logging.debug(f"Thread {self.name} (ID: {self.ident}) was not registered")

threading.Thread.__init__ = patched_thread_init
threading.Thread.run = patched_thread_run
from PyQt6.QtCore import QThread

class QThreadTracker:
    def __init__(self):
        self.threads = {}
        self.lock = threading.Lock()

    def register_thread(self, thread):
        with self.lock:
            self.threads[thread] = thread.objectName() or str(thread)
            logging.debug(f"Registered QThread: {self.threads[thread]}")

    def unregister_thread(self, thread):
        with self.lock:
            if thread in self.threads:
                name = self.threads.pop(thread)
                logging.debug(f"Unregistered QThread: {name}")
            else:
                logging.warning(f"Attempted to unregister unknown QThread: {thread}")

    def get_active_threads(self):
        with self.lock:
            return list(self.threads.keys())

global_qthread_tracker = QThreadTracker()

# Monkey-patch QThread
original_qthread_init = QThread.__init__
original_qthread_run = QThread.run

def patched_qthread_init(self, *args, **kwargs):
    original_qthread_init(self, *args, **kwargs)
    global_qthread_tracker.register_thread(self)

def patched_qthread_run(self):
    try:
        original_qthread_run(self)
    finally:
        global_qthread_tracker.unregister_thread(self)

QThread.__init__ = patched_qthread_init
QThread.run = patched_qthread_run