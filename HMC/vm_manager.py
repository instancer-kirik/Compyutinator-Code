import subprocess
import json
import os
import websockets
import asyncio
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel, QComboBox
from PyQt6.QtCore import pyqtSignal, QThread
from PyQt6.QtCore import QObject

class DevPodManager(QObject):
    workspace_status_changed = pyqtSignal(str, str)  # Workspace name, new status
    message_received = pyqtSignal(str, str)  # Workspace name, message

    def __init__(self, vault_manager):
        super().__init__()
        self.vault_manager = vault_manager
        self.workspace_folder = self.vault_manager.get_workspace_folder()
        self.websocket_servers = {}

    def run_command(self, command):
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print(f"Error running command: {result.stderr}")
        return result.stdout

    def list_workspaces(self):
        output = self.run_command("devpod list -o json")
        return json.loads(output) if output else []

    def create_workspace(self, name, provider="docker"):
        # Add WebSocket server setup to the DevPod workspace
        websocket_port = self._get_available_port()
        self.run_command(f"devpod up {name} --provider {provider} "
                         f"--env WEBSOCKET_PORT={websocket_port}")
        self._start_websocket_server(name, websocket_port)
        self.workspace_status_changed.emit(name, "created")

    def _get_available_port(self):
        # Implement logic to find an available port
        pass

    def _start_websocket_server(self, name, port):
        server = WebSocketServer(self, name, port)
        self.websocket_servers[name] = server
        server.start()

    def send_message_to_workspace(self, name, message):
        if name in self.websocket_servers:
            self.websocket_servers[name].send_message(message)

    def start_workspace(self, name):
        self.run_command(f"devpod up {name}")

    def stop_workspace(self, name):
        self.run_command(f"devpod stop {name}")

    def delete_workspace(self, name):
        self.run_command(f"devpod delete {name}")

    def get_workspace_state(self, name):
        workspaces = self.list_workspaces()
        for workspace in workspaces:
            if workspace['name'] == name:
                return workspace['status']
        return "Not Found"

    def run_command_in_workspace(self, name, command):
        return self.run_command(f"devpod exec {name} -- {command}")

class WebSocketServer(QThread):
    def __init__(self, manager, workspace_name, port):
        super().__init__()
        self.manager = manager
        self.workspace_name = workspace_name
        self.port = port
        self.websocket = None

    def run(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        start_server = websockets.serve(self.handler, "localhost", self.port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    async def handler(self, websocket, path):
        self.websocket = websocket
        try:
            async for message in websocket:
                self.manager.message_received.emit(self.workspace_name, message)
        finally:
            self.websocket = None

    def send_message(self, message):
        if self.websocket:
            asyncio.run(self.websocket.send(message))

class VMManagerWidget(QWidget):
    workspace_status_changed = pyqtSignal(str, str)  # Workspace name, new status

    def __init__(self, vault_manager):
        super().__init__()
        self.devpod_manager = DevPodManager(vault_manager)
        self.devpod_manager.workspace_status_changed.connect(self.on_workspace_status_changed)
        self.devpod_manager.message_received.connect(self.on_message_received)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Workspace List
        self.workspace_list = QListWidget()
        layout.addWidget(QLabel("Workspaces:"))
        layout.addWidget(self.workspace_list)

        # Workspace Controls
        controls_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create Workspace")
        self.start_btn = QPushButton("Start Workspace")
        self.stop_btn = QPushButton("Stop Workspace")
        controls_layout.addWidget(self.create_btn)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        layout.addLayout(controls_layout)

        # Workspace Creation inputs
        create_layout = QHBoxLayout()
        self.workspace_name_input = QLineEdit()
        self.workspace_name_input.setPlaceholderText("Workspace Name")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["docker", "virtualbox", "kubernetes"])
        create_layout.addWidget(self.workspace_name_input)
        create_layout.addWidget(self.provider_combo)
        layout.addLayout(create_layout)

        # Add message input and send button
        self.message_input = QLineEdit()
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        message_layout = QHBoxLayout()
        message_layout.addWidget(self.message_input)
        message_layout.addWidget(self.send_button)
        layout.addLayout(message_layout)

        self.setLayout(layout)

        # Connect signals
        self.create_btn.clicked.connect(self.create_workspace)
        self.start_btn.clicked.connect(self.start_workspace)
        self.stop_btn.clicked.connect(self.stop_workspace)
        self.workspace_list.itemSelectionChanged.connect(self.update_buttons)

        self.update_workspace_list()

    def create_workspace(self):
        workspace_name = self.workspace_name_input.text()
        provider = self.provider_combo.currentText()
        self.devpod_manager.create_workspace(workspace_name, provider)
        self.update_workspace_list()
        self.workspace_status_changed.emit(workspace_name, "created")

    def start_workspace(self):
        selected_items = self.workspace_list.selectedItems()
        if selected_items:
            workspace_name = selected_items[0].text().split(" ")[0]
            self.devpod_manager.start_workspace(workspace_name)
            self.update_workspace_list()
            self.workspace_status_changed.emit(workspace_name, "running")

    def stop_workspace(self):
        selected_items = self.workspace_list.selectedItems()
        if selected_items:
            workspace_name = selected_items[0].text().split(" ")[0]
            self.devpod_manager.stop_workspace(workspace_name)
            self.update_workspace_list()
            self.workspace_status_changed.emit(workspace_name, "stopped")

    def update_workspace_list(self):
        self.workspace_list.clear()
        for workspace in self.devpod_manager.list_workspaces():
            self.workspace_list.addItem(f"{workspace['name']} ({workspace['status']})")

    def update_buttons(self):
        selected_items = self.workspace_list.selectedItems()
        if selected_items:
            workspace_name = selected_items[0].text().split(" ")[0]
            state = self.devpod_manager.get_workspace_state(workspace_name)
            self.start_btn.setEnabled(state != "Running")
            self.stop_btn.setEnabled(state == "Running")
        else:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    def send_message(self):
        selected_items = self.workspace_list.selectedItems()
        if selected_items:
            workspace_name = selected_items[0].text().split(" ")[0]
            message = self.message_input.text()
            self.devpod_manager.send_message_to_workspace(workspace_name, message)
            self.message_input.clear()

    def on_workspace_status_changed(self, workspace_name, status):
        self.update_workspace_list()

    def on_message_received(self, workspace_name, message):
        print(f"Message from {workspace_name}: {message}")
        # Handle the received message (e.g., update UI, process command, etc.)

# Example usage
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    from HMC.vault_manager import VaultManager

    app = QApplication(sys.argv)
    vault_manager = VaultManager()  # You'll need to properly initialize this
    vm_widget = VMManagerWidget(vault_manager)
    vm_widget.show()
    sys.exit(app.exec())
