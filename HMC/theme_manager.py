from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QColorDialog, QInputDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPalette, QColor
from qt_material import apply_stylesheet, list_themes
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QComboBox, QPushButton, QLayout, QVBoxLayout, QInputDialog, QColorDialog
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QThread
import logging
import time
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QComboBox, QPushButton, QColorDialog, QInputDialog
from PyQt6.QtWidgets import QProgressDialog, QFormLayout, QDialogButtonBox, QLineEdit, QDialog
import traceback
import json
import os
class CustomThemeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Custom Theme")
        layout = QFormLayout(self)
        self.name_input = QLineEdit(self)
        self.style_input = QLineEdit(self)
        layout.addRow("Theme Name:", self.name_input)
        layout.addRow("Style File:", self.style_input)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

class ThemeManagerWidget(QWidget):
    theme_selected = pyqtSignal(str)

    def __init__(self, theme_manager):
        super().__init__()
        self.theme_manager = theme_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.theme_combo = QComboBox()
        self.update_theme_list()
        self.apply_button = QPushButton("Apply Theme")
        self.add_custom_button = QPushButton("Add Custom Theme")
        
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.add_custom_button)
        self.setLayout(layout)

        self.apply_button.clicked.connect(self.on_apply_theme)
        self.add_custom_button.clicked.connect(self.on_add_custom_theme)

    def update_theme_list(self):
        self.theme_combo.clear()
        self.theme_combo.addItems(self.theme_manager.get_available_themes())
        current_theme = self.theme_manager.get_current_theme()
        index = self.theme_combo.findText(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

    def on_apply_theme(self):
        selected_theme = self.theme_combo.currentText()
        self.theme_manager.apply_theme(selected_theme)

    def on_add_custom_theme(self):
        dialog = CustomThemeDialog(self)
        if dialog.exec():
            name = dialog.name_input.text()
            style = dialog.style_input.text()
            self.theme_manager.add_custom_theme(name, {'style': style})
            self.update_theme_list()
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

class ThemeApplier(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, theme_manager, widget, theme):
        super().__init__()
        self.theme_manager = theme_manager
        self.widget = widget
        self.theme = theme
        self.total_widgets = 0
        self.processed_widgets = 0

    def run(self):
        self.total_widgets = self.count_widgets(self.widget)
        self.theme_manager.apply_theme_to_widget(self.widget, self.theme, self.update_progress)
        self.finished.emit()

    def count_widgets(self, widget):
        count = 1
        for child in widget.findChildren(QWidget):
            count += self.count_widgets(child)
        return count

    def update_progress(self):
        self.processed_widgets += 1
        progress = int((self.processed_widgets / self.total_widgets) * 100)
        self.progress.emit(progress)

class ThemeManager(QObject):
    theme_changed = pyqtSignal(dict)

    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.config_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.config_dir, 'theme_config.json')
        self.custom_themes = {}
        self.current_theme = 'dark_amber.xml'  # Default theme
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.custom_themes = config.get('custom_themes', {})
                self.current_theme = config.get('current_theme', self.current_theme)
        except FileNotFoundError:
            logging.warning("Theme config file not found. Creating a new one with default settings.")
            self.save_config()
        except json.JSONDecodeError:
            logging.error("Error decoding theme config file. Using default settings.")
            self.save_config()

    def save_config(self):
        config = {
            'current_theme': self.current_theme,
            'custom_themes': self.custom_themes
        }
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def apply_theme(self, theme_name):
        if theme_name in self.custom_themes:
            theme = self.custom_themes[theme_name]
        elif theme_name in list_themes():
            theme = {'style': theme_name}
        else:
            logging.error(f"Theme {theme_name} not found. Using default theme.")
            theme = {'style': 'dark_amber.xml'}

        logging.info(f"Applying theme: {theme_name}")
        try:
            apply_stylesheet(QApplication.instance(), theme=theme['style'])
            self.current_theme = theme_name
            self.save_config()
            self.theme_changed.emit(theme)
            logging.info("Theme applied successfully")
        except Exception as e:
            logging.error(f"Error applying theme: {e}")

    def get_available_themes(self):
        return list(self.custom_themes.keys()) + list_themes()

    def add_custom_theme(self, name, theme_data):
        self.custom_themes[name] = theme_data
        self.save_config()

    def remove_custom_theme(self, name):
        if name in self.custom_themes:
            del self.custom_themes[name]
            self.save_config()

    def get_current_theme(self):
        return self.current_theme

    def update_theme(self, theme_data):
        self.current_theme.update(theme_data)
        self.save_config()

    def apply_theme_to_widget(self, widget, theme, update_progress):
        # Apply theme to the widget
        widget.setStyleSheet(f"""
            background-color: {theme.get('main_window_color', '#2E3440')};
            color: {theme.get('text_color', '#ECEFF4')};
            font-family: {theme.get('font', 'Courier')};
        """)

        # Update progress
        update_progress()

    def set_tab_color(self, index, color):
        self.current_theme["tab_colors"][index] = color
        self.save_config()
        self.theme_changed.emit(self.current_theme)

    def set_last_focused_tab_color(self, color):
        self.current_theme["last_focused_tab_color"] = color
        self.save_config()
        self.theme_changed.emit(self.current_theme)

    def apply_theme_to_editor(self, editor):
        # Apply theme to the editor
        editor.setStyleSheet(f"""
            background-color: {self.current_theme["editor_theme"]};
            color: {self.current_theme["editor_fg"]};
            font-family: {self.current_theme["font"]};
        """)
