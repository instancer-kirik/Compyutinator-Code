from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QColorDialog, QInputDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPalette, QColor
from qt_material import apply_stylesheet, list_themes
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QComboBox, QPushButton, QLayout, QVBoxLayout, QInputDialog, QColorDialog
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
import logging
import time
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QComboBox, QPushButton, QColorDialog, QInputDialog
from PyQt6.QtWidgets import QProgressDialog, QFormLayout, QDialogButtonBox, QLineEdit, QDialog
import traceback
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QMessageBox, QTabWidget
from PyQt6.QtGui import QIcon
from GUX.theme_builder import ThemeBuilderWidget  # Import the ThemeBuilderWidget
from PyQt6.Qsci import QsciLexer
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
        theme_builder = ThemeBuilderWidget(self.theme_manager)
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.add_custom_button)
        layout.addWidget(theme_builder)
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
from NITTY_GRITTY.ThreadTrackers import SafeQThread
class ThemeApplier(SafeQThread):
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
        self.current_theme = {
            'name': 'default',
            'colors': {
                'sidebarBackground': '#2E3440',
                'sidebarText': '#D8DEE9',
                'sidebarHighlight': '#3B4252',
                'sidebarHover': '#434C5E'
            }
        }
        self.custom_themes_dir = os.path.join(os.path.dirname(__file__), 'custom_themes')
        os.makedirs(self.custom_themes_dir, exist_ok=True)
        self.load_config()
        self.load_custom_themes()

    def apply_theme(self, theme):
        logging.info(f"Applying theme: {theme}")
        try:
            if isinstance(theme, dict):
                theme_data = theme
                theme_name = theme.get('name', 'Custom Theme')
            else:
                theme_name = theme
                theme_data = self.get_theme_data(theme_name)

            if not theme_data:
                logging.error(f"Invalid theme data for {theme_name}")
                return

            # Apply Qt Material stylesheet if it's a built-in theme
            if theme_data.get('type') == 'built-in':
                apply_stylesheet(QApplication.instance(), theme=theme_name)
            else:
                # Apply custom stylesheet
                stylesheet = self.generate_stylesheet(theme_data)
                QApplication.instance().setStyleSheet(stylesheet)

            # Apply theme to all CodeEditor instances
            editors = self.get_all_code_editors()
            if editors:
                for editor in editors:
                    try:
                        editor.apply_theme(theme_data)
                    except Exception as e:
                        logging.error(f"Error applying theme to editor: {e}")
            else:
                logging.warning("No editors found to apply theme")

            self.current_theme_name = theme_name
            self.current_theme = theme_data
            self.save_config()
            self.theme_changed.emit(theme_data)
            logging.info("Theme applied successfully")

            # Apply lexer colors
            self.apply_lexer_colors(theme_data.get('lexer', {}))
        except Exception as e:
            logging.error(f"Error applying theme: {str(e)}")
            logging.error(traceback.format_exc())

    def get_theme_data(self, theme_name):
        if isinstance(theme_name, dict):
            return theme_name
        if theme_name in self.custom_themes:
            return self.custom_themes[theme_name]
        elif theme_name in list_themes():
            return {
                "name": theme_name,
                "type": "built-in",
                "colors": {
                    "backgroundColor": "#FFFFFF",
                    "textColor": "#000000",
                    "currentLineColor": "#E8F2FF",
                    "currentLineAlpha": 40,
                },
            }
        return None

    def generate_stylesheet(self, theme_data):
        # Generate QSS based on theme_data
        # This is a basic example, expand as needed
        colors = theme_data.get('colors', {})
        return f"""
            QWidget {{
                background-color: {colors.get('backgroundColor', '#FFFFFF')};
                color: {colors.get('textColor', '#000000')};
            }}
            /* Add more QSS rules based on your theme data */
        """

    def get_all_code_editors(self):
        return self.cccore.editor_manager.get_all_editors()

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
    def get_icon_path(self, icon_name):
        return os.path.join(self.config_dir, 'icons', icon_name)
    def get_icon(self, icon_name):
        return QIcon(self.get_icon_path(icon_name)) 
    def load_custom_themes(self):
        for filename in os.listdir(self.custom_themes_dir):
            if filename.endswith('.json'):
                theme_name = os.path.splitext(filename)[0]
                with open(os.path.join(self.custom_themes_dir, filename), 'r') as f:
                    self.custom_themes[theme_name] = json.load(f)

    def add_custom_theme(self, name, theme_data):
        self.custom_themes[name] = theme_data
        theme_path = os.path.join(self.custom_themes_dir, f"{name}.json")
        with open(theme_path, 'w') as f:
            json.dump(theme_data, f, indent=2)
        self.theme_changed.emit({'style': name})  # Emit the theme changed signal

    def apply_custom_theme(self, theme):
        app = QApplication.instance()
        stylesheet = self.generate_stylesheet(theme)
        app.setStyleSheet(stylesheet)

        # Apply syntax highlighting colors
        if 'highlighting' in theme:
            self.apply_syntax_highlighting(theme['highlighting'])

    def apply_syntax_highlighting(self, highlight_colors):
        # This method should update the syntax highlighter used in your code editors
        # The implementation will depend on how your syntax highlighting is set up
        # Here's a general idea:
        for editor in self.get_all_code_editors():
            highlighter = editor.syntax_highlighter
            if highlighter:
                highlighter.set_colors(highlight_colors)

    def get_available_themes(self):
        return list(self.custom_themes.keys()) + list_themes()

    def remove_custom_theme(self, name):
        if name in self.custom_themes:
            del self.custom_themes[name]
            self.save_config()

    def get_current_theme(self):
        return self.current_theme

    def update_theme(self, theme_name, theme_data):
        self.custom_themes[theme_name] = theme_data
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
        self.current_theme_data["last_focused_tab_color"] = color
        self.save_config()
        self.theme_changed.emit(self.current_theme_data)

    def apply_theme_to_editor(self, editor):
        try:
            colors = self.current_theme.get('editor_colors', {})
            logging.debug(f"Applying theme to editor with colors: {colors}")
            # Apply theme to the editor
            editor.setStyleSheet(f"""
                background-color: {self.current_theme["editor_theme"]};
                color: {self.current_theme["editor_fg"]};
                font-family: {self.current_theme["font"]};
            """)

            # Apply line highlight
            highlight_color = QColor(self.current_theme.get("lineHighlightColor", "#111111"))  # Dark yellow
            highlight_color.setAlpha(40)  # Adjust alpha for transparency
            editor.setCaretLineVisible(True)
            editor.setCaretLineBackgroundColor(QColor(0, 0, 0, .5))

            # Apply sidebar (line number area) color
            sidebar_color = QColor(self.current_theme.get("sidebarColor", "#2E3440"))
            editor.setMarginsBackgroundColor(sidebar_color)
            editor.setMarginsForegroundColor(QColor(self.current_theme.get("sidebarTextColor", "#D8DEE9")))

            # Ensure the changes are applied
            editor.update()
        except Exception as e:
            logging.error(f"Error applying theme to editor: {str(e)}")
            logging.error(traceback.format_exc())
    def get_current_theme_color(self, color_key, default_color):
        # Ensure current_theme is a dictionary containing theme data
        theme_data = self.get_theme_data(self.current_theme)
        if theme_data and 'colors' in theme_data:
            return theme_data['colors'].get(color_key, default_color)
        return default_color

    def generate_stylesheet(self, theme):
        colors = theme['colors']
        fonts = theme.get('fonts', {})
        dimensions = theme.get('dimensions', {})
        animations = theme.get('animations', {})
        styles = []

        # Load custom fonts
        for custom_font in theme.get('custom_fonts', []):
            styles.append(f"""
                @font-face {{
                    font-family: {custom_font['name']};
                    src: url({custom_font['path']});
                }}
            """)

        # Base styles
        styles.append(f"""
            QWidget {{
                background-color: {colors['backgroundColor']};
                color: {colors['textColor']};
                font-family: {fonts.get('main', 'Arial')};
                font-size: {fonts.get('size', '12')}px;
            }}
        """)

        # Window and dialog styles
        styles.append(f"""
            QMainWindow, QDialog {{
                border: {dimensions.get('windowBorder', '1px')} solid {colors.get('windowBorderColor', colors['textColor'])};
            }}
        """)

        # Button styles
        styles.append(f"""
            QPushButton {{
                background-color: {colors.get('buttonColor', colors['backgroundColor'])};
                color: {colors.get('buttonTextColor', colors['textColor'])};
                border: {dimensions.get('buttonBorder', '1px')} solid {colors.get('buttonBorderColor', colors['textColor'])};
                border-radius: {dimensions.get('buttonRadius', '3')}px;
                padding: {dimensions.get('buttonPadding', '5')}px;
                font-weight: {fonts.get('buttonWeight', 'normal')};
                font-size: {fonts.get('buttonSize', fonts.get('size', '12'))}px;
            }}
            QPushButton:hover {{
                background-color: {colors.get('buttonHoverColor', colors.get('buttonColor', colors['backgroundColor']))};
            }}
            QPushButton:pressed {{
                background-color: {colors.get('buttonPressedColor', colors.get('buttonColor', colors['backgroundColor']))};
            }}
        """)

        # Input field styles
        styles.append(f"""
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {colors.get('inputBackgroundColor', colors['backgroundColor'])};
                color: {colors.get('inputTextColor', colors['textColor'])};
                border: {dimensions.get('inputBorder', '1px')} solid {colors.get('inputBorderColor', colors['textColor'])};
                border-radius: {dimensions.get('inputRadius', '3')}px;
                padding: {dimensions.get('inputPadding', '3')}px;
                font-size: {fonts.get('inputSize', fonts.get('size', '12'))}px;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {colors.get('inputFocusBorderColor', colors.get('linkColor', colors['textColor']))};
            }}
        """)

        # Label styles
        styles.append(f"""
            QLabel {{
                color: {colors['textColor']};
                font-weight: {fonts.get('labelWeight', 'normal')};
                font-size: {fonts.get('labelSize', fonts.get('size', '12'))}px;
            }}
        """)

        # List and tree widget styles
        styles.append(f"""
            QListWidget, QTreeWidget {{
                background-color: {colors.get('listBackgroundColor', colors['backgroundColor'])};
                border: {dimensions.get('listBorder', '1px')} solid {colors.get('listBorderColor', colors['textColor'])};
                border-radius: {dimensions.get('listRadius', '3')}px;
                font-size: {fonts.get('listSize', fonts.get('size', '12'))}px;
            }}
            QListWidget::item, QTreeWidget::item {{
                padding: {dimensions.get('listItemPadding', '3')}px;
            }}
            QListWidget::item:selected, QTreeWidget::item:selected {{
                background-color: {colors.get('listSelectedColor', colors.get('linkColor', colors['textColor']))};
                color: {colors.get('listSelectedTextColor', colors['backgroundColor'])};
            }}
        """)

        # Menu styles
        styles.append(f"""
            QMenuBar {{
                background-color: {colors.get('menuBarColor', colors['backgroundColor'])};
                color: {colors.get('menuBarTextColor', colors['textColor'])};
                font-size: {fonts.get('menuBarSize', fonts.get('size', '12'))}px;
            }}
            QMenuBar::item:selected {{
                background-color: {colors.get('menuBarHoverColor', colors.get('linkColor', colors['textColor']))};
            }}
            QMenu {{
                background-color: {colors.get('menuColor', colors['backgroundColor'])};
                color: {colors.get('menuTextColor', colors['textColor'])};
                border: {dimensions.get('menuBorder', '1px')} solid {colors.get('menuBorderColor', colors['textColor'])};
                font-size: {fonts.get('menuSize', fonts.get('size', '12'))}px;
            }}
            QMenu::item:selected {{
                background-color: {colors.get('menuHoverColor', colors.get('linkColor', colors['textColor']))};
            }}
        """)

        # Tab widget styles
        styles.append(f"""
            QTabWidget::pane {{
                border: {dimensions.get('tabBorder', '1px')} solid {colors.get('tabBorderColor', colors['textColor'])};
            }}
            QTabBar::tab {{
                background-color: {colors.get('tabColor', colors['backgroundColor'])};
                color: {colors.get('tabTextColor', colors['textColor'])};
                padding: {dimensions.get('tabPadding', '5')}px;
                border: {dimensions.get('tabBorder', '1px')} solid {colors.get('tabBorderColor', colors['textColor'])};
                font-size: {fonts.get('tabSize', fonts.get('size', '12'))}px;
            }}
            QTabBar::tab:selected {{
                background-color: {colors.get('tabSelectedColor', colors.get('linkColor', colors['textColor']))};
                color: {colors.get('tabSelectedTextColor', colors['backgroundColor'])};
            }}
        """)

        # Scrollbar styles
        styles.append(f"""
            QScrollBar:vertical {{
                border: none;
                background-color: {colors.get('scrollbarBackgroundColor', colors['backgroundColor'])};
                width: {dimensions.get('scrollbarWidth', '10')}px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {colors.get('scrollbarHandleColor', colors.get('linkColor', colors['textColor']))};
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """)

        # Link styles
        styles.append(f"""
            a {{
                color: {colors['linkColor']};
                text-decoration: {fonts.get('linkDecoration', 'none')};
                font-size: {fonts.get('linkSize', fonts.get('size', '12'))}px;
            }}
        """)

        # Cursor styles
        styles.append(f"""
            QLineEdit, QTextEdit, QPlainTextEdit {{
                selection-background-color: {colors.get('selectionBackgroundColor', '#a6a6a6')};
                selection-color: {colors.get('selectionTextColor', colors['textColor'])};
            }}
        """)

        # Focus indicator
        styles.append(f"""
            QWidget:focus {{
                outline: {dimensions.get('focusOutlineWidth', '2px')} solid {colors.get('focusOutlineColor', colors['linkColor'])};
            }}
        """)

        # Slider styles
        styles.append(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {colors.get('sliderBorderColor', colors['textColor'])};
                height: {dimensions.get('sliderGrooveHeight', '4px')};
                background: {colors.get('sliderGrooveColor', colors['backgroundColor'])};
                margin: 2px 0;
            }}
            QSlider::handle:horizontal {{
                background: {colors.get('sliderHandleColor', colors['linkColor'])};
                border: 1px solid {colors.get('sliderHandleBorderColor', colors['textColor'])};
                width: {dimensions.get('sliderHandleWidth', '18px')};
                margin: -2px 0;
                border-radius: {dimensions.get('sliderHandleRadius', '3px')};
            }}
        """)

        # Checkbox and radio button styles
        styles.append(f"""
            QCheckBox::indicator, QRadioButton::indicator {{
                width: {dimensions.get('checkboxSize', '13px')};
                height: {dimensions.get('checkboxSize', '13px')};
            }}
            QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {{
                border: 1px solid {colors.get('checkboxBorderColor', colors['textColor'])};
                background-color: {colors.get('checkboxUncheckedColor', colors['backgroundColor'])};
            }}
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                border: 1px solid {colors.get('checkboxBorderColor', colors['textColor'])};
                background-color: {colors.get('checkboxCheckedColor', colors['linkColor'])};
            }}
        """)

        # Combo box styles
        styles.append(f"""
            QComboBox {{
                border: 1px solid {colors.get('comboBoxBorderColor', colors['textColor'])};
                border-radius: {dimensions.get('comboBoxRadius', '3px')};
                padding: 1px 18px 1px 3px;
                min-width: 6em;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: {colors.get('comboBoxArrowColor', colors['textColor'])};
                border-left-style: solid;
            }}
        """)

        # Group box styles
        styles.append(f"""
            QGroupBox {{
                border: 1px solid {colors.get('groupBoxBorderColor', colors['textColor'])};
                border-radius: {dimensions.get('groupBoxRadius', '5px')};
                margin-top: 1ex;
                font-size: {fonts.get('groupBoxTitleSize', fonts.get('size', '12'))}px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                color: {colors.get('groupBoxTitleColor', colors['textColor'])};
            }}
        """)

        # Status bar styles
        styles.append(f"""
            QStatusBar {{
                background-color: {colors.get('statusBarColor', colors['backgroundColor'])};
                color: {colors.get('statusBarTextColor', colors['textColor'])};
                border-top: 1px solid {colors.get('statusBarBorderColor', colors['textColor'])};
            }}
        """)

        # Dock widget styles
        styles.append(f"""
            QDockWidget {{
                titlebar-close-icon: url({theme.get('icons', {}).get('dockCloseIcon', 'path/to/default/close.png')});
                titlebar-normal-icon: url({theme.get('icons', {}).get('dockFloatIcon', 'path/to/default/float.png')});
            }}
            QDockWidget::title {{
                text-align: left;
                background: {colors.get('dockTitleColor', colors['backgroundColor'])};
                padding-left: 5px;
            }}
        """)

        # Header view styles
        styles.append(f"""
            QHeaderView::section {{
                background-color: {colors.get('headerBackgroundColor', colors['backgroundColor'])};
                color: {colors.get('headerTextColor', colors['textColor'])};
                padding-left: 4px;
                border: 1px solid {colors.get('headerBorderColor', colors['textColor'])};
            }}
        """)

        # Item view hover effects
        styles.append(f"""
            QAbstractItemView::item:hover {{
                background-color: {colors.get('itemHoverColor', colors.get('linkColor', colors['textColor']))};
            }}
        """)

        # Splitter styles
        styles.append(f"""
            QSplitter::handle {{
                background-color: {colors.get('splitterColor', colors['backgroundColor'])};
            }}
            QSplitter::handle:horizontal {{
                width: {dimensions.get('splitterWidth', '5px')};
            }}
            QSplitter::handle:vertical {{
                height: {dimensions.get('splitterWidth', '5px')};
            }}
        """)

        # Dialog button box styles
        styles.append(f"""
            QDialogButtonBox > QPushButton {{
                min-width: {dimensions.get('dialogButtonWidth', '80px')};
            }}
        """)

        # Disabled widget styles
        styles.append(f"""
            QWidget:disabled {{
                color: {colors.get('disabledTextColor', '#808080')};
                background-color: {colors.get('disabledBackgroundColor', '#f0f0f0')};
            }}
        """)
         # Toolbar and context menu styles
        styles.append(f"""
            QToolBar {{
                background-color: {colors.get('toolbarColor', colors['backgroundColor'])};
                border: none;
            }}
            QToolBar::separator {{
                background-color: {colors.get('toolbarSeparatorColor', colors['textColor'])};
                width: 1px;
                height: 1px;
            }}
            QMenu {{
                background-color: {colors.get('menuColor', colors['backgroundColor'])};
                color: {colors.get('menuTextColor', colors['textColor'])};
                border: 1px solid {colors.get('menuBorderColor', colors['textColor'])};
            }}
            QMenu::item:selected {{
                background-color: {colors.get('menuHoverColor', colors.get('linkColor', colors['textColor']))};
            }}
        """)
        # Add animation durations
        # styles.append(f"""
        #     QWidget {{
        #         transition-duration: {animations.get('hoverDuration', '200ms')};
        #     }}
        # """)

        return '\n'.join(styles)
    
    def update_custom_theme(self, theme_name, theme_data):
        # Update the theme data in your storage (e.g., JSON file)
        themes = self.get_available_themes()
        themes[theme_name] = theme_data
        self.update_theme(theme_name = theme_name, theme_data = theme_data)

    def get_all_themes(self):
        # Return a list of all theme names
        return list(self.get_available_themes())

    def update_custom_theme(self, theme_name, theme_data):
        self.custom_themes[theme_name] = theme_data
        self.save_custom_themes()
        self.theme_changed.emit(theme_data)

    def get_all_themes(self):
        # Combine custom themes and built-in themes
        return list(self.custom_themes.keys()) + list_themes()

    def save_custom_themes(self):
        for theme_name, theme_data in self.custom_themes.items():
            theme_file = os.path.join(self.custom_themes_dir, f"{theme_name}.json")
            with open(theme_file, 'w') as f:
                json.dump(theme_data, f, indent=2)

    def load_custom_themes(self):
        for filename in os.listdir(self.custom_themes_dir):
            if filename.endswith('.json'):
                theme_name = os.path.splitext(filename)[0]
                with open(os.path.join(self.custom_themes_dir, filename), 'r') as f:
                    self.custom_themes[theme_name] = json.load(f)

    def apply_lexer_colors(self, lexer_colors):
        for editor in self.get_all_code_editors():
            lexer = editor.current_lexer
            if isinstance(lexer, QsciLexer):
                self.set_lexer_colors(lexer, lexer_colors)
    def get_lexer_color_map(self):
        self.lexer_color_map = {
            'default': 0,
            'keyword': 1,
            'class': 2,
            'function': 3,
            'string': 4,
            'comment': 5,
            'number': 6,
            'operator': 7,
            'variable': 8,
            'preprocessor': 9,
            'identifier': 10,
            'constant': 11,
            'type': 12,
            'bracket': 13,
            'punctuation': 14,
            'label': 15,
            'error': 16,
            'warning': 17,
            'annotation': 18,
            'docComment': 19,
            'regex': 20,
            'attribute': 21,
            'builtinFunction': 22,
            'builtinClass': 23,
            'exception': 24,
            'import': 25,
            'module': 26,
            'property': 27,
            'method': 28,
            'parameter': 29,
            'namespace': 30,
            'interface': 31,
            'enum': 32,
            'boolean': 33,
            'null': 34,
            'escapeChar': 35,
            'heredoc': 36,
            'rawString': 37,
            'formatSpecifier': 38,
            'specialVariable': 39,
            'keywordArg': 40,
            'magicMethod': 41,
            'docstring': 42,
            'markupTag': 43,
            'markupAttribute': 44,
            'cssSelector': 45,
            'cssProperty': 46,
            'cssValue': 47,
            'sqlKeyword': 48,
            'sqlFunction': 49,
            'sqlTable': 50,
            'sqlColumn': 51
        }
        return self.lexer_color_map
    
    def set_lexer_colors(self, lexer, colors):
        color_map = self.get_lexer_color_map()

        for name, style in color_map.items():
            if name in colors:
                lexer.setColor(QColor(colors[name]), style)
                