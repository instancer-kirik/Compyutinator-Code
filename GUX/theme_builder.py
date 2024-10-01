
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QColorDialog, QSlider,
                             QScrollArea, QSpinBox, QComboBox, QFormLayout, QGroupBox,
                             QListWidget, QStackedWidget)
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
        self.theme_manager.add_custom_theme(theme_name, theme_data)

        # Optionally, you can show a success message here
        print(f"Theme '{theme_name}' saved successfully.")