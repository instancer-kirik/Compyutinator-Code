from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QColorDialog, QInputDialog
from PyQt6.QtCore import pyqtSignal

class ThemeManagerWidget(QWidget):
    theme_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.current_theme = {
            "theme_color": "default",
            "scrollbar_color": "default",
            "header_color": "default",
            "main_window_color": "default",
            "window_color": "default",
            "tab_colors": {},
            "last_focused_tab_color": "default"
        }

        self.theme_color_button = QPushButton("Choose Theme Color")
        self.theme_color_button.clicked.connect(self.open_theme_color_dialog)
        self.layout.addWidget(self.theme_color_button)

        self.scrollbar_color_button = QPushButton("Choose Scrollbar Color")
        self.scrollbar_color_button.clicked.connect(self.open_scrollbar_color_dialog)
        self.layout.addWidget(self.scrollbar_color_button)

        self.header_color_button = QPushButton("Choose Header Color")
        self.header_color_button.clicked.connect(self.open_header_color_dialog)
        self.layout.addWidget(self.header_color_button)

        self.main_window_color_button = QPushButton("Choose Main Window Color")
        self.main_window_color_button.clicked.connect(self.open_main_window_color_dialog)
        self.layout.addWidget(self.main_window_color_button)

        self.window_color_button = QPushButton("Choose Window Color")
        self.window_color_button.clicked.connect(self.open_window_color_dialog)
        self.layout.addWidget(self.window_color_button)

        self.last_focused_tab_color_button = QPushButton("Choose Last Focused Tab Color")
        self.last_focused_tab_color_button.clicked.connect(self.open_last_focused_tab_color_dialog)
        self.layout.addWidget(self.last_focused_tab_color_button)

        self.tab_colors_button = QPushButton("Choose Tab Colors")
        self.tab_colors_button.clicked.connect(self.open_tab_colors_dialog)
        self.layout.addWidget(self.tab_colors_button)

        self.save_button = QPushButton("Save Theme")
        self.save_button.clicked.connect(self.save_theme)
        self.layout.addWidget(self.save_button)

        self.load_button = QPushButton("Load Theme")
        self.load_button.clicked.connect(self.load_theme)
        self.layout.addWidget(self.load_button)

    def open_theme_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_theme["theme_color"] = color.name()
            self.theme_changed.emit(self.current_theme)

    def open_scrollbar_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_theme["scrollbar_color"] = color.name()
            self.theme_changed.emit(self.current_theme)

    def open_header_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_theme["header_color"] = color.name()
            self.theme_changed.emit(self.current_theme)

    def open_main_window_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_theme["main_window_color"] = color.name()
            self.theme_changed.emit(self.current_theme)

    def open_window_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_theme["window_color"] = color.name()
            self.theme_changed.emit(self.current_theme)

    def open_last_focused_tab_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_theme["last_focused_tab_color"] = color.name()
            self.theme_changed.emit(self.current_theme)

    def open_tab_colors_dialog(self):
        tab_color = QColorDialog.getColor()
        if tab_color.isValid():
            tab_index, ok = QInputDialog.getInt(self, "Tab Index", "Enter the tab index:")
            if ok:
                self.current_theme["tab_colors"][tab_index] = tab_color.name()
                self.theme_changed.emit(self.current_theme)

    def save_theme(self):
        self.parentWidget().parent().save_settings()

    def load_theme(self):
        self.parentWidget().parent().load_settings()

    def apply_theme(self, theme):
        self.current_theme = theme
        self.theme_changed.emit(self.current_theme)

    def get_current_theme(self):
        return self.current_theme
theme = {
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
