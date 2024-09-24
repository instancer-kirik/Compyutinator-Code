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
# from GUX.ai_chat import AIChatWidget
from GUX.media_player import MediaPlayer
from GUX.diff_merger import DiffMergerWidget
from HMC.sticky_note_manager import StickyNoteManager
from HMC.download_manager import DownloadManager, DownloadManagerUI
import serial
import serial.tools.list_ports

from GUX.diff_merger import DiffMergerWidget
from AuraText.auratext.Core.window import AuraTextWindow

import logging
import traceback


class WidgetManager:
    def __init__(self, cccore, overlay):
        self.cccore = cccore
        self.overlay = overlay
        self.main_window = None
        self.auratext_window = None
        self.auratext_dock = None
        self.dock_widgets = {}
        self.all_dock_widgets = {}  # This will store all dock widgets, including those not in config
        self.db_manager = cccore.db_manager
        self.download_manager = self.cccore.download_manager
        self.settings = cccore.settings_manager.settings
        self.model_manager = cccore.model_manager
        self.theme_manager = cccore.theme_manager
        self.tab_widget = QTabWidget()
       
        self.serial_port_picker = None
        self.ai_chat_widget = None
        
        self.sticky_note_manager = None
        self.symbolic_linker_widget = None
        
        self.dock_map = {
            "Symbolic Linker": self.add_symbolic_linker_dock,
            "File Explorer": self.add_file_explorer_dock,
            "Code Editor": self.add_code_editor_dock,
            "Process Manager": self.add_process_manager_dock,
            "Action Pad": self.add_action_pad_dock,
            "Terminal": self.add_terminal_dock,
            "Theme Manager": self.add_theme_manager_dock,
            "HTML Viewer": self.add_html_viewer_dock,
            "AI Chat": self.add_ai_chat_dock,
            "Media Player": self.add_media_player_dock,
            "Download Manager": self.add_download_manager_dock,
            "Sticky Notes": self.add_sticky_notes_dock,
            "Overlay": self.add_overlay_dock,
            "Diff Merger": self.add_diff_merger_dock,
            "AuraText": self.create_auratext_dock
        }
        self.workspace_manager = cccore.workspace_manager
        self.startup_docks = ['File Explorer', 'Code Editor', 'Terminal', 'AI Chat', 'AuraText']
        self.startup_config = {
            'layout': {
                'left': ['File Explorer', 'Symbolic Linker','Sticky Notes'],
                'right': [ 'AuraText'],
                'bottom': ['Terminal', 'Process Manager']
            }
        }
        self.load_startup_config()
        self.create_auratext_dock()  # Call this in the init method

    def load_startup_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        with open(config_path, 'r') as f:
            self.startup_config = json.load(f)

    def create_startup_docks(self):
        logging.info("Creating startup docks")
        for dock_name in self.startup_docks:
            logging.info(f"Creating dock: {dock_name}")
            dock = self.get_or_create_dock(dock_name)
            if dock:
                logging.info(f"Dock '{dock_name}' created successfully")
            else:
                logging.warning(f"Failed to create dock: {dock_name}")
        logging.info("Finished create_startup_docks method")

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
        
        self.create_auratext_dock()  # Ensure AuraText dock is created
        
        logging.info("set_main_window_and_create_docks method completed")

    def add_dock_widget(self, widget, title, area):
        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(f"{title.replace(' ', '')}DockWidget")
        widget.setMinimumWidth(300)
        dock.setWidget(widget)
        self.main_window.addDockWidget(area, dock)
        self.dock_widgets[title] = dock
        self.all_dock_widgets[title] = dock  # Add to all_dock_widgets
        
        widget.installEventFilter(self.main_window)
        if len(self.dock_widgets) > 1:
            self.main_window.tabifyDockWidget(list(self.dock_widgets.values())[-2], dock)

        return dock

    def add_symbolic_linker_dock(self):
        if self.symbolic_linker_widget is None:
            self.symbolic_linker_widget = SymbolicLinkerWidget()
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
        self.theme_manager_widget = ThemeManagerWidget(self.theme_manager)
        self.theme_manager_dock = self.add_dock_widget(self.theme_manager_widget, "Theme Manager", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_html_viewer_dock(self):
        self.html_viewer_widget = HTMLViewerWidget()
        self.html_viewer_dock = self.add_dock_widget(self.html_viewer_widget, "HTML Viewer", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_ai_chat_dock(self):
        try:
            box = QVBoxLayout()
            label = QLabel("Disabled, debugging")
            box.addWidget(label)
            self.ai_chat_widget = QWidget()
            self.ai_chat_widget.setLayout(box)
            # self.ai_chat_widget = AIChatWidget(
            #     parent=self.main_window,
            #     model_manager=self.model_manager,
            #     download_manager=self.download_manager,
            #     settings_manager=self.cccore.settings_manager
            # )
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
        logging.info("Starting create_auratext_dock method")
        if 'AuraText' not in self.all_dock_widgets:
            logging.info("Creating AuraText dock")
            from AuraText.auratext.Core.window import AuraTextWindow
            self.auratext_window = AuraTextWindow(self.cccore)
            self.auratext_dock = QDockWidget("AuraText", self.main_window)
            self.auratext_dock.setWidget(self.auratext_window)
            self.auratext_dock.setObjectName("AuraTextDock")
            self.all_dock_widgets['AuraText'] = self.auratext_dock
            logging.info("AuraText dock created")
        return self.all_dock_widgets['AuraText']

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

    def get_or_create_dock(self, dock_name):
        logging.info(f"Getting or creating dock: {dock_name}")
        if dock_name not in self.all_dock_widgets:
            if dock_name in self.dock_map:
                try:
                    create_method = self.dock_map[dock_name]
                    dock = create_method()
                    if dock is None:
                        logging.warning(f"Creation method for '{dock_name}' returned None")
                        return None
                    self.all_dock_widgets[dock_name] = dock
                    logging.info(f"Dock '{dock_name}' created successfully")
                except Exception as e:
                    logging.error(f"Error creating dock '{dock_name}': {str(e)}")
                    logging.error(traceback.format_exc())
                    return None
            else:
                logging.error(f"No method found to create dock: {dock_name}")
                return None
        return self.all_dock_widgets.get(dock_name)

    def apply_workspace(self, workspace_name):
        self.workspace_manager.load_workspace_layout(workspace_name)

    def get_all_dock_widgets(self):
        return self.all_dock_widgets

    def save_current_workspace(self):
        active_workspace = self.workspace_manager.get_active_workspace()
        if active_workspace:
            self.workspace_manager.save_workspace_layout(active_workspace.name)

    def get_all_dock_widgets(self):
        return self.all_dock_widgets
  
  