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
from GUX.widget_vault import VaultWidget, VaultsManagerWidget, ProjectsManagerWidget

import serial
import serial.tools.list_ports

from GUX.diff_merger import DiffMergerWidget
from AuraText.auratext.Core.window import AuraTextWindow
from AuraText.auratext.Core.TabWidget import TabWidget
import logging
import traceback
from GUX.file_search_widget import FileSearchWidget

class WidgetManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.main_window = None
        self.auratext_window = None
        self.file_explorer_widget = None
        self.auratext_dock = None
        self.docks = {}
        self.dock_configs = {
            "File Explorer": {
                "widget": "FileExplorerWidget",
                "area": Qt.DockWidgetArea.LeftDockWidgetArea,
                "visible": True
            },
            "Projects Manager": {
                "widget": "ProjectsManagerWidget",
                "area": Qt.DockWidgetArea.LeftDockWidgetArea,
                "visible": True
            },
            "Vaults Manager": {
                "widget": "VaultsManagerWidget",
                "area": Qt.DockWidgetArea.LeftDockWidgetArea,
                "visible": True
            },
            "AI Chat": {
                "widget": "AIChatWidget",
                "area": Qt.DockWidgetArea.RightDockWidgetArea,
                "visible": True
            },
            "Code Editor": {
                "widget": "CodeEditorWidget",
                "area": Qt.DockWidgetArea.RightDockWidgetArea,
                "visible": True
            },
            "AuraText": {
                "widget": "AuraTextWidget",
                "area": Qt.DockWidgetArea.RightDockWidgetArea,
                "visible": True
            },
            "Symbolic Linker": {
                "widget": "SymbolicLinkerWidget",
                "area": Qt.DockWidgetArea.LeftDockWidgetArea,
                "visible": True
            },
        }
        self.all_dock_widgets = {}  # This will store all dock widgets, including those not in config
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
        self.startup_docks = ['File Explorer', 'Code Editor', 'Terminal', 'AI Chat', 'AuraText']
        self.startup_config = {
            'layout': {
                'left': ['File Explorer', 'Symbolic Linker', 'Sticky Notes'],
                'right': ['AuraText', 'File Search'],
                'center': ['Code Editor'],  # Add this line
                'bottom': ['Terminal', 'Process Manager']
            }
        }
       
        self.theme_manager_window = None
        self.load_startup_config()
       

    def FileExplorerWidget(self, cccore):
        if self.file_explorer_widget is None:
            self.file_explorer_widget = FileExplorerWidget(cccore)
        return self.file_explorer_widget

    def ProjectsManagerWidget(self, cccore):
        if self.projects_manager_widget is None:
            self.projects_manager_widget = ProjectsManagerWidget(cccore)
        return self.projects_manager_widget

    def VaultsManagerWidget(self, cccore):
        if self.vaults_manager_widget is None:
            self.vaults_manager_widget = VaultsManagerWidget(cccore)
        return self.vaults_manager_widget
    def VaultWidget(self, cccore):
        if self.vault_widget is None:
            self.vault_widget = VaultWidget(cccore)
        return self.vault_widget

    def AIChatWidget(self, cccore):
        if not hasattr(self, 'ai_chat_widget'):
            try:
                logging.info("Creating AIChatWidget")
                logging.info(f"CCCore attributes: {dir(cccore)}")
                logging.info(f"Context manager: {cccore.context_manager}")
                logging.info(f"Editor manager: {cccore.editor_manager}")
                logging.info(f"Model manager: {cccore.model_manager}")
                logging.info(f"Download manager: {cccore.download_manager}")
                logging.info(f"Settings manager: {cccore.settings_manager}")
                
                self.ai_chat_widget = AIChatWidget(
                    parent=self.main_window,
                    context_manager=cccore.context_manager,
                    editor_manager=cccore.editor_manager,
                    model_manager=cccore.model_manager,
                    download_manager=cccore.download_manager,
                    settings_manager=cccore.settings_manager
                )
                logging.info("AIChatWidget created successfully")
            except Exception as e:
                logging.error(f"Error creating AIChatWidget: {str(e)}")
                logging.error(traceback.format_exc())
                self.ai_chat_widget = None
        else:
            logging.info("AIChatWidget already exists")
            return self.ai_chat_widget
        if self.ai_chat_widget is None:
            logging.error("Failed to create AIChatWidget")
            return None
        
        return self.ai_chat_widget
    def CodeEditorWidget(self, cccore):
        return CodeEditorWidget(cccore)
    def SymbolicLinkerWidget(self, cccore):
        if self.symbolic_linker_widget is None:
            self.symbolic_linker_widget = SymbolicLinkerWidget(cccore)
        return self.symbolic_linker_widget
    def set_main_window(self, main_window):
        self.main_window = main_window

    def get_or_create_dock(self, name, parent=None):
        if name in self.docks:
            return self.docks[name]
        
        if name not in self.dock_configs:
            logging.error(f"No configuration found for dock: {name}")
            return None

        config = self.dock_configs[name]
        widget_method = getattr(self, config["widget"], None)
        if widget_method is None:
            logging.error(f"Widget method {config['widget']} not found")
            return None

        try:
            logging.info(f"Creating widget for dock: {name}")
            widget = widget_method(self.cccore)
            
            if widget is None:
                logging.error(f"Widget creation failed for {name}")
                return None
            
            dock_parent = parent if parent is not None else self.main_window
            dock = self.create_dock(name, widget, dock_parent)
            self.docks[name] = dock
            logging.info(f"Dock created successfully for {name}")
            return dock
        except Exception as e:
            logging.error(f"Error creating dock {name}: {str(e)}")
            logging.error(traceback.format_exc())
        return None  
    def create_dock(self, name, parent=None):
        if name not in self.dock_configs:
            raise ValueError(f"No configuration found for dock: {name}")

        config = self.dock_configs[name]
        widget_class = getattr(self.cccore, config["widget"])
        widget = widget_class(self.cccore)

        # Use the provided parent, or fall back to main_window if not provided
        dock_parent = parent if parent is not None else self.main_window
        dock = QDockWidget(name, dock_parent)
        dock.setWidget(widget)
        dock.setObjectName(name)
        
        self.docks[name] = dock
        return dock

   
    def apply_layout(self):
        # Implement layout application logic here
        pass

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

    def load_startup_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        with open(config_path, 'r') as f:
            self.startup_config = json.load(f)
    def create_startup_docks(self):
        if self.main_window is None:
            raise ValueError("Main window not set. Call set_main_window() first.")
        for name in self.dock_configs:
            dock = self.get_or_create_dock(name, self.main_window)
            self.main_window.addDockWidget(self.dock_configs[name]["area"], dock)
            dock.setVisible(self.dock_configs[name]["visible"])

    
    def apply_layout(self):
        logging.info("Applying layout")
        for area, dock_names in self.startup_config['layout'].items():
            for dock_name in dock_names:
                dock = self.get_or_create_dock(dock_name)
                if dock:
                    logging.info(f"Adding {dock_name} to {area} area")
                    if area == 'left':
                        self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
                    elif area == 'right':
                        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
                    elif area == 'bottom':
                        self.main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
                    elif area == 'center':
                        self.main_window.addDockWidget(Qt.DockWidgetArea.CenterDockWidgetArea, dock)
                else:
                    logging.warning(f"Failed to create or retrieve dock: {dock_name}")
        logging.info("Layout applied")

    def set_main_window_and_create_docks(self, main_window):
        logging.info("Starting set_main_window_and_create_docks method")
        self.main_window = main_window
        logging.info("Main window set")
        
        try:
            logging.info("Creating startup docks")
            self.create_startup_docks()
            logging.info("Startup docks created successfully")
        except Exception as e:
            logging.error(f"Error creating startup docks: {str(e)}")
            logging.error(traceback.format_exc())
        
        try:
            logging.info("Applying layout")
            self.apply_layout()
            logging.info("Layout applied successfully")
        except Exception as e:
            logging.error(f"Error applying layout: {str(e)}")
            logging.error(traceback.format_exc())
        
        # The AuraText dock is now created as part of create_startup_docks if it's in the startup config
        
        logging.info("set_main_window_and_create_docks method completed")

    def add_dock_widget(self, widget, title, area):
        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(f"{title.replace(' ', '')}DockWidget")
        widget.setMinimumWidth(300)
        dock.setWidget(widget)
        self.main_window.addDockWidget(area, dock)
        self.docks[title] = dock
        self.all_dock_widgets[title] = dock  # Add to all_dock_widgets
        
        widget.installEventFilter(self.main_window)
        if len(self.docks) > 1:
            self.main_window.tabifyDockWidget(list(self.docks.values())[-2], dock)

        return dock

    def add_symbolic_linker_dock(self):
        if self.symbolic_linker_widget is None:
            self.symbolic_linker_widget = SymbolicLinkerWidget(self.cccore)
            self.symbolic_linker_dock = self.add_dock_widget(self.symbolic_linker_widget, "BigLinks", Qt.DockWidgetArea.LeftDockWidgetArea)
        return self.symbolic_linker_dock

    def add_file_explorer_dock(self):
        try:
            self.file_explorer_widget = FileExplorerWidget(self.main_window)
            self.file_explorer_dock = self.add_dock_widget(self.file_explorer_widget, "File Explorer", Qt.DockWidgetArea.LeftDockWidgetArea)
            return self.file_explorer_dock
        except Exception as e:
            logging.error(f"Error creating File Explorer dock: {str(e)}")
            return None

    def add_code_editor_dock(self):
        try:
            self.code_editor_widget = CodeEditorWidget()
            self.code_editor_dock = self.add_dock_widget(self.code_editor_widget, "Code Editor", Qt.DockWidgetArea.RightDockWidgetArea)
            return self.code_editor_dock
        except Exception as e:
            logging.error(f"Error creating Code Editor dock: {str(e)}")
            return None

    def add_process_manager_dock(self):
        try:
            self.process_manager_widget = ProcessManagerWidget(self.main_window)
            self.process_manager_dock = self.add_dock_widget(self.process_manager_widget, "Process Manager", Qt.DockWidgetArea.BottomDockWidgetArea)
            return self.process_manager_dock
        except Exception as e:
            logging.error(f"Error creating Process Manager dock: {str(e)}")
            return None

    def add_action_pad_dock(self):
        # Pass the db_manager to ActionPadWidget
        self.action_pad_widget = ActionPadWidget(self.db_manager, self.main_window)
        self.action_pad_dock = self.add_dock_widget(self.action_pad_widget, "Action Pad", Qt.DockWidgetArea.BottomDockWidgetArea)
        
    def add_terminal_dock(self):
        try:
            self.terminal_widget = TerminalWidget()
            self.terminal_dock = self.add_dock_widget(self.terminal_widget, "Terminal", Qt.DockWidgetArea.BottomDockWidgetArea)
            return self.terminal_dock
        except Exception as e:
            logging.error(f"Error creating Terminal dock: {str(e)}")
            return None

    def add_theme_manager_dock(self):
        logging.info("Creating Theme Manager dock")
        if "Theme Manager" not in self.all_dock_widgets:
            theme_manager_widget = ThemeManagerWidget(self.cccore.theme_manager)
            theme_manager_dock = self.add_dock_widget(theme_manager_widget, "Theme Manager", Qt.DockWidgetArea.RightDockWidgetArea)
            self.all_dock_widgets["Theme Manager"] = theme_manager_dock
        logging.info(f"Theme Manager dock created: {self.all_dock_widgets['Theme Manager']}")
        return self.all_dock_widgets["Theme Manager"]

    def add_html_viewer_dock(self):
        self.html_viewer_widget = HTMLViewerWidget()
        self.html_viewer_dock = self.add_dock_widget(self.html_viewer_widget, "HTML Viewer", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_ai_chat_dock(self):
        try:
            box = QVBoxLayout()
           
            label = QLabel("Disabled, debugging")
            box.addWidget(label)
            self.ai_chat_widget.setLayout(box)
            

            self.ai_chat_dock = self.add_dock_widget(self.ai_chat_widget, "AI Chat", Qt.DockWidgetArea.RightDockWidgetArea)
            return self.ai_chat_dock
        except Exception as e:
            logging.error(f"Error creating AI Chat dock: {str(e)}")
            return None

    def add_media_player_dock(self):
        self.media_player_widget = MediaPlayer()
        self.media_player_dock = self.add_dock_widget(self.media_player_widget, "Media Player", Qt.DockWidgetArea.BottomDockWidgetArea)
    # def add_transcriptor_live_dock(self):
    #     self.transcriptor_live_widget = VoiceTypingWidget(self)
    #     self.transcriptor_live_dock = self.add_dock_widget(self.transcriptor_live_widget, "Transcriptor-Live", Qt.DockWidgetArea.BottomDockWidgetArea)

    def add_download_manager_dock(self):
        self.download_manager = DownloadManager()
        self.download_manager_ui = DownloadManagerUI(self.download_manager)
        self.download_manager_dock = self.add_dock_widget(self.download_manager_ui, "Download Manager", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_sticky_notes_dock(self):
        if self.sticky_note_manager is None:
            self.sticky_note_manager = StickyNoteManager(self.main_window)
            self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.sticky_note_manager)
        return self.sticky_note_manager

    def add_brightness_dock(self):
        self.brightness_dock = QDockWidget("Brightness Control", self.main_window)
        self.brightness_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(int(self.overlay.flashlight_overlay.power * 100))
        slider.valueChanged.connect(lambda value: self.overlay.flashlight_overlay.set_power(value / 100.0))
        self.brightness_dock.setWidget(slider)
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.brightness_dock)
        self.all_dock_widgets["Brightness Control"] = self.brightness_dock

    def add_diff_merger_dock(self):
        self.diff_merger_widget = DiffMergerWidget()
        self.diff_merger_widget.setMinimumSize(600, 300)
        self.diff_merger_dock = self.add_dock_widget(self.diff_merger_widget, "Diff Merger", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_overlay_dock(self):
        self.overlay_dock = QDockWidget("Overlay Settings", self.main_window)
        self.overlay_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.overlay_dock)

        layout = QVBoxLayout()
        
        # Brightness slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(int(self.overlay.flashlight_overlay.power * 100))
        slider.valueChanged.connect(self.update_flashlight_settings)
        layout.addWidget(slider)

        # Serial port picker
        self.serial_port_picker = QComboBox()
        self.update_serial_ports()
        self.serial_port_picker.currentIndexChanged.connect(self.on_serial_port_selected)
        layout.addWidget(self.serial_port_picker)

        widget = QWidget()
        widget.setLayout(layout)
        self.overlay_dock.setWidget(widget)

        self.all_dock_widgets["Overlay Settings"] = self.overlay_dock

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

    def create_auratext_dock(self):
        if self.auratext_dock is None:
            auratext_widget = self.AuraTextWidget(self.cccore)
            self.auratext_dock = self.create_dock("AuraText", auratext_widget, self.main_window)
            self.add_dock_widget(self.auratext_dock, "AuraText", Qt.DockWidgetArea.RightDockWidgetArea)
        return self.auratext_dock

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

    def save_current_workspace(self):
        active_workspace = self.workspace_manager.get_active_workspace()
        if active_workspace:
            self.workspace_manager.save_workspace_layout(active_workspace.name)

    def get_all_dock_widgets(self):
        return self.all_dock_widgets

    def add_file_search_dock(self):
        if self.file_search_dock is None:
            self.file_search_widget = FileSearchWidget(self.cccore.vault_manager)
            self.file_search_dock = self.add_dock_widget(self.file_search_widget, "File Search", Qt.DockWidgetArea.RightDockWidgetArea)
            self.file_search_widget.file_selected.connect(self.open_file_from_search)
        return self.file_search_dock

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

    def create_dock(self, name, widget, parent):
        dock = QDockWidget(name, parent)
        dock.setWidget(widget)
        dock.setObjectName(name)
        
        self.docks[name] = dock
        return dock 
    def AuraTextWidget(self, cccore):
        if not hasattr(self, 'auratext_widget'):
            # Create AuraTextWindow if it doesn't exist
            if not hasattr(self, 'auratext_window'):
                self.auratext_window = AuraTextWindow(cccore)
            
            # Wrap AuraTextWindow in a QWidget
            self.auratext_widget = QWidget()
            layout = QVBoxLayout(self.auratext_widget)
            layout.addWidget(self.auratext_window)
            self.auratext_widget.setLayout(layout)

        return self.auratext_widget