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
from .project_manager import ProjectManager
from .build_manager import BuildManager
from GUX.radial_menu import RadialMenu
from .context_manager import ContextManager
from .environment_manager import EnvironmentManager
from .secrets_manager import SecretsManager
from AuraText.auratext.Core.window import AuraTextWindow
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QIcon
from AuraText.auratext.scripts.def_path import resource

class CCCore:  # referred to as mm in other files (auratext)
    def __init__(self, settings_manager, main_window=None):
        self.settings_manager = settings_manager
        self.main_window = main_window
        self.widget_manager = None
        self.auratext_window = None
        self.editor_manager = None
        self.overlay = None
        self.vault_manager = None
        self.workspace_manager = None
        self.secrets_manager = None
        self.env_manager = EnvironmentManager(self.settings_manager.get_value("environments_path", "./environments"))
        self.project_manager = None
        self.build_manager = None
        self.radial_menu = RadialMenu()
        self.radial_menu.optionSelected.connect(self.handle_radial_menu_selection)
        self.late_init_done = False
        
        self.init_managers()
       

    def set_widget_manager(self, widget_manager):
        self.widget_manager = widget_manager
        self.auratext_window = self.widget_manager.auratext_window
        logging.info(f"AuraTextWindow set: {self.auratext_window}")
        logging.info(f"tab_widget exists: {hasattr(self.auratext_window, 'tab_widget')}")
        
    def set_auratext_window(self, window):
        self.auratext_window = window
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
        self.vault_manager = VaultManager(self.settings_manager)
        self.cursor_manager = CursorManager(self)
        # Ensure there's a valid vault path before initializing WorkspaceManager
        if not self.vault_manager.vault_path:
            logging.warning("No default vault set. Creating a temporary vault.")
            temp_vault = os.path.join(tempfile.gettempdir(), 'temp_vault')
            os.makedirs(temp_vault, exist_ok=True)
            self.vault_manager.set_default_vault(temp_vault)
        self.env_manager = EnvironmentManager(self.settings_manager.get_value("environments_path", "./environments"))
        self.secrets_manager = SecretsManager(self.settings_manager)
        
        self.project_manager = ProjectManager(self.settings_manager, self)

        self.build_manager = BuildManager(self)
        self.context_manager = ContextManager(self)

    def late_init(self):
        if not self.late_init_done:
            self.file_manager = FileManager(self)
            self.editor_manager = EditorManager(self)
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

    def switch_workspace(self, workspace_name):
        self.workspace_manager.set_active_workspace(workspace_name)

    def get_vault_manager(self, directory):
        return self.vault_managers.get(directory)

    def set_active_vault(self, directory):
        if directory in self.vault_managers:
            self.active_vault = directory
            self.settings_manager.set_value("default_vault", directory)
            return True
        return False

    def get_active_vault_manager(self):
        return self.vault_managers.get(self.active_vault)

    def switch_workspace(self, workspace_name):
        self.workspace_manager.set_active_workspace(workspace_name)
        return True

    def create_workspace(self, workspace_name):
        self.workspace_manager.create_workspace(workspace_name)

    def get_current_workspace(self):
        return self.workspace_manager.get_active_workspace()

    def set_overlay(self, overlay):
          self.overlay = overlay

    def open_vault(self, path):
        return self.vault_manager.open_vault(path)

    def notify_vault_switch(self, new_vault_path):
        # Update components that need to know about the vault switch
        if self.editor_manager:
            self.editor_manager.on_vault_switch(new_vault_path)
        if self.auratext_window:
            self.auratext_window.on_vault_switch(new_vault_path)
        # Add other components as needed

    def add_vault_directory(self, path, name=None):
        return self.vault_manager.add_vault_directory(path, name)

    def remove_vault_directory(self, name):
        return self.vault_manager.remove_vault_directory(name)

    def set_default_vault(self, name):
        return self.vault_manager.set_default_vault(name)

    def switch_vault(self, name):
        if self.vault_manager.switch_vault(name):
            new_vault_path = self.vault_manager.vault_path
            self.workspace_manager.on_vault_switch(new_vault_path)
            self.notify_vault_switch(new_vault_path)
            return True
        return False

    def open_vault_config_file(self):
        config_file_path = self.vault_manager.get_config_file_path()
        if self.editor_manager:
            self.editor_manager.open_file(config_file_path)
        else:
            logging.warning("Editor manager not initialized. Cannot open config file.")

    def set_main_window(self, main_window):
        self.main_window = main_window
        self.theme_manager.main_window = main_window
        self.widget_manager.set_main_window_and_create_docks(main_window)

    def create_auratext_window(self):
        if self.auratext_window is None:
            self.auratext_window = AuraTextWindow(self)
        return self.auratext_window

    class FileExplorerWidget(QWidget):
        def __init__(self, cccore):
            super().__init__()
            self.cccore = cccore
            self.setWindowTitle("File Explorer")
            self.setGeometry(100, 100, 800, 600)
            self.setStyleSheet("background-color: #282828; color: #FFFFFF;")
            self.setWindowIcon(QIcon(resource(r"../media/terminal/new.svg")))
            self.setWindowIcon(QIcon(resource(r"../media/terminal/remove.svg")))
            self.setWindowIcon(QIcon(resource(r"../media/terminal/remove.svg")))
            self.setWindowIcon(QIcon(resource(r"../media/terminal/remove.svg")))
            self.setWindowIcon(QIcon(resource(r"../media/terminal/remove.svg")))
            
