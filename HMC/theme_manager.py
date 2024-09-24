from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QColorDialog, QInputDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPalette, QColor
from qt_material import apply_stylesheet, list_themes
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QComboBox, QPushButton, QVBoxLayout, QInputDialog, QColorDialog
from PyQt6.QtCore import Qt, QObject, pyqtSignal
import logging

class ThemeManagerWidget(QWidget):
    def __init__(self, theme_manager):
        super().__init__()
        self.theme_manager = theme_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Add UI elements for theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.get_available_themes())
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        layout.addWidget(self.theme_combo)

        # Add color pickers for all custom colors
        color_keys = [
            "main_window_color", "window_color", "header_color", "theme_color",
            "scrollbar_color", "scrollbar_foreground_color", "text_color",
            "last_focused_tab_color"
        ]
        for color_key in color_keys:
            button = QPushButton(f"Choose {color_key.replace('_', ' ').title()}")
            button.clicked.connect(lambda _, ck=color_key: self.choose_color(ck))
            layout.addWidget(button)
    
        # Add button for tab colors
        tab_color_button = QPushButton("Set Tab Color")
        tab_color_button.clicked.connect(self.set_tab_color)
        layout.addWidget(tab_color_button)
    def on_theme_changed(self, theme_name):
        try:
            self.theme_manager.current_theme["style"] = theme_name
            self.theme_manager.save_theme()
            self.theme_manager.apply_theme(self.window())
        except Exception as e:
            logging.error(f"Error changing theme: {e}")
            # Optionally, show an error message to the user

    def get_current_theme(self):
        return self.theme_manager.current_theme

    def choose_color(self, color_key):
        color = QColorDialog.getColor()
        if color.isValid():
            self.theme_manager.update_theme({color_key: color.name()})

    def set_tab_color(self):
        tab_index, ok = QInputDialog.getInt(self, "Tab Index", "Enter the tab index:")
        if ok:
            color = QColorDialog.getColor()
            if color.isValid():
                self.theme_manager.set_tab_color(tab_index, color.name())

    def set_current_theme(self, theme_name):
        index = self.theme_combo.findText(theme_name)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

    def refresh_themes(self):
        current_theme = self.theme_combo.currentText()
        self.theme_combo.clear()
        self.theme_combo.addItems(self.theme_manager.get_available_themes())
        self.set_current_theme(current_theme)

class ThemeManager(QObject):
    theme_changed = pyqtSignal(dict)

    def __init__(self, cccore):
        super().__init__()
        self.settings_manager = cccore.settings_manager
        self.current_theme = self.load_theme()
        self.is_applying_theme = False

    def load_theme(self):
        theme = self.settings_manager.get_value("theme", default={})
        default_theme = self.get_default_theme()
        # Merge the loaded theme with default theme to ensure all keys exist
        for key, value in default_theme.items():
            if isinstance(value, dict):
                theme[key] = {**value, **theme.get(key, {})}
            else:
                theme.setdefault(key, value)
        return theme

    def save_theme(self, theme):
        self.settings_manager.set_value("theme", theme)
        self.current_theme = theme

    def get_default_theme(self):
        return {
            "style": "dark_teal.xml",
            "editor_theme": "#2E3440",
            "editor_fg": "#D8DEE9",
            "font": "Courier",
            "main_window_color": "#2E3440",  # Add this line
            "window_color": "#3B4252",
            "header_color": "#4C566A",
            "theme_color": "#81A1C1",
            "scrollbar_color": "#4C566A",
            "scrollbar_foreground_color": "#D8DEE9",
            "text_color": "#ECEFF4",
            "tab_colors": {
                "0": "#81A1C1",
                "1": "#88C0D0",
                "2": "#5E81AC",
            },
            "last_focused_tab_color": "#81A1C1"
        }

    def apply_theme(self, widget):
        if self.is_applying_theme:
            logging.info("Theme application already in progress. Skipping.")
            return

        self.is_applying_theme = True
        logging.info("Applying theme...")
        try:
            style = self.current_theme.get("style", "dark_teal.xml")
            logging.info(f"Applying stylesheet: {style}")
            apply_stylesheet(widget, theme=style, invert_secondary=True, extra={'density_scale': '-1'})
            logging.info("Stylesheet applied successfully")
            self.apply_custom_colors(widget)
            logging.info("Custom colors applied successfully")

            # Apply theme to AuraTextWindow if it exists
            if hasattr(widget, 'auratext_window'):
                widget.auratext_window.apply_theme(self.current_theme)

            self.theme_changed.emit(self.current_theme)
        except Exception as e:
            logging.error(f"Error applying theme: {e}")
        finally:
            self.is_applying_theme = False
            logging.info("Theme application complete")

    def apply_custom_colors(self, widget):
        # Apply custom colors here if needed
        pass

    def update_theme(self, new_theme):
        self.current_theme.update(new_theme)
        self.save_theme(self.current_theme)
        self.apply_theme()

    def get_available_themes(self):
        return list_themes()

    def get_tab_color(self, index):
        return self.current_theme["tab_colors"].get(index, self.current_theme["last_focused_tab_color"])

    def set_tab_color(self, index, color):
        self.current_theme["tab_colors"][index] = color
        self.save_theme(self.current_theme)
        self.theme_changed.emit(self.current_theme)

    def set_last_focused_tab_color(self, color):
        self.current_theme["last_focused_tab_color"] = color
        self.save_theme(self.current_theme)
        self.theme_changed.emit(self.current_theme)