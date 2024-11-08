from PyQt6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, 
                           QTreeWidgetItem, QVBoxLayout, QWidget, QLabel,
                           QPushButton, QHBoxLayout, QStatusBar)
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtCore import QTimer, Qt
import sys
import os
import subprocess
import psutil
import json
from datetime import datetime

class SystemViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Monitor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Create toolbar-like widget
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        
        # Add refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        toolbar_layout.addWidget(self.refresh_btn)
        
        # Add status label
        self.status_label = QLabel("Monitoring system...")
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addStretch()
        
        main_layout.addWidget(toolbar)
        
        # Create tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Component", "Details", "Status"])
        self.tree.setColumnWidth(0, 250)  # Set column widths
        self.tree.setColumnWidth(1, 600)
        self.tree.setAlternatingRowColors(True)
        main_layout.addWidget(self.tree)
        
        # Set up categories with icons
        self.categories = {
            "System Info": QTreeWidgetItem(["System Information"]),
            "Network Connections": QTreeWidgetItem(["Network Connections"]),
            "SSH Sessions": QTreeWidgetItem(["SSH Sessions"]),
            "System Services": QTreeWidgetItem(["System Services"]),
            "Startup Items": QTreeWidgetItem(["Startup Items"]),
            "Remote Access": QTreeWidgetItem(["Remote Access Tools"]),
            "Monitoring Tools": QTreeWidgetItem(["System Monitors"]),
            "Shell Config": QTreeWidgetItem(["Shell Configuration"]),
            "Boot Config": QTreeWidgetItem(["Boot Configuration"]),
            "Cron Jobs": QTreeWidgetItem(["Scheduled Tasks"]),
            "Version Managers": QTreeWidgetItem(["Version Managers"])
        }
        
        # Add categories to tree
        for category in self.categories.values():
            self.tree.addTopLevelItem(category)
        
        self.setCentralWidget(main_widget)
        
        # Add status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Set up refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000)  # Refresh every 5 seconds
        
        # Initial load
        self.load_data()

    def get_network_connections(self):
        connections = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                try:
                    process = psutil.Process(conn.pid) if conn.pid else None
                    connections.append({
                        'local_addr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A",
                        'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                        'status': conn.status,
                        'pid': conn.pid,
                        'process': process.name() if process else "Unknown",
                        'username': process.username() if process else "Unknown"
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.statusBar.showMessage(f"Error getting network connections: {e}")
        return connections

    def get_system_info(self):
        info = {}
        try:
            info['cpu'] = f"CPU Usage: {psutil.cpu_percent()}%"
            info['memory'] = f"Memory Usage: {psutil.virtual_memory().percent}%"
            info['disk'] = f"Disk Usage: {psutil.disk_usage('/').percent}%"
            info['boot_time'] = f"Up since: {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}"
            
            with open('/etc/os-release', 'r') as f:
                os_info = dict(line.strip().split('=', 1) for line in f if '=' in line)
            info['os'] = os_info.get('PRETTY_NAME', '').strip('"')
            
            info['kernel'] = subprocess.check_output(['uname', '-r'], text=True).strip()
        except Exception as e:
            self.statusBar.showMessage(f"Error getting system info: {e}")
        return info

    def refresh_data(self):
        try:
            self.status_label.setText(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.load_data()
            self.statusBar.showMessage("Data refreshed successfully", 3000)
        except Exception as e:
            self.statusBar.showMessage(f"Error refreshing data: {e}")

    def load_data(self):
        try:
            self.tree.setDisabled(True)
            
            # Clear existing items
            for category in self.categories.values():
                category.takeChildren()

            # Load system information
            sys_info = self.get_system_info()
            for key, value in sys_info.items():
                item = QTreeWidgetItem(self.categories["System Info"])
                item.setText(0, key.replace('_', ' ').title())
                item.setText(1, value)
                if 'usage' in key.lower():
                    usage = int(value.split('%')[0].split(':')[1])
                    if usage > 90:
                        item.setForeground(1, QColor("red"))
                    elif usage > 70:
                        item.setForeground(1, QColor("orange"))
                    else:
                        item.setForeground(1, QColor("green"))

            # Load network connections
            connections = self.get_network_connections()
            for conn in connections:
                item = QTreeWidgetItem(self.categories["Network Connections"])
                item.setText(0, conn['process'])
                item.setText(1, f"{conn['username']} | Local: {conn['local_addr']} → Remote: {conn['remote_addr']}")
                item.setText(2, conn['status'])
                
                if 'ESTABLISHED' in conn['status']:
                    item.setForeground(2, QColor("green"))
                elif 'LISTEN' in conn['status']:
                    item.setForeground(2, QColor("blue"))
                else:
                    item.setForeground(2, QColor("gray"))

            # Load services and other components
            self.load_services()
            self.load_startup_items()
            self.load_remote_access_tools()
            
            # Expand all categories
            self.tree.expandAll()
            
        except Exception as e:
            self.statusBar.showMessage(f"Error loading data: {e}")
        finally:
            self.tree.setDisabled(False)

    def load_services(self):
        try:
            result = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--no-pager', '--no-legend'],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if '.service' in line:
                    parts = line.split()
                    if parts:
                        item = QTreeWidgetItem(self.categories["System Services"])
                        item.setText(0, parts[0])  # Service name
                        item.setText(1, ' '.join(parts[1:3]))  # Load and active state
                        item.setText(2, parts[3] if len(parts) > 3 else "unknown")  # Sub state
                        
                        if 'running' in item.text(2).lower():
                            item.setForeground(2, QColor("green"))
                        elif 'failed' in item.text(2).lower():
                            item.setForeground(2, QColor("red"))
                        else:
                            item.setForeground(2, QColor("orange"))
        except Exception as e:
            self.statusBar.showMessage(f"Error loading services: {e}")

    def load_startup_items(self):
        try:
            autostart_paths = [
                os.path.expanduser("~/.config/autostart"),
                "/etc/xdg/autostart"
            ]
            for path in autostart_paths:
                if os.path.exists(path):
                    for item_name in os.listdir(path):
                        if item_name.endswith('.desktop'):
                            item = QTreeWidgetItem(self.categories["Startup Items"])
                            item.setText(0, item_name)
                            item.setText(1, path)
        except Exception as e:
            self.statusBar.showMessage(f"Error loading startup items: {e}")

    def load_remote_access_tools(self):
        tools = ["teamviewer", "anydesk", "vnc", "remmina", "x11vnc", "sshd"]
        try:
            for tool in tools:
                try:
                    output = subprocess.check_output(['pgrep', '-l', tool], text=True)
                    if output:
                        item = QTreeWidgetItem(self.categories["Remote Access"])
                        item.setText(0, tool.title())
                        item.setText(1, output.strip())
                        item.setText(2, "RUNNING")
                        item.setForeground(2, QColor("red"))
                except subprocess.CalledProcessError:
                    continue
        except Exception as e:
            self.statusBar.showMessage(f"Error checking remote access tools: {e}")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better cross-platform appearance
    viewer = SystemViewer()
    viewer.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()