from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QColorDialog
from PyQt6.QtGui import QColor

class ThemeManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_theme = {
            "theme_color": "default",
            "scrollbar_color": "default",
            "header_color": "default",
            "main_window_color": "default",
            "window_color": "default",
            "tab_color": "default"
        }

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

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

        self.tab_color_button = QPushButton("Choose Tab Color")
        self.tab_color_button.clicked.connect(self.open_tab_color_dialog)
        self.layout.addWidget(self.tab_color_button)

    def open_theme_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.apply_theme_color(color)
            self.current_theme["theme_color"] = color.name()

    def open_scrollbar_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.apply_scrollbar_color(color)
            self.current_theme["scrollbar_color"] = color.name()

    def open_header_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.apply_header_color(color)
            self.current_theme["header_color"] = color.name()

    def open_main_window_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.apply_main_window_color(color)
            self.current_theme["main_window_color"] = color.name()

    def open_window_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.apply_window_color(color)
            self.current_theme["window_color"] = color.name()

    def open_tab_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.apply_tab_color(color)
            self.current_theme["tab_color"] = color.name()

    def apply_theme_color(self, color):
        stylesheet = f"""
        QMainWindow {{
            background-color: {color.name()};
        }}
        QWidget {{
            background-color: {color.name()};
        }}
        """
        self.parent.setStyleSheet(self.parent.styleSheet() + stylesheet)

    def apply_scrollbar_color(self, color):
        stylesheet = f"""
        QScrollBar:vertical {{
            background: {color.darker().name()};
            width: 15px;
        }}
        QScrollBar::handle:vertical {{
            background: {color.name()};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            background: {color.darker().name()};
        }}
        QScrollBar:horizontal {{
            background: {color.darker().name()};
            height: 15px;
        }}
        QScrollBar::handle:horizontal {{
            background: {color.name()};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            background: {color.darker().name()};
        }}
        """
        self.parent.setStyleSheet(self.parent.styleSheet() + stylesheet)

    def apply_header_color(self, color):
        stylesheet = f"""
        QHeaderView::section {{
            background-color: {color.name()};
            color: #FFFFFF;
        }}
        """
        self.parent.setStyleSheet(self.parent.styleSheet() + stylesheet)

    def apply_main_window_color(self, color):
        stylesheet = f"""
        QMainWindow {{
            background-color: {color.name()};
        }}
        """
        self.parent.setStyleSheet(self.parent.styleSheet() + stylesheet)

    def apply_window_color(self, color):
        stylesheet = f"""
        QDockWidget {{
            background-color: {color.name()};
        }}
        """
        self.parent.setStyleSheet(self.parent.styleSheet() + stylesheet)

    def apply_tab_color(self, color):
        stylesheet = f"""
        QTabBar::tab {{
            background-color: {color.name()};
            color: #FFFFFF;
        }}
        QTabBar::tab:selected {{
            background-color: {color.darker().name()};
        }}
        QTabWidget::pane {{
            border: 1px solid {color.darker().name()};
        }}
        """
        self.parent.setStyleSheet(self.parent.styleSheet() + stylesheet)

    def get_current_theme(self):
        return self.current_theme

    def apply_theme(self, theme):
        theme_color = QColor(theme["theme_color"])
        scrollbar_color = QColor(theme["scrollbar_color"])
        header_color = QColor(theme["header_color"])
        main_window_color = QColor(theme["main_window_color"])
        window_color = QColor(theme["window_color"])
        tab_color = QColor(theme["tab_color"])

        self.apply_theme_color(theme_color)
        self.apply_scrollbar_color(scrollbar_color)
        self.apply_header_color(header_color)
        self.apply_main_window_color(main_window_color)
        self.apply_window_color(window_color)
        self.apply_tab_color(tab_color)

        self.current_theme = theme
