import sys
import os

# Add the AuraText directory to the Python path
auratext_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'AuraText')
sys.path.append(auratext_dir)

from PyQt6.QtWidgets import  QVBoxLayout, QDockWidget, QWidget, QSlider, QComboBox, QLabel, QTabWidget, QSizePolicy, QToolBar, QDialog
import json
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QSettings, QByteArray, QTimer
from NITTY_GRITTY.big_links import SymbolicLinkerWidget
from GUX.file_explorer import FileExplorerWidget
from GUX.code_editor import CodeEditorWidget
from HMC.process_manager import ProcessManagerWidget
from GUX.action_pad import ActionPadWidget
from GUX.terminal_widget import TerminalWidget
from HMC.theme_manager import ThemeManagerWidget
from GUX.html_viewer import HTMLViewerWidget
from GUX.ai_chat import AIChatWidget
from GUX.media_player import MediaPlayer
from GUX.diff_merger import DiffMergerWidget
from HMC.sticky_note_manager import StickyNoteManager
from GUX.nix_store_browser import NixStoreBrowser
from HMC.download_manager import DownloadManager, DownloadManagerUI
from NITTY_GRITTY.object_tree import ObjectTreeModel
from GUX.debuuginator import CoolWidget
from GUX.theme_builder import ThemeBuilderWidget
import serial
import serial.tools.list_ports
from HMC.projects.project_manager_widget import ProjectManagerWidget

from GUX.merge_widget import MergeWidget
from AuraText.auratext.Core.window import AuraTextWindow
from AuraText.auratext.Core.TabWidget import TabWidget
import logging
import traceback
from GUX.file_search_widget import FileSearchWidget
from HMC.projects.portfolio_manager_widget import PortfolioManagerWidget
from GUX.widget_vault import VaultWidget, VaultsManagerWidget,  AdvancedDataViewerWidget, StateInspectorWidget
from HMC.risk_manager import RiskManager
from GUX.log_viewer_widget import LogViewerWidget
from HMC.transcriptor_live_widget import VoiceTypingWidget
from datetime import datetime
from GUX.widgets.ram_monitor import RAMMonitor
from GUX.device_manager_view import DeviceManagerView
from HMC.dashboard import Dashboard
from GUX.radial_menu import RadialMenu
from typing import Optional

class WidgetReference:
    def __init__(self, widget, parent=None):
        self.widget = widget
        self.parent = parent
        self.created_at = datetime.now()
        self.is_valid = True
        
    def invalidate(self):
        self.is_valid = False
        self.widget = None

class WidgetManager:
    """Manages creation, tracking and lifecycle of application widgets"""
    
    def __init__(self, cccore):
        self.cccore = cccore
        self.main_window = None
        
        # Core tracking collections
        self.widgets = {}
        self.widget_refs = {}
        self.docks = {}
        self.dock_widgets = {}
        self.all_dock_widgets = {}
        # Tab management
        self.tab_widget = None
        self.tab_config = {}
        self.tab_widgets = {}
        
        # Specialized widgets that need direct access
        self.serial_port_picker = None
        self.ai_chat_widget = None
        self.projects_manager_widget = None
        self.vaults_manager_widget = None
        self.file_search_widget = None
        self.file_search_dock = None
        self.theme_manager_window = None
        self.overlay = None
        
        # Load configuration
        self.load_config()
        self.setup_widget_methods()

    def load_config(self):
        """Load widget/dock configuration from config manager"""
        try:
            config = self.cccore.config_manager
            window_config = config.window
            
            # Load dock configurations
            self.dock_configs = window_config.layout
            self.default_docks = window_config.default_docks
            self.startup_config = self.dock_configs
            
            # Load window behavior settings
            self.enable_snap = window_config.enable_snap
            self.snap_threshold = window_config.snap_threshold
            self.enable_fade = window_config.enable_fade
            self.fade_opacity = window_config.fade_opacity
            
            logging.info("Widget manager configuration loaded successfully")
            
        except Exception as e:
            logging.error(f"Error loading widget manager config: {e}")
            # Fallback to defaults
            self.startup_config = {
                "left": ["File Explorer", "Symbolic Linker"],
                "right": ["Code Editor", "Sticky Notes"],
                "bottom": ["Terminal", "Process Manager"]
            }

    def setup_widget_methods(self):
        """Initialize widget creation methods"""
        try:
            self.widget_methods = {
                'File Explorer': lambda parent: FileExplorerWidget(parent=parent, cccore=self.cccore),
                'Code Editor': lambda parent: CodeEditorWidget(parent=parent, cccore=self.cccore),
                'Terminal': lambda parent: TerminalWidget(parent=parent, cccore=self.cccore),
                'AI Chat': lambda parent: AIChatWidget(
                    parent=parent, 
                    context_manager=self.cccore.context_manager,
                    editor_manager=self.cccore.editor_manager,
                    model_manager=self.cccore.model_manager,
                    download_manager=self.cccore.download_manager,
                    settings_manager=self.cccore.settings_manager,
                    vault_manager=self.cccore.vault_manager,
                    project_manager=self.cccore.project_manager
                ),
                'Big Links': lambda parent: SymbolicLinkerWidget(parent=parent, cccore=self.cccore),
                'Symbolic Linker': lambda parent: SymbolicLinkerWidget(parent=parent, cccore=self.cccore),
                'Sticky Notes': lambda parent: StickyNoteManager(parent=parent, cccore=self.cccore),
                'Process Manager': lambda parent: ProcessManagerWidget(parent=parent, cccore=self.cccore),
                'Vaults Manager': lambda parent: VaultsManagerWidget(parent=parent, cccore=self.cccore),
                'Portfolio Manager': lambda parent: PortfolioManagerWidget(cccore=self.cccore),
                'Risk Manager': lambda parent: RiskManager(
                    parent=parent, 
                    cccore=self.cccore,
                    config_manager=self.cccore.config_manager
                ),
                'Device Manager': lambda parent: self.get_device_manager(),
                'Transcriptor': lambda parent: VoiceTypingWidget(self.cccore.input_manager, parent=parent),
                'Log Viewer': lambda parent: LogViewerWidget(self.cccore, parent),
                'Nix Browser': lambda parent: self.get_nix_browser(),
            }
            logging.info("Widget methods initialized successfully")
        except Exception as e:
            logging.error(f"Error setting up widget methods: {e}")

    def setup_toolbar(self):
        """Initialize and setup toolbar"""
        try:
            if not self.main_window:
                logging.error("Main window not set in widget manager")
                return None
            
            toolbar = QToolBar('Main Toolbar', self.main_window)
            toolbar.setObjectName('MainToolbar')
            self.main_window.addToolBar(toolbar)
            
            # Add standard actions
            actions = {
                'New File': ('Ctrl+N', self.main_window.on_new_file),
                'Open File': ('Ctrl+O', self.main_window.on_open_file),
                'Save': ('Ctrl+S', self.main_window.on_save_file),
                'Toggle File Explorer': ('Ctrl+B', self.main_window.toggle_file_explorer),
                'Toggle Terminal': ('Ctrl+`', self.main_window.toggle_terminal),
                'Toggle Portfolio Manager': ('Ctrl+M', lambda: self.show_widget('Portfolio Manager'))  # Updated reference
            }
            
            for name, (shortcut, handler) in actions.items():
                action = QAction(name, self.main_window)
                action.setShortcut(shortcut)
                action.triggered.connect(handler)
                toolbar.addAction(action)
                if name in ['Save', 'Toggle Terminal']:
                    toolbar.addSeparator()
                    
            # Add workspace selector
            workspace_selector = self.get_workspace_selector()
            if workspace_selector:
                toolbar.addWidget(workspace_selector)
            else:
                logging.warning("Failed to add workspace selector to toolbar")
                
            logging.info("Toolbar setup completed successfully")
            return toolbar
            
        except Exception as e:
            logging.error(f"Error setting up toolbar: {str(e)}")
            logging.error(traceback.format_exc())
            return None
  
    # Widget Creation & Retrieval
    def get_or_create_widget(self, widget_name: str, parent=None) -> Optional[QWidget]:
        """Unified widget creation/retrieval method"""
        try:
            # Check existing widget
            if widget_name in self.widgets and self.widgets[widget_name]:
                return self.widgets[widget_name]
            
            # Create new widget using widget_methods
            if widget_name in self.widget_methods:
                widget = self.widget_methods[widget_name](parent or self.main_window)
                self.widgets[widget_name] = widget
                logging.info(f"Created new widget: {widget_name}")
                return widget
            
            logging.error(f"No creation method found for widget: {widget_name}")
            return None
        except Exception as e:
            logging.error(f"Error creating widget {widget_name}: {e}")
            return None

    def is_dock_valid(self, dock: Optional[QDockWidget]) -> bool:
        """Check if a dock widget is valid"""
        try:
            return dock is not None and dock.parent() is not None and dock.widget() is not None
        except RuntimeError:
            return False

    # Specialized Widget Methods
    def show_cool_dock(self):
        """Show the Cool widget dock"""
        try:
            cool_dock = self.add_cool_dock()
            if cool_dock:
                cool_dock.show()
                cool_dock.raise_()
            else:
                logging.error("Cool dock not initialized")
        except Exception as e:
            logging.error(f"Error showing Cool dock: {e}")
            logging.error(traceback.format_exc())

    
    def cleanup(self):
        """Clean up widget references and resources"""
        try:
            for ref in self.widget_refs.values():
                ref.invalidate()
            self.widgets.clear()
            self.docks.clear()
            logging.info("Widget manager cleanup completed")
        except Exception as e:
            logging.error(f"Error during widget manager cleanup: {e}")

    def set_tab_widget(self, tab_widget):
        """Set the tab widget reference"""
        if tab_widget is None:
            logging.error("Attempted to set None as tab widget")
            return False
            
        if self.tab_widget is tab_widget:
            logging.debug("Tab widget already set to this instance")
            return True
            
        logging.info(f"Setting tab widget: {tab_widget}")
        self.tab_widget = tab_widget
        self.widgets['tab_widget'] = tab_widget
        
        # Ensure proper mouse cursor
        tab_widget.setCursor(Qt.CursorShape.ArrowCursor)
        
        # Initialize any pending tabs
        if hasattr(self, 'initialize_default_tabs'):
            self.initialize_default_tabs()
        return True

    def initialize_default_tabs(self):
        """Initialize default tabs"""
        try:
            if not self.tab_widget:
                logging.warning("Cannot initialize tabs - tab widget not set")
                return
                
            # Add default editor tab
            editor = self.ensure_editor()
            if editor:
                self.tab_widget.addTab(editor, "Editor")
                
            # Add any other default tabs here
            logging.info("Default tabs initialized")
            
        except Exception as e:
            logging.error(f"Error initializing tabs: {e}")
            logging.error(traceback.format_exc())

    def ensure_editor(self):
        """Ensure editor widget exists and return it"""
        try:
            if 'editor' not in self.widgets:
                self.widgets['editor'] = self.EditorWidget(self.cccore)
            return self.widgets['editor']
        except Exception as e:
            logging.error(f"Error ensuring editor: {e}")
            return None

    def get_default_tabs(self):
        """Get list of default tabs to create"""
        default_tabs = []
        try:
            # Add your default tabs here
            if hasattr(self.cccore, 'editor_manager'):
                editor = self.cccore.editor_manager.create_editor()
                default_tabs.append(("Editor", editor))
                
            # Add more default tabs as needed
            
        except Exception as e:
            logging.error(f"Error creating default tabs: {e}")
            
        return default_tabs

    def LoggingWidget(self, cccore):
        # First ensure the directory exists
        app_data_dir = cccore.settings_manager.ensure_app_data_dir()
        if app_data_dir is None:
            if sys.platform.startswith('win32'):
                app_data_dir = os.path.join(os.getenv('APPDATA'), 'ComputinatorCode')
            else:
                app_data_dir = os.path.join(os.path.expanduser('~'), '.computinator_code')
            os.makedirs(app_data_dir, exist_ok=True)
        
        log_file = os.path.join(app_data_dir, 'app.log')
        return LogViewerWidget(initial_log_file_path=log_file, parent=self.main_window, cccore=self.cccore)

    def STTWidget(self, cccore):
        """Create and return a speech-to-text widget"""
        try:
            if 'stt' not in self.widgets:
                if not hasattr(cccore, 'input_manager'):
                    logging.error("CCCore missing input_manager")
                    return None
                self.widgets['stt'] = VoiceTypingWidget(cccore.input_manager)
                logging.info("Created new STT widget")
            return self.widgets['stt']
        except Exception as e:
            logging.error(f"Error creating STT widget: {e}")
            return None

    def set_main_window(self, main_window):
        """Set the main window reference"""
        try:
            if main_window is None:
                logging.error("Attempted to set None as main window")
                return
                
            self.main_window = main_window
            logging.info(f"Main window set successfully: {main_window}")
            self.widgets['main_window'] = main_window
            # Initialize any window-dependent components
            if hasattr(self, 'workspace_selector'):
                self.setup_workspace_selector()
                
        except Exception as e:
            logging.error(f"Error setting main window: {e}")
            logging.error(traceback.format_exc())

    def get_or_create_dock(self, widget_name):
        """Get or create a dock widget"""
        logging.info(f"Attempting to get or create dock: {widget_name}")
        
        # Return existing dock if valid
        if widget_name in self.dock_widgets and self.is_dock_valid(self.dock_widgets[widget_name]):
            logging.info(f"Existing valid dock found for {widget_name}")
            return self.dock_widgets[widget_name]
            
        try:
            # Create widget
            widget_method = self.widget_methods.get(widget_name)
            if not widget_method:
                logging.error(f"No widget method found for {widget_name}")
                return None
                
            widget = widget_method(self.main_window)
            if not widget:
                logging.error(f"Failed to create widget for {widget_name}")
                return None
                
            # Create dock
            dock = QDockWidget(widget_name, self.main_window)
            dock.setWidget(widget)
            dock.setObjectName(widget_name)
            
            # Store reference
            self.dock_widgets[widget_name] = dock
            logging.info(f"Created new dock: {widget_name}")
            return dock
            
        except Exception as e:
            logging.error(f"Error creating widget for {widget_name}: {e}")
            logging.error(traceback.format_exc())
            return None

    def create_dock(self, name: str, widget: QWidget, area: Qt.DockWidgetArea, 
                    hidden: bool = False) -> Optional[QDockWidget]:
        """Unified dock creation method"""
        try:
            # Return existing valid dock
            if name in self.docks and self.is_dock_valid(self.docks[name]):
                return self.docks[name]
                
            # Create new dock
            dock = QDockWidget(name, self.main_window)
            dock.setObjectName(f"{name.replace(' ', '')}DockWidget")
            dock.setWidget(widget)
            
            if not hidden:
                self.main_window.addDockWidget(area, dock)
                
            # Track the dock
            self.docks[name] = dock
            self.dock_widgets[name] = widget
           
            logging.info(f"Created dock: {name}")
            return dock
        except Exception as e:
            logging.error(f"Error creating dock {name}: {e}")
            return None
   
    def apply_startup_layout(self):
        if hasattr(self, 'startup_layout_applied') and self.startup_layout_applied:
            logging.warning("Startup layout already applied, skipping")
            return
        logging.info("Applying startup layout")
        for area, dock_names in self.startup_config.items():
            for dock_name in dock_names:
                dock = self.get_or_create_dock(dock_name)
                if dock and not self.is_dock_deleted(dock):
                    try:
                        if not dock.isFloating():
                            logging.info(f"Adding {dock_name} to {area} area")
                            qt_area = self.get_qt_dock_area(area)
                            if qt_area is not None:
                                if dock_name == "AI Chat":
                                    qt_area = Qt.DockWidgetArea.RightDockWidgetArea
                                self.main_window.addDockWidget(qt_area, dock)
                            else:
                                logging.warning(f"Unknown dock area: {area}")
                    except RuntimeError as e:
                        logging.error(f"Error adding dock {dock_name}: {str(e)}")
                        self.dock_widgets.pop(dock_name, None)
                else:
                    logging.warning(f"Failed to create or retrieve dock: {dock_name}")
        logging.info("Layout applied")
        self.startup_layout_applied = True

    def is_dock_deleted(self, dock):
        try:
            _ = dock.objectName()
            return False
        except RuntimeError:
            return True
        
    def create_startup_docks(self):
        """Create startup docks"""
        try:
            startup_docks = {}
            
            # Create standard docks
            dock_configs = {
                'File Explorer': Qt.DockWidgetArea.LeftDockWidgetArea,
                'Code Editor': Qt.DockWidgetArea.RightDockWidgetArea,
                'Terminal': Qt.DockWidgetArea.BottomDockWidgetArea,
                'Process Manager': Qt.DockWidgetArea.BottomDockWidgetArea,
                'Big Links': Qt.DockWidgetArea.LeftDockWidgetArea,
                'Risk Manager': Qt.DockWidgetArea.RightDockWidgetArea,  # Add Risk Manager
                'Vaults Manager': Qt.DockWidgetArea.BottomDockWidgetArea
            }
            
            for name, area in dock_configs.items():
                dock = self.ensure_dock(name)
                if dock:
                    startup_docks[name] = dock
                    if self.main_window:
                        self.main_window.addDockWidget(area, dock)
                        
            logging.warning(f"Startup docks created: {startup_docks}")
            return startup_docks
            
        except Exception as e:
            logging.error(f"Error creating startup docks: {e}")
            logging.error(traceback.format_exc())
            return {}

    def ensure_dock(self, name):
        logging.info(f"Ensuring dock: {name}")
        dock = self.get_or_create_dock(name)
        if dock:
            logging.info(f"Dock ensured successfully for {name}")
        else:
            logging.warning(f"Failed to ensure dock: {name}")
        return dock

    def set_main_window_and_create_docks(self, main_window = None):
        logging.warning(f"Setting main window: {main_window}")
        self.set_main_window(main_window)
        if self.main_window is None:
            logging.error("Main window is None, cannot create docks")
            return
        self.create_startup_docks()
        logging.warning(f"Startup docks created: {self.dock_widgets}")#just one?
        try:
            self.apply_startup_layout()
            logging.warning(f"Layout applied: {self.dock_widgets}") 
        except Exception as e:
            logging.error(f"Error applying layout: {e}")
            logging.error(traceback.format_exc())

    def get_qt_dock_area(self, area):
        area_map = {
            'left': Qt.DockWidgetArea.LeftDockWidgetArea,
            'right': Qt.DockWidgetArea.RightDockWidgetArea,
            'top': Qt.DockWidgetArea.TopDockWidgetArea,
            'bottom': Qt.DockWidgetArea.BottomDockWidgetArea,
            'center': None  # Handle central widget separately
        }
        return area_map.get(area.lower())

    # Add methods for fullscreen, hiding, and moving docks between windows
    def set_dock_fullscreen(self, name, fullscreen=True):
        if name in self.docks:
            dock = self.docks[name]
            if fullscreen:
                dock.setFloating(True)
                dock.showMaximized()
            else:
                dock.setFloating(False)

    def hide_dock(self, name):
        if name in self.docks:
            self.docks[name].hide()

    def show_dock(self, name):
        if name in self.docks:
            self.docks[name].show()

    def move_dock_to_window(self, name, target_window):
        if name in self.docks:
            dock = self.docks[name]
            current_parent = dock.parent()
            if current_parent != target_window:
                current_parent.removeDockWidget(dock)
                target_window.addDockWidget(self.dock_configs[name]["area"], dock)
     # Dock Management
    def add_dock_widget(self, widget: QWidget, title: str, area: Qt.DockWidgetArea, 
                       hidden: bool = False) -> Optional[QDockWidget]:
        """Add a widget as a dock widget"""
        try:
            dock = QDockWidget(title, self.main_window)
            dock.setObjectName(f"{title.replace(' ', '')}DockWidget")
            dock.setWidget(widget)
            
            if self.main_window and not hidden:
                self.main_window.addDockWidget(area, dock)
                
            return dock
            
        except Exception as e:
            logging.error(f"Error adding dock widget {title}: {e}")
            logging.error(traceback.format_exc())
            return None

    def add_dock_widget(self, widget: QWidget, title: str, area: Qt.DockWidgetArea, 
                       hidden: bool = False) -> Optional[QDockWidget]:
        """Add a widget as a dock widget"""
        try:
            if not self.main_window:
                logging.error("Main window not initialized")
                return None
                
            dock = QDockWidget(title, self.main_window)
            dock.setObjectName(f"{title.replace(' ', '')}DockWidget")
            dock.setWidget(widget)
            
            if not hidden:
                self.main_window.addDockWidget(area, dock)
                
            return dock
            
        except Exception as e:
            logging.error(f"Error adding dock widget {title}: {e}")
            return None

    def show_dock_widget(self, title):
        if title in self.docks:
            self.docks[title].show()   
   
    def update_flashlight_settings(self, value):
        power = value / 100.0
        self.overlay.flashlight_overlay.set_power(power)
        if power > 0.42:
            new_size = int(200 * (power / 0.42))
            self.overlay.flashlight_overlay.set_size(new_size)

    def update_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        self.serial_port_picker.clear()
        self.serial_port_picker.addItems([port.device for port in ports])

    def on_serial_port_selected(self, index):
        selected_port = self.serial_port_picker.currentText()
        self.main_window.set_serial_port(selected_port)

    def refresh_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        self.serial_port_picker.clear()
        for port in ports:
            self.serial_port_picker.addItem(port.device)

    def update_flashlight_power(self, value):
        self.flashlight.set_power(value / 100)

    def move_ai_chat_dock(self):
        logging.info("Starting move_ai_chat_dock method")
        if self.ai_chat_dock.parent() == self.main_window:
            logging.info("Moving AI chat dock to AuraText window")
            self.main_window.removeDockWidget(self.ai_chat_dock)
            if self.auratext_window and hasattr(self.auratext_window, 'layout'):
                self.auratext_window.layout.addWidget(self.ai_chat_widget)
                self.ai_chat_widget.show()
                if hasattr(self.auratext_window, 'toggle_ai_chat_button'):
                    self.auratext_window.toggle_ai_chat_button.hide()
            else:
                logging.error("AuraText window or its layout is not properly initialized")
        else:
            logging.info("Moving AI chat dock back to main window")
            if self.ai_chat_widget is not None:
                if self.auratext_window and hasattr(self.auratext_window, 'layout'):
                    self.auratext_window.layout.removeWidget(self.ai_chat_widget)
                self.ai_chat_dock.setWidget(self.ai_chat_widget)
                self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ai_chat_dock)
                if hasattr(self.auratext_window, 'toggle_ai_chat_button'):
                    self.auratext_window.toggle_ai_chat_button.show()
            else:
                logging.error("AI chat widget is None")

    def apply_theme_to_all_widgets(self):
        logging.info("Applying theme to all widgets")
        for dock in self.all_dock_widgets.values():
            if hasattr(dock.widget(), 'apply_theme'):
                dock.widget().apply_theme()
        logging.info("Theme applied to all widgets")

    def get_all_dock_widgets(self):
        return self.all_dock_widgets

    def register_widget(self, name, widget, parent=None):
        """Register a widget reference"""
        self.widget_refs[name] = WidgetReference(widget, parent)
        return widget
    
    def add_advanced_data_viewer_dock(self):
        if 'advanced_data_viewer_dock' not in self.docks:
            advanced_data_viewer = AdvancedDataViewerWidget(self.cccore)
            dock = self.add_dock_widget(advanced_data_viewer, "Advanced Data Viewer", Qt.DockWidgetArea.RightDockWidgetArea)
            self.docks['advanced_data_viewer_dock'] = dock
            
            # Create an action to toggle the dock's visibility
            action = QAction("Advanced Data Viewer", self.cccore.main_window)
            action.setCheckable(True)
            action.setChecked(dock.isVisible())
            action.triggered.connect(dock.toggleViewAction().trigger)
            
            return dock, action
        return self.docks['advanced_data_viewer_dock'], self.docks['advanced_data_viewer_dock'].toggleViewAction()

    def save_current_workspace(self):
        active_workspace = self.workspace_manager.get_active_workspace()
        if active_workspace:
            self.workspace_manager.save_workspace_layout(active_workspace.name)

    def add_file_search_dock(self):
        if self.file_search_dock is None:
            self.file_search_widget = FileSearchWidget(self.cccore.vault_manager, parent=self.main_window)
            self.file_search_dock = self.add_dock_widget(self.file_search_widget, "File Search", Qt.DockWidgetArea.RightDockWidgetArea)
            self.file_search_widget.file_selected.connect(self.open_file_from_search)
        return self.file_search_dock
    
    def FileExplorerWidget(self, cccore):
        logging.info(f"Creating FileExplorerWidget with cccore: {cccore}")
        if 'file_explorer' not in self.widgets:
            self.widgets['file_explorer'] = FileExplorerWidget(parent=self.main_window, cccore=cccore)
        return self.widgets['file_explorer']

    def PortfolioManagerWidget(self, cccore):
        if 'portfolio_manager' not in self.widgets:
            self.widgets['portfolio_manager'] = PortfolioManagerWidget(cccore=cccore)
        return self.widgets['portfolio_manager']

   
    def ProjectManagerWidget(self, cccore):
        """Single project detailed management"""
        if 'project_manager' not in self.widgets:
            try:
                self.widgets['project_manager'] = ProjectManagerWidget(
                    cccore=cccore,
                    parent=self.main_window
                )
                logging.info("Project Manager widget created successfully")
            except Exception as e:
                logging.error(f"Error creating Project Manager widget: {e}")
                return None
        return self.widgets['project_manager']

    def PortfolioManagerWidget(self, cccore):
        """Multi-project portfolio management"""
        if 'portfolio_manager' not in self.widgets:
            try:
                self.widgets['portfolio_manager'] = PortfolioManagerWidget(
                    cccore=cccore,
                    parent=self.main_window
                )
                logging.info("Portfolio Manager widget created successfully")
            except Exception as e:
                logging.error(f"Error creating Portfolio Manager widget: {e}")
                return None
        return self.widgets['portfolio_manager']

    def VaultsManagerWidget(self, cccore):
        if not hasattr(self, '_vaults_manager_widget'):
            self._vaults_manager_widget = VaultsManagerWidget(parent=self.main_window, cccore=cccore)
        return self._vaults_manager_widget

    def VaultWidget(self, cccore):
        if 'vault' not in self.widgets:
            self.widgets['vault'] = VaultWidget(parent=self.main_window, cccore=self.cccore)
        return self.widgets['vault']

    def ProcessManagerWidget(self, cccore):
        if 'process_manager' not in self.widgets:
            self.widgets['process_manager'] = ProcessManagerWidget(parent=self.main_window, cccore=self.cccore)
        return self.widgets['process_manager']

    def AIChatWidget(self, cccore, parent=None):
        if 'ai_chat' not in self.widgets:
            self.widgets['ai_chat'] = AIChatWidget(parent=parent, 
                                                   context_manager=cccore.context_manager, 
                                                   editor_manager=cccore.editor_manager, 
                                                   model_manager=cccore.model_manager, 
                                                   download_manager=cccore.download_manager, 
                                                   settings_manager=cccore.settings_manager, 
                                                   vault_manager=cccore.vault_manager,
                                                   project_manager=cccore.project_manager)
        return self.widgets['ai_chat']

    def RiskManagerWidget(self, cccore):
        if 'risk_manager' not in self.widgets:
            try:
                self.widgets['risk_manager'] = RiskManager(
                    config_manager=cccore.settings_manager,
                    notification_manager=cccore.notification_manager,
                    cccore=cccore
                )
                logging.info("Risk Manager widget created successfully")
            except Exception as e:
                logging.error(f"Error creating Risk Manager widget: {e}")
                return None
                
        return self.widgets['risk_manager']

    def MergeWidget(self, cccore):
        if not hasattr(self, 'merge_widget'):
            self.merge_widget = MergeWidget(parent=self.main_window,)
        return self.merge_widget

    def CodeEditorWidget(self, cccore):
        if not hasattr(self, 'code_editor_widget'):
            self.code_editor_widget = CodeEditorWidget(parent=self.main_window, cccore=self.cccore)
        return self.code_editor_widget

    def SymbolicLinkerWidget(self, cccore):
        """Create or return the Symbolic Linker widget"""
        if not hasattr(self, 'symbolic_linker_widget'):
            try:
                self.symbolic_linker_widget = SymbolicLinkerWidget(
                    parent=self.main_window,
                    cccore=cccore
                )
                logging.info("Symbolic Linker widget created successfully")
            except Exception as e:
                logging.error(f"Error creating Symbolic Linker widget: {e}")
                return None
        return self.symbolic_linker_widget

    def TerminalWidget(self, cccore):
        if not hasattr(self, 'terminal_widget'):
            self.terminal_widget = TerminalWidget(parent=self.main_window, cccore=self.cccore)
        return self.terminal_widget

    
    def create_auratext_window(self, cccore):
        new_window = AuraTextWindow(mm=cccore)
        new_window.setWindowOpacity(0)  # Start fully transparent
        new_window.hide()  # Hide the window initially
        self.auratext_windows.append(new_window)
        QTimer.singleShot(1000, lambda: self.show_auratext_window(new_window))  # Show after a short delay
        return new_window

    def show_auratext_window(self, window):
        window.show()
        window.fade_in()  # Assuming you have a fade_in method in AuraTextWindow

    def StickyNotesWidget(self, cccore):
        if 'sticky_notes' not in self.widgets:
            self.widgets['sticky_notes'] = StickyNoteManager(parent=self.main_window, cccore=self.cccore)
        return self.widgets['sticky_notes']

    def OverlaySettingsWidget(self, cccore):
        if not hasattr(self, 'overlay_settings_widget'):
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(int(self.overlay.flashlight_overlay.power * 100))
            slider.valueChanged.connect(self.update_flashlight_settings)
            layout.addWidget(slider)

            self.serial_port_picker = QComboBox()
            self.update_serial_ports()
            self.serial_port_picker.currentIndexChanged.connect(self.on_serial_port_selected)
            layout.addWidget(self.serial_port_picker)

            self.overlay_settings_widget = widget
        return self.overlay_settings_widget

    def AdvancedDataViewerWidget(self, cccore):
        if 'advanced_data_viewer' not in self.widgets:
            self.widgets['advanced_data_viewer'] = AdvancedDataViewerWidget(parent=self.main_window)
        return self.widgets['advanced_data_viewer']

    def open_file_from_search(self, file_path):
        self.cccore.editor_manager.open_file(file_path)

    def create_theme_manager_window(self):
        if self.theme_manager_window is None:
            self.theme_manager_window = ThemeManagerWidget(self.cccore.theme_manager)
        return self.theme_manager_window

    def show_theme_manager(self):
        window = self.create_theme_manager_window()
        window.show()
        window.raise_()
        
    def show_theme_builder(self):
        if not hasattr(self, 'theme_builder_widget'):
            self.theme_builder_widget = ThemeBuilderWidget(self.cccore.theme_manager)
        self.theme_builder_widget.show()

    def recreate_invalid_docks(self):
        for name, dock in list(self.dock_widgets.items()):
            if not self.is_dock_valid(dock):
                logging.warning(f"Recreating invalid dock: {name}")
                new_dock = self.ensure_dock(name)
                if new_dock and self.is_dock_valid(new_dock):
                    self.dock_widgets[name] = new_dock
                    if self.main_window:
                        self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, new_dock)
                    logging.info(f"Successfully recreated dock: {name}")
                else:
                    logging.error(f"Failed to recreate dock: {name}")
                    
    def create_project_widget(self, parent):
        if 'project_widget' not in self.widgets:
            self.widgets['project_widget'] = self.create_project_selector_widget(parent)
        return self.widgets['project_widget']

    def create_project_selector_widget(self, parent):
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        vault_selector = QComboBox(widget)
        project_selector = QComboBox(widget)
        layout.addWidget(QLabel("Vault:"))
        layout.addWidget(vault_selector)
        layout.addWidget(QLabel("Project:"))
        layout.addWidget(project_selector)
        return widget
    
    def StateInspectorWidget(self, cccore):
        if 'state_inspector' not in self.widgets:
            self.widgets['state_inspector'] = StateInspectorWidget(cccore, parent=self.main_window)
        return self.widgets['state_inspector']

    def add_state_inspector_dock(self):
        if 'state_inspector_dock' not in self.docks:
            state_inspector = self.StateInspectorWidget(self.cccore)
            self.docks['state_inspector_dock'] = self.add_dock_widget(
                state_inspector,
                "State Inspector",
                Qt.DockWidgetArea.RightDockWidgetArea,
                hidden=True
            )
        return self.docks['state_inspector_dock']

    def get_cool_widget(self):
        logging.info("Entering get_cool_widget method")
        if 'cool' not in self.widgets:
            logging.info("Creating new CoolWidget instance")
            try:
                self.widgets['cool'] = CoolWidget(self.cccore)
                logging.info("CoolWidget created successfully")
            except Exception as e:
                logging.error(f"Error creating CoolWidget: {str(e)}")
                logging.error(traceback.format_exc())
        else:
            logging.info("Returning existing CoolWidget instance")
        return self.widgets['cool']

    def add_cool_dock(self):
        logging.info("Entering add_cool_dock method")
        if 'cool_dock' not in self.docks:
            logging.info("Creating new Cool dock")
            try:
                cool_widget = self.get_cool_widget()
                self.docks['cool_dock'] = self.add_dock_widget(
                    cool_widget,
                    "Code Tool",
                    Qt.DockWidgetArea.BottomDockWidgetArea,
                    hidden=False
                )
                logging.info(f"Cool dock created: {self.docks['cool_dock']}")
            except Exception as e:
                logging.error(f"Error creating Cool dock: {str(e)}")
                logging.error(traceback.format_exc())
        else:
            logging.info("Returning existing Cool dock")
        return self.docks['cool_dock']

    
    # Add this method to ensure the Cool dock is visible
    def show_cool_dock(self):
        logging.warning("Entering show_cool_dock method")
        try:
            cool_dock = self.add_cool_dock()
            if cool_dock:
                logging.warning("Attempting to show Cool dock")
                cool_dock.show()
                cool_dock.raise_()
                logging.warning("Cool dock shown successfully")
            else:
                logging.warning("Failed to create or retrieve Cool dock")
        except Exception as e:
            logging.error(f"Error showing Cool dock: {str(e)}")
            logging.error(traceback.format_exc())

    def RiskManagerWidget(self, cccore):
        """Create Risk Manager widget"""
        if 'risk_manager' not in self.widgets:
            try:
                self.widgets['risk_manager'] = RiskManager(
                    config_manager=cccore.settings_manager,
                    notification_manager=cccore.notification_manager,
                    cccore=cccore
                )
                logging.info("Risk Manager widget created successfully")
            except Exception as e:
                logging.error(f"Error creating Risk Manager widget: {e}")
                return None
                
        return self.widgets['risk_manager']
       
    def setup_central_tabs(self):
        """Initialize the central tab widget"""
        try:
            # If tab widget already exists in main window, use that
            if (hasattr(self, 'main_window') and 
                hasattr(self.main_window, 'tab_widget')):
                self.tab_widget = self.main_window.tab_widget
                logging.info("Using existing tab widget from main window")
                return self.tab_widget
                
            # If we already have a tab widget, return it
            if hasattr(self, 'tab_widget') and self.tab_widget:
                return self.tab_widget
                
            # Create new tab widget if needed
            self.tab_widget = QTabWidget()
            self.tab_widget.setTabsClosable(True)
            self.tab_widget.setMovable(True)
            self.tab_widget.tabCloseRequested.connect(self.on_tab_close_requested)
            
            # Add to main window if available
            if hasattr(self, 'main_window') and self.main_window:
                if hasattr(self.main_window, 'central_layout'):
                    self.main_window.central_layout.addWidget(self.tab_widget)
                    logging.info("Tab widget initialized and added to main window")
                else:
                    logging.error("Main window has no central layout")
                
            return self.tab_widget
            
        except Exception as e:
            logging.error(f"Error setting up central tabs: {e}")
            return None

    def get_tab_widget(self):
        """Get or create the tab widget"""
        if not hasattr(self, 'tab_widget') or not self.tab_widget:
            return self.setup_central_tabs()
        return self.tab_widget

    def add_to_central_tabs(self, widget, tab_name):
        """Add a widget to the central tab widget"""
        if not self.main_window or not hasattr(self.main_window, 'tab_widget'):
            logging.warning(f"Cannot add {tab_name} to central tabs - tab widget not initialized")
            return False
            
        try:
            self.main_window.tab_widget.addTab(widget, tab_name)
            self.tab_widgets[tab_name] = widget
            logging.info(f"Added {tab_name} to central tabs")
            return True
        except Exception as e:
            logging.error(f"Error adding {tab_name} to central tabs: {str(e)}")
            return False

    def setup_workspace_selector(self):
        """Create and configure workspace selector"""
        try:
            if not hasattr(self, 'workspace_selector') or self.workspace_selector is None:
                from PyQt6.QtWidgets import QComboBox
                
                self.workspace_selector = QComboBox()
                self.workspace_selector.setObjectName("WorkspaceSelector")
                self.workspace_selector.setMaximumWidth(200)
                
                # Get workspaces from current vault
                if hasattr(self.cccore, 'workspace_manager'):
                    current_vault = self.cccore.vault_manager.get_current_vault()
                    if current_vault:
                        workspaces = self.cccore.workspace_manager.get_workspace_names(current_vault.path)
                        if workspaces:
                            self.workspace_selector.addItems(workspaces)
                            current = self.cccore.workspace_manager.get_current_workspace()
                            if current:
                                index = self.workspace_selector.findText(current)
                                if index >= 0:
                                    self.workspace_selector.setCurrentIndex(index)
                                    
                # Connect signals
                if hasattr(self.cccore.workspace_manager, 'workspace_changed'):
                    self.workspace_selector.currentTextChanged.connect(
                        self.cccore.workspace_manager.set_current_workspace
                    )
                    
                logging.info("Workspace selector initialized successfully")
                return self.workspace_selector
                
        except Exception as e:
            logging.error(f"Error setting up workspace selector: {e}")
            logging.error(traceback.format_exc())
            self.workspace_selector = None
            
        return None

    def get_workspace_selector(self):
        """Get or create workspace selector"""
        if not hasattr(self, 'workspace_selector') or not self.workspace_selector:
            self.workspace_selector = self.setup_workspace_selector()
        return self.workspace_selector

    def show_device_manager(self):
        """Show device manager widget"""
        try:
            if 'Device Manager' not in self.widgets:
                self.widgets['Device Manager'] = DeviceManagerView(self.cccore)
            dock = self.get_or_create_dock('Device Manager', self.widgets['Device Manager'])
            if dock:
                dock.show()
                dock.raise_()
        except Exception as e:
            logging.error(f"Error showing device manager: {e}")

    def show_nix_browser(self):
        """Show Unix/Linux file browser"""
        try:
            if 'nix_browser' not in self.widgets:
                self.widgets['nix_browser'] = NixStoreBrowser(parent=self.main_window)
            dock = self.get_or_create_dock('Unix Browser', self.widgets['nix_browser'])
            if dock:
                dock.show()
                dock.raise_()
        except Exception as e:
            logging.error(f"Error showing Unix browser: {e}")

    def show_dashboard(self):
        """Show dashboard widget"""
        try:
            if 'dashboard' not in self.widgets:
                self.widgets['dashboard'] = Dashboard(self.cccore)
            dock = self.get_or_create_dock('Dashboard', self.widgets['dashboard'])
            if dock:
                dock.show()
                dock.raise_()
        except Exception as e:
            logging.error(f"Error showing dashboard: {e}")

    def setup_menu_bar(self):
        """Initialize and setup menu bar"""
        try:
            if not self.main_window:
                logging.error("Main window not set in widget manager")
                return None
            
            menubar = self.main_window.menuBar()
            
            # File Menu
            file_menu = menubar.addMenu('&File')
            file_menu.addAction('New File', self.main_window.on_new_file, 'Ctrl+N')
            file_menu.addAction('Open File', self.main_window.on_open_file, 'Ctrl+O')
            file_menu.addAction('Save', self.main_window.on_save_file, 'Ctrl+S')
            file_menu.addSeparator()
            file_menu.addAction('Exit', self.main_window.close, 'Alt+F4')

            # View Menu
            view_menu = menubar.addMenu('&View')
            view_menu.addAction('Dashboard', self.show_dashboard)
            view_menu.addAction('File Explorer', lambda: self.show_dock_widget('File Explorer'))
            view_menu.addAction('Terminal', lambda: self.show_dock_widget('Terminal'))
            view_menu.addAction('Unix Browser', self.show_nix_browser)
            
            # Tools Menu
            tools_menu = menubar.addMenu('&Tools')
            tools_menu.addAction('Process Manager', lambda: self.show_dock_widget('Process Manager'))
            tools_menu.addAction('Risk Manager', lambda: self.show_dock_widget('Risk Manager'))
            tools_menu.addAction('Theme Manager', self.show_theme_manager)
            
            return menubar
            
        except Exception as e:
            logging.error(f"Error creating menu bar: {e}")
            logging.error(traceback.format_exc())
            return None
