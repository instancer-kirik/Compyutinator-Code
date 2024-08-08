import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QListWidget, QVBoxLayout, QWidget, QLabel, QPushButton
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtCore import QSettings, QByteArray, QUrl
from HMC.widget_manager import WidgetManager
from HMC.transcriptor_live_widget import VoiceTypingWidget
from GUX.overlay import CompositeOverlay, Flashlight
from GUX.log_viewer_widget import LogViewerWidget
log_directory = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

log_file_path = os.path.join(log_directory, 'app.log')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file_path, 'a'), logging.StreamHandler()])
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

def merge_themes(default_theme, custom_theme):
    merged_theme = default_theme.copy()
    merged_theme.update(custom_theme)
    return merged_theme

class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Computinator Code')
        self.setGeometry(300, 100, 800, 600)
        self.child_processes = {}
        self.history = []
        self.max_history_length = 10
        self.last_focused_widget = None
        self.flashlight = Flashlight(size=200)
        self.overlay = CompositeOverlay(flashlight_size=200, flashlight_power=0.069, serial_port=None)
        self.overlay.show()
        self.widget_manager = WidgetManager(self)
        self.initUI()
        self.load_settings()

    def initUI(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.handle_tab_change)
        self.setCentralWidget(self.tab_widget)

        self.add_history_tab()
        self.create_menu_bar()
        self.add_support_box()
        self.add_transcriptor_live_tab()
        self.add_logs_viewer_tab()
    def add_history_tab(self):
        self.history_widget = QListWidget()
        self.tab_widget.addTab(self.history_widget, "Action History")

    def update_history(self, path):
        if path in self.history:
            self.history.remove(path)
        self.history.insert(0, path)
        if len(self.history) > self.max_history_length:
            self.history.pop()

        self.history_widget.clear()
        for item in self.history:
            self.history_widget.addItem(item)

        if self.widget_manager.ai_chat_widget:
            self.widget_manager.ai_chat_widget.set_context(path)

    def handle_tab_change(self, index):
        self.last_focused_widget = self.tab_widget.widget(index)
        self.update_tab_color(index)

    def focus_changed_event(self, old, new):
        if new is not None and isinstance(new, QWidget):
            for widget in self.widget_manager.dock_widgets:
                if widget.isAncestorOf(new):
                    self.last_focused_widget = widget
                    self.update_tab_color(self.tab_widget.indexOf(self.last_focused_widget))
                    break

    def update_tab_color(self, index):
        tab_color = self.widget_manager.theme_manager_widget.current_theme["tab_colors"].get(index, self.widget_manager.theme_manager_widget.current_theme["last_focused_tab_color"])
        self.apply_tab_color(tab_color, index)

    def apply_tab_color(self, color, index):
        stylesheet = f"""
        QTabBar::tab:selected {{
            background-color: {color};
        }}
        """
        self.tab_widget.setStyleSheet(stylesheet)
        self.widget_manager.theme_manager_widget.current_theme["last_focused_tab_color"] = color

    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('File')
        save_layout_action = QAction('Save Layout', self)
        save_layout_action.triggered.connect(self.save_layout)
        file_menu.addAction(save_layout_action)

        load_layout_action = QAction('Load Layout', self)
        load_layout_action.triggered.connect(self.load_layout)
        file_menu.addAction(load_layout_action)

        view_menu = menubar.addMenu('View')

        self.add_toggle_view_action(view_menu, "Symbolic Linker", self.widget_manager.symbolic_linker_dock)
        self.add_toggle_view_action(view_menu, "File Explorer", self.widget_manager.file_explorer_dock)
        self.add_toggle_view_action(view_menu, "Code Editor", self.widget_manager.code_editor_dock)
        self.add_toggle_view_action(view_menu, "Process Manager", self.widget_manager.process_manager_dock)
        self.add_toggle_view_action(view_menu, "Action Pad", self.widget_manager.action_pad_dock)
        self.add_toggle_view_action(view_menu, "Terminal", self.widget_manager.terminal_dock)
        self.add_toggle_view_action(view_menu, "Theme Manager", self.widget_manager.theme_manager_dock)
        self.add_toggle_view_action(view_menu, "HTML Viewer", self.widget_manager.html_viewer_dock)
        self.add_toggle_view_action(view_menu, "AI Chat", self.widget_manager.ai_chat_dock)
        self.add_toggle_view_action(view_menu, "Media Player", self.widget_manager.media_player_dock)
        self.add_toggle_view_action(view_menu, "Download Manager", self.widget_manager.download_manager_dock)
        self.add_toggle_view_action(view_menu, "Sticky Notes", self.widget_manager.sticky_note_manager_dock)
        self.add_toggle_view_action(view_menu, "Overlay", self.widget_manager.overlay_dock)
        self.add_toggle_view_action(view_menu, "Diff Merger", self.widget_manager.diff_merger_dock)

    def add_toggle_view_action(self, menu, title, dock_widget):
        action = QAction(title, self, checkable=True)
        action.setChecked(True)
        action.triggered.connect(dock_widget.setVisible)
        dock_widget.visibilityChanged.connect(action.setChecked)
        menu.addAction(action)

    def save_layout(self):
        settings = QSettings("MyCompany", "MyApp")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def load_layout(self):
        settings = QSettings("MyCompany", "MyApp")
        geometry = settings.value("geometry")
        windowState = settings.value("windowState")
        if geometry:
            self.restoreGeometry(QByteArray(geometry))
        if windowState:
            self.restoreState(QByteArray(windowState))

    def load_settings(self):
        self.load_layout()

    def save_settings(self):
        self.save_layout()

    def apply_theme(self, theme):
        merged_theme = merge_themes(default_theme, theme)
        stylesheet = f"""
        QMainWindow {{
            background-color: {theme["main_window_color"]};
            color: {theme["text_color"]};
        }}
        QTreeView {{
            background-color: {theme["window_color"]};
            alternate-background-color: {theme["header_color"]};
            color: {theme["text_color"]};
            selection-background-color: {theme["theme_color"]};
            selection-color: {theme["text_color"]};
        }}
        QTreeView::item:hover {{
            background-color: {theme["theme_color"]};
        }}
        QTreeView::item:selected {{
            background-color: {theme["theme_color"]};
        }}
        QHeaderView::section {{
            background-color: {theme["header_color"]};
            color: {theme["text_color"]};
        }}
        QScrollBar:vertical {{
            background: {theme["scrollbar_color"]};
            width: 15px;
        }}
        QScrollBar::handle:vertical {{
            background: {theme["scrollbar_foreground_color"]};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            background: {theme["scrollbar_color"]};
        }}
        QScrollBar:horizontal {{
            background: {theme["scrollbar_color"]};
            height: 15px;
        }}
        QScrollBar::handle:horizontal {{
            background: {theme["scrollbar_foreground_color"]};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            background: {theme["scrollbar_color"]};
        }}
        QHeaderView::section {{
            background-color: {theme["header_color"]};
            color: {theme["text_color"]};
        }}
        """
        self.setStyleSheet(stylesheet)
        self.widget_manager.theme_manager_widget.current_theme = merged_theme
        for index in range(self.tab_widget.count()):
            tab_color = theme["tab_colors"].get(index, theme["last_focused_tab_color"])
            self.apply_tab_color(tab_color, index)

    def set_serial_port(self, port):
        self.serial_port = port
        logging.info(f"Serial port set to {port}")
        if self.serial_port:
            self.overlay.set_serial_port(port)

    def add_support_box(self):
        support_box = QWidget()
        support_layout = QVBoxLayout()
        support_label = QLabel("Support Me")
        github_button = QPushButton("https://github.com/instancer-kirik/BigLinks")
        github_button.clicked.connect(self.open_github)

        support_layout.addWidget(support_label)
        support_layout.addWidget(github_button)
        support_box.setLayout(support_layout)
        
        self.tab_widget.addTab(support_box, "Support Me")

    def open_github(self):
      QDesktopServices.openUrl(QUrl("https://github.com/instancer-kirik/BigLinks"))

    def add_transcriptor_live_tab(self):
        self.transcriptor_live_widget = VoiceTypingWidget(self)
        self.tab_widget.addTab(self.transcriptor_live_widget, "Voice Typing")
    def add_logs_viewer_tab(self):
        self.log_viewer_widget = LogViewerWidget(log_file_path=self.get_log_file_path())
        self.tab_widget.addTab(self.log_viewer_widget, "Logs Viewer")

    def get_log_file_path(self):
        return os.path.join(os.getcwd(), 'logs', 'app.log')
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = MainApplication()
    QApplication.instance().focusChanged.connect(main_app.focus_changed_event)
    main_app.show()
    sys.exit(app.exec())
