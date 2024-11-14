from .vault_manager import VaultManager
from .file_manager import FileManager
from .download_manager import DownloadManager
from .theme_manager import ThemeManager
from AuraText.auratext.Core.Lexers import LexerManager
from .LSP_manager import LSPManager

from .workspace_manager import WorkspaceManager
from NITTY_GRITTY.database import DatabaseManager, setup_local_database
from .editor_manager import EditorManager
from .cursor_text_manager import CursorManager
import logging
import os
import tempfile
from HMC.mark_manager import MarkManager
from HMC.risk_manager import RiskManager
from .file_manager import FileManager
from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtCore import Qt
from .workspace_manager import WorkspaceManager
from GUX.fileset_manager_widget import FilesetManagerWidget
from HMC.projects.project_manager import ProjectManager
from .build_manager import BuildManager
from GUX.radial_menu import RadialMenu
from HMC.config_manager import ConfigManager
from .context_manager import ContextManager
from .environment_manager import EnvironmentManager
from .secrets_manager import SecretsManager
from .process_manager import ProcessManager
from AuraText.auratext.Core.window import AuraTextWindow
from .input_manager import InputManager
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QIcon
from AuraText.auratext.scripts.def_path import resource
from .ai_model_manager import AIMemoryManager
from .font_manager import FontManager
from .thread_controller import ThreadController
from .action_handlers import ActionHandlers
from PyQt6.QtWidgets import QApplication
import time
import logging
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from .macro_manager import MacroManager
from .menu_manager import MenuManager
from .notification_manager import NotificationManager
import transformers
import warnings
from .code_manager import CodeManager
from .ai_model_manager import ModelManager

class CCCore(QObject):  # referred to as mm in other files (auratext)
    lsp_manager_initialized = pyqtSignal()

    def __init__(self, config_manager):
        super().__init__()
        
        # Suppress HuggingFace messages
        transformers.logging.set_verbosity_error()
        warnings.filterwarnings('ignore', category=UserWarning, module='transformers')
        
        # Initialize core configuration
        self.config_manager = config_manager
        self.settings_manager = config_manager  # Add this line - use config_manager as settings_manager
        
        # Initialize managers that depend on configuration
        self.notification_manager = NotificationManager()
        self.vault_manager = VaultManager(self)
        self.env_manager = EnvironmentManager(self.config_manager.get_value('environments_path', './environments'))
        self.project_manager = None  # Will be initialized later
        self.secrets_manager = None  # Will be initialized later
        
        # Other initializations
        self.main_window = None
        self.main_window_set = False
        self._window_ref = None
        self.action_handlers = None
        self.menu_manager = None
        self.widget_manager = None
        
        self.auratext_windows = []
        self.editor_manager = None
        self.overlay = None
        self.workspace_manager = None
        self.project_manager = None
        self.secrets_manager = None
        self.macro_manager = MacroManager(self)
        self.vault_manager = VaultManager(self)
        self.ai_memory_manager = AIMemoryManager()
        # Add debug logging
        logging.debug(f"Initializing CCCore. Default vault path: {self.config_manager.get_value('app_data_dir')}")
        
        # Ensure default vault is created and set
        default_vault_path = os.path.join(self.config_manager.get_value('app_data_dir'), 'default_vault')
        if not self.vault_manager.get_current_vault():
            logging.info(f"Creating default vault at: {default_vault_path}")
            self.vault_manager.create_vault("Default Vault", default_vault_path)
            self.vault_manager.set_current_vault("Default Vault")
        
        logging.debug(f"Current vault after initialization: {self.vault_manager.get_current_vault()}")
        
        self.process_manager = ProcessManager(self)
        self.lsp_manager = None
        self.build_manager = None
        self.file_manager = None
        self.font_manager = None
        self.input_manager = InputManager(self, model_path=None)  # Defaults to small en-us 0.15 model
        self.radial_menu = RadialMenu()
        self.radial_menu.optionSelected.connect(self.handle_radial_menu_selection)
        self.late_init_done = False
        self.vault_windows = {}  # Dictionary to store vault paths and their corresponding windows
        self.main_vault = None
        logging.info(f"CCCore initialized with main vault: {self.main_vault}")
        self.notification_manager = NotificationManager()
        self.init_managers()
        logging.info("CCCore initialization complete")
        
    def set_widget_manager(self, widget_manager):
        self.widget_manager = widget_manager
        # Instead of directly accessing auratext_window, let's create it if needed
     
    def set_auratext_window(self, window):
        self.auratext_windows.append(window)
        if self.editor_manager:
            self.editor_manager.window = window
        self.late_init()
        
    def init_managers(self):
        """Initialize all managers in correct order"""
        try:
            logging.info("Initializing managers")
            
            # Core managers first
            self.code_manager = CodeManager(self)
            logging.info("Code manager initialized")
            
            self.file_manager = FileManager(self)
            logging.info("File manager initialized")
            
            # Model and context managers
            self.model_manager = ModelManager(self)
            self.context_manager = ContextManager(self, max_tokens=4000)
            logging.info(f"Context manager initialized with max tokens: {self.context_manager.max_tokens}")
            # Set up cross-references
            self.model_manager.setup_context_manager(self.context_manager)
            self.context_manager.setup_memory_manager(self.model_manager.memory_manager)
            
            self.project_manager = ProjectManager(self)
            
            # Build manager depends on project manager
            self.build_manager = BuildManager(self)
            
            # Font manager initialization
            self.font_manager = FontManager()
            
            # Thread controller
            self.thread_controller = ThreadController()
            logging.debug("All managers initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing managers: {e}")
            raise
     
        self.action_handlers = ActionHandlers(window=self.main_window, cccore=self)
        self.db_manager = DatabaseManager('local')
        self.download_manager = DownloadManager(self)
        self.theme_manager = ThemeManager(self)
        self.lexer_manager = LexerManager(self)
        self.cursor_manager = CursorManager(self)
        # Initialize notification manager if not already done
        if not hasattr(self, 'notification_manager'):
            from .notification_manager import NotificationManager
            self.notification_manager = NotificationManager()
        
        logging.info(f"Current vault: {self.vault_manager.current_vault.name if self.vault_manager.current_vault else 'None'}")
       
        self.env_manager = EnvironmentManager(self.config_manager.get_value("environments_path", "./environments"))
        self.secrets_manager = SecretsManager(self.config_manager)
        
        self.build_manager = BuildManager(self)
        self.workspace_manager = WorkspaceManager(self)
        # Initialize FontManagerWidget
        self.font_manager = FontManager()
        self.risk_manager = RiskManager(
            config_manager=self.config_manager,
            notification_manager=self.notification_manager,
            project_manager=self.project_manager,  # This will be None initially
            cccore=self
        )
        self.macro_manager = MacroManager(self)
        self.mark_manager = MarkManager(self)
    def late_init(self):
        if not self.late_init_done:
            try:
                # Initialize managers
                self.file_manager = FileManager(self)
                self.editor_manager = EditorManager(self)
                self.editor_manager.set_current_window(self.main_window)
                
                # Initialize menu manager if not already done
                if not hasattr(self, 'menu_manager'):
                    self.menu_manager = MenuManager(self.main_window, self)
                
                # Initialize LSP manager
                self.init_lsp_manager()
                
                # Late init editor manager
                self.editor_manager.late_init()
                
                # Add automatic project loading
                self.project_manager.load_default_project()
                
                # Ensure proper widget state
                if self.main_window:
                    self.main_window.raise_()
                    self.main_window.activateWindow()
                    
                    # Reset any problematic widgets
                    for widget in self.main_window.findChildren(QWidget):
                        if widget.cursor().shape() != Qt.CursorShape.ArrowCursor:
                            widget.setCursor(Qt.CursorShape.ArrowCursor)
                        if widget.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
                            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                    
                    # Show dashboard for loaded project
                    if hasattr(self, 'widget_manager'):
                        current_project = self.project_manager.get_current_project()
                        if current_project:
                            self.widget_manager.show_dashboard(current_project.name)
                
                self.late_init_done = True
                logging.info("CCCore late initialization complete")
                
            except Exception as e:
                logging.error(f"Error in late initialization: {e}")
    def init_lsp_manager(self):
        self.lsp_manager = LSPManager(self)
        self.lsp_manager.initialize()
        self.lsp_manager_initialized.emit()
        logging.info("LSP manager initialized and signal emitted")

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
        """Set the main window and initialize related components"""
        if self.main_window_set:
            logging.warning("Main window already set, skipping")
            return
            
        if main_window is None:
            logging.error("Attempted to set None as main window")
            return
            
        logging.info(f"Setting main window: {main_window}")
        self.main_window = main_window
        self._window_ref = main_window  # Keep strong reference
        
        
        # Set main window for managers
        if self.widget_manager:
            self.widget_manager.set_main_window_and_create_docks(main_window)
        if self.theme_manager:
            self.theme_manager.main_window = main_window
            
        # Mark as set
        self.main_window_set = True
        logging.info("Main window set successfully")
        
        # Post-setup initialization
        QTimer.singleShot(0, self.post_window_setup)
        
    def post_window_setup(self):
        """Ensure proper window setup after Qt event loop starts"""
        if self.main_window and self.main_window.isVisible():
            logging.info("Window already visible")
            return
            
        if self.main_window:
            self.main_window.show()
            logging.info("Window shown in post_window_setup")

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
        try:
            # Clean up risk manager first
            if hasattr(self, 'risk_manager'):
                try:
                    self.risk_manager.cleanup()
                except Exception as e:
                    logging.error(f"Error cleaning up risk manager: {e}")
                self.risk_manager = None
                
            # Then clean up other managers
            managers_to_cleanup = [
                'thread_controller', 'process_manager', 'lsp_manager',
                'file_manager', 'download_manager', 'build_manager',
                'widget_manager'  # Add widget manager to cleanup list
            ]
            
            for manager_name in managers_to_cleanup:
                if hasattr(self, manager_name):
                    try:
                        manager = getattr(self, manager_name)
                        if manager and hasattr(manager, 'cleanup'):
                            logging.info(f"Cleaning up {manager_name}")
                            manager.cleanup()
                    except Exception as e:
                        logging.error(f"Error cleaning up {manager_name}: {e}")
                    finally:
                        setattr(self, manager_name, None)
                        
        except Exception as e:
            logging.error(f"Error during CCCore cleanup: {e}")
        finally:
            logging.info("CCCore cleanup complete")
    def get_project_manager(self):
        return self.project_manager
    def get_vault_manager(self):
        return self.vault_manager
    def get_current_window(self):
        return self.editor_manager.current_window
    def start_macro_recording(self, name):
        self.action_handlers.start_macro_recording(name)
        logging.info(f"Started recording macro: {name}")

    def stop_macro_recording(self):
        actions = self.action_handlers.stop_macro_recording()
        if actions:
            self.macro_manager.record_macro(self.action_handlers.current_macro_name, actions)
            logging.info(f"Recorded macro: {self.action_handlers.current_macro_name} with {len(actions)} actions")
        else:
            logging.warning("No actions recorded in the macro")

    def play_macro(self, name):
        logging.info(f"Playing macro: {name}")
        self.macro_manager.play_macro(name)

    def get_macro_list(self):
        return self.macro_manager.get_macro_list()

    def delete_macro(self, name):
        self.macro_manager.delete_macro(name)

    def get_workspaces(self):
        """Get list of workspaces for current vault"""
        current_vault = self.vault_manager.get_current_vault()
        if current_vault and self.workspace_manager:
            return self.workspace_manager.get_workspace_names(current_vault.path)
        return []

    def get_current_workspace(self):
        """Get current workspace name"""
        current_vault = self.vault_manager.get_current_vault()
        if current_vault and self.workspace_manager:
            return self.workspace_manager.active_workspaces.get(current_vault.path)
        return None

    def set_current_workspace(self, workspace_name):
        """Set current workspace"""
        current_vault = self.vault_manager.get_current_vault()
        if current_vault and self.workspace_manager:
            return self.workspace_manager.set_active_workspace(current_vault.path, workspace_name)
        return False

    def set_current_project(self, project_data):
        """Set the current project in the project manager."""
        try:
            if isinstance(project_data, dict):
                # Convert dict to Project object
                from HMC.projects.project_manager import Project
                project = Project(
                    name=project_data['name'],
                    path=project_data['path'],
                    project_type=project_data['type'],
                    created_at=project_data['created_at'],
                    updated_at=project_data['updated_at']
                )
            else:
                project = project_data
                
            if self.project_manager:
                self.project_manager.current_project = project
                logging.info(f"Current project set to: {project.name}")
                # Update the dashboard if it exists
                if hasattr(self, 'project_dashboard'):
                    self.project_dashboard.update_dashboard(project)
            else:
                logging.error("Project manager is not initialized.")
                
        except Exception as e:
            logging.error(f"Error setting project@cccore: {e}")
    
    def set_current_project(self, project_name):
        """Set the current project in the project manager."""
        if self.project_manager:
            self.project_manager.current_project = project_name
            logging.info(f"Current project set to: {project_name}")
            # Update the dashboard if it exists
            if hasattr(self, 'project_dashboard'):
                self.project_dashboard.update_dashboard(project_name)
        else:
            logging.error("Project manager is not initialized.")

    