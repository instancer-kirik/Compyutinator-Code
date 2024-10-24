import sys
import os

# Add the AuraText directory to the Python path
auratext_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'AuraText')
sys.path.append(auratext_dir)

from PyQt6.QtWidgets import  QVBoxLayout, QDockWidget, QWidget, QSlider, QComboBox, QLabel, QTabWidget, QSizePolicy
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
from HMC.project_manager import ProjectManagerWidget, ManyProjectsManagerWidget
from GUX.merge_widget import MergeWidget
from AuraText.auratext.Core.window import AuraTextWindow
from AuraText.auratext.Core.TabWidget import TabWidget
import logging
import traceback
from GUX.file_search_widget import FileSearchWidget
from HMC.project_manager import ManyProjectsManagerWidget
from GUX.widget_vault import VaultWidget, VaultsManagerWidget,  AdvancedDataViewerWidget, StateInspectorWidget
class WidgetManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.main_window = None
        self.docks = {}
        self.widgets = {}  
        self.dock_widgets = {}  # Add this line to store strong references to dock widgets
        self.all_dock_widgets = {}  # This will store all created dock widgets
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

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
            self.startup_config = self.config['layout']
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            self.config = {}
            self.startup_config = {}
        return self.startup_config
    def set_main_window(self, main_window):
        self.main_window = main_window

    def get_or_create_dock(self, name,widget=None, area=Qt.DockWidgetArea.LeftDockWidgetArea, parent=None):#also makes widgets?
        logging.info(f"Attempting to get or create dock: {name}")
        if name in self.dock_widgets and self.is_dock_valid(self.dock_widgets[name]):
            logging.info(f"Existing valid dock found for {name}")
            return self.dock_widgets[name]
        if widget is None:
            widget_method = getattr(self, f"{name.replace(' ', '')}Widget", None)
            if widget_method:
                logging.info(f"Creating widget for {name}")
                try:
                    if parent is None:
                        widget = widget_method(self.cccore)
                    else:
                        widget = widget_method(self.cccore, parent)
                    if widget:
                        logging.info(f"Widget created successfully for {name}")
                        dock = self.create_dock(name, widget, self.main_window)
                        if dock:
                            self.dock_widgets[name] = dock
                            logging.info(f"Dock created successfully for {name}")
                            return dock
                        else:
                            logging.error(f"Failed to create dock for {name}")
                    else:
                        logging.error(f"Widget creation returned None for {name}")
                except Exception as e:
                    logging.error(f"Error creating widget for {name}: {str(e)}")
                    logging.error(traceback.format_exc())
            else:
                logging.error(f"No widget method found for {name}")
        else:
            logging.warning(f"Widget already created for {name}")
            dock = self.create_dock(name, widget, self.main_window)
            if dock:
                self.dock_widgets[name] = dock
                logging.info(f"Dock created successfully for {name}")
                return dock
            else:
                logging.error(f"Failed to create dock for {name}")
        logging.warning(f"Failed to create or retrieve dock: {name}")
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
        try:
            # Create and add your startup docks here
            self.create_dock("Projects Manager", self.ProjectManagerWidget(self.cccore, parent=self.main_window), parent=self.main_window)
            #self.add_cool_dock()  # Add this line to create the Cool dock on startup
            # ... other startup docks
            
            # Create and add the AI Chat dock
            ai_chat_widget = self.AIChatWidget(self.cccore, parent=self.main_window)
            ai_chat_dock = self.create_dock("AI Chat", ai_chat_widget, parent=self.main_window)
            if ai_chat_dock:
                self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, ai_chat_dock)
                logging.info("AI Chat dock created and added to the right dock area")
            else:
                logging.error("Failed to create AI Chat dock")
        except Exception as e:
            logging.error(f"Error creating startup docks: {e}")
            logging.error(traceback.format_exc())
     #   default_docks = [
    #         "File Explorer", "Code Editor", "Terminal", "AI Chat", 
    #         "Symbolic Linker", "Sticky Notes", "Process Manager", 
    #         "Vaults Manager", "Projects Manager", "AuraText"
    #     ]
    #     for name in default_docks:
    #         self.ensure_dock(name)
    #     logging.info("Startup docks creation completed")

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
    #         auratext_widget = self.AuraTextWidget(self.cccore)
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
    def ProjectManagerWidget(self, cccore, parent):
        if 'projects_manager' not in self.widgets:
            self.widgets['projects_manager'] = ProjectManagerWidget(parent=parent, cccore=cccore, window=self.main_window)
        return self.widgets['projects_manager']

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

    def MergeWidget(self, cccore):
        if not hasattr(self, 'merge_widget'):
            self.merge_widget = MergeWidget(parent=self.main_window,)
        return self.merge_widget
    def CodeEditorWidget(self, cccore):
        if not hasattr(self, 'code_editor_widget'):
            self.code_editor_widget = CodeEditorWidget(parent=self.main_window, cccore=self.cccore)
        return self.code_editor_widget
    def SymbolicLinkerWidget(self, cccore):
        if self.symbolic_linker_widget is None:
            self.symbolic_linker_widget = SymbolicLinkerWidget(parent=self.main_window, cccore=self.cccore)
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
  