import os
import json
from DEV.workspace import Workspace

class WorkspaceManager:
    def __init__(self, vault_manager):
        self.vault_manager = vault_manager
        self.workspaces = {}
        self.active_workspace = None
        self.load_workspaces()

    def load_workspaces(self):
        vault_path = self.vault_manager.vault_path
        workspace_configs = [f for f in os.listdir(vault_path) if f.startswith('.workspace_') and f.endswith('.json')]
        for config in workspace_configs:
            name = config[10:-5]  # Remove '.workspace_' prefix and '.json' suffix
            self.workspaces[name] = Workspace(name, vault_path)
        self.active_workspace = self.vault_manager.get_config('active_workspace')

    def create_workspace(self, name):
        if name not in self.workspaces:
            vault_path = self.vault_manager.vault_path
            self.workspaces[name] = Workspace(name, vault_path)
            self.set_active_workspace(name)

    def remove_workspace(self, name):
        if name in self.workspaces:
            del self.workspaces[name]
            if self.active_workspace == name:
                self.active_workspace = None
                self.vault_manager.set_config('active_workspace', None)

    def set_active_workspace(self, name):
        if name in self.workspaces:
            self.active_workspace = name
            self.vault_manager.set_config('active_workspace', name)

    def get_active_workspace(self):
        return self.workspaces.get(self.active_workspace)

    def get_workspace_names(self):
        return list(self.workspaces.keys())

    def get_workspace(self, name):
        return self.workspaces.get(name)

    def save_workspace(self, name):
        if name in self.workspaces:
            self.workspaces[name].save()

    def load_workspace(self, name):
        if name in self.workspaces:
            self.workspaces[name].load()
            self.set_active_workspace(name)

    def add_file_to_workspace(self, workspace_name, file_path):
        if workspace_name in self.workspaces:
            self.workspaces[workspace_name].add_file(file_path)

    def remove_file_from_workspace(self, workspace_name, file_path):
        if workspace_name in self.workspaces:
            self.workspaces[workspace_name].remove_file(file_path)

    def save_workspace_layout(self, name):
        if name in self.workspaces:
            layout = self.main_window.saveState()
            visible_docks = [dock_name for dock_name, dock in self.widget_manager.dock_widgets.items() if dock.isVisible()]
            self.workspaces[name].set_layout(layout, visible_docks)

    def load_workspace_layout(self, name):
        if name in self.workspaces:
            layout, visible_docks = self.workspaces[name].get_layout()
            if layout:
                self.main_window.restoreState(layout)
            for dock_name in self.widget_manager.dock_widgets:
                self.widget_manager.dock_widgets[dock_name].setVisible(dock_name in visible_docks)