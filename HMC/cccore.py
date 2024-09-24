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
        
        self.init_managers()

    def set_widget_manager(self, widget_manager):
        self.widget_manager = widget_manager
       
        self.editor_manager = EditorManager(self)
        self.file_manager = FileManager(self)  # Initialize FileManager after widget_manager is set
       
        
    def init_managers(self):
        self.db_manager = DatabaseManager('local')
        from HMC.ai_model_manager import ModelManager
        self.model_manager = ModelManager(self.settings_manager)
        self.download_manager = DownloadManager(self)
        self.theme_manager = ThemeManager(self)
        self.lexer_manager = LexerManager(self)
        self.lsp_manager = LSPManager(self)
        self.vault_manager = VaultManager(self.settings_manager)
        self.workspace_manager = WorkspaceManager(self.vault_manager)
        
        # Don't initialize editor_manager here

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