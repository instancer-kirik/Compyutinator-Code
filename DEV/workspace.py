import json
import os

class Workspace:
    def __init__(self, name, vault_path):
        self.name = name
        self.vault_path = vault_path
        self.filesets = {}
        self.active_fileset = None
        self.config_file = os.path.join(vault_path, f'.workspace_{name}.json')
        self.layout = None
        self.visible_docks = []
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.filesets = config.get('filesets', {})
                self.active_fileset = config.get('active_fileset')
        else:
            self.save_config()

    def save_config(self):
        config = {
            'filesets': self.filesets,
            'active_fileset': self.active_fileset
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

    def get_layout(self):
        return self.layout, self.visible_docks