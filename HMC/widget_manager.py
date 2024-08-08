from PyQt6.QtWidgets import  QVBoxLayout, QDockWidget, QWidget, QSlider, QComboBox, QLabel

from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QSettings, QByteArray
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
import sys
from PyQt6.QtCore import Qt, QSettings, QByteArray
from GUX.overlay import Flashlight
import serial
import serial.tools.list_ports

from GUX.diff_merger import DiffMergerWidget


class WidgetManager:
    def __init__(self, main_app):
        self.main_app = main_app
        self.dock_widgets = []
        self.overlay_dock = None
        self.serial_port_picker = None
        self.create_widgets()
    def add_dock_widget(self, widget, title, area):
        dock_widget = QDockWidget(title, self.main_app)
        dock_widget.setObjectName(f"{title.replace(' ', '')}DockWidget")
        dock_widget.setWidget(widget)
        self.main_app.addDockWidget(area, dock_widget)
        self.dock_widgets.append(dock_widget)
        widget.installEventFilter(self.main_app)
        return dock_widget

    def create_widgets(self):
        self.add_symbolic_linker_dock()
        self.add_file_explorer_dock()
        self.add_code_editor_dock()
        self.add_process_manager_dock()
        self.add_action_pad_dock()
        self.add_terminal_dock()
        self.add_theme_manager_dock()
        self.add_html_viewer_dock()
        self.add_ai_chat_dock()
        self.add_media_player_dock()
        self.add_download_manager_dock()
        self.add_sticky_note_manager_dock()
        self.add_overlay_dock()
        self.add_brightness_dock()
        self.add_diff_merger_dock()
    def add_symbolic_linker_dock(self):
        self.symbolic_linker_widget = SymbolicLinkerWidget()
        self.symbolic_linker_dock = self.add_dock_widget(self.symbolic_linker_widget, "Symbolic Linker", Qt.DockWidgetArea.LeftDockWidgetArea)

    def add_file_explorer_dock(self):
        self.file_explorer_widget = FileExplorerWidget(self.main_app)
        self.file_explorer_dock = self.add_dock_widget(self.file_explorer_widget, "File Explorer", Qt.DockWidgetArea.LeftDockWidgetArea)

    def add_code_editor_dock(self):
        self.code_editor_widget = CodeEditorWidget()
        self.code_editor_dock = self.add_dock_widget(self.code_editor_widget, "Code Editor", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_process_manager_dock(self):
        self.process_manager_widget = ProcessManagerWidget(self.main_app)
        self.process_manager_dock = self.add_dock_widget(self.process_manager_widget, "Process Manager", Qt.DockWidgetArea.BottomDockWidgetArea)

    def add_action_pad_dock(self):
        self.action_pad_widget = ActionPadWidget(self.main_app)
        self.action_pad_dock = self.add_dock_widget(self.action_pad_widget, "Action Pad", Qt.DockWidgetArea.BottomDockWidgetArea)

    def add_terminal_dock(self):
        self.terminal_widget = TerminalWidget()
        self.terminal_dock = self.add_dock_widget(self.terminal_widget, "Terminal", Qt.DockWidgetArea.BottomDockWidgetArea)

    def add_theme_manager_dock(self):
        self.theme_manager_widget = ThemeManagerWidget(self.main_app)
        self.theme_manager_dock = self.add_dock_widget(self.theme_manager_widget, "Theme Manager", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_html_viewer_dock(self):
        self.html_viewer_widget = HTMLViewerWidget()
        self.html_viewer_dock = self.add_dock_widget(self.html_viewer_widget, "HTML Viewer", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_ai_chat_dock(self):
        self.ai_chat_widget = AIChatWidget()
        self.ai_chat_dock = self.add_dock_widget(self.ai_chat_widget, "AI Chat", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_media_player_dock(self):
        self.media_player_widget = MediaPlayer()
        self.media_player_dock = self.add_dock_widget(self.media_player_widget, "Media Player", Qt.DockWidgetArea.BottomDockWidgetArea)
    def add_transcriptor_live_dock(self):
        self.transcriptor_live_widget = VoiceTypingWidget(self)
        self.transcriptor_live_dock = self.add_dock_widget(self.transcriptor_live_widget, "Transcriptor-Live", Qt.DockWidgetArea.BottomDockWidgetArea)

    def add_download_manager_dock(self):
        self.download_manager = DownloadManager()
        self.download_manager_ui = DownloadManagerUI(self.download_manager)
        self.download_manager_dock = self.add_dock_widget(self.download_manager_ui, "Download Manager", Qt.DockWidgetArea.RightDockWidgetArea)

    def add_sticky_note_manager_dock(self):
        self.sticky_note_manager = StickyNoteManager()
        self.sticky_note_manager_dock = self.add_dock_widget(self.sticky_note_manager, "Sticky Notes", Qt.DockWidgetArea.RightDockWidgetArea)
   
    
    def add_brightness_dock(self):
        self.brightness_dock = QDockWidget("Brightness Control", self.main_app)
        self.brightness_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(int(self.main_app.flashlight.power * 100))
        slider.valueChanged.connect(lambda value: self.main_app.flashlight.set_power(value / 100.0))
        self.brightness_dock.setWidget(slider)
        self.main_app.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.brightness_dock)
        self.dock_widgets.append(self.brightness_dock)

    
   
    def add_diff_merger_dock(self):
        self.diff_merger_widget = DiffMergerWidget()
        self.diff_merger_dock = self.add_dock_widget(self.diff_merger_widget, "Diff Merger", Qt.DockWidgetArea.RightDockWidgetArea)
   
    
    def add_overlay_dock(self):
        self.overlay_dock = QDockWidget("Overlay Settings", self.main_app)
        self.overlay_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.main_app.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.overlay_dock)

        layout = QVBoxLayout()
        
        # Brightness slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(int(self.main_app.overlay.flashlight_overlay.power * 100))
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

        self.dock_widgets.append(self.overlay_dock)

    def update_flashlight_settings(self, value):
        power = value / 100.0
        self.main_app.overlay.flashlight_overlay.set_power(power)
        if power > 0.42:
            new_size = int(200 * (power / 0.42))
            self.main_app.overlay.flashlight_overlay.set_size(new_size)
    def update_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        self.serial_port_picker.clear()
        self.serial_port_picker.addItems([port.device for port in ports])

    def on_serial_port_selected(self, index):
        selected_port = self.serial_port_picker.currentText()
        self.main_app.set_serial_port(selected_port)

    def refresh_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        self.serial_port_picker.clear()
        for port in ports:
            self.serial_port_picker.addItem(port.device)

    def update_flashlight_power(self, value):
        self.flashlight.set_power(value / 100)
