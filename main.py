import sys
import os
from PyQt6.QtCore import QThreadPool
# Get the absolute path of the directory containing the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Add the project root directory to Python path
sys.path.insert(0, script_dir)
import cProfile
import pstats
from NITTY_GRITTY.ThreadTrackers import ThreadTracker, QThreadTracker, global_thread_tracker, global_qthread_tracker
profiler = cProfile.Profile()
from HMC.config_manager import ConfigManager
# Now try to import from HMC
from HMC.cccore import CCCore
from HMC.sticky_note_manager import StickyNoteManager
from PyQt6.QtWidgets import QWidget
import io
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QInputDialog, QMessageBox, QFileDialog, QTabWidget, QListWidget, QVBoxLayout, QWidget, QLabel, QPushButton
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import QMenu, QSizePolicy, QToolBar
from PyQt6.QtCore import QSettings, QByteArray, QRect, QProcess,  QUrl, QTimer, Qt, pyqtSignal
from DEV.websocket_client import WebSocketClient
from riskkit.client import RiskkitClient
import subprocess
import asyncio
from HMC.cccore import CCCore
from HMC.sticky_note_manager import StickyNoteManager
# Create AuraText directory if it doesn't exist

auratext_dir = os.path.join(script_dir, 'AuraText')
if not os.path.exists(auratext_dir):
    os.makedirs(auratext_dir)
from HMC.download_manager import DownloadManager
from HMC.widget_manager import WidgetManager
from HMC.transcriptor_live_widget import VoiceTypingWidget
from GUX.overlay import CompositeOverlay, Flashlight
import json
from HMC.theme_manager import ThemeManager
from PyQt6.QtGui import QPalette, QColor

from PyQt6.QtWidgets import QInputDialog
import threading
from HMC.workspace_manager import WorkspaceManager
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QEvent
from NITTY_GRITTY.ThreadTrackers import SafeQThread
from GUX.widgets.many_project_manager_widget import ManyProjectsManagerWidget
from PyQt6.QtWidgets import QDockWidget
from HMC.vm_manager import VMManagerWidget
from HMC.history_manager import HistoryManager
from HMC.toolbar_manager import ToolbarManager
from HMC.menu_manager import MenuManager

log_directory = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

log_file_path = os.path.join(log_directory, 'app.log')

# Remove duplicate logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, 'a'),
        logging.StreamHandler()
    ],
    force=True  # Force reconfiguration
)

# Remove the second logging.basicConfig call
# logging.basicConfig(level=logging.DEBUG, ...)  # Remove this

#this not showing any logs wtf
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
import signal

def signal_handler(signum, frame):
    logging.critical(f"Received signal: {signum}")
    # Force exit without waiting for threads
    os._exit(1)

# In your main function:
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Use a timer to process signals
timer = QTimer()
timer.start(500)
timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms

def qt_thread_exception_handler(type, value, tb):
    logging.critical("Uncaught exception in QThread:", exc_info=(type, value, tb))
    sys.__excepthook__(type, value, tb)

#SafeQThread.setExceptionHandler(qt_thread_exception_handler)

from HMC.workspace_manager import WorkspaceManager

def initialize_core(config_manager):
    # Create CCCore with settings manager
    cccore = CCCore(config_manager)
    
    # Create overlay after CCCore is initialized
    overlay = CompositeOverlay(
        cccore, 
        flashlight_size=200, 
        flashlight_power=0.069, 
        serial_port=None
    )
    
    return cccore, overlay

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

import traceback  # Add this import at the top of the file
from HMC.event_manager import AppEventManager, AppEvent
from typing import Optional
from HMC.notification_manager import NotificationManager,  NotificationPriority
from GUX.dialogs.login_dialog import LoginDialog
from riskkit.events import NotificationType

from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QDockWidget, 
    QWidget, QVBoxLayout, QLabel, QTabWidget,
    QComboBox, QApplication, QSizePolicy, QHBoxLayout
)
from PyQt6.QtGui import QIcon, QPalette, QColor, QAction
from PyQt6.QtCore import (
    Qt, QSettings, QTimer, QRect, 
    QPoint, QSize, QByteArray
)

class MainApplication(QMainWindow):
    def __init__(self, cccore, widget_manager):
        super().__init__()
        self.cccore = cccore
        
        self.widget_manager = widget_manager
        # Add opacity animation initialization
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(200)  # 200ms duration
        self.is_dragging = False 
        try:
            self.setup_window()
            self.setup_ui()    
            # Initialize managers
            self.menu_manager = MenuManager(self, self.cccore)
            
            # Create toolbars
            self.create_toolbars()
            
            # Initialize other UI components
           
            self.setup_connections()
            
            logging.info("MainApplication initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing MainApplication: {e}")

    def create_toolbars(self):
        """Create and initialize all toolbars"""
        try:
            # Main toolbar
            self.main_toolbar = self.addToolBar("Main")
            self.main_toolbar.setObjectName("MainToolbar")
            
            # File dropdown
            file_button = QPushButton("File")
            file_menu = QMenu()
            file_actions = [
                ("New", "Ctrl+N", self.cccore.action_handlers.new_file),
                ("Open", "Ctrl+O", self.cccore.action_handlers.open_file),
                ("Save", "Ctrl+S", self.cccore.action_handlers.save_file),
                ("Save As", "Ctrl+Shift+S", self.cccore.action_handlers.save_file_as),
            ]
            for name, shortcut, handler in file_actions:
                action = QAction(name, self)
                action.setShortcut(shortcut)
                action.triggered.connect(handler)
                file_menu.addAction(action)
            file_button.setMenu(file_menu)
            self.main_toolbar.addWidget(file_button)

            # Edit dropdown
            edit_button = QPushButton("Edit")
            edit_menu = QMenu()
            edit_actions = [
                ("Undo", "Ctrl+Z", self.cccore.action_handlers.undo),
                ("Redo", "Ctrl+Shift+Z", self.cccore.action_handlers.redo),
                (None, None, None),  # Separator
                ("Cut", "Ctrl+X", self.cccore.action_handlers.cut_document),
                ("Copy", "Ctrl+C", self.cccore.action_handlers.copy_document),
                ("Paste", "Ctrl+V", self.cccore.action_handlers.paste_document),
            ]
            for name, shortcut, handler in edit_actions:
                if name is None:
                    edit_menu.addSeparator()
                    continue
                action = QAction(name, self)
                action.setShortcut(shortcut)
                action.triggered.connect(handler)
                edit_menu.addAction(action)
            edit_button.setMenu(edit_menu)
            self.main_toolbar.addWidget(edit_button)

            # Add workspace selector
            if hasattr(self.cccore, 'widget_manager'):
                workspace_selector = self.cccore.widget_manager.get_workspace_selector()
                if workspace_selector:
                    self.main_toolbar.addWidget(workspace_selector)

            logging.info("Toolbars created successfully")
        except Exception as e:
            logging.error(f"Error creating toolbars: {e}")

    def toggle_dock(self, dock_name):
        """Toggle visibility of a dock widget"""
        try:
            if hasattr(self.cccore, 'widget_manager'):
                dock = self.cccore.widget_manager.get_dock(dock_name)
                if dock:
                    dock.setVisible(not dock.isVisible())
                    # Update action state
                    action = self.sender()
                    if isinstance(action, QAction):
                        action.setChecked(dock.isVisible())
        except Exception as e:
            logging.error(f"Error toggling dock {dock_name}: {e}")

    def setup_ui(self):
        """Initialize all UI components"""
        try:
            # Set window properties
            
            self.setDockOptions(
                QMainWindow.DockOption.AllowTabbedDocks |
                QMainWindow.DockOption.AllowNestedDocks
            )
            
            # Create central widget and layout first
            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)
            self.central_layout = QVBoxLayout(self.central_widget)
            
            # Initialize core managers
            if not hasattr(self, 'cccore'):
                logging.error("CCCore not initialized")
                return
                
            # Initialize UI managers
            self.menu_manager = MenuManager(self, self.cccore)
            self.toolbar_manager = ToolbarManager(self, self.cccore)
            
            # Create menus and toolbars
            menubar = self.menu_manager.create_menu_bar()
            self.setMenuBar(menubar)
            
            # Create toolbars
            self.toolbar_manager.create_main_toolbar()
            self.toolbar_manager.create_tools_toolbar()
            
            # Initialize tab widget through widget manager
            if hasattr(self.cccore, 'widget_manager'):
                tab_widget = self.cccore.widget_manager.setup_central_tabs()
                if not tab_widget:
                    logging.error("Failed to initialize tab widget")
            
            # Setup remaining connections
            self.setup_connections()
            
            logging.info("MainApplication UI initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing MainApplication UI: {e}")
            logging.error(traceback.format_exc())

    def setup_main_toolbar(self):
        """Initialize main toolbar"""
        try:
            self.main_toolbar = QToolBar("Main Tools")
            self.main_toolbar.setObjectName("MainToolbar")
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_toolbar)
            
            # Add file operations
            actions = {
                'New': ('Ctrl+N', self.cccore.action_handlers.new_file, 'New File'),
                'Open': ('Ctrl+O', self.cccore.action_handlers.open_file, 'Open File'),
                'Save': ('Ctrl+S', self.cccore.action_handlers.save_file, 'Save File'),
            }
            
            for name, (shortcut, handler, tooltip) in actions.items():
                action = QAction(name, self)
                action.setShortcut(shortcut)
                action.setToolTip(tooltip)
                action.triggered.connect(handler)
                self.main_toolbar.addAction(action)
            
            self.main_toolbar.addSeparator()
            
            # Add workspace selector
            if hasattr(self.cccore, 'widget_manager'):
                workspace_selector = self.cccore.widget_manager.get_workspace_selector()
                if workspace_selector:
                    self.main_toolbar.addWidget(workspace_selector)
            
            logging.info("Main toolbar initialized")
        except Exception as e:
            logging.error(f"Error setting up main toolbar: {e}")

    def setup_tools_toolbar(self):
        """Initialize tools toolbar"""
        try:
            self.tools_toolbar = QToolBar("Tools")
            self.tools_toolbar.setObjectName("ToolsToolbar")
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.tools_toolbar)
            
            # Add tool toggles
            toggles = {
                'Log Viewer': self.cccore.widget_manager.create_log_viewer,
                'Voice Typing': self.cccore.widget_manager.create_voice_typing,
                'File Explorer': self.cccore.widget_manager.create_file_explorer,
                'Terminal': self.cccore.widget_manager.create_terminal,
                'Process Manager': self.cccore.widget_manager.create_process_manager
            }
            
            for name, creator in toggles.items():
                action = QAction(name, self)
                action.setCheckable(True)
                action.triggered.connect(lambda checked, c=creator: self.toggle_tool(checked, c))
                self.tools_toolbar.addAction(action)
            
            logging.info("Tools toolbar initialized")
        except Exception as e:
            logging.error(f"Error setting up tools toolbar: {e}")

    def toggle_tool(self, checked, creator_func):
        """Toggle visibility of a tool widget"""
        try:
            widget = creator_func()
            if widget:
                widget.setVisible(checked)
        except Exception as e:
            logging.error(f"Error toggling tool: {e}")

    def setup_central_tabs(self):
        """Initialize central tab widgets"""
        try:
            if not hasattr(self, 'tab_widget'):
                logging.error("Tab widget not initialized")
                return
                
            # Add logging widget
            log_widget = self.cccore.widget_manager.create_widget('LogViewer')
            if log_widget:
                self.tab_widget.addTab(log_widget, "Logs")
                logging.info("Added logging widget to tabs")
                
            # Add STT widget
            stt_widget = self.cccore.widget_manager.create_widget('VoiceTyping')
            if stt_widget:
                self.tab_widget.addTab(stt_widget, "Voice Typing")
                logging.info("Added STT widget to tabs")
                
            # Set the tab widget in widget manager
            if hasattr(self.cccore, 'widget_manager'):
                self.cccore.widget_manager.set_tab_widget(self.tab_widget)
                
            # Make sure tab widget is visible
            self.tab_widget.show()
            logging.info("Central tabs initialized successfully")
            
        except Exception as e:
            logging.error(f"Error setting up central tabs: {e}")

    def restore_window_state(self):
        """Restore all window state information"""
        try:
            # Restore window geometry and state
            if self.settings.contains('window/geometry'):
                self.restoreGeometry(self.settings.value('window/geometry'))
            if self.settings.contains('window/state'):
                self.restoreState(self.settings.value('window/state'))
            if self.settings.value('window/maximized', False, type=bool):
                self.showMaximized()
                
            # Restore dock widget states
            dock_states = self.settings.value('docks/states', {})
            if isinstance(dock_states, dict):
                for name, state in dock_states.items():
                    dock = self.cccore.widget_manager.dock_widgets.get(name)
                    if dock:
                        if state.get('floating', False):
                            dock.setFloating(True)
                        self.addDockWidget(Qt.DockWidgetArea(state.get('area', 1)), dock)
                        dock.setVisible(state.get('visible', True))
            
            # Restore tab state
            if hasattr(self, 'tab_widget'):
                current_tab = self.settings.value('tabs/current', 0, type=int)
                if self.tab_widget.count() > current_tab:
                    self.tab_widget.setCurrentIndex(current_tab)
                    
            logging.info("Window state restored successfully")
        except Exception as e:
            logging.error(f"Error restoring window state: {e}")

    def save_window_state(self):
        """Save window state to settings"""
        try:
            settings = QSettings()
            settings.setValue("mainwindow/geometry", self.saveGeometry())
            settings.setValue("mainwindow/state", self.saveState())
            settings.setValue("mainwindow/maximized", self.isMaximized())
            logging.info("Window state saved successfully")
        except Exception as e:
            logging.error(f"Error saving window state: {e}")

    def save_window_state(self):
        """Save current window state"""
        try:
            if hasattr(self, 'settings'):
                self.settings.setValue('window_state', self.saveState())
                self.settings.setValue('window_geometry', self.geometry().getRect())
                logging.info("Window state saved successfully")
        except Exception as e:
            logging.error(f"Error saving window state: {e}")
            logging.error(traceback.format_exc())

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            self.save_window_state()
            super().closeEvent(event)
        except Exception as e:
            logging.error(f"Error in closeEvent: {e}")
            logging.error(traceback.format_exc())
            event.accept()
    
    def init_menu_bar(self):
        """Initialize the menu bar"""
        try:
            self.menuBar().clear()
            
            # Create main menus
            self.file_menu = self.menuBar().addMenu("&File")
            self.edit_menu = self.menuBar().addMenu("&Edit")
            self.view_menu = self.menuBar().addMenu("&View")
            self.tools_menu = self.menuBar().addMenu("&Tools")
            self.vault_menu = self.menuBar().addMenu("&Vault")
            self.graph_menu = self.menuBar().addMenu("&Graph")
            self.workspace_menu = self.menuBar().addMenu("&Workspace")
            self.help_menu = self.menuBar().addMenu("&Help")
            
            # Add risk manager to View menu if dock exists
            if "Risk Manager" in self.widget_manager.dock_widgets:
                risk_dock = self.widget_manager.dock_widgets["Risk Manager"]
                self.view_menu.addAction(risk_dock.toggleViewAction())
            
            # Let menu manager handle the rest
            if hasattr(self, 'menu_manager'):
                self.menu_manager.setup_menus()
            
        except Exception as e:
            logging.error(f"Error creating menu bar: {e}")

    def init_managers(self):
        """Initialize all managers"""
        try:
            self.widget_manager = self.cccore.widget_manager
            self.widget_manager.set_main_window(self)
            self.menu_manager = MenuManager(self, self.cccore)
            self.cccore.set_menu_manager(self.menu_manager)
            logging.info("Managers initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing managers: {str(e)}")
            logging.error(traceback.format_exc())

    def setup_window(self):
        """Setup basic window properties"""
        self.setWindowTitle("Compyutinator Code")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinMaxButtonsHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def maximize_restore(self):
        """Toggle between maximized and normal window state"""
        try:
            if self.isMaximized():
                self.showNormal()
                self.is_maximized = False
            else:
                self.showMaximized()
                self.is_maximized = True
        except Exception as e:
            logging.error(f"Error in maximize_restore: {e}")

    def mouseDoubleClickEvent(self, event):
        """Handle double-click on title bar"""
        try:
            if event.position().y() <= self.title_bar_height:
                self.maximize_restore()
        except Exception as e:
            logging.error(f"Error in mouseDoubleClickEvent: {e}")
        super().mouseDoubleClickEvent(event)

    def setup_window_state(self):
        """Initialize window state"""
        try:
            # Enable maximize/minimize buttons
            self.setWindowState(Qt.WindowState.WindowActive)
            
            # Restore saved state if exists
            settings = QSettings()
            if settings.contains("windowState"):
                self.restoreState(settings.value("windowState"))
            if settings.contains("windowGeometry"):
                self.restoreGeometry(settings.value("windowGeometry"))
                
            # Add maximize button to title bar
            maximize_action = QAction("Maximize", self)
            maximize_action.triggered.connect(self.maximize_restore)
            self.addAction(maximize_action)
            
            logging.info("Window state handling initialized")
        except Exception as e:
            logging.error(f"Error setting up window state: {e}")

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Save window state
            settings = QSettings()
            settings.setValue("windowState", self.saveState())
            settings.setValue("windowGeometry", self.saveGeometry())
            
            super().closeEvent(event)
        except Exception as e:
            logging.error(f"Error saving window state: {e}")

    def set_default_window_state(self, screen_geometry=None):
        """Set default window size and position"""
        if screen_geometry is None:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.geometry()
            else:
                return
        
        # Set to 80% of screen size
        width = int(screen_geometry.width() * 0.8)
        height = int(screen_geometry.height() * 0.8)
        
        # Center on screen
        x = screen_geometry.x() + (screen_geometry.width() - width) // 2
        y = screen_geometry.y() + (screen_geometry.height() - height) // 2
        
        self.setGeometry(x, y, width, height)

    def mousePressEvent(self, event):
        """Handle mouse press events"""
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self.is_dragging = True
                self.drag_position = event.globalPosition().toPoint()
        except Exception as e:
            logging.error(f"Error in mousePressEvent: {e}")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self.is_dragging = False
                self.drag_position = None
        except Exception as e:
            logging.error(f"Error in mouseReleaseEvent: {e}")
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        try:
            if not self.is_dragging:
                return
                
            if self.isMaximized():
                return
                
            if self.drag_position is not None:
                delta = event.globalPosition().toPoint() - self.drag_position
                self.move(self.pos() + delta)
                self.drag_position = event.globalPosition().toPoint()
        except Exception as e:
            logging.error(f"Error in mouseMoveEvent: {e}")
        super().mouseMoveEvent(event)

    def snap_to_right_half(self):
        """Snap window to right half of screen"""
        current_screen = self.screen()
        if current_screen:
            screen_geometry = current_screen.availableGeometry()
            target_geometry = QRect(
                screen_geometry.width() // 2,
                screen_geometry.y(),
                screen_geometry.width() // 2,
                screen_geometry.height()
            )
            self._animate_snap(target_geometry)

    def snap_to_left_half(self):
        """Snap window to left half of screen"""
        current_screen = self.screen()
        if current_screen:
            screen_geometry = current_screen.availableGeometry()
            target_geometry = QRect(
                screen_geometry.x(),
                screen_geometry.y(),
                screen_geometry.width() // 2,
                screen_geometry.height()
            )
            self._animate_snap(target_geometry)

    def snap_to_top(self):
        """Snap window to top of screen"""
        current_screen = self.screen()
        if current_screen:
            screen_geometry = current_screen.availableGeometry()
            target_geometry = QRect(
                screen_geometry.x(),
                screen_geometry.y(),
                screen_geometry.width(),
                screen_geometry.height() // 2
            )
            self._animate_snap(target_geometry)

    def _animate_snap(self, target_geometry):
        """Animate window snapping"""
        self.snap_animation.setStartValue(self.geometry())
        self.snap_animation.setEndValue(target_geometry)
        self.snap_animation.start()

    def maximize(self):
        """Maximize the window"""
        current_screen = self.screen()
        if current_screen:
            screen_geometry = current_screen.availableGeometry()
            self.setGeometry(screen_geometry)

    def changeEvent(self, event):
        """Handle window state changes"""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMaximized:
                self.is_maximized = True
            else:
                self.is_maximized = False
        super().changeEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double-click on title bar for maximize/restore"""
        if event.position().y() <= self.title_bar_height:
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for window management"""
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                if self.is_maximized:
                    self.showMaximized()
                else:
                    self.showNormal()
            else:
                self.showFullScreen()
        elif event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            if event.key() == Qt.Key.Key_Up:
                if not self.isMaximized():
                    self.showMaximized()
            elif event.key() == Qt.Key.Key_Down:
                if self.isMaximized():
                    self.showNormal()
            elif event.key() == Qt.Key.Key_Left:
                self.snap_to_left_half()
            elif event.key() == Qt.Key.Key_Right:
                self.snap_to_right_half()
        super().keyPressEvent(event)

    def enterEvent(self, event):
        """Handle mouse enter events"""
        if self.windowOpacity() < 1.0:
            self.opacity_animation.setStartValue(self.windowOpacity())
            self.opacity_animation.setEndValue(1.0)
            self.opacity_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave events"""
        if not self.isActiveWindow() and self.config_manager.get_value("enable_window_fade", False):
            self.opacity_animation.setStartValue(self.windowOpacity())
            self.opacity_animation.setEndValue(0.85)
            self.opacity_animation.start()
        super().leaveEvent(event)
        
       
    def update_history(self, path):
        """Update history using the history manager"""
        self.history_manager.update_history(path)
        if self.widget_manager.ai_chat_widget:
            self.widget_manager.ai_chat_widget.set_context(path)

    def show_status_message(self, message: str, error: bool = False):
        """Show status message in status bar"""
        if error:
            self.statusBar().setStyleSheet("color: red")
        else:
            self.statusBar().setStyleSheet("")
        self.statusBar().showMessage(message, 5000)  # Show for 5 seconds

    def _process_async_events(self):
        """Process pending async events"""
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()

    def cleanup(self):
        """Cleanup application resources"""
        try:
            # Stop any active timers first
            for child in self.findChildren(QTimer):
                child.stop()

            # Use synchronous cleanup for client
            if hasattr(self, 'client') and self.client:
                self.client.sync_close()  # Use sync version instead of async
                
            # Cleanup processes
            self.cleanup_processes()
            
            # Clean up any remaining threads
            if hasattr(self, 'thread') and self.thread:
                self.thread.quit()
                self.thread.wait()
                
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            
  
    def cleanup_processes(self):
        """Cleanup child processes"""
        for process in self.child_processes.values():
            try:
                process.terminate()
                process.waitForFinished(1000)  # Wait up to 1 second
                if process.state() == QProcess.ProcessState.Running:
                    process.kill()  # Force kill if still running
            except Exception as e:
                logging.warning(f"Error cleaning up process: {e}")

    def setup_client(self):
        """Setup RiskkitClient and related widgets"""
        api_config = self.config_manager.get_api_config()
        self.client = RiskkitClient(api_config)
        
        # Create risk manager widget using widget manager
        if hasattr(self.widget_manager, 'RiskManagerWidget'):
            self.risk_manager = self.widget_manager.RiskManagerWidget(self.cccore)
            # Create a dock widget for the risk manager
            risk_dock = self.widget_manager.get_or_create_dock("Risk Manager")
            if risk_dock:
                self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, risk_dock)
                # Add toggle action to View menu
                self.cccore.menu_manager.view_menu.addAction(risk_dock.toggleViewAction())

    def get_auth_token(self) -> Optional[str]:
        """Get authentication token from settings or login"""
        token = self.config_manager.get_setting("auth_token")
        if not token:
            # Show login dialog
            success = self.show_login_dialog()
            if not success:
                return None
            token = self.config_manager.get_setting("auth_token")
        return token

    def handle_auth_failure(self, error_msg: str):
        """Handle authentication failures"""
        self.notification_manager.add_notification(
            type=NotificationType.SECURITY,
            priority=NotificationPriority.HIGH,
            title="Authentication Failed",
            message=error_msg,
            action="Login Again"
        )
        # Clear stored token
        self.config_manager.set_setting("auth_token", "")
        
        # Show login dialog
        self.show_login_dialog()

    def show_login_dialog(self) -> bool:
        """Show login dialog and handle authentication"""
        dialog = LoginDialog(self)
        if dialog.exec():
            # Store new token
            self.config_manager.set_setting("auth_token", dialog.token)
            return True
        return False
      
       
    def setup_websocket(self):
        """Initialize and setup WebSocket client"""
        self.ws_client = WebSocketClient(
            base_url=self.config_manager.get_setting("websocket_url", "ws://localhost:4000"),
            token=self.config_manager.get_setting("websocket_token", "")
        )
        
        # Connect all signals
        self.setup_websocket_connections()
        
        # Subscribe to all channels if enabled in settings
        if self.config_manager.get_setting("subscribe_to_all_channels", True):
            self.ws_client.subscribe_to_all_channels()
        
        self.ws_client.connect_to_server()

    def setup_websocket_connections(self):
        """Setup all WebSocket event handlers"""
        if not hasattr(self, 'ws_client'):
            return

        # Project-related connections
        self.ws_client.risk_created.connect(self.on_risk_created)
        self.ws_client.risk_updated.connect(self.on_risk_updated)
        self.ws_client.risk_deleted.connect(self.on_risk_deleted)

        # News and events connections
        self.ws_client.news_received.connect(self.on_news_received)
        self.ws_client.event_received.connect(self.on_event_received)
        self.ws_client.notification_received.connect(self.on_notification_received)
        self.ws_client.system_status_updated.connect(self.on_system_status_updated)

    def on_news_received(self, news_data: dict):
        """Handle incoming news updates"""
        if hasattr(self.widget_manager, 'news_widget'):
            self.widget_manager.news_widget.add_news_item(news_data)
        # Optionally show notification
        self.show_notification("News Update", news_data.get("title", ""))

    def on_event_received(self, event_data: dict):
        """Handle incoming events"""
        if hasattr(self.widget_manager, 'event_widget'):
            self.widget_manager.event_widget.add_event(event_data)
        # Optionally show notification
        self.show_notification("New Event", event_data.get("title", ""))

    def on_system_status_updated(self, status_data: dict):
        """Handle system status updates"""
        if hasattr(self.widget_manager, 'status_widget'):
            self.widget_manager.status_widget.update_status(status_data)
        
        # Update status bar if critical
        if status_data.get("priority") == "critical":
            self.statusBar().showMessage(status_data.get("message", ""))

    def show_notification(self, title: str, message: str):
        """Show system notification"""
        if self.config_manager.get_setting("show_notifications", True):
            # You can implement this using your preferred notification system
            pass

   
    def setup_toolbars(self):
        """Setup all toolbars in one place"""
        try:
            # Main toolbar
            self.main_toolbar = QToolBar("Main Toolbar", self)
            self.main_toolbar.setObjectName("MainToolbar")  # Required for state saving
            self.addToolBar(self.main_toolbar)
            
            # Add basic actions
            self.main_toolbar.addAction(QIcon(), "New", self.cccore.action_handlers.new_file)
            self.main_toolbar.addAction(QIcon(), "Open", self.cccore.action_handlers.open_file)
            self.main_toolbar.addAction(QIcon(), "Save", self.cccore.action_handlers.save_file)
            
            # Workspace toolbar
            self.workspace_toolbar = QToolBar("Workspace", self)
            self.workspace_toolbar.setObjectName("WorkspaceToolbar")
            self.addToolBar(self.workspace_toolbar)
            
            # Add workspace selector
            workspace_widget = QWidget()
            workspace_layout = QHBoxLayout(workspace_widget)
            workspace_layout.setContentsMargins(0, 0, 0, 0)
            workspace_layout.addWidget(QLabel("Workspace:"))
            self.workspace_selector = QComboBox()
            self.workspace_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            workspace_layout.addWidget(self.workspace_selector)
            self.workspace_toolbar.addWidget(workspace_widget)
            
            # Remove duplicate toolbar initializations
            if hasattr(self, 'toolbar'):
                self.removeToolBar(self.toolbar)
                del self.toolbar
                
            logging.info("All toolbars initialized successfully")
            
        except Exception as e:
            logging.error(f"Error setting up toolbars: {e}")

    def setup_ui(self):
        """Initialize all UI components"""
        try:
            
            # Create central widget first
            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)
            self.central_layout = QVBoxLayout(self.central_widget)
            
            # Initialize tab widget first
            self.tab_widget = QTabWidget()
            self.tab_widget.setTabsClosable(True)
            self.tab_widget.setMovable(True)
            self.central_layout.addWidget(self.tab_widget)
            
            # Set the tab widget in widget manager
            if hasattr(self.cccore, 'widget_manager'):
                self.cccore.widget_manager.tab_widget = self.tab_widget
                self.cccore.widget_manager.main_window = self
            
            # Initialize UI managers
            self.menu_manager = MenuManager(self, self.cccore)
            self.toolbar_manager = ToolbarManager(self, self.cccore)
            
            # Create menus and toolbars
            self.setMenuBar(self.menu_manager.create_menu_bar())
            self.addToolBar(self.toolbar_manager.create_main_toolbar())
            self.addToolBar(self.toolbar_manager.create_tools_toolbar())
            
            logging.info("MainApplication UI initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing MainApplication UI: {e}")
            logging.error(traceback.format_exc())

    def setup_connections(self):
        """Set up signal connections"""
        try:
            # Connect tab widget signals if it exists
            if hasattr(self, 'tab_widget') and self.tab_widget:
                self.tab_widget.currentChanged.connect(self.handle_tab_change)
                logging.debug("Successfully connected tab changed signal")
            
            # Connect workspace selector signals using widget manager
            workspace_selector = self.cccore.widget_manager.get_workspace_selector()
            if workspace_selector:
                workspace_selector.currentTextChanged.connect(self.on_workspace_changed)
                logging.info("Workspace selector signals connected")
            else:
                logging.warning("Workspace selector not initialized, skipping signal connection")
                
        except Exception as e:
            logging.error(f"Error setting up connections: {str(e)}")
            logging.error(traceback.format_exc())

    def on_workspace_changed(self, workspace_name):
        """Handle workspace change"""
        try:
            if workspace_name:
                self.cccore.set_current_workspace(workspace_name)
                logging.info(f"Workspace changed to: {workspace_name}")
                # Update any UI elements that depend on workspace
                self.update_workspace_dependent_ui()
        except Exception as e:
            logging.error(f"Error changing workspace: {str(e)}")
            logging.error(traceback.format_exc())
            
    def dump_thread_info():
        logging.critical("Active threads at exit:")
        for thread in global_thread_tracker.get_active_threads():
            logging.critical(f"Thread {thread.name} (ID: {thread.ident}) is still running")
            stack = traceback.format_stack(sys._current_frames()[thread.ident])
            logging.critical("".join(stack))
        
        for thread in global_qthread_tracker.get_active_threads():
            logging.critical(f"QThread {thread.objectName()} is still running")

    def setup_menu(self):
        if hasattr(self, 'menu_setup_done') and self.menu_setup_done:
            logging.warning("Menu setup already done, skipping")
            return
        try:
            logging.info("Setting up menu")
            self.menu_manager = MenuManager(main_window=self, cccore=self.cccore)
            self.menuBar = self.menu_manager.create_menu_bar()
            self.setMenuBar(self.menuBar)
            logging.info("Menu setup complete")
            self.menu_setup_done = True
        except Exception as e:
            logging.error(f"Error setting up menu: {str(e)}")
            logging.error(traceback.format_exc())

    def load_settings(self):
        self.load_layout()

    def setup_workspace_selector(self):
        """Initialize the workspace selector"""
        try:
            if hasattr(self.cccore, 'widget_manager'):
                # Update workspace selector items
                if hasattr(self, 'workspace_selector'):
                    self.workspace_selector.clear()
                    
                    current_vault = self.cccore.vault_manager.get_current_vault()
                    if current_vault:
                        workspaces = self.cccore.workspace_manager.get_workspaces(current_vault.path)
                        if workspaces:
                            self.workspace_selector.addItems(workspaces)
                            
                            current_workspace = self.cccore.workspace_manager.get_active_workspace(
                                vault_path=current_vault.path
                            )
                            if current_workspace:
                                index = self.workspace_selector.findText(current_workspace)
                                if index >= 0:
                                    self.workspace_selector.setCurrentIndex(index)
                                    
                    logging.info("Workspace selector updated successfully")
                    
        except Exception as e:
            logging.error(f"Error setting up workspace selector: {e}")
            logging.error(traceback.format_exc())

    def set_vault(self, vault_path):
        self.setWindowTitle(f"AuraText - Main Vault: {os.path.basename(vault_path)}")
        self.cccore.vault_manager.set_current_vault(vault_path)
        self.load_vault(vault_path)

    def load_vault(self, vault_path):
        # Load main vault-specific data
        workspaces = self.cccore.workspace_manager.get_workspace_names(vault_path)
        self.update_workspace_list(workspaces)
        self.cccore.project_manager.load_projects(vault_path)

    def update_workspace_list(self, workspaces):
        # Update UI with the list of workspaces for the main vault
        pass

    def open_new_vault(self):
        vault_path = QFileDialog.getExistingDirectory(self, "Select Vault Directory")
        if vault_path:
            self.cccore.open_vault(vault_path)

    def on_workspace_changed(self, workspace_name):
        """Handle workspace change"""
        try:
            if workspace_name:
                self.cccore.set_current_workspace(workspace_name)
                logging.info(f"Workspace changed to: {workspace_name}")
                # Update any UI elements that depend on workspace
                self.update_workspace_dependent_ui()
        except Exception as e:
            logging.error(f"Error changing workspace: {str(e)}")
            logging.error(traceback.format_exc())

    def update_workspace_dependent_ui(self):
        """Update UI elements that depend on workspace"""
        try:
            # Update window title
            self.setWindowTitle(f"Computinator Code - {self.cccore.get_current_workspace()}")
            
            # Update other workspace-dependent elements
            if hasattr(self.cccore, 'widget_manager'):
                self.cccore.widget_manager.apply_theme_to_all_widgets()
                
        except Exception as e:
            logging.error(f"Error updating workspace UI: {str(e)}")
            logging.error(traceback.format_exc())

    def handle_tab_change(self, index):
        self.last_focused_widget = self.tab_widget.widget(index)
        self.update_tab_color(index)

    def focus_changed_event(self, old, new):
        if new is not None and isinstance(new, QWidget):
            for dock_name, dock_widget in self.widget_manager.dock_widgets.items():
                if dock_widget.isAncestorOf(new):
                    self.last_focused_widget = dock_widget
                    if self.tab_widget:
                        self.update_tab_color(self.tab_widget.indexOf(self.last_focused_widget))
                    break

    def update_tab_color(self, index):
        current_theme = self.cccore.theme_manager.get_current_theme()
        if isinstance(current_theme, dict):  # Add this check
            tab_color = current_theme.get("tab_colors", {}).get(index,
                                                                current_theme.get("theme_color", "#81A1C1"))
            self.tab_widget.tabBar().setTabTextColor(index, QColor(tab_color))
        else:
            logging.error(f"Invalid theme type: {type(current_theme)}")

    def apply_tab_color(self, color, index):
        stylesheet = f"""
        QTabBar::tab:selected {{
            background-color: {color};
        }}
        """
        self.tab_widget.setStyleSheet(stylesheet)
        self.cccore.theme_manager.set_last_focused_tab_color(color)

    
    def set_dark_background(self):
        dark_palette = self.palette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(46, 52, 64))  # Nord theme dark color
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(236, 239, 244))  # Nord theme light color
        self.setPalette(dark_palette)

        # Apply dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2E3440;
                color: #D8DEE9;
            }
        """)

    def save_layout(self):
        self.config_manager.save_layout(self)

    def load_layout(self):
        self.config_manager.load_layout(self)

    def on_theme_changed(self, theme_name):
        logging.info(f"Theme changed to: {theme_name}")
        self.update_ui_after_theme_change()

    def update_ui_after_theme_change(self):
        # Update any UI elements that need special handling after a theme change
        self.update_tab_colors()
        self.refresh_widgets_after_theme_change()

    def refresh_widgets_after_theme_change(self):
        for dock_name, dock in self.cccore.widget_manager.dock_widgets.items():
            if dock and not self.cccore.widget_manager.is_dock_deleted(dock):
                widget = dock.widget()
                if widget and hasattr(widget, 'apply_theme'):
                    widget.apply_theme()
            else:
                logging.warning(f"Invalid dock or widget for {dock_name}")
        
    def update_tab_colors(self):
        # Update tab colors if needed
        pass

    def set_serial_port(self, port):
        self.serial_port = port
        logging.info(f"Serial port set to {port}")
        if self.serial_port:
            self.overlay.set_serial_port(port)


    def open_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/instancer-kirik/BigLinks"))

   
    
    def switch_workspace(self):
        """Switch to a different workspace"""
        try:
            # Get vault directories from cccore
            vault_dirs = self.cccore.vault_manager.get_vault_directories()
            vault_dir, ok = QInputDialog.getItem(
                self, 
                "Select Vault", 
                "Choose a vault:", 
                vault_dirs, 
                0, 
                False
            )
            
            if ok and vault_dir:
                workspace_names = self.cccore.workspace_manager.get_workspace_names(vault_dir)
                workspace, ok = QInputDialog.getItem(
                    self, 
                    "Switch Workspace", 
                    "Choose a workspace:", 
                    workspace_names, 
                    0, 
                    False
                )
                
                if ok and workspace:
                    self.cccore.switch_to_workspace(vault_dir, workspace)
                    self.update_workspace_dependent_ui()
                    
        except Exception as e:
            logging.error(f"Error switching workspace: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to switch workspace: {str(e)}"
            )

    def switch_to_workspace(self, vault_dir, workspace_name):
        vault = self.vault_manager.get_vault(vault_dir)
        if vault:
            workspace = vault.get_workspace(workspace_name)
            if workspace:
                for window in self.auratext_windows:
                    if window.current_vault == vault:
                        window.set_workspace(workspace)
            else:
                logging.error(f"Workspace not found: {workspace_name}")
        else:
            logging.error(f"Vault not found: {vault_dir}")

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
    def setup_animations(self):
        """Initialize all window animations"""
        try:
            # Window opacity animation for fade effects
            self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
            self.opacity_animation.setDuration(200)  # 200ms duration
            
            # Window snap animation for window snapping
           
            self.snap_animation = QPropertyAnimation(self, b"geometry")
            self.snap_animation.setDuration(200)  # 200ms duration
            self.snap_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # Initialize snap threshold
            self.snap_threshold = 20  # pixels
            
            # Initialize dragging state
            self.is_dragging = False
            self.drag_position = None
            
            logging.debug("Window animations initialized successfully")
        except Exception as e:
            logging.error(f"Error setting up animations: {str(e)}")
            logging.error(traceback.format_exc())

    def fade_in(self):
        logging.info("Starting fade_in animation")
        try:
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(1000)
            self.animation.setStartValue(0)
            self.animation.setEndValue(1)
            self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            logging.info("Fade_in animation started successfully")
        except Exception as e:
            logging.error(f"Error in fade_in method: {str(e)}")
            logging.error(traceback.format_exc())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            logging.debug(f"Mouse press event on {obj}")
        return super().eventFilter(obj, event)

    
    def create_auratext_window(self):
        auratext_window = self.cccore.create_auratext_window()
       
        auratext_window.show()
    def setup_window_properties(self):
        """Set up window properties and geometry"""
        try:
            # Set window title
            self.setWindowTitle(self.config_manager.get_value('window_title', 'Computinator Code'))
            
            # Set window geometry
            default_geometry = (100, 100, 1280, 720)  # x, y, width, height
            geometry = self.config_manager.get_value('window_geometry', default_geometry)
            self.setGeometry(*geometry)
            
            # Set window flags and attributes
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            
            # Set window opacity for fade effects
            self.setWindowOpacity(1.0)
            
            # Ensure proper widget stacking
            self.raise_()  # Bring main window to front
            self.activateWindow()
            
            # Clear any existing overlays
            for child in self.findChildren(QWidget):
                if child.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
                    child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            
            logging.info("Window properties initialized successfully")
            
        except Exception as e:
            logging.error(f"Error setting up window properties: {e}")
            logging.error(traceback.format_exc())
    def cleanup(self):
        """Clean up resources before exit"""
        try:
            logging.info("Starting application cleanup")
            
            # Save window state first
            try:
                settings = QSettings()
                settings.setValue("windowState", self.saveState())
                settings.setValue("windowGeometry", self.saveGeometry())
                logging.info("Window state saved successfully")
            except Exception as e:
                logging.error(f"Error saving window state: {e}")
            
            # Clean up CCCore first
            if hasattr(self, 'cccore'):
                try:
                    self.cccore.cleanup()
                    logging.info("CCCore cleanup completed")
                except Exception as e:
                    logging.error(f"Error cleaning up CCCore: {e}")
            
            # Clean up widgets
            try:
                if hasattr(self, 'tab_widget'):
                    self.tab_widget.clear()
                    self.tab_widget.deleteLater()
                if hasattr(self, 'central_widget'):
                    self.central_widget.deleteLater()
                logging.info("Widgets cleaned up")
            except Exception as e:
                logging.error(f"Error cleaning up widgets: {e}")
                
            logging.info("Cleanup process completed")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        finally:
            logging.info("Application cleanup complete")
                
    def setup_many_projects_manager(self):
        self.many_projects_manager = ManyProjectsManagerWidget(self.cccore)
        many_projects_dock = QDockWidget("Many Projects Manager", self)
        many_projects_dock.setWidget(self.many_projects_manager)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, many_projects_dock)

        # Add a toggle action to the View menu
        self.cccore.menu_manager.view_menu.addAction(many_projects_dock.toggleViewAction())
        self.cccore.widget_manager.dock_widgets["Many Projects Manager"] = many_projects_dock
        # Update other UI elements as needed
    def post_show_init(self):
        """Initialize components after window is shown"""
        try:
            logging.info("Starting post-show initialization")
            
            # Apply theme to all widgets
            self.apply_theme_to_widgets()
            logging.info("Theme applied to all widgets")
            
            # Setup late connections
            self.setup_late_connections()
            logging.info("Late connections established")
            
            # Initialize late-loading components
            if hasattr(self.cccore, 'late_init'):
                self.cccore.late_init()
                logging.info("CCCore late initialization completed")
                
            # Update UI elements that depend on loaded data
            if hasattr(self, 'update_workspace_dependent_ui'):
                self.update_workspace_dependent_ui()
                logging.info("Workspace-dependent UI updated")
            
            logging.info("Post-show initialization completed successfully")
            
        except Exception as e:
            logging.error(f"Error in post-show initialization: {e}")
            logging.error(traceback.format_exc())
            
    def cleanup_resources(self):
        """Clean up application resources"""
        try:
            # Clean up managers
            if hasattr(self, 'cccore'):
                if hasattr(self.cccore, 'widget_manager'):
                    self.cccore.widget_manager.cleanup()
                if hasattr(self.cccore, 'process_manager'):
                    self.cccore.process_manager.cleanup_processes()
                    
            # Clean up any open windows
            for window in QApplication.topLevelWindows():
                window.close()
                
            # Clean up any remaining resources
            self.cleanup_widgets()
            self.cleanup_connections()
            
            logging.info("Resources cleaned up successfully")
            
        except Exception as e:
            logging.error(f"Error cleaning up resources: {e}")
            logging.error(traceback.format_exc())
            
    def cleanup_widgets(self):
        """Clean up widget resources"""
        try:
            if hasattr(self, 'central_widget'):
                self.central_widget.deleteLater()
            if hasattr(self, 'statusBar'):
                self.statusBar().deleteLater()
        except Exception as e:
            logging.error(f"Error cleaning up widgets: {e}")
            
    def cleanup_connections(self):
        """Clean up signal connections"""
        try:
            if hasattr(self, 'tab_widget'):
                self.tab_widget.currentChanged.disconnect()
        except Exception as e:
            logging.error(f"Error cleaning up connections: {e}")

    def setup_late_connections(self):
        """Setup connections that need to be made after window is shown"""
        try:
            # Connect workspace selector if it exists
            if hasattr(self.cccore.widget_manager, 'workspace_selector'):
                selector = self.cccore.widget_manager.workspace_selector
                if selector:
                    selector.currentTextChanged.connect(self.handle_workspace_change)
                    logging.info("Workspace selector connections established")
                    
            # Connect any remaining dock widget signals
            for dock_name, dock in self.cccore.widget_manager.dock_widgets.items():
                if hasattr(dock.widget(), 'late_connect'):
                    dock.widget().late_connect()
                    logging.info(f"Late connections established for {dock_name}")
                    
            logging.info("Late connections setup completed")
            
        except Exception as e:
            logging.error(f"Error setting up late connections: {e}")
            logging.error(traceback.format_exc())

    def apply_theme_to_widgets(self):
        """Apply current theme to all widgets"""
        try:
            # Get current theme
            theme = self.cccore.theme_manager.get_current_theme()
            
            # Apply to dock widgets
            for dock in self.cccore.widget_manager.dock_widgets.values():
                if hasattr(dock.widget(), 'apply_theme'):
                    dock.widget().apply_theme(theme)
                    
            # Apply to main window components
            self.apply_theme_to_window(theme)
            
            logging.info("Theme applied to all widgets")
            
        except Exception as e:
            logging.error(f"Error applying theme to widgets: {e}")
            logging.error(traceback.format_exc())

    def apply_theme_to_window(self, theme):
        """Apply theme to main window components"""
        try:
            # Apply window colors
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {theme.get('main_window_color', '#2E3440')};
                }}
                QDockWidget {{
                    background-color: {theme.get('window_color', '#3B4252')};
                    color: {theme.get('text_color', '#ECEFF4')};
                }}
                QDockWidget::title {{
                    background-color: {theme.get('header_color', '#4C566A')};
                    padding: 3px;
                }}
                QMenuBar {{
                    background-color: {theme.get('header_color', '#4C566A')};
                    color: {theme.get('text_color', '#ECEFF4')};
                }}
                QToolBar {{
                    background-color: {theme.get('header_color', '#4C566A')};
                    border: none;
                }}
                QStatusBar {{
                    background-color: {theme.get('header_color', '#4C566A')};
                    color: {theme.get('text_color', '#ECEFF4')};
                }}
            """)
            
            # Apply to menu bar
            if hasattr(self, 'menuBar'):
                self.menuBar().setStyleSheet(f"""
                    QMenuBar::item:selected {{
                        background-color: {theme.get('theme_color', '#81A1C1')};
                    }}
                """)
                
            logging.info("Theme applied to main window")
            
        except Exception as e:
            logging.error(f"Error applying theme to window: {e}")
            logging.error(traceback.format_exc())

    def setup_toolbar(self):
        """Initialize application toolbars"""
        try:
            # Main toolbar
            self.main_toolbar = QToolBar("Main Tools")
            self.main_toolbar.setObjectName("MainToolbar")
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_toolbar)
            
            # Add main actions
            actions = {
                'New': ('Ctrl+N', lambda: self.cccore.action_handlers.new_file(), 'New File'),
                'Open': ('Ctrl+O', lambda: self.cccore.action_handlers.open_file(), 'Open File'),
                'Save': ('Ctrl+S', lambda: self.cccore.action_handlers.save_file(), 'Save File'),
                'Undo': ('Ctrl+Z', lambda: self.cccore.action_handlers.undo(), 'Undo'),
                'Redo': ('Ctrl+Shift+Z', lambda: self.cccore.action_handlers.redo(), 'Redo'),
            }
            
            for name, (shortcut, handler, tooltip) in actions.items():
                action = QAction(name, self)
                action.setShortcut(shortcut)
                action.setToolTip(tooltip)
                action.triggered.connect(handler)
                self.main_toolbar.addAction(action)
                
            self.main_toolbar.addSeparator()
            
            # Tools toolbar
            self.tools_toolbar = QToolBar("Tools")
            self.tools_toolbar.setObjectName("ToolsToolbar")
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.tools_toolbar)
            
            # Add tool toggles
            toggles = {
                'Log Viewer': (lambda: self.toggle_dock('LogViewer'), 'Toggle Log Viewer'),
                'Voice Typing': (lambda: self.toggle_dock('VoiceTyping'), 'Toggle Voice Typing'),
                'File Explorer': (lambda: self.toggle_dock('FileExplorer'), 'Toggle File Explorer'),
                'Terminal': (lambda: self.toggle_dock('Terminal'), 'Toggle Terminal'),
                'Process Manager': (lambda: self.toggle_dock('ProcessManager'), 'Toggle Process Manager'),
            }
            
            for name, (handler, tooltip) in toggles.items():
                action = QAction(name, self)
                action.setCheckable(True)
                action.setToolTip(tooltip)
                action.triggered.connect(handler)
                self.tools_toolbar.addAction(action)
                
            self.tools_toolbar.addSeparator()
            
            # Add workspace selector
            if hasattr(self.cccore, 'widget_manager'):
                workspace_selector = self.cccore.widget_manager.get_workspace_selector()
                if workspace_selector:
                    self.tools_toolbar.addWidget(workspace_selector)
                    
            logging.info("Toolbars initialized successfully")
        except Exception as e:
            logging.error(f"Error setting up toolbars: {e}")

    def setup_widgets(self):
        """Set up all dock widgets"""
        try:
            # Create and add log viewer
            log_viewer = self.cccore.widget_manager.create_widget('LogViewer')
            if log_viewer:
                log_dock = QDockWidget("Logs", self)
                log_dock.setWidget(log_viewer)
                log_dock.setObjectName("LogViewerDock")
                self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, log_dock)
                logging.info("Log viewer dock widget added")
                
            # Create and add STT widget
            stt_widget = self.cccore.widget_manager.create_widget('VoiceTyping')
            if stt_widget:
                stt_dock = QDockWidget("Voice Typing", self)
                stt_dock.setWidget(stt_widget)
                stt_dock.setObjectName("VoiceTypingDock")
                self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, stt_dock)
                logging.info("Voice typing dock widget added")
                
            # Store dock widgets in widget manager
            if hasattr(self.cccore, 'widget_manager'):
                self.cccore.widget_manager.dock_widgets.update({
                    'LogViewer': log_dock if log_viewer else None,
                    'VoiceTyping': stt_dock if stt_widget else None
                })
                
            logging.info("All dock widgets initialized")
            
        except Exception as e:
            logging.error(f"Error setting up dock widgets: {e}")

def exception_hook(exctype, value, tb):
    logging.error("Uncaught exception", exc_info=(exctype, value, tb))
    traceback.print_exception(exctype, value, tb)
    QApplication.quit()

def setup_logging(log_file_path):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, 'a'),
            logging.StreamHandler()
        ],
        force=True
    )

# Call this function at the beginning of your main() function
setup_logging(log_file_path)

def global_exception_handler(exctype, value, traceback):
    logging.critical("Unhandled exception", exc_info=(exctype, value, traceback))
    # Optionally, you can add code here to display an error message to the user
    sys.__excepthook__(exctype, value, traceback)

sys.excepthook = global_exception_handler

def main():
    profiler = cProfile.Profile()
    # profiler.enable()
    # Use your existing logging configuration
    log_directory = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_file_path = os.path.join(log_directory, 'app.log')

    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(levelname)s - %(message)s', 
                        handlers=[logging.FileHandler(log_file_path, 'a'), 
                                  logging.StreamHandler()])

    logging.debug("Starting application")

    sys.excepthook = exception_hook

    try:
        logging.debug("Starting splash screen process")
        splash_process = subprocess.Popen([sys.executable, 'GUX/splash_process.py'])
        
        logging.debug("Creating QApplication")
        app = QApplication(sys.argv)

        # Create timer after QApplication
        timer = QTimer()
        timer.moveToThread(app.thread())  # Ensure timer runs in main thread
        timer.start(500)
        timer.timeout.connect(lambda: None)

        logging.debug("Setting application-wide stylesheet")
        app.setStyleSheet("""
            QWidget {
                background-color: #2E3440;
                color: #D8DEE9;
            }
        """)
       
        logging.debug("Creating SettingsManager")
        config_manager = ConfigManager()
        
        logging.info("Initializing managers")
        cccore, overlay = initialize_core(config_manager)
        
        logging.info("Creating WidgetManager")
        widget_manager = WidgetManager(cccore)

        logging.info("Initializing CCCore managers")
        cccore.init_managers()
        
        logging.info("Setting overlay for CCCore")
        cccore.set_overlay(overlay)
        
        logging.info("Setting widget_manager for CCCore")
        cccore.set_widget_manager(widget_manager)
        
        logging.info("Creating MainApplication instance")
        main_app = MainApplication(cccore, widget_manager)

        # Set main window for widget manager and CCCore
        logging.info("Setting main_window for widget_manager and CCCore")
        widget_manager.set_main_window(main_app)
        cccore.set_main_window(main_app)
        
        logging.info("Performing CCCore late initialization")
        cccore.late_init()
        
        def show(self):
            super().show()
            
        def show_app():
            try:
                logging.info("Entering show_app function")
                if not main_app.isVisible():
                    # Ensure window state is restored
                    main_app.restore_window_state()
                    
                    # Show the window
                    main_app.show()
                    
                    # Ensure menu bar is visible
                    menubar = main_app.menuBar()
                    if not menubar.isVisible():
                        menubar.show()
                        logging.info("Forced menu bar visibility")
                        
                    # Ensure proper window state
                    if not main_app.isMaximized():
                        main_app.showMaximized()
                    
                    # Start fade-in animation
                    QTimer.singleShot(100, main_app.fade_in)
                    
                    # Schedule post-show initialization
                    QTimer.singleShot(200, main_app.post_show_init)
                    
                    logging.info("Main application window shown successfully")
            except Exception as e:
                logging.error(f"Error showing application: {e}", exc_info=True)
            logging.info("Exiting show_app function")
            try:
                splash_process.terminate()
                splash_process.wait(5000)  # Wait up to 5 seconds for the process to terminate
                if splash_process.poll() is None:
                    logging.warning("Splash process did not terminate, forcing kill")
                    splash_process.kill()
            except Exception as e:
                logging.error(f"Error terminating splash process: {e}")

        logging.info("Scheduling application display")
        QTimer.singleShot(0, show_app)

        def cleanup():
            """Handle application cleanup"""
            logging.info("Starting application cleanup")
            try:
                if 'main_app' in locals():
                    main_app.cleanup()
                if hasattr(cccore, 'process_manager'):
                    cccore.process_manager.cleanup_processes()
                logging.info("Cleanup process completed")
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")
            finally:
                logging.info("Application cleanup complete")
                
        app.aboutToQuit.connect(cleanup)

        logging.debug("Entering Qt event loop")
        try:
            sys.exit(app.exec())
        except Exception as e:
            logging.error(f"Unhandled exception in main: {str(e)}")
            logging.error(traceback.format_exc())
        finally:
            if 'main_app' in locals():
                main_app.cleanup()
            if 'global_thread_tracker' in globals():
                global_thread_tracker.dump_thread_info()      
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logging.warning("Main function completed")
        # try:    
        #     profiler.disable()
        #     s = io.StringIO()
        #     sortby = 'cumulative'
        #     ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
        #     ps.print_stats()
        #     print(s.getvalue())
        
        # # Optionally, save the profiling results to a file
        #     with open('profile_results.txt', 'w') as f:
        #         ps.stream = f
        #         ps.print_stats()
        # except Exception as e:
        #     logging.error(f"Error saving profiling results: {e}")
if __name__ == '__main__':
    main()
