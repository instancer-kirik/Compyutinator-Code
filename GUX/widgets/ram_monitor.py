import sys
import psutil
import gc
import logging
import tracemalloc
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, 
                            QComboBox, QSpinBox, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

class RAMMonitor(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RAM Usage Monitor")
        self.resize(800, 600)
        
        # Initialize tracemalloc for Python object tracking
        tracemalloc.start()
        
        # Setup UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.setup_ui()
        self.setup_timers()
        
    def setup_ui(self):
        """Initialize the UI components"""
        # System RAM Overview
        self.system_ram_bar = QProgressBar()
        self.system_ram_label = QLabel("System RAM Usage:")
        self.layout.addWidget(self.system_ram_label)
        self.layout.addWidget(self.system_ram_bar)
        
        # Process Selection
        self.process_combo = QComboBox()
        self.process_combo.setMaximumWidth(300)
        self.refresh_btn = QPushButton("Refresh Processes")
        self.refresh_btn.clicked.connect(self.refresh_processes)
        
        process_layout = QHBoxLayout()
        process_layout.addWidget(QLabel("Select Process:"))
        process_layout.addWidget(self.process_combo)
        process_layout.addWidget(self.refresh_btn)
        process_layout.addStretch()
        self.layout.addLayout(process_layout)
        
        # Memory Tree View
        self.memory_tree = QTreeWidget()
        self.memory_tree.setHeaderLabels(["Name", "Memory Usage", "Type", "Details"])
        self.memory_tree.setColumnWidth(0, 250)
        self.memory_tree.setColumnWidth(1, 150)
        self.layout.addWidget(self.memory_tree)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        self.track_btn = QPushButton("Track Python Objects")
        self.track_btn.clicked.connect(self.track_python_objects)
        self.clear_btn = QPushButton("Clear Tracking")
        self.clear_btn.clicked.connect(self.clear_tracking)
        
        button_layout.addWidget(self.track_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        self.layout.addLayout(button_layout)
        
        # Update interval control
        interval_layout = QHBoxLayout()
        self.update_interval = QSpinBox()
        self.update_interval.setRange(1, 60)
        self.update_interval.setValue(5)
        self.update_interval.valueChanged.connect(self.update_timer_interval)
        
        interval_layout.addWidget(QLabel("Update Interval (seconds):"))
        interval_layout.addWidget(self.update_interval)
        interval_layout.addStretch()
        self.layout.addLayout(interval_layout)
        
        # Initial process list
        self.refresh_processes()
        
    def setup_timers(self):
        """Setup update timers"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(5000)  # 5 second default
        
    def update_timer_interval(self):
        """Update the refresh timer interval"""
        interval = self.update_interval.value() * 1000
        self.update_timer.setInterval(interval)
        
    def refresh_processes(self):
        """Refresh the process list"""
        self.process_combo.clear()
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                proc_info = proc.info
                if proc_info['memory_percent'] > 0.1:  # Filter out tiny processes
                    self.process_combo.addItem(
                        f"{proc_info['name']} (PID: {proc_info['pid']}) - {proc_info['memory_percent']:.1f}%",
                        proc_info['pid']
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
    def update_display(self):
        """Update the display with current memory usage"""
        try:
            # Update system RAM
            mem = psutil.virtual_memory()
            self.system_ram_bar.setValue(mem.percent)
            self.system_ram_bar.setFormat(f"{mem.percent:.1f}% ({mem.used / 1024**3:.1f}GB / {mem.total / 1024**3:.1f}GB)")
            
            # Update process info
            if self.process_combo.currentData():
                pid = self.process_combo.currentData()
                try:
                    proc = psutil.Process(pid)
                    proc_item = QTreeWidgetItem(["Process", f"{proc.memory_info().rss / 1024**2:.1f} MB", 
                                               proc.name(), f"PID: {pid}"])
                    self.update_tree_item(proc_item)
                except psutil.NoSuchProcess:
                    pass
                    
        except Exception as e:
            logging.error(f"Error updating RAM display: {e}")
            
    def track_python_objects(self):
        """Track Python object memory usage"""
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        # Clear existing items
        self.memory_tree.clear()
        
        # Add Python objects
        python_root = QTreeWidgetItem(["Python Objects", "", "", ""])
        self.memory_tree.addTopLevelItem(python_root)
        
        for stat in top_stats[:25]:  # Show top 25 memory users
            size_mb = stat.size / 1024 / 1024
            item = QTreeWidgetItem([
                stat.traceback[-1].filename,
                f"{size_mb:.1f} MB",
                "Python Object",
                f"Line {stat.traceback[-1].lineno}"
            ])
            python_root.addChild(item)
            
            if size_mb > 100:  # Highlight large objects
                item.setForeground(1, QColor("red"))
            elif size_mb > 50:
                item.setForeground(1, QColor("orange"))
                
        python_root.setExpanded(True)
        
    def clear_tracking(self):
        """Clear memory tracking data"""
        self.memory_tree.clear()
        gc.collect()  # Force garbage collection
        
    def update_tree_item(self, item: QTreeWidgetItem):
        """Update or add an item to the tree"""
        found = self.memory_tree.findItems(item.text(0), Qt.MatchFlag.MatchExactly, 0)
        if found:
            found[0].setText(1, item.text(1))
            found[0].setText(3, item.text(3))
        else:
            self.memory_tree.addTopLevelItem(item)
            
    def closeEvent(self, event):
        """Clean up when closing"""
        tracemalloc.stop()
        super().closeEvent(event) 