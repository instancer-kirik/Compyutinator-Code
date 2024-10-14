from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QAction, QIcon
from .action_handlers import ActionHandlers
from GUX.merge_widget import MergeWidget
import logging
from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtCore import QObject, Qt
class MenuManager:
    def __init__(self, main_window, cccore = None):
        self.main_window = main_window
        self.cccore = cccore
        self.action_handlers = ActionHandlers(cccore=cccore)

    def create_menu_bar(self):
        logging.warning("Creating menu bar")
        menubar = QMenuBar(self.main_window)
        
        menus = {
            "File": self.create_file_menu(),
            "Edit": self.create_edit_menu(),
            "View": self.create_view_menu(),
            "Tools": self.create_tools_menu(),
            "Vault": self.create_vault_menu(),
            "Graph": self.create_graph_menu(),
            "Workspace": self.create_workspace_menu(),
            "Help": self.create_help_menu()
        }

        for menu_name, menu in menus.items():
            logging.info(f"Adding {menu_name} menu")
            try:
                menubar.addMenu(menu)
            except Exception as e:
                logging.error(f"Error adding {menu_name} menu: {str(e)}")

        logging.warning("Menu bar created successfully")
        return menubar

    def create_file_menu(self):
        self.file_menu = QMenu("&File", self.main_window)
        self.file_menu.addAction("New", self.action_handlers.new_file)
        self.file_menu.addAction("Open", self.action_handlers.open_file)
        self.file_menu.addAction("Save", self.action_handlers.save_file)
        self.file_menu.addAction("Save As", self.action_handlers.save_file_as)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.create_action("Exit", self.main_window.close, "Ctrl+Q"))
        return self.file_menu

    def create_edit_menu(self):
        self.edit_menu = QMenu("&Edit", self.main_window)
        self.edit_menu.addAction("Undo", self.action_handlers.undo)
        self.edit_menu.addAction("Redo", self.action_handlers.redo)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction("Cut", self.action_handlers.cut_document)
        self.edit_menu.addAction("Copy", self.action_handlers.copy_document)
        self.edit_menu.addAction("Paste", self.action_handlers.paste_document)
        self.edit_menu.addAction("Theme Builder", self.main_window.cccore.widget_manager.show_theme_builder)
        self.edit_menu.addAction("Settings", self.action_handlers.show_settings)
        return self.edit_menu

    def create_view_menu(self):
        self.view_menu = QMenu("View", self.main_window)
        
        # Add existing dock widget toggles
        for dock_name, dock_widget in self.cccore.widget_manager.dock_widgets.items():
            action = self.create_action(dock_name, lambda checked, w=dock_widget: self.toggle_dock_visibility(w, checked))
            action.setCheckable(True)
            action.setChecked(dock_widget.isVisible() if dock_widget else False)
            
            try:
                if dock_widget and isinstance(dock_widget, QObject):
                    parent = dock_widget.parent()
                    is_visible = dock_widget.isVisible()
                    action.setChecked(is_visible)
                    action.triggered.connect(lambda checked, w=dock_widget: self.toggle_dock_visibility(w, checked))
                else:
                    action.setEnabled(False)
                    logging.warning(f"Dock widget '{dock_name}' is not a valid QObject.")
            except RuntimeError:
                action.setEnabled(False)
                logging.warning(f"Dock widget '{dock_name}' has been deleted or is invalid.")
            except Exception as e:
                action.setEnabled(False)
                logging.error(f"Unexpected error with dock widget '{dock_name}': {str(e)}")
                # Add separator before new actions
            self.view_menu.addAction(action)
        self.view_menu.addSeparator()

        self.view_menu.addSeparator()
        self.view_menu.addAction(self.create_action("Show Demo Diff Merger", self.spawn_prefilled_merger))
        
        # Add Many Projects Manager toggle
        # try:
        #     # Add a toggle action to the View menu
        #     # Add a toggle action to the View menu
        #     self.view_menu.addAction(self.cccore.widget_manager.many_projects_manager.toggleViewAction())

        #     #self.add_toggle_view_action(view_menu, "Many Projects Manager", self.cccore.widget_manager.many_projects_manager)
        # except AttributeError:
        #     logging.warning("Many Projects Manager not found, skipping addition of toggle action.")
        
        # Add Advanced Data Viewer action
        try:
            _, advanced_data_viewer_action = self.cccore.widget_manager.add_advanced_data_viewer_dock()
            self.view_menu.addAction(advanced_data_viewer_action)
            
        except AttributeError:
            logging.warning("Advanced Data Viewer not found, skipping addition of toggle action.")
        return self.view_menu

    
    def create_tools_menu(self):
        tools_menu = QMenu("&Tools", self.main_window)
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
        return tools_menu

    def create_vault_menu(self):
        self.vault_menu = QMenu("&Vault", self.main_window)
        self.vault_menu.addAction(self.create_action("Add Vault Directory", self.action_handlers.add_vault_directory))
        self.vault_menu.addAction(self.create_action("Remove Vault Directory", self.action_handlers.remove_vault_directory))
        self.vault_menu.addAction(self.create_action("Set Default Vault", self.action_handlers.set_default_vault))
        self.vault_menu.addSeparator()
        self.vault_menu.addAction(self.create_action("Vault Explorer", self.action_handlers.show_vault_explorer))
        self.vault_menu.addAction(self.create_action("Vault Search", self.action_handlers.show_vault_search))
        self.vault_menu.addAction(self.create_action("Vault Statistics", self.action_handlers.show_vault_statistics))
        self.vault_menu.addAction(self.create_action("Vault Graph", self.action_handlers.show_vault_graph))
        return self.vault_menu

    def create_graph_menu(self):
        self.graph_menu = QMenu("&Graph", self.main_window)
        self.graph_menu.addAction(self.create_action("Show 2D Graph", self.action_handlers.show_2d_graph))
        self.graph_menu.addAction(self.create_action("Show 3D Graph", self.action_handlers.show_3d_graph))
        self.graph_menu.addAction(self.create_action("Graph Settings", self.action_handlers.show_graph_settings))
        return self.graph_menu

    def create_workspace_menu(self):
        self.workspace_menu = QMenu("&Workspace", self.main_window)
        self.workspace_menu.addAction(self.create_action("Create Workspace", self.main_window.create_workspace))
        self.workspace_menu.addAction(self.create_action("Switch Workspace", self.main_window.switch_workspace))
        self.workspace_menu.addAction(self.create_action("Manage Workspaces", self.action_handlers.manage_workspaces))
        return self.workspace_menu

    def create_help_menu(self):
        self.help_menu = QMenu("&Help", self.main_window)
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
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(slot)
            return action
        except Exception as e:
            logging.error(f"Error creating action '{text}': {str(e)}")
            return None

    def toggle_dock_visibility(self, dock_widget, checked):
        try:
            dock_widget.setVisible(checked)
        except RuntimeError:
            logging.warning(f"Failed to set visibility for a dock widget. It may have been deleted.")
        except Exception as e:
            logging.error(f"Unexpected error toggling dock visibility: {str(e)}")
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