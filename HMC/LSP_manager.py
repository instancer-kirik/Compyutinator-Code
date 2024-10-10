import json
from PyQt6.QtCore import QObject, pyqtSignal, QProcess
import os
import ast
import logging

import logging

from PyQt6.QtCore import QObject, pyqtSignal, QThread
import logging
import os
import json
import ast

class LSPInitializationThread(QThread):
    initialization_complete = pyqtSignal()

    def __init__(self, lsp_manager):
        super().__init__()
        self.lsp_manager = lsp_manager

    def run(self):
        self.lsp_manager.start_lsp_server()
        self.lsp_manager.load_config()
        self.lsp_manager.index_project_imports()
        self.initialization_complete.emit()

class LSPManager(QObject):
    completionsReceived = pyqtSignal(list)
    importsIndexed = pyqtSignal(dict)
    referencesFound = pyqtSignal(list)
    symbolsReceived = pyqtSignal(list)

    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        logging.warning("Creating LSPManager instance")
        self.cccore = cccore
        self.process_id = None
        self.import_index = {}
        self.initialized = False

    def initialize(self):
        logging.warning("Starting LSPManager initialization")
        self.init_thread = LSPInitializationThread(self)
        self.init_thread.initialization_complete.connect(self.on_initialization_complete)
        self.init_thread.start()

    def on_initialization_complete(self):
        logging.warning("LSPManager initialization complete")
        self.initialized = True
        # Perform any post-initialization tasks here

    def is_initialized(self):
        return self.initialized

    def load_config(self):
        config_path = "NITTY_GRITTY/anakinls_config.json"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
            self.send_request("workspace/didChangeConfiguration", {"settings": config})
        else:
            logging.warning(f"LSP config file not found: {config_path}")

    def initialize_workspace(self):
        current_vault = self.cccore.vault_manager.get_current_vault()
        if current_vault:
            workspace_path = current_vault.path
            self.send_request("workspace/didChangeWorkspaceFolders", {
                "event": {
                    "added": [{"uri": f"file://{workspace_path}", "name": current_vault.name}],
                    "removed": []
                }
            })

    def on_vault_changed(self, new_vault_name):
        self.initialize_workspace()

    def index_project_imports(self):
        current_workspace = self.cccore.workspace_manager.get_active_workspace()
        if not current_workspace:
            return

        for root, _, files in os.walk(current_workspace.vault_path):
            for file in files:
                if file.endswith(('.py', '.js', '.html', '.css')):  # Add more extensions as needed
                    file_path = os.path.join(root, file)
                    self.index_file_imports(file_path)

        self.importsIndexed.emit(self.import_index)

    def index_file_imports(self, file_path):
        if file_path.endswith('.py'):
            self.index_python_imports(file_path)
        # TODO: Add methods for other file types as needed

    def index_python_imports(self, file_path):
        with open(file_path, 'r') as file:
            try:
                tree = ast.parse(file.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.import_index[alias.name] = f"import {alias.name}"
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module
                        for alias in node.names:
                            self.import_index[alias.name] = f"from {module} import {alias.name}"
            except SyntaxError:
                # Handle syntax errors in the file
                pass

    def get_import_suggestions(self, partial_import):
        return [import_stmt for name, import_stmt in self.import_index.items() 
                if partial_import.lower() in name.lower()]

    def start_lsp_server(self):
        try:
            command = "anakinls"
            self.process = self.cccore.process_manager.start_process(command, "LSP Server", capture_output=True)
            if self.process:
                self.process_id = self.process.processId()
                # Wait for the server to start (you might need to adjust this)
                self.process.waitForStarted(5000)  # Wait up to 5 seconds
                logging.info(f"LSP server started with PID: {self.process_id}")
            else:
                logging.error("Failed to start LSP server")
        except Exception as e:
            logging.error(f"Error starting LSP server: {e}")

    def send_request(self, method, params):
        if not hasattr(self, 'process') or not self.process:
            logging.error("LSP server process is not available")
            return

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        try:
            self.process.write(json.dumps(request).encode() + b'\n')
        except Exception as e:
            logging.error(f"Error sending request to LSP server: {e}")

    def handle_stdout(self):
        response = json.loads(self.process.stdout.readline().decode())
        if "result" in response:
            if response.get("method") == "textDocument/completion":
                self.handle_completion(response["result"]["items"])
            elif response.get("method") == "textDocument/references":
                self.handle_references(response["result"])
            elif response.get("method") == "textDocument/documentSymbol":
                self.handle_document_symbols(response["result"])

    def handle_completion(self, lsp_completions):
        import_suggestions = self.get_import_suggestions(self.last_completion_context)
        all_completions = lsp_completions + [{"label": s, "kind": 9} for s in import_suggestions]
        self.completionsReceived.emit(all_completions)

    def handle_references(self, references):
        self.referencesFound.emit(references)

    def handle_document_symbols(self, symbols):
        self.symbolsReceived.emit(symbols)

    def get_log_function_calls(self):
        current_workspace = self.cccore.workspace_manager.get_active_workspace()
        if not current_workspace:
            return []

        params = {
            "textDocument": {"uri": f"file://{current_workspace.vault_path}"},
            "query": "def.*log"
        }
        self.send_request("textDocument/documentSymbol", params)
        # The response will be handled in handle_stdout
        # You might need to implement a way to wait for and process this response

    def request_completions(self, file_uri, position):
        self.last_completion_context = position['character']
        params = {
            "textDocument": {"uri": file_uri},
            "position": position
        }
        self.send_request("textDocument/completion", params)

    def find_references(self, file_uri, position):
        params = {
            "textDocument": {"uri": file_uri},
            "position": position,
            "context": {"includeDeclaration": True}
        }
        self.send_request("textDocument/references", params)

    def cleanup(self):
        if hasattr(self, 'process') and self.process:
            self.cccore.process_manager.kill_process("LSP Server")
            self.process = None
            self.process_id = None

    def on_project_changed(self, new_project_name):
        current_project = self.cccore.project_manager.get_current_project()
        if current_project:
            project_path = current_project['path']
            self.send_request("workspace/didChangeConfiguration", {
                "settings": {
                    "python": {
                        "analysis": {
                            "extraPaths": [project_path]
                        }
                    }
                }
            })
