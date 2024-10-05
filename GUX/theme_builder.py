from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QColorDialog, QSlider,
                             QScrollArea, QSpinBox, QComboBox, QFormLayout, QGroupBox,
                             QListWidget, QStackedWidget, QInputDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import json
import os

class ColorPicker(QWidget):
    def __init__(self, label):
        super().__init__()
        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel(label))
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 25)
        self.color_button.clicked.connect(self.pick_color)
        layout.addWidget(self.color_button)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_button.setStyleSheet(f"background-color: {color.name()};")

    def get_color(self):
        return self.color_button.palette().button().color().name()

class StyleInput(QWidget):
    def __init__(self, label, input_type=QLineEdit):
        super().__init__()
        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel(label))
        self.input = input_type()
      
        layout.addWidget(self.input)

    def get_value(self):
        if isinstance(self.input, QComboBox):
            return self.input.currentText()
        return self.input.text() if isinstance(self.input, QLineEdit) else self.input.value()

class ThemeBuilderWidget(QWidget):
    def __init__(self, theme_manager):
        super().__init__()
        self.theme_manager = theme_manager
        self.current_theme = None  # To store the currently edited theme
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Theme name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Theme Name:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Scroll area for all options
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # General colors
        general_group = QGroupBox("General Colors")
        general_layout = QFormLayout()
        self.color_pickers = {
            "backgroundColor": ColorPicker("Background Color"),
            "textColor": ColorPicker("Text Color"),
            "linkColor": ColorPicker("Link Color"),
        }
        for name, picker in self.color_pickers.items():
            general_layout.addRow(picker)
        general_group.setLayout(general_layout)
        scroll_layout.addWidget(general_group)

        # Code highlighting colors
        highlight_group = QGroupBox("Code Highlighting")
        highlight_layout = QFormLayout()
        self.highlight_pickers = {
            "keyword": ColorPicker("Keyword"),
            "string": ColorPicker("String"),
            "comment": ColorPicker("Comment"),
            "function": ColorPicker("Function"),
            "class": ColorPicker("Class"),
            "number": ColorPicker("Number"),
            "operator": ColorPicker("Operator"),
        }
        for name, picker in self.highlight_pickers.items():
            highlight_layout.addRow(picker)
        highlight_group.setLayout(highlight_layout)
        scroll_layout.addWidget(highlight_group)

        # Code Editor Sidebar options
        sidebar_group = QGroupBox("Code Editor Sidebar")
        sidebar_layout = QFormLayout()
        self.sidebar_pickers = {
            "sidebarBackground": ColorPicker("Sidebar Background"),
            "sidebarText": ColorPicker("Sidebar Text"),
            "sidebarHighlight": ColorPicker("Sidebar Highlight"),
        }
        for name, picker in self.sidebar_pickers.items():
            sidebar_layout.addRow(picker)
        sidebar_group.setLayout(sidebar_layout)
        scroll_layout.addWidget(sidebar_group)

        # Toolbar and context menu options
        toolbar_group = QGroupBox("Toolbar and Context Menu")
        toolbar_layout = QFormLayout()
        self.toolbar_pickers = {
            "toolbarColor": ColorPicker("Toolbar Color"),
            "toolbarSeparatorColor": ColorPicker("Toolbar Separator Color"),
            "menuColor": ColorPicker("Menu Background Color"),
            "menuTextColor": ColorPicker("Menu Text Color"),
            "menuBorderColor": ColorPicker("Menu Border Color"),
            "menuHoverColor": ColorPicker("Menu Hover Color"),
        }
        for name, picker in self.toolbar_pickers.items():
            toolbar_layout.addRow(picker)
        toolbar_group.setLayout(toolbar_layout)
        scroll_layout.addWidget(toolbar_group)

        # Code editor options
        editor_group = QGroupBox("Code Editor")
        editor_layout = QFormLayout()
        self.editor_pickers = {
            "lineHighlightColor": ColorPicker("Line Highlight Color"),
            "sidebarColor": ColorPicker("Sidebar Color"),
            "sidebarTextColor": ColorPicker("Sidebar Text Color"),
        }
        for name, picker in self.editor_pickers.items():
            editor_layout.addRow(picker)
        editor_group.setLayout(editor_layout)
        scroll_layout.addWidget(editor_group)

        # Qt DOM elements list
        self.elements_list = QListWidget()
        self.elements_list.addItems([
            "QWidget", "QPushButton", "QLabel", "QLineEdit", "QTextEdit",
            "QComboBox", "QCheckBox", "QRadioButton", "QSlider", "QProgressBar",
            "QScrollBar", "QTabWidget", "QTableWidget", "QTreeWidget", "QListWidget",
            "QMenuBar", "QMenu", "QToolBar", "QStatusBar", "QDialog"
        ])
        self.elements_list.currentItemChanged.connect(self.on_element_changed)
        scroll_layout.addWidget(self.elements_list)

        # Stacked widget for element-specific styles
        self.style_stack = QStackedWidget()
        scroll_layout.addWidget(self.style_stack)

        # Create style pages for each element
        self.create_style_pages()

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Save button
        save_button = QPushButton("Save Theme")
        save_button.clicked.connect(self.save_theme)
        layout.addWidget(save_button)

        # Add Load Theme button
        load_button = QPushButton("Load Existing Theme")
        load_button.clicked.connect(self.load_theme)
        layout.addWidget(load_button)

    def create_style_pages(self):
        for i in range(self.elements_list.count()):
            element = self.elements_list.item(i).text()
            page = QWidget()
            page_layout = QFormLayout(page)
            
            # Common style options
            self.add_common_style_options(page_layout, element)
            
            # Element-specific options
            if element == "QPushButton":
                self.add_button_specific_options(page_layout)
            elif element in ["QLineEdit", "QTextEdit"]:
                self.add_input_specific_options(page_layout)
            # Add more element-specific options as needed
            
            self.style_stack.addWidget(page)

    def add_common_style_options(self, layout, element):
        layout.addRow("Background Color", ColorPicker(f"{element} Background"))
        layout.addRow("Text Color", ColorPicker(f"{element} Text"))
        layout.addRow("Font Family", StyleInput("Font Family", QComboBox))
        layout.addRow("Font Size", StyleInput("Font Size", QSpinBox))
        layout.addRow("Border Style", StyleInput("Border Style"))
        layout.addRow("Border Width", StyleInput("Border Width", QSpinBox))
        layout.addRow("Border Color", ColorPicker("Border Color"))
        layout.addRow("Border Radius", StyleInput("Border Radius", QSpinBox))
        layout.addRow("Padding", StyleInput("Padding"))
        layout.addRow("Margin", StyleInput("Margin"))

    def add_button_specific_options(self, layout):
        layout.addRow("Hover Background", ColorPicker("Hover Background"))
        layout.addRow("Hover Text Color", ColorPicker("Hover Text"))
        layout.addRow("Pressed Background", ColorPicker("Pressed Background"))
        layout.addRow("Pressed Text Color", ColorPicker("Pressed Text"))

    def add_input_specific_options(self, layout):
        layout.addRow("Placeholder Text Color", ColorPicker("Placeholder Text"))
        layout.addRow("Focus Border Color", ColorPicker("Focus Border"))

    def on_element_changed(self, current, previous):
        if current:
            self.style_stack.setCurrentIndex(self.elements_list.row(current))

    def save_theme(self):
        theme_name = self.name_input.text()
        if not theme_name:
            # Show an error message
            return

        theme_data = {
            "colors": {name: picker.get_color() for name, picker in self.color_pickers.items()},
            "highlighting": {name: picker.get_color() for name, picker in self.highlight_pickers.items()},
            "sidebar": {name: picker.get_color() for name, picker in self.sidebar_pickers.items()},
            "toolbar": {name: picker.get_color() for name, picker in self.toolbar_pickers.items()},
            "editor": {name: picker.get_color() for name, picker in self.editor_pickers.items()},
        }

        for i in range(self.elements_list.count()):
            element = self.elements_list.item(i).text()
            page = self.style_stack.widget(i)
            element_data = {}
            for j in range(page.layout().rowCount()):
                item = page.layout().itemAt(j, QFormLayout.ItemRole.FieldRole).widget()
                if isinstance(item, ColorPicker):
                    element_data[page.layout().itemAt(j, QFormLayout.ItemRole.LabelRole).widget().text()] = item.get_color()
                elif isinstance(item, StyleInput):
                    element_data[page.layout().itemAt(j, QFormLayout.ItemRole.LabelRole).widget().text()] = item.get_value()
            theme_data[element] = element_data

        # Save the theme using the ThemeManager
        if self.current_theme:
            self.theme_manager.update_custom_theme(self.current_theme, theme_data)
        else:
            self.theme_manager.add_custom_theme(theme_name, theme_data)

        # Optionally, you can show a success message here
        print(f"Theme '{theme_name}' saved successfully.")

    def load_theme(self):
        themes = self.theme_manager.get_all_themes()
        theme_name, ok = QInputDialog.getItem(self, "Load Theme", "Select a theme to edit:", themes, 0, False)
        if ok and theme_name:
            self.current_theme = theme_name
            theme_data = self.theme_manager.get_theme_data(theme_name)
            self.name_input.setText(theme_name)
            self.load_theme_data(theme_data)

    def load_theme_data(self, theme_data):
        # Load general colors
        for name, picker in self.color_pickers.items():
            if name in theme_data.get("colors", {}):
                picker.color_button.setStyleSheet(f"background-color: {theme_data['colors'][name]};")

        # Load highlighting colors
        for name, picker in self.highlight_pickers.items():
            if name in theme_data.get("highlighting", {}):
                picker.color_button.setStyleSheet(f"background-color: {theme_data['highlighting'][name]};")

        # Load sidebar colors
        for name, picker in self.sidebar_pickers.items():
            if name in theme_data.get("sidebar", {}):
                picker.color_button.setStyleSheet(f"background-color: {theme_data['sidebar'][name]};")

        # Load toolbar and context menu colors
        for name, picker in self.toolbar_pickers.items():
            if name in theme_data.get("toolbar", {}):
                picker.color_button.setStyleSheet(f"background-color: {theme_data['toolbar'][name]};")

        # Load editor colors
        for name, picker in self.editor_pickers.items():
            if name in theme_data.get("editor", {}):
                picker.color_button.setStyleSheet(f"background-color: {theme_data['editor'][name]};")

        # Load element-specific styles
        for i in range(self.elements_list.count()):
            element = self.elements_list.item(i).text()
            if element in theme_data:
                page = self.style_stack.widget(i)
                for j in range(page.layout().rowCount()):
                    item = page.layout().itemAt(j, QFormLayout.ItemRole.FieldRole).widget()
                    key = page.layout().itemAt(j, QFormLayout.ItemRole.LabelRole).widget().text()
                    if key in theme_data[element]:
                        if isinstance(item, ColorPicker):
                            item.color_button.setStyleSheet(f"background-color: {theme_data[element][key]};")
                        elif isinstance(item, StyleInput):
                            item.input.setItemText(str(theme_data[element][key]))