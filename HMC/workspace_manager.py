import os
import json
from DEV.workspace import Workspace
import logging
import tempfile
##  Vaults:
# A vault is the top-level container in your application.
# It represents a directory on the file system where all related data is stored.
# Each vault has its own configuration, including workspaces and filesets.
## Workspaces:
# Workspaces exist within a vault.
# They represent different contexts or projects within the same vault.
# Each workspace can have its own set of open files, settings, and potentially its own filesets.
## Filesets:
# Filesets are collections of files within a vault.
# They are typically stored in the vault's configuration and can be associated with specific workspaces or be vault-wide.
class WorkspaceManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.workspaces = {}
        self.active_workspace_name = None
        self.default_workspace_name = "Default"
        
        self.config_file = os.path.join(self.cccore.vault_manager.get_current_vault_path() or tempfile.gettempdir(), "workspace_config.json")
        
        self.load_config()
        self.load_workspaces()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.default_workspace_name = config.get('default_workspace', "Default")
                self.active_workspace_name = config.get('active_workspace', self.default_workspace_name)
        else:
            self.save_config()

    def save_config(self):
        config = {
            'default_workspace': self.default_workspace_name,
            'active_workspace': self.active_workspace_name
        }
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def load_workspaces(self):
        if self.cccore.vault_manager.vault_path:
            workspace_configs = [f for f in os.listdir(self.cccore.vault_manager.vault_path) if f.startswith('.workspace_') and f.endswith('.json')]
            for config in workspace_configs:
                name = config[10:-5]  # Remove '.workspace_' prefix and '.json' suffix
                self.workspaces[name] = Workspace(name, self.cccore.vault_manager.vault_path)
        else:
            logging.warning("No vault path set. Unable to load workspaces.")

        if self.default_workspace_name not in self.workspaces:
            self.create_workspace(self.default_workspace_name)
        
        if self.active_workspace_name not in self.workspaces:
            self.set_active_workspace(self.default_workspace_name)

    def create_workspace(self, name):
        sanitized_name = Workspace.sanitize_name(name)
        if sanitized_name not in self.workspaces:
            vault_path = self.cccore.vault_manager.vault_path or tempfile.gettempdir()
            self.workspaces[sanitized_name] = Workspace(sanitized_name, vault_path)
            self.set_active_workspace(sanitized_name)
            self.save_config()

    def remove_workspace(self, name):
        if name in self.workspaces and name != self.default_workspace_name:
            del self.workspaces[name]
            if self.active_workspace_name == name:
                self.set_active_workspace(self.default_workspace_name)
            self.save_config()

    def get_active_workspace(self):
        return self.workspaces.get(self.active_workspace_name)

    def set_active_workspace(self, name):
        if name in self.workspaces:
            self.active_workspace_name = name
            self.save_config()

    def get_workspace_names(self):
        return list(self.workspaces.keys())

    def get_workspaces(self):
        return self.workspaces

    def on_vault_switch(self, new_vault_path):
        self.config_file = os.path.join(new_vault_path, "workspace_config.json")
        self.load_config()
        self.load_workspaces()