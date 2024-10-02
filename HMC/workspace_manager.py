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
        self.active_workspace = None
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
            self.default_workspace_name = "Default"
            self.active_workspace_name = self.default_workspace_name
            self.save_config()
    def get_default_workspace(self, vault_path):
        if vault_path in self.workspaces:
            default_workspace = self.workspaces[vault_path].get('default')
            if default_workspace:
                return default_workspace
            elif self.workspaces[vault_path]:
                # Return the name of the first workspace if no default is set
                return next(iter(self.workspaces[vault_path].keys()))
        return None

    def save_config(self):
        config = {
            'default_workspace': self.default_workspace_name,
            'active_workspace': self.active_workspace_name if self.active_workspace else None
        }
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def load_workspaces(self):
        current_vault = self.cccore.vault_manager.get_current_vault()
        if current_vault is None:
            logging.warning("No current vault set. Cannot load workspaces.")
            return

        workspace_configs = [f for f in os.listdir(current_vault.path) if f.startswith('.workspace_') and f.endswith('.json')]
        for config_file in workspace_configs:
            workspace_name = config_file[11:-5]  # Remove '.workspace_' prefix and '.json' suffix
            config_path = os.path.join(current_vault.path, config_file)
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.workspaces[workspace_name] = Workspace(workspace_name, current_vault.path, config)

    def create_workspace(self, vault, name):
        if vault.path not in self.workspaces:
            self.workspaces[vault.path] = {}
        self.workspaces[vault.path][name] = Workspace(name, vault.path)
        self.set_active_workspace(vault.path, name)
        self.save_config()
        return self.workspaces[vault.path][name]

    def remove_workspace(self, vault_path, name):
        if vault_path in self.workspaces and name in self.workspaces[vault_path] and name != self.default_workspace_name:
            del self.workspaces[vault_path][name]
            if self.active_workspace and self.active_workspace.name == name:
                self.set_active_workspace(vault_path, self.default_workspace_name)
            self.save_config()

    def get_active_workspace(self):
        return self.active_workspace

    def set_active_workspace(self, vault_path, name):
        if vault_path in self.workspaces and name in self.workspaces[vault_path]:
            self.active_workspace = self.workspaces[vault_path][name]
            self.active_workspace_name = name
            self.save_config()
            return True
        return False

    def get_workspace(self, vault_path, name):
        return self.workspaces.get(vault_path, {}).get(name)

    def get_workspace_names(self, vault_path):
        return list(self.workspaces.get(vault_path, {}).keys())

    def get_workspaces(self, vault_path):
        return self.workspaces.get(vault_path, {})

    def on_vault_switch(self, new_vault_path):
        self.config_file = os.path.join(new_vault_path, "workspace_config.json")
        self.load_config()
        self.load_workspaces()
    
    def switch_workspace(self, vault_path, workspace_name):
        if self.set_active_workspace(vault_path, workspace_name):
            logging.info(f"Switched to workspace: {workspace_name}")
            return workspace_name
        else:
            logging.error(f"Workspace not found: {workspace_name}")
            return None

    def switch_workspace_by_path(self, workspace_path):
        vault_dir = os.path.dirname(workspace_path)
        workspace_name = os.path.basename(workspace_path)
        return self.switch_workspace(vault_dir, workspace_name)