import os
import json
import logging
from pathlib import Path
from DEV.workspace import Workspace
import tempfile

class VaultManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.app_config_dir = Path.home() / ".computinator_code"
        self.app_config_dir.mkdir(exist_ok=True)
        self.vaults_config_file = self.app_config_dir / "vaults_config.json"
        self.vaults = self.load_vaults_config()
        
        # Create a default vault if no vaults exist
        if not self.vaults["vaults"]:
            default_vault_path = self.app_config_dir / "default_vault"
            default_vault_name = self.add_vault_directory(str(default_vault_path), "Default Vault")
            self.set_default_vault(default_vault_name)
        
        self.current_vault = self.vaults.get("default")
        self.vault_path = self.vaults.get("vaults", {}).get(self.current_vault)
        
        if self.vault_path:
            self.initialize_vault(self.vault_path)
        else:
            logging.warning("No default vault set. Some features may be unavailable.")
    def get_config_file_path(self):
        return str(self.vaults_config_file)
    def get_current_vault_path(self):
        return self.vault_path
    def open_vault_config_file(self):
        config_file_path = self.get_config_file_path()
        if os.path.exists(config_file_path):
            os.startfile(config_file_path)
        else:
            logging.warning(f"Vault config file not found at {config_file_path}")

    def load_vaults_config(self):
        if self.vaults_config_file.exists():
            with open(self.vaults_config_file, 'r') as f:
                return json.load(f)
        return {"vaults": {}, "default": None}

    def save_vaults_config(self):
        with open(self.vaults_config_file, 'w') as f:
            json.dump(self.vaults, f, indent=4)

    def initialize_vault(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
        self.config_file = os.path.join(path, '.vault_config.json')
        self.index_file = os.path.join(path, '.vault_index.json')
        self.filesets_file = os.path.join(path, '.vault_filesets.json')
        
        # Create empty config and index files if they don't exist
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w') as f:
                json.dump({}, f)
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump({}, f)
        if not os.path.exists(self.filesets_file):
            with open(self.filesets_file, 'w') as f:
                json.dump({}, f)
        
        self.load_config()
        self.load_index()
        self.load_filesets()
        self.workspaces = {}
        self.load_workspaces()

    def add_vault_directory(self, path, name=None):
        if name is None:
            name = os.path.basename(path)

        # Check if a vault with this name already exists
        counter = 1
        original_name = name
        while name in self.vaults["vaults"]:
            name = f"{original_name}_{counter}"
            counter += 1

        if not os.path.exists(path):
            os.makedirs(path)
        
        self.vaults["vaults"][name] = path
        self.save_vaults_config()
        logging.info(f"Added new vault: {name} at {path}")
        return name  # Return the final name used

    def remove_vault_directory(self, name):
        if name not in self.vaults["vaults"]:
            logging.warning(f"Vault '{name}' does not exist.")
            return False
        
        del self.vaults["vaults"][name]
        if self.vaults["default"] == name:
            self.vaults["default"] = None
        self.save_vaults_config()
        logging.info(f"Removed vault: {name}")
        return True
    
    def rename_vault(self, old_name, new_name):
        if old_name in self.vaults["vaults"] and new_name not in self.vaults["vaults"]:
            self.vaults["vaults"][new_name] = self.vaults["vaults"].pop(old_name)
            if self.vaults["default_vault"] == old_name:
                self.vaults["default_vault"] = new_name
            self.save_vaults()
            return True
        return False
    def set_default_vault(self, name):
        if name not in self.vaults["vaults"]:
            logging.warning(f"Vault '{name}' does not exist.")
            return False
        
        self.vaults["default"] = name
        self.save_vaults_config()
        self.current_vault = name
        self.vault_path = self.vaults["vaults"][name]
        self.initialize_vault(self.vault_path)
        logging.info(f"Set default vault to: {name}")
        return True

    def switch_vault(self, name):
        if name not in self.vaults["vaults"]:
            logging.warning(f"Vault '{name}' does not exist.")
            return False
        
        self.current_vault = name
        self.vault_path = self.vaults["vaults"][name]
        self.initialize_vault(self.vault_path)
        logging.info(f"Switched to vault: {name}")
        return True

    def load_workspaces(self):
        if not self.vault_path:
            logging.warning("No vault path set. Cannot load workspaces.")
            return

        workspace_configs = [f for f in os.listdir(self.vault_path) if f.startswith('.workspace_') and f.endswith('.json')]
        for config in workspace_configs:
            name = config[10:-5]  # Remove '.workspace_' prefix and '.json' suffix
            self.workspaces[name] = Workspace(name, self.vault_path)
        self.active_workspace = self.get_config('active_workspace')

    def create_workspace(self, name):
        sanitized_name = Workspace.sanitize_name(name)
        if sanitized_name not in self.workspaces:
            self.workspaces[sanitized_name] = Workspace(sanitized_name, self.vault_path)
            self.set_active_workspace(sanitized_name)

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

    def load_filesets(self):
        if os.path.exists(self.filesets_file):
            with open(self.filesets_file, 'r') as f:
                self.filesets = json.load(f)
        else:
            self.filesets = {}
            self.save_filesets()

    def save_filesets(self):
        with open(self.filesets_file, 'w') as f:
            json.dump(self.filesets, f, indent=4)

    def create_fileset(self, name, files):
        if name not in self.filesets:
            self.filesets[name] = files
            self.save_filesets()
            return True
        return False

    def update_fileset(self, name, files):
        if name in self.filesets:
            self.filesets[name] = files
            self.save_filesets()
            return True
        return False

    def delete_fileset(self, name):
        if name in self.filesets:
            del self.filesets[name]
            self.save_filesets()
            return True
        return False
    def get_vault_path(self, name):
        return self.vaults["vaults"].get(name, None)
    def get_vault_name(self, path):
        for name, vault_path in self.vaults["vaults"].items():
            if vault_path == path:
                return name
        return None 
    def get_current_vault(self):
        return self.current_vault
    def get_fileset(self, name):
        return self.filesets.get(name, [])

    def get_all_filesets(self):
        return list(self.filesets.keys())

    def get_config(self, key, default=None):
        return self.vaults.get(key, default)

    def set_config(self, key, value):
        self.vaults[key] = value
        self.save_vaults_config()

    def get_index(self):
        return self.index

    def get_file_info(self, rel_path):
        return self.index.get(rel_path)

    def is_vault_set(self):
        return self.vault_path is not None

    def open_vault(self, path):
        if os.path.exists(path):
            self.vault_path = path
            self.config_file = os.path.join(self.vault_path, '.vault_config.json')
            self.index_file = os.path.join(self.vault_path, '.vault_index.json')
            self.filesets_file = os.path.join(self.vault_path, '.vault_filesets.json')
            self.load_config()
            self.load_index()
            self.load_filesets()
            self.load_workspaces()
            return True
        return False

    def switch_vault(self, path):
        if self.open_vault(path):
            # Update the settings
            self.settings_manager.set_vault_path(path)
            # Update the index for the new vault
            self.update_index()
            return True
        return False
    def get_vaults(self):
    # Implement this method to return a list of vault names
        # For example:
        return list(self.vaults.keys())