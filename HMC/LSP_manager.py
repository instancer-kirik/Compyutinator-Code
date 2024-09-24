import json

from PyQt6.QtCore import QObject, pyqtSignal, QProcess

class LSPManager(QObject):
    completionsReceived = pyqtSignal(list)

    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.start("anakinls")
        
        with open("NITTY_GRITTY/anakinls_config.json", "r") as f:
            config = json.load(f)
        self.send_request("workspace/didChangeConfiguration", {"settings": config})

    def send_request(self, method, params):
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        self.process.write(json.dumps(request).encode() + b"\n")

    def handle_stdout(self):
        response = json.loads(self.process.readAllStandardOutput().data().decode())
        if "result" in response and response["method"] == "textDocument/completion":
            self.completionsReceived.emit(response["result"]["items"])

    def request_completions(self, file_uri, position):
        params = {
            "textDocument": {"uri": file_uri},
            "position": position
        }
        self.send_request("textDocument/completion", params)