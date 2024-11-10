from PyQt6.QtWidgets import QToolBar, QPushButton, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
import logging

class ToolbarManager:
    def __init__(self, main_window, cccore):
        self.main_window = main_window
        self.cccore = cccore
        self.toolbars = {}
        
    def create_main_toolbar(self):
        """Create main application toolbar"""
        try:
            toolbar = QToolBar("Main", self.main_window)
            toolbar.setObjectName("MainToolbar")
            
            # File dropdown
            file_menu = QMenu("File")
            file_actions = [
                ("New", "Ctrl+N", self.cccore.action_handlers.new_file),
                ("Open", "Ctrl+O", self.cccore.action_handlers.open_file),
                ("Save", "Ctrl+S", self.cccore.action_handlers.save_file),
                ("Save As", "Ctrl+Shift+S", self.cccore.action_handlers.save_file_as),
            ]
            self.add_actions_to_menu(file_menu, file_actions)
            toolbar.addAction(file_menu.menuAction())
            
            # Edit dropdown
            edit_menu = QMenu("Edit")
            edit_actions = [
                ("Undo", "Ctrl+Z", self.cccore.action_handlers.undo),
                ("Redo", "Ctrl+Shift+Z", self.cccore.action_handlers.redo),
                (None, None, None),  # Separator
                ("Cut", "Ctrl+X", self.cccore.action_handlers.cut),
                ("Copy", "Ctrl+C", self.cccore.action_handlers.copy),
                ("Paste", "Ctrl+V", self.cccore.action_handlers.paste),
            ]
            self.add_actions_to_menu(edit_menu, edit_actions)
            toolbar.addAction(edit_menu.menuAction())
            
            # Add workspace selector if available
            if hasattr(self.cccore, 'widget_manager'):
                workspace_selector = self.cccore.widget_manager.get_workspace_selector()
                if workspace_selector:
                    toolbar.addWidget(workspace_selector)
            
            return toolbar
            
        except Exception as e:
            logging.error(f"Error creating main toolbar: {e}")
            return None
            
    def create_tools_toolbar(self):
        """Create tools toolbar"""
        try:
            toolbar = QToolBar("Tools", self.main_window)
            toolbar.setObjectName("ToolsToolbar")
            
            # Tools dropdown
            tools_menu = QMenu("Tools")
            tools_actions = [
                ("Log Viewer", None, lambda: self.toggle_tool(self.cccore.widget_manager.create_log_viewer)),
                ("File Explorer", None, lambda: self.toggle_tool(self.cccore.widget_manager.create_file_explorer)),
                ("Terminal", None, lambda: self.toggle_tool(self.cccore.widget_manager.create_terminal)),
                ("Process Manager", None, lambda: self.toggle_tool(self.cccore.widget_manager.create_process_manager)),
            ]
            self.add_actions_to_menu(tools_menu, tools_actions)
            toolbar.addAction(tools_menu.menuAction())
            
            return toolbar
            
        except Exception as e:
            logging.error(f"Error creating tools toolbar: {e}")
            return None
    
    def add_actions_to_menu(self, menu, actions):
        """Add actions to a menu"""
        for name, shortcut, handler in actions:
            if name is None:
                menu.addSeparator()
                continue
            action = QAction(name, self.main_window)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(handler)
            menu.addAction(action)
    
    def toggle_tool(self, creator_func):
        """Toggle visibility of a tool widget"""
        try:
            widget = creator_func()
            if widget:
                widget.setVisible(not widget.isVisible())
        except Exception as e:
            logging.error(f"Error toggling tool: {e}")