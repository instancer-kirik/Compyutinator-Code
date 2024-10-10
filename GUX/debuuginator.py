import sys
import threading
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QLineEdit, QTreeView, QSplitter, QLabel,
                             QTabWidget, QListWidget, QTreeWidget, QTreeWidgetItem)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QStandardItemModel, QStandardItem
import debugpy
from debugpy.server import api
import psutil
import networkx as nx
import matplotlib.pyplot as plt
import traceback
import logging
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from NITTY_GRITTY.ThreadTrackers import global_thread_tracker, global_qthread_tracker
from PyQt6.QtCore import pyqtSignal
class BreakpointBookmarkWidget(QWidget):
    def __init__(self, cool_widget):
        super().__init__()
        logging.warning("BreakpointBookmarkWidget initialized")
        self.cool_widget = cool_widget
        self.setup_ui()
        self.breakpoint_list.itemDoubleClicked.connect(self.goto_breakpoint)
        self.bookmark_list.itemDoubleClicked.connect(self.goto_bookmark)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.breakpoint_list = QListWidget()
        self.bookmark_list = QListWidget()
        
        layout.addWidget(QLabel("Breakpoints:"))
        layout.addWidget(self.breakpoint_list)
        layout.addWidget(QLabel("Bookmarks:"))
        layout.addWidget(self.bookmark_list)

        self.breakpoint_list.itemDoubleClicked.connect(self.goto_breakpoint)
        self.bookmark_list.itemDoubleClicked.connect(self.goto_bookmark)

    def update_breakpoints(self, breakpoints):
        self.breakpoint_list.clear()
        for bp in breakpoints:
            self.breakpoint_list.addItem(f"{bp['file']}:{bp['line']}")

    def update_bookmarks(self, bookmarks):
        self.bookmark_list.clear()
        for bm in bookmarks:
            self.bookmark_list.addItem(f"{bm['file']}:{bm['line']} - {bm['name']}")

    def goto_breakpoint(self, item):
        file, line = item.text().split(':')
        self.cool_widget.goto_file_line(file, int(line))

    def goto_bookmark(self, item):
        file, rest = item.text().split(':', 1)
        line = rest.split(' - ')[0]
        self.cool_widget.goto_file_line(file, int(line))

class ForestWidget(QWidget):
    def __init__(self, debugger_widget):
        super().__init__()
        self.debugger_widget = debugger_widget
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.forest_tree = QTreeWidget()
        self.forest_tree.setHeaderLabels(["File", "Line", "Log Call"])
        layout.addWidget(self.forest_tree)

        self.forest_tree.itemDoubleClicked.connect(self.goto_log_call)

    def update_forest(self, log_calls):
        self.forest_tree.clear()
        for log_call in log_calls:
            item = QTreeWidgetItem(self.forest_tree)
            item.setText(0, log_call['file'])
            item.setText(1, str(log_call['line']))
            item.setText(2, log_call['call'])

    def goto_log_call(self, item, column):
        file = item.text(0)
        line = int(item.text(1))
        self.debugger_widget.goto_file_line(file, line)

class DebuggerThread(QThread):
    output_received = pyqtSignal(str)
    state_changed = pyqtSignal(str)
    stack_trace_updated = pyqtSignal(list)
    variables_updated = pyqtSignal(dict)

    def __init__(self, code):
        super().__init__()
        self.code = code

    def run(self):
        debugpy.listen(("localhost", 5678))
        self.output_received.emit("Waiting for debugpy client to attach...")
        debugpy.wait_for_client()
        self.output_received.emit("Debugpy client attached.")
        
        def output_callback(category, output):
            self.output_received.emit(f"{category}: {output}")

        def thread_stopped_callback(thread_id, reason, thread_name, *args):
            self.state_changed.emit("stopped")
            frames = debugpy.get_stack_trace(thread_id)
            self.stack_trace_updated.emit(frames)
            variables = debugpy.get_variables(thread_id, frames[0]['id'])
            self.variables_updated.emit(variables)

        debugpy.set_output_callback(output_callback)
        debugpy.set_thread_stopped_callback(thread_stopped_callback)

        try:
            debugpy.run_file(self.code)
        except Exception as e:
            self.output_received.emit(f"Error: {str(e)}")

class CoolWidget(QWidget):
    def __init__(self, cccore):
        logging.info("Initializing CoolWidget")
        try:
            super().__init__()
            self.cccore = cccore
            self.setup_ui()
            self.connect_signals()
            self.debugger_thread = None
            self.breakpoints = []
            self.bookmarks = []
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.update_thread_and_memory_info)
            self.update_timer.start(1000)  # Update every second
            logging.info("CoolWidget initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing CoolWidget: {str(e)}")
            logging.error(traceback.format_exc())

    def setup_ui(self):
        logging.info("Setting up CoolWidget UI")
        try:
            layout = QVBoxLayout(self)

            # Control buttons
            control_layout = QHBoxLayout()
            self.run_button = QPushButton("Run")
            self.step_button = QPushButton("Step")
            self.continue_button = QPushButton("Continue")
            self.stop_button = QPushButton("Stop")
            control_layout.addWidget(self.run_button)
            control_layout.addWidget(self.step_button)
            control_layout.addWidget(self.continue_button)
            control_layout.addWidget(self.stop_button)
            layout.addLayout(control_layout)

            # Main splitter
            splitter = QSplitter(Qt.Orientation.Horizontal)

            # Left side: Stack, Variables, and Console
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            
            self.stack_view = QTreeView()
            left_layout.addWidget(QLabel("Stack Trace"))
            left_layout.addWidget(self.stack_view)

            self.var_view = QTreeView()
            left_layout.addWidget(QLabel("Variables"))
            left_layout.addWidget(self.var_view)

            self.console_output = QTextEdit()
            self.console_output.setReadOnly(True)
            left_layout.addWidget(QLabel("Console Output"))
            left_layout.addWidget(self.console_output)

            splitter.addWidget(left_widget)

            # Right side: Tabs for additional features
            right_widget = QTabWidget()

            # Breakpoints and Bookmarks tab
            self.breakpoint_bookmark_widget = BreakpointBookmarkWidget(self)
            right_widget.addTab(self.breakpoint_bookmark_widget, "Breakpoints & Bookmarks")

            # Thread viewer tab
            self.thread_list = QListWidget()
            right_widget.addTab(self.thread_list, "Threads")

            # Memory usage tab
            self.memory_view = FigureCanvas(plt.Figure(figsize=(5, 4)))
            right_widget.addTab(self.memory_view, "Memory Usage")

            # Call graph tab
            self.call_graph = FigureCanvas(plt.Figure(figsize=(5, 4)))
            right_widget.addTab(self.call_graph, "Call Graph")

            # Forest tab
            self.forest_widget = ForestWidget(self)
            right_widget.addTab(self.forest_widget, "Forest")

            splitter.addWidget(right_widget)

            layout.addWidget(splitter)

            # Command input
            self.command_input = QLineEdit()
            layout.addWidget(QLabel("Debugger Command"))
            layout.addWidget(self.command_input)

            logging.info("CoolWidget UI setup complete")
        except Exception as e:
            logging.error(f"Error setting up CoolWidget UI: {str(e)}")
            logging.error(traceback.format_exc())

    def connect_signals(self):
        # ... (existing signal connections) ...
        self.run_button.clicked.connect(self.run_debugger)
        self.step_button.clicked.connect(self.step)
        self.continue_button.clicked.connect(self.continue_execution)
        self.stop_button.clicked.connect(self.stop_debugger)
        self.command_input.returnPressed.connect(self.execute_command)
        #self.breakpoint_bookmark_widget.itemDoubleClicked.connect(self.toggle_breakpoint)
       # self.thread_list.itemDoubleClicked.connect(self.goto_thread)
    def run_debugger(self):
        code = self.cccore.editor_manager.get_current_editor_content()
        self.debugger_thread = DebuggerThread(code)
        self.debugger_thread.output_received.connect(self.update_console)
        self.debugger_thread.state_changed.connect(self.update_state)
        self.debugger_thread.stack_trace_updated.connect(self.update_stack_view)
        self.debugger_thread.variables_updated.connect(self.update_var_view)
        self.debugger_thread.start()
        self.update_breakpoints()
        self.update_bookmarks()
        self.update_forest()

    def step(self):
        debugpy.step_into()

    def continue_execution(self):
        debugpy.continue_execution()

    def stop_debugger(self):
        if self.debugger_thread:
            debugpy.stop_debugging()
            self.debugger_thread.quit()
            self.debugger_thread.wait()
        self.update_timer.stop()

    def execute_command(self):
        command = self.command_input.text()
        self.command_input.clear()
        try:
            result = debugpy.evaluate(command)
            self.update_console(f"> {command}\n{result}")
        except Exception as e:
            self.update_console(f"Error: {str(e)}")

    def update_console(self, message):
        self.console_output.append(message)

    def update_state(self, state):
        # Update UI based on debugger state
        pass

    def update_stack_view(self, frames):
        model = QStandardItemModel()
        for frame in frames:
            item = QStandardItem(f"{frame['name']} at line {frame['line']}")
            model.appendRow(item)
        self.stack_view.setModel(model)
        self.update_call_graph(frames)

    def update_var_view(self, variables):
        model = QStandardItemModel()
        root = model.invisibleRootItem()
        for category, vars in variables.items():
            category_item = QStandardItem(category)
            root.appendRow(category_item)
            for var in vars:
                item = QStandardItem(f"{var['name']}: {var['value']}")
                category_item.appendRow(item)
        self.var_view.setModel(model)
        self.var_view.expandAll()

    def toggle_breakpoint(self, item):
        # Toggle breakpoint logic
        breakpoint = item.text()
        if breakpoint in self.breakpoints:
            self.breakpoints.remove(breakpoint)
            debugpy.clear_breakpoint(breakpoint)
        else:
            self.breakpoints.append(breakpoint)
            file, line = breakpoint.split(':')
            debugpy.set_breakpoint(file, int(line))
        self.update_breakpoint_list()

    def update_breakpoint_list(self):
        self.breakpoint_list.clear()
        for bp in self.breakpoints:
            self.breakpoint_list.addItem(bp)

    def update_thread_and_memory_info(self):
        self.update_thread_list()
        self.update_memory_usage()

    def update_thread_list(self):
        self.thread_list.clear()
        for thread in global_thread_tracker.get_active_threads():
            self.thread_list.addItem(f"Python Thread: {thread.name} (ID: {thread.ident})")
        for thread in global_qthread_tracker.get_active_threads():
            self.thread_list.addItem(f"QThread: {thread.objectName()} (ID: {int(thread.currentThreadId())})")

    def update_memory_usage(self):
        if self.debugger_thread:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            ax = self.memory_view.figure.subplots()
            ax.clear()
            ax.bar(['RSS', 'VMS'], [memory_info.rss, memory_info.vms])
            ax.set_ylabel('Bytes')
            ax.set_title('Memory Usage')
            self.memory_view.draw()

    def update_call_graph(self, frames):
        G = nx.DiGraph()
        for i, frame in enumerate(frames):
            G.add_node(i, name=frame['name'])
            if i > 0:
                G.add_edge(i-1, i)
        
        ax = self.call_graph.figure.subplots()
        ax.clear()
        pos = nx.spring_layout(G)
        nx.draw(G, pos, ax=ax, with_labels=True, labels={i: data['name'] for i, data in G.nodes(data=True)})
        ax.set_title('Call Graph')
        self.call_graph.draw()

    def update_breakpoints(self):
        self.breakpoint_bookmark_widget.update_breakpoints(self.breakpoints)

    def update_bookmarks(self):
        self.breakpoint_bookmark_widget.update_bookmarks(self.bookmarks)

    def goto_file_line(self, file, line):
        
        self.cccore.editor_manager.open(file,line)

    def update_forest(self):
        # Use LSP to get log function calls
        if hasattr(self.cccore, 'lsp_manager'):
            log_calls = self.cccore.lsp_manager.get_log_function_calls()
            self.forest_widget.update_forest(log_calls)

    def cleanup(self):
        logging.info("Cleaning up CoolWidget")
        # Add any necessary cleanup code here
        # For example, stopping any running processes or threads

    def __del__(self):
        logging.info("CoolWidget is being destroyed")
        self.cleanup()


    