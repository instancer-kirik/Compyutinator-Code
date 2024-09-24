import os
import json
import logging
from DEV.workspace import Workspace

import json
import logging
from DEV.workspace import Workspace

class VaultManager:
    def __init__(self, settings_manager):
        self.vault_path = settings_manager.get_vault_path()
        if not self.vault_path:
            raise ValueError("Vault path is not set.")
        if not os.path.exists(self.vault_path):
            os.makedirs(self.vault_path)
        self.config_file = os.path.join(self.vault_path, '.vault_config.json')
        self.index_file = os.path.join(self.vault_path, '.vault_index.json')
        self.workspaces = {}
        self.active_workspace = None
        self.load_config()
        self.load_index()
        self.load_workspaces()

    def load_workspaces(self):
        workspace_configs = [f for f in os.listdir(self.vault_path) if f.startswith('.workspace_') and f.endswith('.json')]
        for config in workspace_configs:
            name = config[10:-5]  # Remove '.workspace_' prefix and '.json' suffix
            self.workspaces[name] = Workspace(name, self.vault_path)
        self.active_workspace = self.get_config('active_workspace')

    def create_workspace(self, name):
        if name not in self.workspaces:
            self.workspaces[name] = Workspace(name, self.vault_path)
            self.set_active_workspace(name)

    def remove_workspace(self, name):
        if name in self.workspaces:
            del self.workspaces[name]
            if self.active_workspace == name:
                self.active_workspace = None
                self.set_config('active_workspace', None)

    def set_active_workspace(self, name):
        if name in self.workspaces:
            self.active_workspace = name
            self.set_config('active_workspace', name)

    def get_active_workspace(self):
        return self.workspaces.get(self.active_workspace)

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def load_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {}
            self.update_index()

    def update_index(self):
        self.index = {}
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith(('.md', '.txt', '.png', '.jpg', '.jpeg', '.gif')):
                    rel_path = os.path.relpath(os.path.join(root, file), self.vault_path)
                    self.index[rel_path] = {
                        'last_modified': os.path.getmtime(os.path.join(root, file)),
                        'type': 'image' if file.endswith(('.png', '.jpg', '.jpeg', '.gif')) else 'document'
                    }
        self.save_index()

    def save_index(self):
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=4)

    def get_config(self, key, default=None):
        return self.config.get(key, default)

    def set_config(self, key, value):
        self.config[key] = value
        self.save_config()

    def get_index(self):
        return self.index

    def get_file_info(self, rel_path):
        return self.index.get(rel_path)