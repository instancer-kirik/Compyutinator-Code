from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QMessageBox
import httpx

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.token = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)
        
        layout.addLayout(form)
        
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)

    async def handle_login(self):
        """Handle login and token retrieval"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.parent().settings_manager.get_setting('api_url')}/api/login",
                    json={
                        "username": self.username_edit.text(),
                        "password": self.password_edit.text()
                    }
                )
                
                if response.status_code == 200:
                    self.token = response.json().get("token")
                    self.accept()
                else:
                    self.show_error("Login failed")
                    
        except Exception as e:
            self.show_error(f"Login error: {str(e)}")

    def show_error(self, message: str):
        """Show error message"""
        QMessageBox.critical(self, "Login Error", message) 