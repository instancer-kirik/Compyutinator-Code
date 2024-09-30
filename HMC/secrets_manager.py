import os
import json
from cryptography.fernet import Fernet
#https://www.youtube.com/watch?v=151-LPzcrjAv
#
#Pinned by Scholastum Provost
#@whisper8742
#10 days ago
#I think sometimes, the most merciful thing about the human mind, is it's inability to correlate it's contents.
#
#
class SecretsManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.secrets_file = self.settings_manager.get_value("secrets_file", "secrets.enc")
        self.key_file = self.settings_manager.get_value("key_file", "secret.key")
        self.fernet = self._load_or_create_key()

    def _load_or_create_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as key_file:
                key = key_file.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as key_file:
                key_file.write(key)
        return Fernet(key)

    def set_secret(self, key, value):
        secrets = self._load_secrets()
        secrets[key] = value
        self._save_secrets(secrets)

    def get_secret(self, key, default=None):
        secrets = self._load_secrets()
        return secrets.get(key, default)

    def _load_secrets(self):
        if os.path.exists(self.secrets_file):
            with open(self.secrets_file, "rb") as file:
                encrypted_data = file.read()
                decrypted_data = self.fernet.decrypt(encrypted_data)
                return json.loads(decrypted_data)
        return {}

    def _save_secrets(self, secrets):
        encrypted_data = self.fernet.encrypt(json.dumps(secrets).encode())
        with open(self.secrets_file, "wb") as file:
            file.write(encrypted_data)