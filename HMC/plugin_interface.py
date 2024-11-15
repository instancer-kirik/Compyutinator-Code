from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import QObject
from typing import Optional, Type, Dict, Callable
import logging

class WidgetPlugin(QObject):
    """Base class for widget plugins"""
    
    # Class attributes for plugin metadata
    widget_name: str = ""  # Name shown in UI
    widget_class: Type[QWidget] = None  # Widget class to instantiate
    dock_area: str = "right"  # Default dock area
    default_visible: bool = True  # Show on startup
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        
    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create an instance of the widget"""
        if not self.widget_class:
            raise NotImplementedError("Widget class not specified")
        return self.widget_class(parent=parent or self.main_window)
        
    def initialize(self):
        """Called when plugin is loaded"""
        pass
        
    def cleanup(self):
        """Called when plugin is unloaded"""
        pass

class WidgetRegistry:
    """Central registry for widget plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, Type[WidgetPlugin]] = {}
        self.widget_factories: Dict[str, Callable] = {}
        
    def register_plugin(self, plugin_class: Type[WidgetPlugin]):
        """Register a widget plugin"""
        try:
            name = plugin_class.widget_name
            if not name:
                name = plugin_class.__name__
            self.plugins[name] = plugin_class
            logging.info(f"Registered widget plugin: {name}")
        except Exception as e:
            logging.error(f"Failed to register plugin {plugin_class}: {e}")
            
    def register_widget_factory(self, name: str, factory: Callable):
        """Register a widget factory function"""
        self.widget_factories[name] = factory
        logging.info(f"Registered widget factory: {name}")
        
    def create_widget(self, name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        """Create a widget instance by name"""
        try:
            # Try plugin first
            if name in self.plugins:
                plugin = self.plugins[name](parent)
                return plugin.create_widget(parent)
                
            # Fall back to factory function
            if name in self.widget_factories:
                return self.widget_factories[name](parent)
                
            logging.error(f"No widget found for name: {name}")
            return None
            
        except Exception as e:
            logging.error(f"Error creating widget {name}: {e}")
            return None 