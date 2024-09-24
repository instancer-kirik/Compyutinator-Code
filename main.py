import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QListWidget, QVBoxLayout, QWidget, QLabel, QPushButton
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import QSettings, QByteArray,QProcess,  QUrl, QTimer, Qt, QThread, pyqtSignal
from HMC.sticky_note_manager import StickyNoteManager
import subprocess
from HMC.cccore import CCCore
# Create AuraText directory if it doesn't exist

auratext_dir = os.path.join(os.path.dirname(__file__), 'AuraText')
if not os.path.exists(auratext_dir):
    os.makedirs(auratext_dir)
from HMC.download_manager import DownloadManager
from HMC.widget_manager import WidgetManager
from HMC.transcriptor_live_widget import VoiceTypingWidget
from GUX.overlay import CompositeOverlay, Flashlight
from GUX.log_viewer_widget import LogViewerWidget
import json
from HMC.theme_manager import ThemeManager
from PyQt6.QtGui import QPalette, QColor
from HMC.settings_manager import SettingsManager
from HMC.vault_manager import VaultManager
from PyQt6.QtWidgets import QInputDialog
import threading
from HMC.workspace_manager import WorkspaceManager

log_directory = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

log_file_path = os.path.join(log_directory, 'app.log')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file_path, 'a'), logging.StreamHandler()])
logging.info("Application started")

default_theme = {
    "main_window_color": "#2E3440",
    "window_color": "#3B4252",
    "header_color": "#4C566A",
    "theme_color": "#81A1C1",
    "scrollbar_color": "#4C566A",
    "scrollbar_foreground_color": "#D8DEE9",
    "text_color": "#ECEFF4",
    "tab_colors": {
        0: "#81A1C1",
        1: "#88C0D0",
        2: "#5E81AC",
    },
    "last_focused_tab_color": "#81A1C1"
}

from HMC.workspace_manager import WorkspaceManager

def initialize_managers(settings_manager):
    cccore = CCCore(settings_manager)
    overlay = CompositeOverlay(flashlight_size=200, flashlight_power=0.069, serial_port=None)
    cccore.set_overlay(overlay)
    vault_manager = VaultManager(settings_manager)
    workspace_manager = WorkspaceManager(vault_manager)
    return cccore, vault_manager, workspace_manager, overlay

def merge_themes(default_theme, custom_theme):
    merged_theme = default_theme.copy()
    merged_theme.update(custom_theme)
    return merged_theme
def load_config(config_file):
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file {config_file} not found. Using default configuration.")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding {config_file}. Using default configuration.")
        return {}

from HMC.menu_manager import MenuManager
import tempfile
class MainApplication(QMainWindow):
    def __init__(self, settings_manager, cccore, widget_manager, vault_manager, workspace_manager):
        logging.info("Initializing MainApplication")
        super().__init__()
        self.settings_manager = settings_manager
        self.cccore = cccore
        self.widget_manager = widget_manager
        self.vault_manager = vault_manager
        self.workspace_manager = workspace_manager
        self.config = load_config('config.json')
        self.history = []
        self.max_history_length = 10
        self.last_focused_widget = None
        self.child_processes = {}
        self.overlay = self.cccore.overlay
        
        logging.info("Setting main window for widget_manager")
        self.widget_manager.set_main_window_and_create_docks(self)
        logging.info("Initializing UI")
        self.init_ui()
        logging.info("Loading settings")
        self.load_settings()
        logging.info("Setting up connections")
        self.setup_connections()
        logging.info("Loading splash input")
        self.load_splash_input()
        logging.info("MainApplication initialization complete")

    def init_ui(self):
        self.set_dark_background()
        self.setWindowTitle(self.config['window_title'])
        self.setGeometry(*self.config['window_geometry'])
        self.init_menu_bar()
        self.init_tab_widget()
        self.add_support_box()
        self.add_transcriptor_live_tab()
        self.add_logs_viewer_tab()
        self.flashlight = Flashlight(size=200)

    def setup_connections(self):
        self.tab_widget.currentChanged.connect(self.handle_tab_change)
        self.cccore.theme_manager.theme_changed.connect(self.on_theme_changed)
        QApplication.instance().focusChanged.connect(self.focus_changed_event)

    def load_settings(self):
        self.load_layout()

    def update_history(self, path):
        if path in self.history:
            self.history.remove(path)
        self.history.insert(0, path)
        if len(self.history) > self.max_history_length:
            self.history.pop()

        self.history_widget.clear()
        for item in self.history:
            self.history_widget.addItem(item)

        if self.widget_manager.ai_chat_widget:
            self.widget_manager.ai_chat_widget.set_context(path)

    def handle_tab_change(self, index):
        self.last_focused_widget = self.tab_widget.widget(index)
        self.update_tab_color(index)

    def focus_changed_event(self, old, new):
        if new is not None and isinstance(new, QWidget):
            for dock_name, dock_widget in self.widget_manager.dock_widgets.items():
                if dock_widget.isAncestorOf(new):
                    self.last_focused_widget = dock_widget
                    self.update_tab_color(self.tab_widget.indexOf(self.last_focused_widget))
                    break

    def update_tab_color(self, index):
        tab_color = self.cccore.theme_manager.current_theme.get("tab_colors", {}).get(index, 
                    self.cccore.theme_manager.current_theme.get("last_focused_tab_color", "#81A1C1"))
        self.apply_tab_color(tab_color, index)

    def apply_tab_color(self, color, index):
        stylesheet = f"""
        QTabBar::tab:selected {{
            background-color: {color};
        }}
        """
        self.tab_widget.setStyleSheet(stylesheet)
        self.cccore.theme_manager.current_theme["last_focused_tab_color"] = color

    def init_tab_widget(self):
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.add_history_tab()

    def add_history_tab(self):
        self.history_widget = QListWidget()
        self.tab_widget.addTab(self.history_widget, "Action History")

    def init_menu_bar(self):
        menu_manager = MenuManager(self)
        self.setMenuBar(menu_manager.create_menu_bar())

    def set_dark_background(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(46, 52, 64))  # Nord theme dark color
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(236, 239, 244))  # Nord theme light color
        self.setPalette(dark_palette)

    def save_layout(self):
        self.settings_manager.save_layout(self)

    def load_layout(self):
        self.settings_manager.load_layout(self)

    def on_theme_changed(self, theme):
        # Apply the new theme to all widgets
        self.cccore.theme_manager.apply_theme(self)
        
        # Update tab colors
        default_tab_color = theme.get("last_focused_tab_color", "#81A1C1")
        tab_colors = theme.get("tab_colors", {})
        
        for index in range(self.tab_widget.count()):
            tab_color = tab_colors.get(str(index), default_tab_color)
            self.apply_tab_color(tab_color, index)
        
        # You might need to update other widgets or elements that are not automatically styled

        # This method should update the AuraTextWindow when the theme changes
        auratext_dock = self.widget_manager.get_or_create_dock('AuraText')
        if auratext_dock:
            auratext_window = auratext_dock.widget()
            auratext_window.apply_theme(theme)

    def set_serial_port(self, port):
        self.serial_port = port
        logging.info(f"Serial port set to {port}")
        if self.serial_port:
            self.overlay.set_serial_port(port)

    def add_support_box(self):
        support_box = QWidget()
        support_layout = QVBoxLayout()
        support_label = QLabel("Support Me - links on github")
        github_button = QPushButton("https://github.com/instancer-kirik/BigLinks")
        github_button.clicked.connect(self.open_github)

        support_layout.addWidget(support_label)
        support_layout.addWidget(github_button)
        support_box.setLayout(support_layout)
        
        self.tab_widget.addTab(support_box, "Support Me")

    def open_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/instancer-kirik/BigLinks"))

    def add_transcriptor_live_tab(self):
        self.transcriptor_live_widget = VoiceTypingWidget(self)
        self.tab_widget.addTab(self.transcriptor_live_widget, "Voice Typing")

    def add_logs_viewer_tab(self):
        self.log_viewer_widget = LogViewerWidget(log_file_path=self.get_log_file_path())
        self.tab_widget.addTab(self.log_viewer_widget, "Logs Viewer")
    
    def get_log_file_path(self):
        return os.path.join(os.getcwd(), 'logs', 'app.log')

    def create_workspace(self):
        vault_dir, ok = QInputDialog.getItem(self, "Select Vault", 
                                             "Choose a vault for the new workspace:", 
                                             self.vault_manager.vault_directories, 0, False)
        if ok and vault_dir:
            name, ok = QInputDialog.getText(self, "New Workspace", "Enter workspace name:")
            if ok and name:
                self.workspace_manager.create_workspace(vault_dir, name)
                self.switch_to_workspace(vault_dir, name)

    def switch_workspace(self):
        vault_dir, ok = QInputDialog.getItem(self, "Select Vault", 
                                             "Choose a vault:", 
                                             self.vault_manager.vault_directories, 0, False)
        if ok and vault_dir:
            workspace_names = self.workspace_manager.get_workspace_names(vault_dir)
            workspace, ok = QInputDialog.getItem(self, "Switch Workspace", 
                                                 "Choose a workspace:", 
                                                 workspace_names, 0, False)
            if ok and workspace:
                self.switch_to_workspace(vault_dir, workspace)

    def switch_to_workspace(self, vault_dir, workspace_name):
        self.workspace_manager.set_active_workspace(vault_dir, workspace_name)
        self.vault_manager.set_default_vault(vault_dir)
        self.load_workspace(self.workspace_manager.get_active_workspace())

    def load_workspace(self, workspace):
        # Close all open files
        if self.widget_manager.auratext_window:
            self.widget_manager.auratext_window.close_all_files()

            # Open files from the active fileset
            for file_path in workspace.get_active_files():
                self.widget_manager.auratext_window.open_file(file_path)

            # Load workspace-specific plugins or settings here
            self.load_workspace_plugins(workspace)

    def load_workspace_plugins(self, workspace):
        # Implement plugin loading logic here
        pass

    def load_splash_input(self):
        temp_dir = tempfile.gettempdir()
        for filename in os.listdir(temp_dir):
            if filename.endswith('.txt'):
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'r') as f:
                    content = f.read()
                os.remove(file_path)  # Delete the temporary file
                self.create_sticky_note_from_splash(content)
                break  # We only need to process one file

    def create_sticky_note_from_splash(self, content):
        sticky_note_manager = self.widget_manager.get_or_create_dock("Sticky Notes")
        if isinstance(sticky_note_manager, StickyNoteManager):
            sticky_note_manager.add_sticky_note(content)
        else:
            logging.error(f"Expected StickyNoteManager, got {type(sticky_note_manager)}")

    def closeEvent(self, event):
        self.cleanup_processes()
        super().closeEvent(event)

    def cleanup_processes(self):
        # Terminate all running processes
        for process in self.child_processes.values():
            if process.state() == QProcess.Running:
                process.terminate()
                process.waitForFinished(1000)  # Wait for 1 second
                if process.state() == QProcess.Running:
                    process.kill()  # Force kill if it doesn't terminate

        # Clear the process dictionary
        self.child_processes.clear()

def main():
    logging.info("Starting main function")
    
    # Start the splash screen process
    logging.info("Starting splash screen process")
    splash_process = subprocess.Popen([sys.executable, 'GUX/splash_process.py'])
    
    logging.info("Creating QApplication")
    app = QApplication(sys.argv)

    # Initialize SettingsManager in the main thread
    logging.info("Initializing SettingsManager")
    settings_manager = SettingsManager()
    
    logging.info("Initializing managers")
    cccore, vault_manager, workspace_manager, overlay = initialize_managers(settings_manager)

    # Set overlay for CCCore
    logging.info("Setting overlay for CCCore")
    cccore.set_overlay(overlay)

    # Create WidgetManager
    logging.info("Creating WidgetManager")
    widget_manager = WidgetManager(cccore, overlay)

    # Set widget_manager for CCCore
    logging.info("Setting widget_manager for CCCore")
    cccore.set_widget_manager(widget_manager)

    # Create the main application instance
    logging.info("Creating MainApplication instance")
    main_app = MainApplication(settings_manager, cccore, widget_manager, vault_manager, workspace_manager)

    # Set the main_window for widget_manager
    logging.info("Setting main_window for widget_manager")
    widget_manager.set_main_window_and_create_docks(main_app)

    # Function to show the application
    def show_app():
        logging.info("Showing main application")
        main_app.show()
        
        # Terminate the splash screen process
        splash_process.terminate()

    # Start the show process
    QTimer.singleShot(0, show_app)

    sys.exit(app.exec())

if __name__ == '__main__':
    main()

   
