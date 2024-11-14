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

from HMC.download_manager import DownloadManager, DownloadManagerUI
from NITTY_GRITTY.object_tree import ObjectTreeModel
from GUX.debuuginator import CoolWidget
from GUX.theme_builder import ThemeBuilderWidget
import serial
import serial.tools.list_ports
from HMC.project_manager import ProjectManagerWidget
from GUX.widgets.many_project_manager_widget import ManyProjectsManagerWidget
from GUX.merge_widget import MergeWidget
from AuraText.auratext.Core.window import AuraTextWindow
from AuraText.auratext.Core.TabWidget import TabWidget
import logging
import traceback
from GUX.file_search_widget import FileSearchWidget
from GUX.widgets.many_project_manager_widget import ManyProjectsManagerWidget
from GUX.widget_vault import VaultWidget, VaultsManagerWidget,  AdvancedDataViewerWidget, StateInspectorWidget
from HMC.risk_manager import RiskManager
from GUX.log_viewer_widget import LogViewerWidget
from HMC.transcriptor_live_widget import VoiceTypingWidget
from datetime import datetime
from GUX.widgets.ram_monitor import RAMMonitor
from GUX.device_manager_view import DeviceManagerView
from HMC.dashboard import Dashboard
from GUX.radial_menu import RadialMenu

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
    def __init__(self, cccore):
        self.cccore = cccore
        self.main_window = None
        self.tab_widget = None
        self.tab_config = {}
        self.docks = {}
        self.widgets = {}
        self.widget_refs = {}
        self.dock_widgets = {}
        self.all_dock_widgets = {}
        self.tab_widgets = {}
        self.overlay = None
        
        """Initialize widget manager"""
        try:
            self.cccore = cccore
            self.main_window = None
            self.widgets = {}
            self.dock_widgets = {}
            self.all_dock_widgets = {}
            
            # Initialize widget creation methods with correct argument order
            self.widget_methods = {
                'File Explorer': lambda parent: FileExplorerWidget(parent=parent, cccore=self.cccore),
                'Code Editor': lambda parent: CodeEditorWidget(parent=parent, cccore=self.cccore),
                'Terminal': lambda parent: TerminalWidget(parent=parent, cccore=self.cccore),
                'AI Chat': lambda parent: AIChatWidget(parent=parent, cccore=self.cccore),
                'Big Links': lambda parent: SymbolicLinkerWidget(parent=parent, cccore=self.cccore),
                'Symbolic Linker': lambda parent: SymbolicLinkerWidget(parent=parent, cccore=self.cccore),
                'Sticky Notes': lambda parent: StickyNoteManager(parent=parent, cccore=self.cccore),
                'Process Manager': lambda parent: ProcessManagerWidget(parent=parent, cccore=self.cccore),
                'Vaults Manager': lambda parent: VaultsManagerWidget(parent=parent, cccore=self.cccore),
                'Projects Manager': lambda parent: ManyProjectsManagerWidget(cccore=self.cccore),
                'Many Projects Manager': lambda parent: ManyProjectsManagerWidget(cccore=self.cccore),
                'Risk Manager': lambda parent: RiskManager(parent=parent, cccore=self.cccore),
                'Device Manager': lambda parent: self.get_device_manager(),
                'Log Viewer': lambda parent: LogViewerWidget(self.cccore, parent),
                'Nix Browser': lambda parent: self.get_nix_browser(),
            }
            logging.info("Widget methods initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing widget manager: {e}")
        self.load_config()
        self.db_manager = cccore.db_manager
        self.download_manager = self.cccore.download_manager
        self.settings = cccore.settings_manager.settings
        self.model_manager = cccore.model_manager
        self.theme_manager = cccore.theme_manager
        self.tab_widget = QTabWidget()
        self.serial_port_picker = None
        self.ai_chat_widget = None
        self.projects_manager_widget = None
        self.vaults_manager_widget = None
        self.sticky_note_manager = None
        self.symbolic_linker_widget = None
        
        self.file_search_widget = None
        self.file_search_dock = None
        
        self.workspace_manager = cccore.workspace_manager
       
        self.theme_manager_window = None
        
        self.auratext_windows = []
        self.startup_layout_applied = False
        self.widget_methods = {}
        self.setup_widget_methods()
        # Initialize workspace selector
        self.workspace_selector = None
       
        self.device_manager_dock = None

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
    def setup_widget_methods(self):
        """Initialize widget creation methods"""
        try:
            self.widget_methods = {
                'File Explorer': lambda parent: FileExplorerWidget(parent=parent, cccore=self.cccore),
                'Code Editor': lambda parent: CodeEditorWidget(parent=parent, cccore=self.cccore),
                'Terminal': lambda parent: TerminalWidget(parent=parent, cccore=self.cccore),
                'AI Chat': lambda parent: AIChatWidget(parent=parent, cccore=self.cccore),
                'Big Links': lambda parent: SymbolicLinkerWidget(parent=parent, cccore=self.cccore),
                'Symbolic Linker': lambda parent: SymbolicLinkerWidget(parent=parent, cccore=self.cccore),
                'Sticky Notes': lambda parent: StickyNoteManager(parent=parent, cccore=self.cccore),
                'Process Manager': lambda parent: ProcessManagerWidget(parent=parent, cccore=self.cccore),
                'Vaults Manager': lambda parent: VaultsManagerWidget(parent=parent, cccore=self.cccore),
                'Projects Manager': lambda parent: ManyProjectsManagerWidget(cccore=self.cccore),
                'Many Projects Manager': lambda parent: ManyProjectsManagerWidget(cccore=self.cccore),
                'Risk Manager': lambda parent: RiskManager(parent=parent, cccore=self.cccore),
                'Device Manager': lambda parent: self.get_device_manager(),
                'Transcriptor': lambda parent: VoiceTypingWidget(self.cccore.input_manager, parent=parent),
                'Log Viewer': lambda parent: LogViewerWidget(self.cccore, parent),
                'Nix Browser': lambda parent: self.get_nix_browser(),
            }
            logging.info("Widget methods initialized successfully")
        except Exception as e:
            logging.error(f"Error setting up widget methods: {e}")

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

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
            self.startup_config = self.config.get('layout', {
                'left': ['File Explorer', 'Many Projects Manager'],  # Use Many Projects Manager consistently
                'right': ['Code Editor', 'Sticky Notes', 'AI Chat'],
                'bottom': ['Terminal', 'Process Manager', 'Vaults Manager'],
                'floating': []
            })
            logging.info("Configuration loaded successfully")
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            self.config = {}
            self.startup_config = {}
        return self.startup_config
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

    def create_dock(self, name, widget, parent=None):
        if name in self.docks and self.is_dock_valid(self.docks[name]):
            logging.info(f"Valid dock {name} already exists. Returning existing dock.")
            return self.docks[name]
        
        try:
            dock = QDockWidget(name, parent)
            dock.setObjectName(f"{name.replace(' ', '')}DockWidget")
            dock.setWidget(widget)
            self.docks[name] = dock
            self.dock_widgets[name] = dock  # Store a strong reference
            self.all_dock_widgets[name] = dock
            logging.info(f"Created new dock: {name}")
            return dock
        except Exception as e:
            logging.error(f"Error creating dock {name}: {str(e)}")
            logging.error(traceback.format_exc())
            return None

    def is_dock_valid(self, dock):
        try:
            return dock is not None and not self.is_dock_deleted(dock) and dock.widget() is not None
        except RuntimeError:
            return False
   
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

    def add_dock_widget(self, widget, title, area, hidden=False):
        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(f"{title.replace(' ', '')}DockWidget")
        widget.setMinimumWidth(300)
        dock.setWidget(widget)
        self.main_window.addDockWidget(area, dock)
        self.docks[title] = dock
        self.all_dock_widgets[title] = dock  # Add to all_dock_widgets
        if hidden:
            dock.hide()
        widget.installEventFilter(self.main_window)
        if len(self.docks) > 1:
            self.main_window.tabifyDockWidget(list(self.docks.values())[-2], dock)

        return dock

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

    # def create_auratext_dock(self):
    #     if self.auratext_dock is None:
    #         auratext_widget = self.AuraTextWidget(self.cccore, parent=self.main_window)
    #         self.auratext_dock = self.create_dock("AuraText", auratext_widget, self.main_window)
    #         self.add_dock_widget(self.auratext_dock, "AuraText", Qt.DockWidgetArea.RightDockWidgetArea)
    #     return self.auratext_dock

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
        
    def get_widget(self, name):
        """Get widget by name, ensuring it's valid"""
        ref = self.widget_refs.get(name)
        if ref and ref.is_valid and ref.widget:
            return ref.widget
        return None
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
    def ManyProjectsManagerWidget(self, cccore):
        if 'many_projects_manager' not in self.widgets:
            self.widgets['many_projects_manager'] = ManyProjectsManagerWidget(cccore)
        return self.widgets['many_projects_manager']
    def ProjectManagerWidget(self, cccore):
        if 'project_manager' not in self.widgets:
            try:
                self.widgets['project_manager'] = ProjectManagerWidget(
                    parent=self.main_window,
                    cccore=cccore
                )
                logging.info("Project Manager widget created successfully") 
            except Exception as e:
                logging.error(f"Error creating Project Manager widget: {e}")
                return None
            
        return self.widgets['project_manager']

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
                    
    # def create_file_selector(self, parent):
    #     if 'file_selector' not in self.widgets:
    #         self.widgets['file_selector'] = QComboBox(parent)
    #     return self.widgets['file_selector']

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

    def setup_toolbar(self):
        """Initialize and setup toolbar"""
        try:
            if not self.main_window:
                logging.error("Main window not set in widget manager")
                return None
            
            toolbar = QToolBar('Main Toolbar', self.main_window)
            toolbar.setObjectName('MainToolbar')  # This is required
            self.main_window.addToolBar(toolbar)
            
            # Add standard actions
            actions = {
                'New File': ('Ctrl+N', self.main_window.on_new_file),
                'Open File': ('Ctrl+O', self.main_window.on_open_file),
                'Save': ('Ctrl+S', self.main_window.on_save_file),
                'Toggle File Explorer': ('Ctrl+B', self.main_window.toggle_file_explorer),
                'Toggle Terminal': ('Ctrl+`', self.main_window.toggle_terminal),
                'Toggle Many Projects Manager': ('Ctrl+M', self.cccore.widget_manager.many_projects_manager.toggleView)
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

    def cleanup(self):
        """Clean up all managed widgets and resources"""
        try:
            # First clear any references to prevent circular dependencies
            self.main_window = None
            self.cccore = None
            
            # Then invalidate widget references
            for name, ref in list(self.widget_refs.items()):
                try:
                    if ref and ref.is_valid:
                        ref.invalidate()
                except Exception as e:
                    logging.error(f"Error invalidating widget ref {name}: {e}")

            # Close docks next
            for name, dock in list(self.dock_widgets.items()):
                try:
                    if dock and not self.is_dock_deleted(dock):
                        dock.close()
                        dock.deleteLater()
                except Exception as e:
                    logging.error(f"Error closing dock {name}: {e}")
                    
            # Finally delete remaining widgets
            for name, widget in list(self.widgets.items()):
                try:
                    if widget and not self.is_widget_deleted(widget):
                        widget.deleteLater()
                except Exception as e:
                    logging.error(f"Error deleting widget {name}: {e}")
                    
            # Clear collections
            self.dock_widgets.clear()
            self.widget_refs.clear()
            self.widgets.clear()
            
        except Exception as e:
            logging.error(f"Error during widget manager cleanup: {e}")
            logging.error(traceback.format_exc())

    def save_state(self):
        """Save current widget states"""
        state = {
            'dock_geometry': {},
            'widget_states': {},
            'layout': self.startup_config
        }
        
        for name, dock in self.dock_widgets.items():
            if not self.is_dock_deleted(dock):
                state['dock_geometry'][name] = dock.saveGeometry()
                
        for name, ref in self.widget_refs.items():
            if ref.is_valid and hasattr(ref.widget, 'save_state'):
                state['widget_states'][name] = ref.widget.save_state()
                
        return state

    def restore_state(self, state):
        """Restore widget states"""
        try:
            # Restore dock geometry
            for name, geometry in state.get('dock_geometry', {}).items():
                if name in self.dock_widgets:
                    self.dock_widgets[name].restoreGeometry(geometry)
                    
            # Restore widget states
            for name, widget_state in state.get('widget_states', {}).items():
                widget = self.get_widget(name)
                if widget and hasattr(widget, 'restore_state'):
                    widget.restore_state(widget_state)
                    
        except Exception as e:
            logging.error(f"Error restoring widget states: {e}")
            logging.error(traceback.format_exc())

    def apply_theme_to_widgets(self, theme):
        """Apply theme to all managed widgets"""
        try:
            # Apply to dock widgets
            for dock in self.dock_widgets.values():
                if hasattr(dock.widget(), 'apply_theme'):
                    dock.widget().apply_theme(theme)
                    
            # Apply to standalone widgets
            for ref in self.widget_refs.values():
                if ref.is_valid and hasattr(ref.widget, 'apply_theme'):
                    ref.widget.apply_theme(theme)
                    
            logging.info("Theme applied to all managed widgets")
            
        except Exception as e:
            logging.error(f"Error applying theme to managed widgets: {e}")
            logging.error(traceback.format_exc())

    def init_tab_widget(self):
        """Initialize the tab widget once"""
        if not hasattr(self, 'tab_widget') and self.main_window:
            self.tab_widget = QTabWidget()
            self.main_window.central_widget.layout().addWidget(self.tab_widget)
            # Store reference to prevent garbage collection
            self.widgets['tab_widget'] = self.tab_widget
            logging.info("Tab widget initialized successfully")
            return self.tab_widget
        return getattr(self, 'tab_widget', None)

    def ensure_tab_widget(self):
        """Ensure tab widget exists"""
        if not hasattr(self, 'tab_widget'):
            return self.init_tab_widget()
        return self.tab_widget

    def ensure_tab_widget_exists(self):
        """Ensure tab widget is initialized"""
        if not self.tab_widget and self.main_window:
            if hasattr(self.main_window, 'tab_widget'):
                self.set_tab_widget(self.main_window.tab_widget)
                return True
            else:
                logging.error("Main window does not have tab_widget")
                return False
        return bool(self.tab_widget)

    def get_tab_widget(self):
        """Get the tab widget, ensuring it exists first"""
        if self.ensure_tab_widget_exists():
            return self.tab_widget
        return None

    def is_widget_deleted(self, widget):
        """Check if widget has been deleted"""
        try:
            return not bool(widget) or not widget.isVisible()
        except (RuntimeError, AttributeError):
            return True

    
    def show_dock_widget(self, widget_name):
        """Show a dock widget by name"""
        try:
            dock = self.get_or_create_dock(widget_name)
            if dock:
                dock.show()
                dock.raise_()
            else:
                logging.error(f"Failed to show dock widget: {widget_name}")
        except Exception as e:
            logging.error(f"Error showing dock widget {widget_name}: {e}")

    def initialize_docks(self):
        """Initialize dock widgets once window is ready"""
        if not self.main_window or not self.main_window.isVisible():
            # Retry after a short delay if window isn't ready
            QTimer.singleShot(100, self.initialize_docks)
            return

        try:
            # Ensure all necessary docks are initialized
            if not hasattr(self, 'device_manager_dock'):
                self.device_manager_dock = self.create_device_manager_dock()
            # Ensure ManyProjectsManager is initialized
            if not hasattr(self, 'many_projects_manager'):
                self.many_projects_manager = ManyProjectsManagerWidget(self.main_window, self.cccore)
                self.add_dock_widget(self.many_projects_manager, "Many Projects Manager", Qt.DockWidgetArea.LeftDockWidgetArea)
                self.many_projects_manager.hide()  # Initially hidden
        except Exception as e:
            logging.error(f"Error initializing Many Projects Manager: {e}")

    def DashboardWidget(self, cccore):
        """Create or return the Dashboard widget"""
        try:
            if 'dashboard' not in self.widgets:
                from HMC.dashboard import Dashboard  # Import here to avoid circular imports
                dashboard = Dashboard(cccore)
                self.widgets['dashboard'] = dashboard
                logging.info("Dashboard widget created successfully")
                return dashboard
            return self.widgets['dashboard']
        except Exception as e:
            logging.error(f"Error creating Dashboard widget: {e}")
            return None

    def show_dashboard(self, project_name=None):
        """Show the project dashboard as a dialog"""
        try:
            # Create dialog first
            dialog = QDialog(self.cccore.main_window)
            dialog.setWindowTitle("Project Dashboard")
            dialog.setMinimumSize(800, 600)
            
            # Create dashboard with dialog as parent
            dashboard = Dashboard(self.cccore, parent=dialog)  # Add parent parameter
            
            # Create layout
            layout = QVBoxLayout(dialog)
            layout.addWidget(dashboard)
            
            # Set project if provided
            if project_name:
                dashboard.set_project(project_name)
            else:
                # Try to get current project
                current_project = self.cccore.project_manager.get_current_project()
                if current_project:
                    dashboard.set_project(current_project)
                
            # Refresh dashboard
            dashboard.refresh_dashboard()
            
            # Show dialog
            dialog.exec()
            logging.info(f"Dashboard dialog shown for project: {project_name or current_project}")
            
        except Exception as e:
            logging.error(f"Error showing dashboard dialog: {e}")
            traceback.print_exc()

    def DeviceManagerWidget(self, cccore):
        """Create or return the Device Manager widget"""
        if 'device_manager' not in self.widgets:
            try:
                from GUX.device_manager_view import DeviceManagerView
                widget = DeviceManagerView(parent=self.main_window)
                widget.cccore = cccore
                self.widgets['device_manager'] = widget
                logging.info("Device Manager widget created successfully")
            except Exception as e:
                logging.error(f"Error creating Device Manager widget: {e}")
                logging.error(traceback.format_exc())
                return None
        return self.widgets['device_manager']

    def add_device_manager_dock(self):
        """Create and add the Device Manager dock widget"""
        if 'device_manager_dock' not in self.docks:
            try:
                device_manager = self.DeviceManagerWidget(self.cccore)
                if device_manager:
                    self.docks['device_manager_dock'] = self.add_dock_widget(
                        device_manager,
                        "Device Manager",
                        Qt.DockWidgetArea.RightDockWidgetArea,
                        hidden=False
                    )
                    logging.info("Device Manager dock created successfully")
                    
                    # Create an action to toggle the dock's visibility
                    action = QAction("Device Manager", self.cccore.main_window)
                    action.setCheckable(True)
                    action.setChecked(self.docks['device_manager_dock'].isVisible())
                    action.triggered.connect(self.docks['device_manager_dock'].toggleViewAction().trigger)
                    
                    return self.docks['device_manager_dock'], action
            except Exception as e:
                logging.error(f"Error creating Device Manager dock: {e}")
                logging.error(traceback.format_exc())
                return None, None
                
        return self.docks['device_manager_dock'], self.docks['device_manager_dock'].toggleViewAction()

    def init_device_manager(self):
        """Initialize the device manager"""
        try:
            # Create device manager instance if it doesn't exist
            if not hasattr(self, 'device_manager'):
                from GUX.device_manager_view import DeviceManagerView
                from HMC.device_manager import DeviceManager
                
                # Create the backend manager first
                self.device_manager_backend = DeviceManager()
                
                # Create the view and connect it to the backend
                self.device_manager = DeviceManagerView(parent=self.main_window)
                self.device_manager.device_manager = self.device_manager_backend
                self.device_manager.cccore = self.cccore
                logging.info("Device Manager widget created successfully")

            # Create dock if it doesn't exist
            if not hasattr(self, 'device_manager_dock'):
                self.device_manager_dock = self.add_dock_widget(
                    self.device_manager,
                    "Device Manager",
                    Qt.DockWidgetArea.RightDockWidgetArea
                )
                logging.info("Device Manager dock created successfully")

            return self.device_manager_dock
        except Exception as e:
            logging.error(f"Error initializing device manager: {e}")
            logging.error(traceback.format_exc())
            return None

    def show_device_manager(self):
        """Show the device manager dock"""
        try:
            dock = self.init_device_manager()
            if dock:
                dock.show()
                dock.raise_()
            else:
                logging.error("Device manager dock not initialized")
                
        except Exception as e:
            logging.error(f"Error showing device manager: {e}")
            logging.error(traceback.format_exc())

    def get_device_manager(self):
        """Get or create the device manager instance"""
        try:
            if not hasattr(self, 'device_manager'):
                self.init_device_manager()
            return self.device_manager
        except Exception as e:
            logging.error(f"Error getting device manager: {e}")
            return None

    def init_nix_browser(self):
        """Initialize the Nix Store Browser"""
        try:
            if not hasattr(self, 'nix_browser'):
                from GUX.nix_store_browser import NixStoreBrowser
                self.nix_browser = NixStoreBrowser(parent=self.main_window)
                logging.info("Nix Store Browser created successfully")

            if not hasattr(self, 'nix_browser_dock'):
                self.nix_browser_dock = self.add_dock_widget(
                    self.nix_browser,
                    "Nix Store Browser",
                    Qt.DockWidgetArea.RightDockWidgetArea
                )
                logging.info("Nix Store Browser dock created successfully")

            return self.nix_browser_dock
        except Exception as e:
            logging.error(f"Error initializing Nix Store Browser: {e}")
            logging.error(traceback.format_exc())
            return None
  
    def show_nix_browser(self):
        """Show the Nix Store Browser dock"""
        try:
            dock = self.init_nix_browser()
            if dock:
                dock.show()
                dock.raise_()
        except Exception as e:
            logging.error(f"Error showing Nix Store Browser: {e}")
  
    def show_radial_menu(self, position):
        """Show radial menu with registered hotkeys"""
        # Get registered hotkeys from your hotkey manager
        hotkey_mappings = {
            "New File": "Ctrl+N",
            "Open": "Ctrl+O",
            "Save": "Ctrl+S",
            "Find": "Ctrl+F",
            "Replace": "Ctrl+H",
            "Terminal": "Ctrl+`",
            "Build": "F5",
            "Debug": "F9"
        }  # Replace with actual hotkey mappings

        menu = RadialMenu(self.main_window)
        menu.set_options_with_hotkeys(hotkey_mappings)
        menu.optionSelected.connect(self.handle_radial_menu_selection)
        menu.show_at(position)
  