from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QColorDialog, QSlider,
                             QScrollArea, QSpinBox, QComboBox, QFormLayout, QGroupBox)
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
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Theme name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Theme Name:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        main_layout.addLayout(name_layout)

        # Scroll area for all options
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QHBoxLayout()
        scroll_widget.setLayout(scroll_layout)

        # Colors section
        colors_group = QGroupBox("Colors")
        colors_layout = QFormLayout()
        self.color_pickers = {
            "primaryColor": ColorPicker("Primary Color"),
            "secondaryColor": ColorPicker("Secondary Color"),
            "backgroundColor": ColorPicker("Background Color"),
            "textColor": ColorPicker("Text Color"),
            "linkColor": ColorPicker("Link Color"),
            "scrollbarColor": ColorPicker("Scrollbar Color"),
            "buttonColor": ColorPicker("Button Color"),
            "buttonTextColor": ColorPicker("Button Text Color"),
            "highlightColor": ColorPicker("Highlight Color"),
        }
        for name, picker in self.color_pickers.items():
            colors_layout.addRow(picker)
        colors_group.setLayout(colors_layout)
        scroll_layout.addWidget(colors_group)

        # Dimensions and Fonts section
        dims_fonts_group = QGroupBox("Dimensions & Fonts")
        dims_fonts_layout = QFormLayout()
        self.dimension_inputs = {
            "borderRadius": StyleInput("Border Radius", QSpinBox),
            "buttonHeight": StyleInput("Button Height", QSpinBox),
            "scrollbarWidth": StyleInput("Scrollbar Width", QSpinBox),
            "padding": StyleInput("Padding"),
            "margin": StyleInput("Margin"),
        }
        for name, input_widget in self.dimension_inputs.items():
            if isinstance(input_widget.input, QSpinBox):
                input_widget.input.setRange(0, 100)
            dims_fonts_layout.addRow(input_widget)
        
        self.font_family = QComboBox()
        self.font_family.addItems(["Arial", "Helvetica", "Times New Roman", "Courier", "Verdana"])
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_weight = QComboBox()
        self.font_weight.addItems(["Normal", "Bold", "Light"])
        dims_fonts_layout.addRow("Font Family", self.font_family)
        dims_fonts_layout.addRow("Font Size", self.font_size)
        dims_fonts_layout.addRow("Font Weight", self.font_weight)
        dims_fonts_group.setLayout(dims_fonts_layout)
        scroll_layout.addWidget(dims_fonts_group)

        # Styles and Effects section
        styles_effects_group = QGroupBox("Styles & Effects")
        styles_effects_layout = QFormLayout()
        self.style_inputs = {
            "borderStyle": StyleInput("Border Style"),
            "borderWidth": StyleInput("Border Width"),
            "borderColor": ColorPicker("Border Color"),
            "buttonStyle": StyleInput("Button Style"),
            "inputStyle": StyleInput("Input Style"),
            "linkStyle": StyleInput("Link Style"),
            "hoverEffects": StyleInput("Hover Effects"),
            "activeEffects": StyleInput("Active Effects"),
            "transitionEffects": StyleInput("Transition Effects"),
        }
        for name, input_widget in self.style_inputs.items():
            styles_effects_layout.addRow(input_widget)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.box_shadow = StyleInput("Box Shadow")
        self.text_shadow = StyleInput("Text Shadow")
        styles_effects_layout.addRow("Opacity", self.opacity_slider)
        styles_effects_layout.addRow(self.box_shadow)
        styles_effects_layout.addRow(self.text_shadow)
        styles_effects_group.setLayout(styles_effects_layout)
        scroll_layout.addWidget(styles_effects_group)

        # Layout section
        layout_group = QGroupBox("Layout")
        layout_form = QFormLayout()
        self.layout_inputs = {
            "flexDirection": StyleInput("Flex Direction", QComboBox),
            "justifyContent": StyleInput("Justify Content", QComboBox),
            "alignItems": StyleInput("Align Items", QComboBox),
            "flexWrap": StyleInput("Flex Wrap", QComboBox),
            "gridColumns": StyleInput("Grid Columns"),
            "gridRows": StyleInput("Grid Rows"),
            "gridGap": StyleInput("Grid Gap"),
        }
        for name, input_widget in self.layout_inputs.items():
            if isinstance(input_widget.input, QComboBox):
                if name == "flexDirection":
                    input_widget.input.addItems(["row", "column", "row-reverse", "column-reverse"])
                elif name in ["justifyContent", "alignItems"]:
                    input_widget.input.addItems(["flex-start", "flex-end", "center", "space-between", "space-around"])
                elif name == "flexWrap":
                    input_widget.input.addItems(["nowrap", "wrap", "wrap-reverse"])
            layout_form.addRow(input_widget)
        layout_group.setLayout(layout_form)
        scroll_layout.addWidget(layout_group)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Save button
        save_button = QPushButton("Save Theme")
        save_button.clicked.connect(self.save_theme)
        main_layout.addWidget(save_button)

    def save_theme(self):
        theme_name = self.name_input.text()
        if not theme_name:
            # Show an error message
            return

        theme_data = {
            "colors": {name: picker.get_color() for name, picker in self.color_pickers.items()},
            "dimensions": {name: input_widget.get_value() for name, input_widget in self.dimension_inputs.items()},
            "fonts": {
                "family": self.font_family.currentText(),
                "size": self.font_size.value(),
                "weight": self.font_weight.currentText()
            },
            "effects": {
                "opacity": self.opacity_slider.value() / 100,
                "boxShadow": self.box_shadow.get_value(),
                "textShadow": self.text_shadow.get_value()
            },
            "styles": {name: input_widget.get_value() for name, input_widget in self.style_inputs.items()},
            "layout": {name: input_widget.get_value() for name, input_widget in self.layout_inputs.items()}
        }

        # Save the theme
        theme_path = os.path.join(self.theme_manager.theme_directory, 'custom', f"{theme_name}.json")
        os.makedirs(os.path.dirname(theme_path), exist_ok=True)
        with open(theme_path, 'w') as f:
            json.dump(theme_data, f, indent=2)

        # Refresh the theme manager
        self.theme_manager.load_themes()