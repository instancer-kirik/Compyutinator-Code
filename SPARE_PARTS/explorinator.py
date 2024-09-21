# import os
# import sys
# import logging
# from PyQt6.QtWidgets import QApplication, QMainWindow, QDockWidget, QTabWidget
# from PyQt6.QtGui import QAction
# from PyQt6.QtCore import Qt, QSettings
# from big_links import SymbolicLinkerWidget
# from file_explorer import FileExplorerWidget
# from code_editor import CodeEditorWidget
# from process_manager import ProcessManagerWidget
# from action_pad import ActionPadWidget
# from terminal_widget import TerminalWidget
# from theme_manager import ThemeManagerWidget
# from html_viewer import HTMLViewerWidget

# log_directory = os.path.join(os.getcwd(), 'logs')
# if not os.path.exists(log_directory):
#     os.makedirs(log_directory)

# log_file_path = os.path.join(log_directory, 'app.log')

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file_path, 'a'), logging.StreamHandler()])

# logging.info("Application started")

# class MainApplication(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle('Main Application')
#         self.setGeometry(300, 100, 800, 600)
#         self.child_processes = {}
#         self.initUI()
#         self.load_settings()

#     def initUI(self):
#         self.add_symbolic_linker_dock()
#         self.add_file_explorer_dock()
#         self.add_code_editor_dock()
#         self.add_process_manager_dock()
#         self.add_action_pad_dock()
#         self.add_terminal_dock()
#         self.add_theme_manager_dock()
#         self.add_html_viewer_dock()

#         # Adding menu bar for saving and loading layouts
#         menubar = self.menuBar()
#         file_menu = menubar.addMenu('File')
#         save_layout_action = QAction('Save Layout', self)
#         save_layout_action.triggered.connect(self.save_layout)
#         file_menu.addAction(save_layout_action)

#         load_layout_action = QAction('Load Layout', self)
#         load_layout_action.triggered.connect(self.load_layout)
#         file_menu.addAction(load_layout_action)

#         self.tab_widget = QTabWidget()
#         self.tab_widget.tabBarClicked.connect(self.handle_tab_change)
#         self.setCentralWidget(self.tab_widget)

#     def handle_tab_change(self, index):
#         tab_color = self.theme_manager_widget.current_theme["tab_color"]
#         self.apply_tab_color(QColor(tab_color), index)

#     def apply_tab_color(self, color, index):
#         stylesheet = f"""
#         QTabBar::tab:selected {{
#             background-color: {color.name()};
#         }}
#         """
#         self.tab_widget.setStyleSheet(stylesheet)

#     def add_symbolic_linker_dock(self):
#         self.symbolic_linker_widget = SymbolicLinkerWidget()
#         symbolic_linker_dock = QDockWidget("Symbolic Linker", self)
#         symbolic_linker_dock.setWidget(self.symbolic_linker_widget)
#         self.addDockWidget(Qt.LeftDockWidgetArea, symbolic_linker_dock)

#     def add_file_explorer_dock(self):
#         self.file_explorer_widget = FileExplorerWidget()
#         file_explorer_dock = QDockWidget("File Explorer", self)
#         file_explorer_dock.setWidget(self.file_explorer_widget)
#         self.addDockWidget(Qt.LeftDockWidgetArea, file_explorer_dock)

#     def add_code_editor_dock(self):
#         self.code_editor_widget = CodeEditorWidget()
#         code_editor_dock = QDockWidget("Code Editor", self)
#         code_editor_dock.setWidget(self.code_editor_widget)
#         self.addDockWidget(Qt.RightDockWidgetArea, code_editor_dock)

#     def add_process_manager_dock(self):
#         self.process_manager_widget = ProcessManagerWidget(self)
#         process_manager_dock = QDockWidget("Process Manager", self)
#         process_manager_dock.setWidget(self.process_manager_widget)
#         self.addDockWidget(Qt.BottomDockWidgetArea, process_manager_dock)

#     def add_action_pad_dock(self):
#         self.action_pad_widget = ActionPadWidget(self)
#         action_pad_dock = QDockWidget("Action Pad", self)
#         action_pad_dock.setWidget(self.action_pad_widget)
#         self.addDockWidget(Qt.BottomDockWidgetArea, action_pad_dock)

#     def add_terminal_dock(self):
#         self.terminal_widget = TerminalWidget()
#         terminal_dock = QDockWidget("Terminal", self)
#         terminal_dock.setWidget(self.terminal_widget)
#         self.addDockWidget(Qt.BottomDockWidgetArea, terminal_dock)

#     def add_theme_manager_dock(self):
#         self.theme_manager_widget = ThemeManagerWidget(self)
#         theme_manager_dock = QDockWidget("Theme Manager", self)
#         theme_manager_dock.setWidget(self.theme_manager_widget)
#         self.addDockWidget(Qt.RightDockWidgetArea, theme_manager_dock)

#     def add_html_viewer_dock(self):
#         self.html_viewer_widget = HTMLViewerWidget()
#         html_viewer_dock = QDockWidget("HTML Viewer", self)
#         html_viewer_dock.setWidget(self.html_viewer_widget)
#         self.addDockWidget(Qt.RightDockWidgetArea, html_viewer_dock)

#     def save_layout(self):
#         settings = QSettings("MyCompany", "MyApp")
#         settings.setValue("geometry", self.saveGeometry())
#         settings.setValue("windowState", self.saveState())

#     def load_layout(self):
#         settings = QSettings("MyCompany", "MyApp")
#         self.restoreGeometry(settings.value("geometry"))
#         self.restoreState(settings.value("windowState"))

#     def save_settings(self):
#         settings = QSettings("MyCompany", "MyApp")
#         theme = self.theme_manager_widget.get_current_theme()
#         settings.setValue("theme", theme)

#     def load_settings(self):
#         settings = QSettings("MyCompany", "MyApp")
#         self.restoreGeometry(settings.value("geometry"))
#         self.restoreState(settings.value("windowState"))
#         theme = settings.value("theme", {
#             "theme_color": "default",
#             "scrollbar_color": "default",
#             "header_color": "default",
#             "main_window_color": "default",
#             "window_color": "default",
#             "tab_color": "default"
#         })
#         self.theme_manager_widget.apply_theme(theme)

#     def closeEvent(self, event):
#         self.save_settings()
#         super().closeEvent(event)

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     main_app = MainApplication()
#     main_app.show()
#     sys.exit(app.exec_())
