import sys
import os
from PyQt6.QtCore import QUrl, Qt, QSize, QFileInfo
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QLineEdit, QProgressBar, QStatusBar,
                             QTabWidget, QMenu, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
                             QTreeView, QFileDialog, QSplitter, QWidget, QDockWidget, QTabBar, QStylePainter, QStyleOptionTab, QStyle)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QColor, QPalette
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineSettings,QWebEngineScript
from html_viewer import HTMLViewerWidget
from PyQt6.QtCore import QRect, QPoint

class CircularTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setUsesScrollButtons(True)
        self.setDocumentMode(True)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.setCurrentIndex((self.currentIndex() - 1) % self.count())
        else:
            self.setCurrentIndex((self.currentIndex() + 1) % self.count())

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        size.setWidth(min(200, size.width()))  # Limit max width to 200 pixels
        return size

    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionTab()

        for i in range(self.count()):
            self.initStyleOption(opt, i)
            if opt.text:
                text_rect = self.style().subElementRect(QStyle.SubElement.SE_TabBarTabText, opt, self)
                painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, opt)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextShowMnemonic, opt.text)
            else:
                painter.drawControl(QStyle.ControlElement.CE_TabBarTab, opt)

class ImprovedTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(CircularTabBar(self))
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setMovable(True)
        self.setTabsClosable(True)

class AdvancedBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.dev_tools_windows = {}  # Store dev tools windows for each tab
        self.page_profiles = {}

    def initUI(self):
        self.setWindowTitle('Custom Web Browser')
        self.setGeometry(100, 100, 1280, 800)

        # Create ImprovedTabWidget
        self.tabs = ImprovedTabWidget()
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        # Create NavBar
        navbar = QToolBar()
        self.addToolBar(navbar)

        # Back Button
        back_btn = QAction(QIcon('icons/back.png'), 'Back', self)
        back_btn.triggered.connect(lambda: self.current_tab().back())
        navbar.addAction(back_btn)

        # Forward Button
        forward_btn = QAction(QIcon('icons/forward.png'), 'Forward', self)
        forward_btn.triggered.connect(lambda: self.current_tab().forward())
        navbar.addAction(forward_btn)

        # Reload Button
        reload_btn = QAction(QIcon('icons/reload.png'), 'Reload', self)
        reload_btn.triggered.connect(lambda: self.current_tab().reload())
        navbar.addAction(reload_btn)

        # Home Button
        home_btn = QAction(QIcon('icons/home.png'), 'Home', self)
        home_btn.triggered.connect(self.navigate_home)
        navbar.addAction(home_btn)

        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navbar.addWidget(self.url_bar)

        # New Tab Button
        new_tab_btn = QAction(QIcon('icons/new_tab.png'), 'New Tab', self)
        new_tab_btn.triggered.connect(self.add_new_tab)
        navbar.addAction(new_tab_btn)

        # Bookmarks Button
        bookmarks_btn = QAction(QIcon('icons/bookmark.png'), 'Bookmarks', self)
        bookmarks_btn.triggered.connect(self.show_bookmarks)
        navbar.addAction(bookmarks_btn)

        # History Button
        history_btn = QAction(QIcon('icons/history.png'), 'History', self)
        history_btn.triggered.connect(self.show_history)
        navbar.addAction(history_btn)

        # Downloads Button
        downloads_btn = QAction(QIcon('icons/download.png'), 'Downloads', self)
        downloads_btn.triggered.connect(self.show_downloads)
        navbar.addAction(downloads_btn)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(120)
        navbar.addWidget(self.progress_bar)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Create side tray
        self.side_tray = QDockWidget("Side Tray", self)
        self.side_tray.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.side_tray)

        side_tray_widget = QWidget()
        side_tray_layout = QVBoxLayout(side_tray_widget)

        # Bookmark folders
        self.bookmark_tree = QTreeView()
        self.bookmark_model = QStandardItemModel()
        self.bookmark_tree.setModel(self.bookmark_model)
        side_tray_layout.addWidget(self.bookmark_tree)

        # Grouped tabs
        self.grouped_tabs = QListWidget()
        side_tray_layout.addWidget(self.grouped_tabs)

        self.side_tray.setWidget(side_tray_widget)

        # Developer tools action
        dev_tools_action = QAction(QIcon('icons/dev_tools.png'), 'Developer Tools', self)
        dev_tools_action.triggered.connect(self.toggle_dev_tools)
        navbar.addAction(dev_tools_action)

        # Styles dashboard
        self.styles_dashboard = HTMLViewerWidget()
        styles_dock = QDockWidget("Styles Dashboard", self)
        styles_dock.setWidget(self.styles_dashboard)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, styles_dock)

        # Set default dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QToolBar, QStatusBar {
                background-color: #333333;
                color: #ffffff;
            }
            QLineEdit, QTreeView, QListWidget {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QPushButton {
                background-color: #4c4c4c;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QPushButton:hover {
                background-color: #5c5c5c;
            }
            QTabWidget::pane {
                border-top: 2px solid #555555;
            }
            QTabBar::tab {
                background-color: #3c3f41;
                color: #ffffff;
                padding: 5px;
            }
            QTabBar::tab:selected {
                background-color: #4c4c4c;
            }
        """)

        # Set up dark mode for web content
        self.setup_dark_mode_for_web()

        # Bookmarks
        self.bookmarks = []

        # History
        self.history = []

        # Downloads
        self.downloads = []

        # Add initial tab
        self.add_new_tab()

    def setup_dark_mode_for_web(self):
        # Create a QWebEngineScript to inject custom CSS
        dark_mode_js = """
        (function() {
            function addStyle(css) {
                const style = document.createElement('style');
                style.textContent = css;
                document.head.appendChild(style);
            }
            
            const css = `
                html, body, input, textarea, select, button {
                    background-color: #2b2b2b !important;
                    color: #e8e6e3 !important;
                    border-color: #555555 !important;
                }
                a {
                    color: #6699cc !important;
                }
                a:visited {
                    color: #9966cc !important;
                }
                input, textarea, select, button {
                    background-color: #3c3f41 !important;
                }
                ::-webkit-scrollbar {
                    width: 12px;
                    height: 12px;
                    background-color: #2b2b2b;
                }
                ::-webkit-scrollbar-thumb {
                    background-color: #555555;
                }
                ::placeholder {
                    color: #888888 !important;
                }
            `;
            
            addStyle(css);
            
            // Re-inject styles periodically to override any dynamic changes
            setInterval(function() {
                addStyle(css);
            }, 1000);
        })()
        """
        script = QWebEngineScript()
        script.setName("dark_mode")
        script.setSourceCode(dark_mode_js)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)

        # Add the script to the default profile
        QWebEngineProfile.defaultProfile().scripts().insert(script)

    def add_new_tab(self, qurl=None):
        if qurl is None:
            qurl = QUrl('https://duckduckgo.com')

        browser = QWebEngineView()
        
        # Set custom headers
        profile = QWebEngineProfile(browser)
        profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Disable FLoC
        profile.setHttpAcceptLanguage("en-US,en;q=0.9")
        profile.setHttpUserAgent(profile.httpUserAgent() + " Permissions-Policy: interest-cohort=()")

        page = QWebEnginePage(profile, browser)
        browser.setPage(page)
        
        # Set dark background for web view
        browser.setStyleSheet("background-color: #2b2b2b;")
        browser.page().setBackgroundColor(QColor(43, 43, 43))  # #2b2b2b in RGB
        
        # Load empty HTML with dark background
        initial_html = """
        <html>
        <head>
            <style>
                body { background-color: #2b2b2b; margin: 0; padding: 0; height: 100vh; }
            </style>
        </head>
        <body></body>
        </html>
        """
        browser.setHtml(initial_html)
        
        # Now set the actual URL
        browser.setUrl(qurl)
        
        i = self.tabs.addTab(browser, "New Tab")
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(lambda _, i=i, browser=browser: self.tabs.setTabText(i, browser.page().title()))
        browser.loadProgress.connect(self.update_progress)
        browser.page().profile().downloadRequested.connect(self.download_requested)

        # Connect tab index changed signal
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Update grouped tabs
        self.update_grouped_tabs()

    def current_tab(self):
        return self.tabs.currentWidget()

    def close_tab(self, i):
        if self.tabs.count() < 2:
            return
        
        # Close associated dev tools window if it exists
        if i in self.dev_tools_windows:
            self.dev_tools_windows[i].close()
            del self.dev_tools_windows[i]
        
        self.tabs.removeTab(i)
        self.update_grouped_tabs()

    def navigate_home(self):
        self.current_tab().setUrl(QUrl("https://duckduckgo.com"))

    def navigate_to_url(self):
        q = QUrl(self.url_bar.text())
        if q.scheme() == "":
            q.setScheme("http")
        self.current_tab().setUrl(q)

    def update_urlbar(self, q, browser=None):
        if browser != self.current_tab():
            return
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def show_bookmarks(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Bookmarks")
        layout = QVBoxLayout()
        bookmarks_list = QListWidget()
        for bookmark in self.bookmarks:
            bookmarks_list.addItem(bookmark)
        layout.addWidget(bookmarks_list)
        dialog.setLayout(layout)
        dialog.exec()

    def show_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("History")
        layout = QVBoxLayout()
        history_list = QListWidget()
        for item in self.history:
            history_list.addItem(item)
        layout.addWidget(history_list)
        dialog.setLayout(layout)
        dialog.exec()

    def show_downloads(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Downloads")
        layout = QVBoxLayout()
        downloads_list = QListWidget()
        for item in self.downloads:
            downloads_list.addItem(item)
        layout.addWidget(downloads_list)
        dialog.setLayout(layout)
        dialog.exec()

    def download_requested(self, download):
        old_path = download.path()
        suffix = QFileInfo(old_path).suffix()
        path, _ = QFileDialog.getSaveFileName(self, "Save File", old_path, f"*.{suffix}")
        if path:
            download.setPath(path)
            download.accept()
            self.downloads.append(os.path.basename(path))

    def toggle_dev_tools(self):
        current_tab = self.current_tab()
        if current_tab:
            if self.tabs.currentIndex() in self.dev_tools_windows:
                # If dev tools window exists, toggle its visibility
                dev_tools_window = self.dev_tools_windows[self.tabs.currentIndex()]
                if dev_tools_window.isVisible():
                    dev_tools_window.hide()
                else:
                    dev_tools_window.show()
            else:
                # Create new dev tools window
                dev_tools_page = QWebEnginePage(current_tab.page().profile(), current_tab)
                current_tab.page().setDevToolsPage(dev_tools_page)

                dev_tools_view = QWebEngineView()
                dev_tools_view.setPage(dev_tools_page)

                # Set dark background for dev tools
                dev_tools_view.setStyleSheet("background-color: #2b2b2b;")
                dev_tools_view.page().setBackgroundColor(QColor(43, 43, 43))

                dev_tools_window = QDockWidget("Developer Tools", self)
                dev_tools_window.setWidget(dev_tools_view)
                dev_tools_window.setFloating(True)
                dev_tools_window.resize(800, 600)
                dev_tools_window.show()

                self.dev_tools_windows[self.tabs.currentIndex()] = dev_tools_window

    def update_grouped_tabs(self):
        self.grouped_tabs.clear()
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            self.grouped_tabs.addItem(f"Tab {i+1}: {tab.page().title()}")

    def add_bookmark_folder(self, folder_name):
        folder_item = QStandardItem(folder_name)
        self.bookmark_model.appendRow(folder_item)

    def add_bookmark(self, url, folder_name=None):
        bookmark_item = QStandardItem(url)
        if folder_name:
            for row in range(self.bookmark_model.rowCount()):
                folder_item = self.bookmark_model.item(row)
                if folder_item.text() == folder_name:
                    folder_item.appendRow(bookmark_item)
                    return
        self.bookmark_model.appendRow(bookmark_item)

    def on_tab_changed(self, index):
        # Update dev tools window visibility when switching tabs
        for i, window in self.dev_tools_windows.items():
            if i == index:
                window.show()
            else:
                window.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    browser = AdvancedBrowser()
    browser.show()
    sys.exit(app.exec())