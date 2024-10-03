from .vault_manager import VaultManager
from .file_manager import FileManager
from .download_manager import DownloadManager
from .theme_manager import ThemeManager
from AuraText.auratext.Core.Lexers import LexerManager
from .LSP_manager import LSPManager
from .settings_manager import SettingsManager
from .workspace_manager import WorkspaceManager
from NITTY_GRITTY.database import DatabaseManager, setup_local_database
from .editor_manager import EditorManager
from .cursor_manager import CursorManager
import logging
import os
import tempfile
from .file_manager import FileManager
from .workspace_manager import WorkspaceManager
from .project_manager import ProjectManager
from .build_manager import BuildManager
from GUX.radial_menu import RadialMenu
from .context_manager import ContextManager
from .environment_manager import EnvironmentManager
from .secrets_manager import SecretsManager
from .process_manager import ProcessManager
from AuraText.auratext.Core.window import AuraTextWindow
from .input_manager import InputManager
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QIcon
from AuraText.auratext.scripts.def_path import resource

from .font_manager import FontManager
from .thread_controller import ThreadController

class CCCore:  # referred to as mm in other files (auratext)
    def __init__(self, settings_manager, main_window=None):
        self.settings_manager = settings_manager
        self.main_window = main_window
        
        self.widget_manager = None
        self.auratext_windows = []
        self.editor_manager = None
        self.overlay = None
        self.workspace_manager = None
        self.project_manager = None
        self.secrets_manager = None
        self.env_manager = EnvironmentManager(self.settings_manager.get_value("environments_path", "./environments"))
        self.vault_manager = VaultManager(self.settings_manager, cccore=self)
        
        # Add debug logging
        logging.debug(f"Initializing CCCore. Default vault path: {self.settings_manager.get_value('app_data_dir')}")
        
        # Ensure default vault is created and set
        default_vault_path = os.path.join(self.settings_manager.get_value('app_data_dir'), 'default_vault')
        if not self.vault_manager.get_current_vault():
            logging.info(f"Creating default vault at: {default_vault_path}")
            self.vault_manager.create_vault("Default Vault", default_vault_path)
            self.vault_manager.set_current_vault("Default Vault")
        
        logging.debug(f"Current vault after initialization: {self.vault_manager.get_current_vault()}")
        
        self.process_manager = ProcessManager(self)
        self.build_manager = None
        self.file_manager = None
        self.font_manager = None
        self.input_manager = InputManager(model_path=None)  # Defaults to small en-us 0.15 model
        self.radial_menu = RadialMenu()
        self.radial_menu.optionSelected.connect(self.handle_radial_menu_selection)
        self.late_init_done = False
        self.vault_windows = {}  # Dictionary to store vault paths and their corresponding windows
        self.main_vault = None
        
        self.init_managers()
       

    def set_widget_manager(self, widget_manager):
        self.widget_manager = widget_manager
        # Instead of directly accessing auratext_window, let's create it if needed
     
        
    def set_auratext_window(self, window):
        self.auratext_windows.append(window)
        if self.editor_manager:
            self.editor_manager.window = window
        self.late_init()
        
    def init_managers(self):
        self.db_manager = DatabaseManager('local')
        from HMC.ai_model_manager import ModelManager
        self.model_manager = ModelManager(self.settings_manager)
        self.download_manager = DownloadManager(self)
        self.theme_manager = ThemeManager(self)
        self.lexer_manager = LexerManager(self)
        self.lsp_manager = LSPManager(self)
      #  self.vault_manager = VaultManager(self.settings_manager, self)
        self.cursor_manager = CursorManager(self)
        
        # The vault manager is already initialized in __init__, so we don't need to create it here
        # Just ensure that a current vault is set
        # if not self.vault_manager.get_current_vault():
        #     logging.warning("No current vault set. Creating a default vault.")
        #     default_vault_path = os.path.join(self.settings_manager.get_value('app_data_dir'), 'default_vault')
        #     self.vault_manager.create_vault("Default Vault", default_vault_path)
        #     self.vault_manager.set_current_vault("Default Vault")
        # else:
        #     logging.warning("No current vault set. Using the first available vault.")
        #     available_vaults = self.vault_manager.get_vaults()
        #     if available_vaults:
        #         self.vault_manager.set_current_vault(available_vaults[0])
        #     else:
        #         logging.error("No vaults available. Application may not function correctly.")
        logging.info(f"Current vault: {self.vault_manager.current_vault.name if self.vault_manager.current_vault else 'None'}")
       
        self.env_manager = EnvironmentManager(self.settings_manager.get_value("environments_path", "./environments"))
        self.secrets_manager = SecretsManager(self.settings_manager)
        self.project_manager = ProjectManager(self.settings_manager, self)
        self.build_manager = BuildManager(self)
        self.context_manager = ContextManager(self)
        self.file_manager = FileManager(self)
        self.workspace_manager = WorkspaceManager(self)
        # Initialize FontManagerWidget
        self.font_manager = FontManager()
      
    def late_init(self):
        if not self.late_init_done:
            self.file_manager = FileManager(self)
            self.editor_manager = EditorManager(self)
            self.editor_manager.set_current_window(self.main_window)
            self.late_init_done = True

    def show_radial_menu(self, pos, context):
        if not self.late_init_done:
            self.late_init()
        options = self.get_radial_menu_options(context)
        self.radial_menu.set_options(options)
        self.radial_menu.show_at(pos)

    def get_radial_menu_options(self, context):
        if context == "editor":
            return ["Code", "Markdown", "LaTeX", "Plain Text", "Comment", "Uncomment"]
        elif context == "file_explorer":
            return ["New File", "New Folder", "Rename", "Delete"]
        elif context == "tab_bar":
            return ["Close Tab", "Close Other Tabs", "Close All Tabs"]
        return ["Default Option 1", "Default Option 2"]

    def handle_radial_menu_selection(self, option):
        if not self.late_init_done:
            self.late_init()
        if option in ["Code", "Markdown", "LaTeX", "Plain Text"]:
            self.file_manager.handle_radial_selection(option)
        elif option == "Comment":
            self.editor_manager.comment_selection()
        elif option == "Uncomment":
            self.editor_manager.uncomment_selection()
        elif option == "New File":
            self.file_manager.new_document()
        elif option == "New Folder":
            self.file_manager.create_new_folder()
        elif option == "Rename":
            self.file_manager.rename_selected_item()
        elif option == "Delete":
            self.file_manager.delete_selected_item()
        elif option == "Close Tab":
            self.editor_manager.close_current_tab()
        elif option == "Close Other Tabs":
            self.editor_manager.close_other_tabs()
        elif option == "Close All Tabs":
            self.editor_manager.close_all_tabs()

    def create_auratext_window(self):
        new_window = self.widget_manager.create_auratext_window(self)
        self.editor_manager.set_current_window(new_window)
        current_vault = self.vault_manager.get_current_vault()
        if current_vault:
            new_window.set_vault(current_vault)
            self.auratext_windows.append(new_window)
        else:
            logging.warning("No current vault set. Creating window without a vault.")
        return new_window

    def get_vault_manager(self, directory):
        return self.vault_managers.get(directory)

    def get_auratext_windows(self):
        return self.auratext_windows

    def switch_workspace(self, vault_dir, workspace_name):
        if self.workspace_manager.set_active_workspace(vault_dir, workspace_name):
            for window in self.auratext_windows:
                window.on_workspace_switch(vault_dir, workspace_name)
            return True
        return False

    def notify_vault_switch(self, new_vault_path):
        for window in self.auratext_windows:
            window.on_vault_switch(new_vault_path)
        # Notify other components
        if self.editor_manager:
            self.editor_manager.on_vault_switch(new_vault_path)
        if self.file_manager:
            self.file_manager.on_vault_switch(new_vault_path)
        if self.workspace_manager:
            self.workspace_manager.on_vault_switch(new_vault_path)
       
    def set_active_vault(self, directory):
        if self.vault_manager.set_default_vault(directory):
            self.notify_vault_switch(directory)
            return True
        return False

    def get_active_vault_manager(self):
        return self.vault_managers.get(self.active_vault)

    def create_workspace(self, workspace_name):
        self.workspace_manager.create_workspace(workspace_name)

    def get_current_workspace(self):
        return self.workspace_manager.get_active_workspace()

    def set_overlay(self, overlay):
          self.overlay = overlay

    def open_vault(self, path):
        vault = self.vault_manager.get_vault(path)
        if vault:
            window = self.create_auratext_window()
            window.set_vault(vault)
            window.show()
        else:
            logging.error(f"Vault not found: {path}")

    def add_vault_directory(self, path, name=None):
        return self.vault_manager.add_vault_directory(path, name)

    def remove_vault_directory(self, name):
        return self.vault_manager.remove_vault_directory(name)

    def open_vault_config_file(self):
        config_file_path = self.vault_manager.get_config_file_path()
        if self.editor_manager:
            self.editor_manager.open_file(config_file_path)
        else:
            logging.warning("Editor manager not initialized. Cannot open config file.")

    def set_main_window(self, main_window):
        main_window.setWindowOpacity(0)
        self.main_window = main_window
        
        self.theme_manager.main_window = main_window
        self.widget_manager.set_main_window_and_create_docks(main_window)

    def create_vault_window(self, vault_path):
        if vault_path not in self.vault_windows:
            new_window = self.widget_manager.create_auratext_window(self)
            new_window.set_vault(vault_path)
            self.vault_windows[vault_path] = new_window
        return self.vault_windows[vault_path]

    def get_vault_window(self, vault_path):
        return self.vault_windows.get(vault_path)

    def set_main_vault(self, vault_path):
        self.main_vault = vault_path
        if self.main_window:
            self.main_window.set_vault(vault_path)

    def close_vault(self, vault_path):
        if vault_path in self.vault_windows:
            self.vault_windows[vault_path].close()
            del self.vault_windows[vault_path]

    def create_vault(self, name, path):
        return self.vault_manager.create_vault(name, path)

    def create_project(self, name, path, language, version):
        return self.project_manager.create_project(name, path, language, version)

    def create_workspace(self, vault, name):
        return self.workspace_manager.create_workspace(vault, name)
    
    def set_menu_manager(self, menu_manager):
        self.menu_manager = menu_manager
    def cleanup(self):
        logging.info("Starting CCCore cleanup")
        if hasattr(self, 'thread_controller'):
            self.thread_controller.shutdown()
        if hasattr(self, 'process_manager'):
            self.process_manager.cleanup_processes()
       # ... cleanup other managers ...
        if hasattr(self, 'lsp_manager'):
            self.lsp_manager.cleanup()
        logging.info("CCCore cleanup complete")
    def get_project_manager(self):
        return self.project_manager
    def get_vault_manager(self):
        return self.vault_manager
