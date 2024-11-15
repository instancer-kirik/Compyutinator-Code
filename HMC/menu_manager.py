from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QAction, QIcon
from .action_handlers import ActionHandlers
from GUX.merge_widget import MergeWidget
import logging
from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtCore import QTimer
from GUX.widgets.project_dashboard import ProjectDashboard

class MenuManager:
    def __init__(self, main_window, cccore):
        """Initialize menu manager"""
        try:
            self.main_window = main_window
            self.cccore = cccore
            self.action_handlers = ActionHandlers(main_window, cccore)
            self.device_manager_dock = None
            self.dock_widgets = {}
            
            # Initialize menu references
            self.file_menu = None
            self.edit_menu = None
            self.view_menu = None
            self.tools_menu = None
            self.vault_menu = None
            self.graph_menu = None
            self.workspace_menu = None
            self.help_menu = None
            self.macro_menu = None
            
            logging.info("MenuManager initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing MenuManager: {e}")

    def initialize_docks(self):
        """Initialize dock widgets once window is ready"""
        if not self.main_window or not self.main_window.isVisible():
            # Retry after a short delay if window isn't ready
            QTimer.singleShot(100, self.initialize_docks)
            return
        
        try:
            if not self.device_manager_dock:
                from GUX.device_manager_view import DeviceManagerView
                device_manager = DeviceManagerView(self.main_window)
                self.device_manager_dock = self.cccore.widget_manager.add_dock_widget(
                    device_manager,
                    "Device Manager",
                    Qt.DockWidgetArea.RightDockWidgetArea
                )
                self.device_manager_dock.hide()  # Initially hidden
                
        except Exception as e:
            logging.error(f"Error initializing device manager: {e}")

    def create_menu_bar(self):
        """Create the menu bar with all menus"""
        try:
            menubar = QMenuBar(self.main_window)
            
            # Create all menus
            self.file_menu = self.create_file_menu(menubar)
            self.edit_menu = self.create_edit_menu(menubar)
            self.view_menu = self.create_view_menu(menubar)
            self.tools_menu = self.create_tools_menu(menubar)
            self.vault_menu = self.create_vault_menu(menubar)
            self.graph_menu = self.create_graph_menu(menubar)
            self.workspace_menu = self.create_workspace_menu(menubar)
            self.help_menu = self.create_help_menu(menubar)
            self.macro_menu = self.create_macro_menu()
            menubar.addMenu(self.macro_menu)
            
            self.main_window.setMenuBar(menubar)
            logging.info("Menu bar created successfully")
            return menubar
            
        except Exception as e:
            logging.error(f"Error creating menu bar: {e}")
            return None

    def create_file_menu(self, menubar):
        self.file_menu = menubar.addMenu('&File')

        # Add Open Project by Folder action
        open_project_action = QAction("Open Project by Folder", self.main_window)
        open_project_action.triggered.connect(self.cccore.project_manager.open_project_by_folder)
        self.file_menu.addAction(open_project_action)

        self.file_menu.addAction('&New', self.action_handlers.new_file)
        self.file_menu.addAction('&Open', self.action_handlers.open_file)
        self.file_menu.addAction('&Save', self.action_handlers.save_file)
        self.file_menu.addAction('Save &As', self.action_handlers.save_file_as)
        
        # Add a new action for creating a new AuraText window
        self.file_menu.addAction('New AuraText Window', self.cccore.create_auratext_window)  # Connect to the method that creates a new window
        
        self.file_menu.addSeparator()
        self.file_menu.addAction('&Exit', self.main_window.close)
        return self.file_menu

    def create_edit_menu(self, menubar):
        self.edit_menu = menubar.addMenu('&Edit')
        self.edit_menu.addAction('&Undo', self.action_handlers.undo)
        self.edit_menu.addAction('&Redo', self.action_handlers.redo)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction('&Cut', self.action_handlers.cut_document)
        self.edit_menu.addAction('&Copy', self.action_handlers.copy_document)
        self.edit_menu.addAction('&Paste', self.action_handlers.paste_document)
        self.edit_menu.addAction('Theme Builder', self.main_window.cccore.widget_manager.show_theme_builder)
        self.edit_menu.addAction('Settings', self.action_handlers.show_settings)
        return self.edit_menu

    def create_view_menu(self, menubar):
        """Create the view menu"""
        try:
            self.view_menu = menubar.addMenu('&View')
            
            # Add dashboard action
            dashboard_action = QAction("Project Dashboard", self.main_window)
            dashboard_action.triggered.connect(lambda: self.action_handlers.show_dashboard(main_window=self.main_window))
            dashboard_action.setShortcut("Ctrl+Shift+D")
            self.view_menu.addAction(dashboard_action)
            
            # Add dock toggles submenu
            docks_menu = self.view_menu.addMenu("Docks")
            
            # Add standard dock toggles
            standard_docks = [
                "File Explorer",
                "Code Editor", 
                "Terminal",
                "Process Manager",
                "Big Links",
                "Risk Manager",
                "Vaults Manager"
            ]
            
            for dock_name in standard_docks:
                action = QAction(dock_name, self.main_window)
                action.setCheckable(True)
                action.setChecked(True)
                action.triggered.connect(lambda checked, name=dock_name: 
                    self.toggle_dock_visibility(name, checked))
                docks_menu.addAction(action)
            
            return self.view_menu
            
        except Exception as e:
            logging.error(f"Error creating view menu: {e}")
            return None

    
    def create_tools_menu(self, menubar):
        """Create tools menu"""
        tools_menu = menubar.addMenu('&Tools')
        
        # Add Device Management submenu
        device_menu = tools_menu.addMenu("Device Management")
        
        show_device_manager = device_menu.addAction("Device Manager")
        show_device_manager.triggered.connect(self.cccore.widget_manager.show_device_manager)
        
        show_nix_browser = device_menu.addAction("Nix Store Browser")
        show_nix_browser.triggered.connect(self.cccore.widget_manager.show_nix_browser)
        
        manage_flows = device_menu.addAction("Manage Device Flows")
        manage_flows.triggered.connect(self.show_flow_manager)
        
        device_menu.addSeparator()
        
        refresh_devices = device_menu.addAction("Refresh Devices")
        refresh_devices.triggered.connect(self.refresh_devices)
        
        tools_menu.addAction(self.create_action("Plugin Manager", self.action_handlers.show_plugin_manager))
        tools_menu.addAction(self.create_action("Theme Manager", self.action_handlers.show_theme_manager))
        tools_menu.addAction(self.create_action("Workspace Manager", self.action_handlers.show_workspace_manager))
        tools_menu.addAction(self.create_action("Model Manager", self.action_handlers.show_model_manager))
        tools_menu.addAction(self.create_action("Download Manager", self.action_handlers.show_download_manager))
        tools_menu.addAction(self.create_action("Load Layout", self.action_handlers.load_layout))
        tools_menu.addAction(self.create_action("Diff Merger", self.action_handlers.show_diff_merger))
        try:
            tools_menu.addAction(self.create_action("CodeToolWidget", self.cccore.widget_manager.show_cool_dock))
        except Exception as e:
            logging.error(f"Error adding CodeToolWidget action: {str(e)}")
        # Add Big Links action
        big_links_action = QAction('Big Links', self.main_window)
        big_links_action.setShortcut("Ctrl+B")
        big_links_action.triggered.connect(
            lambda: self.cccore.widget_manager.show_dock_widget("Big Links")
        )
        tools_menu.addAction(big_links_action) 
        return tools_menu

    def create_vault_menu(self, menubar):
        self.vault_menu = menubar.addMenu('&Vault')
        self.vault_menu.addAction(self.create_action("Add Vault Directory", self.action_handlers.add_vault_directory))
        self.vault_menu.addAction(self.create_action("Remove Vault Directory", self.action_handlers.remove_vault_directory))
        self.vault_menu.addAction(self.create_action("Set Default Vault", self.action_handlers.set_default_vault))
        self.vault_menu.addSeparator()
        self.vault_menu.addAction(self.create_action("Vault Explorer", self.action_handlers.show_vault_explorer))
        self.vault_menu.addAction(self.create_action("Vault Search", self.action_handlers.show_vault_search))
        self.vault_menu.addAction(self.create_action("Vault Statistics", self.action_handlers.show_vault_statistics))
        self.vault_menu.addAction(self.create_action("Vault Graph", self.action_handlers.show_vault_graph))
        return self.vault_menu

    def create_graph_menu(self, menubar):
        self.graph_menu = menubar.addMenu('&Graph')
        self.graph_menu.addAction(self.create_action("Show 2D Graph", self.action_handlers.show_2d_graph))
        self.graph_menu.addAction(self.create_action("Show 3D Graph", self.action_handlers.show_3d_graph))
        self.graph_menu.addAction(self.create_action("Graph Settings", self.action_handlers.show_graph_settings))
        return self.graph_menu

    def create_workspace_menu(self, menubar):
        """Create the workspace menu"""
        try:
            self.workspace_menu = menubar.addMenu('&Workspace')
            
            # Add workspace management items
            if hasattr(self.action_handlers, 'manage_workspaces'):
                self.workspace_menu.addAction(self.create_action(
                    "Manage Workspaces",
                    self.action_handlers.manage_workspaces
                ))
                
            if hasattr(self.action_handlers, 'show_project_dashboard'):
                self.workspace_menu.addAction(self.create_action(
                    "Project Dashboard",
                    self.action_handlers.show_project_dashboard,
                    shortcut="Ctrl+Alt+D"
                ))
            
            return self.workspace_menu
            
        except Exception as e:
            logging.error(f"Error creating workspace menu: {e}")
            return menubar.addMenu('&Workspace')  # Return empty menu instead of None

    def show_project_dashboard(self):
        """Show the project dashboard for the current project"""
        try:
            current_project = self.cccore.project_manager.get_current_project()
            if current_project:
                # Use the widget manager to show the dashboard
                self.cccore.widget_manager.show_dashboard(current_project)
            else:
                QMessageBox.warning(self.main_window, "No Project", 
                                  "Please select or create a project first.")
        except Exception as e:
            logging.error(f"Error showing project dashboard: {e}")
            QMessageBox.warning(self.main_window, "Error",
                              f"Could not show project dashboard: {str(e)}")

    def create_help_menu(self, menubar):
        self.help_menu = menubar.addMenu('&Help')
        self.help_menu.addAction(self.create_action("About", self.action_handlers.show_about))
        self.help_menu.addAction(self.create_action("Documentation", self.action_handlers.show_documentation))
        self.help_menu.addAction(self.create_action("Check for Updates", self.action_handlers.check_for_updates))
        return self.help_menu

    def add_toggle_view_action(self, menu, title, dock_widget):
        if dock_widget is None:
            logging.warning(f"Cannot add toggle view action for '{title}' as the dock widget is None")
            return
        
        action = QAction(title, self.main_window, checkable=True)
        action.setChecked(dock_widget.isVisible())
        action.triggered.connect(dock_widget.setVisible)
        dock_widget.visibilityChanged.connect(action.setChecked)
        menu.addAction(action)

    def create_action(self, text, slot, shortcut=None, icon=None):
        try:
            action = QAction(text, self.main_window)
            if icon:
                action.setIcon(QIcon(icon))
            
            # Use configured hotkey if available
            configured_shortcut = self.cccore.settings_manager.get_hotkey(text)
            if configured_shortcut:
                action.setShortcut(configured_shortcut)
            elif shortcut:  # Fall back to provided shortcut
                action.setShortcut(shortcut)
            
            action.triggered.connect(slot)
            return action
        except Exception as e:
            logging.error(f"Error creating action '{text}': {str(e)}")
            return None

    def toggle_dock_visibility(self, dock_widget, checked):
        try:
            self.cccore.widget_manager.show_dock_widget(dock_widget)
        except Exception as e:
            logging.error(f"Error toggling dock visibility: {str(e)}")

    def spawn_prefilled_merger(self):
        # Sample data
        original_content = """def greet(name):
    print(f"Hello, {name}!")

def main():
    greet("World")

if __name__ == "__main__":
    main()
"""
        modified_content = """def greet(name):
    print(f"Hello, {name}!")

def farewell(name):
    print(f"Goodbye, {name}!")

def main():
    greet("World")
    farewell("World")

if __name__ == "__main__":
    main()
"""
        
        # Create and show the MergeWidget
        merger_widget = MergeWidget(file_path="original.py", original_content=original_content, new_content=modified_content, parent=self.main_window)
  
        # Create a new dock widget for the merger
        dock = self.cccore.widget_manager.add_dock_widget(
            merger_widget,
            "Diff Merger",
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        dock.show()

    def create_macro_menu(self):
       
        # Add a Macros menu
        self.macro_menu = QMenu("&Macros", self.main_window)
        
        start_recording_action = self.macro_menu.addAction("Start Recording")
        start_recording_action.triggered.connect(self.start_macro_recording)

        stop_recording_action = self.macro_menu.addAction("Stop Recording")
        stop_recording_action.triggered.connect(self.stop_macro_recording)

        play_macro_action = self.macro_menu.addAction("Play Macro")
        play_macro_action.triggered.connect(self.play_macro)
        return self.macro_menu

    def start_macro_recording(self):
        name, ok = QInputDialog.getText(self.main_window, "Record Macro", "Enter macro name:")
        if ok and name:
            self.cccore.start_macro_recording(name)

    def stop_macro_recording(self):
        self.cccore.stop_macro_recording()

    def play_macro(self):
        macros = self.cccore.get_macro_list()
        if not macros:
            QMessageBox.information(self.main_window, "Play Macro", "No macros available.")
            return
        name, ok = QInputDialog.getItem(self.main_window, "Play Macro", "Select a macro:", macros, 0, False)
        if ok and name:
            self.cccore.macro_manager.play_macro(name)
            
    def show_device_manager(self):
        """Show device manager dock"""
        if self.cccore.widget_manager:
            self.cccore.widget_manager.show_device_manager()

    def show_flow_manager(self):
        """Show the device flow manager dialog"""
        try:
            if hasattr(self, 'device_manager_dock') and self.device_manager_dock:
                widget = self.device_manager_dock.widget()
                if widget:
                    widget.manage_flows()
                else:
                    raise RuntimeError("Device manager widget not found")
            else:
                raise RuntimeError("Device manager not initialized")
                
        except Exception as e:
            logging.error(f"Error showing flow manager: {e}")
            QMessageBox.warning(self.main_window, "Error", 
                              f"Could not show flow manager: {str(e)}")
            
    def refresh_devices(self):
        """Refresh the device list"""
        try:
            if hasattr(self, 'device_manager_dock') and self.device_manager_dock:
                widget = self.device_manager_dock.widget()
                if widget:
                    widget.refresh_devices()
                else:
                    raise RuntimeError("Device manager widget not found")
            else:
                raise RuntimeError("Device manager not initialized")
                
        except Exception as e:
            logging.error(f"Error refreshing devices: {e}")
            QMessageBox.warning(self.main_window, "Error", 
                              f"Could not refresh devices: {str(e)}")

    def init_menu_bar(self):
        """Initialize the menu bar"""
        try:
            self.main_window.menuBar().clear()  # Clear existing menus
            # Create main menus
            self.file_menu = self.create_file_menu(self.main_window.menuBar())
            self.edit_menu = self.create_edit_menu(self.main_window.menuBar())
            self.view_menu = self.create_view_menu(self.main_window.menuBar())
            self.tools_menu = self.create_tools_menu(self.main_window.menuBar())
            self.vault_menu = self.create_vault_menu(self.main_window.menuBar())
            self.graph_menu = self.create_graph_menu(self.main_window.menuBar())
            self.workspace_menu = self.create_workspace_menu(self.main_window.menuBar())
            self.help_menu = self.create_help_menu(self.main_window.menuBar())
            
            logging.info("Menu bar initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing menu bar: {str(e)}")