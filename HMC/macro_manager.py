import json
import os
from PyQt6.QtCore import QObject, pyqtSignal
import logging

class MacroManager(QObject):
    macro_updated = pyqtSignal()

    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.macros = {}
        self.macro_file = os.path.join(self.cccore.settings_manager.get_value('app_data_dir'), 'macros.json')
        self.load_macros()

    def load_macros(self):
        if os.path.exists(self.macro_file):
            with open(self.macro_file, 'r') as f:
                loaded_macros = json.load(f)
                # Convert the loaded data to the correct format
                self.macros = {name: [tuple(action) for action in actions] for name, actions in loaded_macros.items()}

    def save_macros(self):
        # Convert tuples to lists for JSON serialization
        serializable_macros = {name: [list(action) for action in actions] for name, actions in self.macros.items()}
        with open(self.macro_file, 'w') as f:
            json.dump(serializable_macros, f, indent=2)
        self.macro_updated.emit()

    def record_macro(self, name, actions):
        self.macros[name] = actions
        self.save_macros()

    def play_macro(self, name):
        if name in self.macros:
            for action in self.macros[name]:
                action_name, *args = action
                if hasattr(self.cccore.action_handlers, action_name):
                    method = getattr(self.cccore.action_handlers, action_name)
                    method(*args)
                else:
                    logging.warning(f"Action '{action_name}' not found in action handlers")

    def delete_macro(self, name):
        if name in self.macros:
            del self.macros[name]
            self.save_macros()

    def get_macro_list(self):
        return list(self.macros.keys())