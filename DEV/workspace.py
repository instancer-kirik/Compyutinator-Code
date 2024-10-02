import json
import os

class Workspace:
    def __init__(self, name, vault_path, config=None):
        self.name = self.sanitize_name(name)
        self.vault_path = vault_path
        self.filesets = {}
        self.active_fileset = None
        self.layout = None
        self.visible_docks = []
        self.config_file = os.path.join(vault_path, f'.workspace_{self.name}.json')
        
        if config:
            self.load_from_config(config)
        else:
            self.load_config()

    def sanitize_name(self, name=None):
        if name is None:
            return 'Untitled'
        # Replace any characters that might cause issues in filenames
        return ''.join(c for c in name if c.isalnum() or c in ('_', '-', ' '))[:50]

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.filesets = config.get('filesets', {})
                self.active_fileset = config.get('active_fileset')
                self.layout = config.get('layout')
                self.visible_docks = config.get('visible_docks', [])
        else:
            self.save_config()

    def save_config(self):
        config = {
            'name': self.name,
            'filesets': self.filesets,
            'active_fileset': self.active_fileset,
            'layout': self.layout,
            'visible_docks': self.visible_docks
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def add_fileset(self, name, files):
        self.filesets[name] = files
        self.save_config()

    def remove_fileset(self, name):
        if name in self.filesets:
            del self.filesets[name]
            if self.active_fileset == name:
                self.active_fileset = None
            self.save_config()

    def set_active_fileset(self, name):
        if name in self.filesets:
            self.active_fileset = name
            self.save_config()

    def get_active_files(self):
        return self.filesets.get(self.active_fileset, [])

    def set_layout(self, layout, visible_docks):
        self.layout = layout
        self.visible_docks = visible_docks
        self.save_config()

    def get_layout(self):
        return self.layout, self.visible_docks

    def load_from_config(self, config):
        self.filesets = config.get('filesets', {})
        self.active_fileset = config.get('active_fileset')
        self.layout = config.get('layout')
        self.visible_docks = config.get('visible_docks', [])