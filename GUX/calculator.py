import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QListWidgetItem,
                             QLineEdit, QTabWidget, QLabel, QListWidget, QSlider, QComboBox, QDoubleSpinBox, QCheckBox,
                             QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
import math
from sympy import sympify, SympifyError, Symbol, lambdify, diff, integrate, solve, parsing
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from datetime import datetime
import re
from PyQt6.QtWidgets import QMessageBox

class CalculatorButton(QPushButton):
    def __init__(self, text, color="#4a4a4a", text_color="grey"):
        super().__init__(text)
        self.setFont(QFont('Arial', 12))
        self.setMinimumSize(50, 50)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                border: 1px solid #5a5a5a;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: #5a5a5a;
            }}
            QPushButton:pressed {{
                background-color: #3a3a3a;
            }}
        """)

class GraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        self.ax = self.figure.add_subplot(111)
        self.polar_ax = self.figure.add_subplot(111, projection='polar')
        self.polar_ax.set_visible(False)
        
        # Set the background color
        self.figure.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        self.polar_ax.set_facecolor('#2b2b2b')

    def evaluate_custom_function(self, func_name, x_val, custom_functions, var_values):
        if func_name not in custom_functions:
            raise ValueError(f"Function '{func_name}' is not defined")
        
        func_def = custom_functions[func_name]
        # Replace all occurrences of custom function calls in the definition
        for f_name in custom_functions:
            func_def = re.sub(f'{f_name}\((.*?)\)', lambda m: f'self.evaluate_custom_function("{f_name}", {m.group(1)}, custom_functions, var_values)', func_def)
        
        # Replace variable names with their values
        for var, value in var_values.items():
            func_def = func_def.replace(var, str(value))
        
        # Replace 'x' with the actual x value
        func_def = func_def.replace('x', str(x_val))
        
        return eval(func_def)

    def plot(self, expr_list, var_values, custom_functions, x_range=(-10, 10), polar=False):
        if polar:
            self.ax.set_visible(False)
            self.polar_ax.set_visible(True)
            ax = self.polar_ax
        else:
            self.ax.set_visible(True)
            self.polar_ax.set_visible(False)
            ax = self.ax

        ax.clear()
        
        for expr_str in expr_list:
            try:
                # Replace custom function calls with lambda functions
                for func_name in custom_functions:
                    expr_str = re.sub(f'{func_name}\((.*?)\)', 
                                      lambda m: f'self.evaluate_custom_function("{func_name}", {m.group(1)}, custom_functions, var_values)', 
                                      expr_str)
                
                # Create a lambda function for the expression
                f = lambda x: eval(expr_str)

                if polar:
                    theta = np.linspace(0, 2*np.pi, 1000)
                    r = [f(t) for t in theta]
                    ax.plot(theta, r)
                else:
                    x_vals = np.linspace(x_range[0], x_range[1], 1000)
                    y_vals = [f(x) for x in x_vals]
                    ax.plot(x_vals, y_vals, linewidth=2)

            except Exception as e:
                print(f"Error plotting {expr_str}: {e}")

        if not polar:
            ax.set_xlim(x_range)
            ax.grid(True, color='#555555', linestyle='--', linewidth=0.5)
            ax.axhline(y=0, color='#555555', linestyle='-', linewidth=0.5)
            ax.axvline(x=0, color='#555555', linestyle='-', linewidth=0.5)

        # Set tick colors to light grey
        ax.tick_params(axis='x', colors='#aaaaaa')
        ax.tick_params(axis='y', colors='#aaaaaa')

        # Set axis label colors to light grey
        ax.xaxis.label.set_color('#aaaaaa')
        ax.yaxis.label.set_color('#aaaaaa')

        # Set title color to light grey (if you decide to add a title)
        ax.title.set_color('#aaaaaa')

        # Set spine colors to light grey
        for spine in ax.spines.values():
            spine.set_edgecolor('#555555')

        self.canvas.draw()

class FunctionInput(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.function_input = QLineEdit()
        self.function_input.setPlaceholderText("Enter function (e.g., a*x**2 + b*x + c)")
        layout.addWidget(self.function_input, 3)
        
        self.color_button = QPushButton("Color")
        self.color_button.setMaximumWidth(60)
        layout.addWidget(self.color_button)
        
        self.visible_checkbox = QCheckBox("Visible")
        self.visible_checkbox.setChecked(True)
        layout.addWidget(self.visible_checkbox)
        
        self.delete_button = QPushButton("X")
        self.delete_button.setMaximumWidth(30)
        layout.addWidget(self.delete_button)

class VariableSlider(QWidget):
    def __init__(self, variable, min_val=-10, max_val=10, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        
        self.variable = variable
        self.label = QLabel(f"{variable} =")
        layout.addWidget(self.label)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val * 100, max_val * 100)
        self.slider.setValue(0)
        layout.addWidget(self.slider, 2)
        
        self.value_label = QLabel("0.00")
        layout.addWidget(self.value_label)
        
        self.slider.valueChanged.connect(self.update_value)
        
    def update_value(self):
        value = self.slider.value() / 100
        self.value_label.setText(f"{value:.2f}")

class FunctionDefinitionWidget(QWidget):
    function_defined = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Function name (e.g., f)")
        layout.addWidget(self.name_input)
        
        layout.addWidget(QLabel("(x) ="))
        
        self.definition_input = QLineEdit()
        self.definition_input.setPlaceholderText("Definition (e.g., x**2 + 2*x + 1)")
        layout.addWidget(self.definition_input)
        
        self.add_button = QPushButton("Add Function")
        self.add_button.clicked.connect(self.add_function)
        layout.addWidget(self.add_button)

    def add_function(self):
        name = self.name_input.text().strip()
        definition = self.definition_input.text().strip()
        if name and definition:
            self.function_defined.emit(name, definition)
            self.name_input.clear()
            self.definition_input.clear()

class GraphTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.custom_functions = {}
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Add FunctionDefinitionWidget
        self.function_def_widget = FunctionDefinitionWidget()
        self.function_def_widget.function_defined.connect(self.add_custom_function)
        layout.addWidget(self.function_def_widget)
        
        # Function list
        self.function_list = QListWidget()
        layout.addWidget(self.function_list)
        
        add_function_button = QPushButton("Add Function")
        add_function_button.clicked.connect(self.add_function_input)
        layout.addWidget(add_function_button)
        
        # Graph controls
        controls_layout = QHBoxLayout()
        
        self.x_min = QDoubleSpinBox()
        self.x_min.setRange(-1000, 1000)
        self.x_min.setValue(-10)
        self.x_min.setPrefix("X min: ")
        controls_layout.addWidget(self.x_min)
        
        self.x_max = QDoubleSpinBox()
        self.x_max.setRange(-1000, 1000)
        self.x_max.setValue(10)
        self.x_max.setPrefix("X max: ")
        controls_layout.addWidget(self.x_max)
        
        self.polar_checkbox = QCheckBox("Polar")
        controls_layout.addWidget(self.polar_checkbox)
        
        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self.plot_graph)
        controls_layout.addWidget(self.plot_button)
        
        layout.addLayout(controls_layout)
        
        # Variable sliders
        self.slider_layout = QVBoxLayout()
        layout.addLayout(self.slider_layout)
        
        add_variable_button = QPushButton("Add Variable")
        add_variable_button.clicked.connect(self.add_variable_slider)
        layout.addWidget(add_variable_button)
        
        # Automation controls
        auto_layout = QHBoxLayout()
        
        self.auto_checkbox = QCheckBox("Auto-update")
        auto_layout.addWidget(self.auto_checkbox)
        
        self.update_interval = QDoubleSpinBox()
        self.update_interval.setRange(0.1, 10)
        self.update_interval.setValue(1)
        self.update_interval.setSuffix(" sec")
        auto_layout.addWidget(self.update_interval)
        
        layout.addLayout(auto_layout)
        
        # Graph widget
        self.graph_widget = GraphWidget()
        layout.addWidget(self.graph_widget)
        
        # Setup auto-update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.plot_graph)
        self.auto_checkbox.stateChanged.connect(self.toggle_auto_update)
        
    def add_function_input(self):
        function_input = FunctionInput()
        item = QListWidgetItem(self.function_list)
        item.setSizeHint(function_input.sizeHint())
        self.function_list.addItem(item)
        self.function_list.setItemWidget(item, function_input)
        function_input.delete_button.clicked.connect(lambda: self.remove_function_input(item))
        
    def remove_function_input(self, item):
        row = self.function_list.row(item)
        self.function_list.takeItem(row)
        
    def add_variable_slider(self):
        variable, ok = QInputDialog.getText(self, "Add Variable", "Enter variable name:")
        if ok and variable:
            slider = VariableSlider(variable)
            self.slider_layout.addWidget(slider)
        
    def add_custom_function(self, name, definition):
        self.custom_functions[name] = definition
        print(f"Added custom function: {name}(x) = {definition}")
        
    def plot_graph(self):
        expr_list = []
        var_values = {}
        for i in range(self.function_list.count()):
            item = self.function_list.item(i)
            widget = self.function_list.itemWidget(item)
            if widget.visible_checkbox.isChecked():
                expr_list.append(widget.function_input.text())
        
        for slider in self.findChildren(VariableSlider):
            var_values[slider.variable] = slider.slider.value() / 100
        
        x_min = self.x_min.value()
        x_max = self.x_max.value()
        polar = self.polar_checkbox.isChecked()
        
        try:
            self.graph_widget.plot(expr_list, var_values, self.custom_functions, (x_min, x_max), polar)
        except Exception as e:
            print(f"Error plotting graph: {e}")
            QMessageBox.warning(self, "Plotting Error", f"An error occurred while plotting: {str(e)}")
        
    def toggle_auto_update(self, state):
        if state == Qt.CheckState.Checked:
            interval = int(self.update_interval.value() * 1000)  # Convert to milliseconds
            self.timer.start(interval)
        else:
            self.timer.stop()

class CalculatorWidget(QWidget):
    calculation_performed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")

        # Create tabs
        self.tab_widget = QTabWidget()
        self.standard_tab = QWidget()
        self.scientific_tab = QWidget()
        self.graph_tab = GraphTab()
        self.advanced_tab = QWidget()
        self.tab_widget.addTab(self.standard_tab, "Standard")
        self.tab_widget.addTab(self.scientific_tab, "Scientific")
        self.tab_widget.addTab(self.graph_tab, "Graph")
        self.tab_widget.addTab(self.advanced_tab, "Advanced")
        main_layout.addWidget(self.tab_widget)

        # Create display
        self.display = QLineEdit()
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setReadOnly(True)
        self.display.setFont(QFont('Arial', 24))
        self.display.setStyleSheet("background-color: #3a3a3a; border: 1px solid #5a5a5a; border-radius: 5px; padding: 5px;")
        main_layout.addWidget(self.display)

        # Create Standard Calculator layout
        standard_layout = QGridLayout(self.standard_tab)
        standard_buttons = [
            ('7', None), ('8', None), ('9', None), ('/', '#ff9800'),
            ('4', None), ('5', None), ('6', None), ('*', '#ff9800'),
            ('1', None), ('2', None), ('3', None), ('-', '#ff9800'),
            ('0', None), ('.', None), ('=', '#4caf50'), ('+', '#ff9800')
        ]

        positions = [(i, j) for i in range(4) for j in range(4)]

        for position, (button_text, color) in zip(positions, standard_buttons):
            button = CalculatorButton(button_text, color or "#4a4a4a", "black" if color else "grey")
            button.clicked.connect(self.on_button_click)
            standard_layout.addWidget(button, *position)

        # Create Scientific Calculator layout
        scientific_layout = QGridLayout(self.scientific_tab)
        scientific_buttons = [
            ('sin', '#2196f3'), ('cos', '#2196f3'), ('tan', '#2196f3'), ('log', '#2196f3'),
            ('ln', '#2196f3'), ('e', '#2196f3'), ('π', '#2196f3'), ('^', '#2196f3'),
            ('(', '#ff9800'), (')', '#ff9800'), ('√', '#2196f3'), ('/', '#ff9800'),
            ('7', None), ('8', None), ('9', None), ('*', '#ff9800'),
            ('4', None), ('5', None), ('6', None), ('-', '#ff9800'),
            ('1', None), ('2', None), ('3', None), ('+', '#ff9800'),
            ('0', None), ('.', None), ('=', '#4caf50'), ('C', '#f44336')
        ]

        positions = [(i, j) for i in range(7) for j in range(4)]

        for position, (button_text, color) in zip(positions, scientific_buttons):
            button = CalculatorButton(button_text, color or "#4a4a4a", "black" if color else "white")
            button.clicked.connect(self.on_button_click)
            scientific_layout.addWidget(button, *position)

        # Redesign Advanced tab
        advanced_layout = QVBoxLayout(self.advanced_tab)
        
        # Create sub-tabs for different tool categories
        tools_tabs = QTabWidget()
        advanced_layout.addWidget(tools_tabs)

        # Number Systems tab
        number_systems_tab = QWidget()
        number_systems_layout = QVBoxLayout(number_systems_tab)
        tools_tabs.addTab(number_systems_tab, "Number Systems")

        # Base conversion
        base_layout = QGridLayout()
        self.base_input = QLineEdit()
        self.base_input.setPlaceholderText("Enter number")
        base_layout.addWidget(QLabel("Number:"), 0, 0)
        base_layout.addWidget(self.base_input, 0, 1, 1, 3)
        
        self.base_from = QComboBox()
        self.base_to = QComboBox()
        bases = ["Decimal", "Binary", "Octal", "Hexadecimal"]
        self.base_from.addItems(bases)
        self.base_to.addItems(bases)
        base_layout.addWidget(QLabel("From:"), 1, 0)
        base_layout.addWidget(self.base_from, 1, 1)
        base_layout.addWidget(QLabel("To:"), 1, 2)
        base_layout.addWidget(self.base_to, 1, 3)
        
        self.base_convert = CalculatorButton("Convert", "#2196f3", "black")
        self.base_convert.clicked.connect(self.convert_base)
        base_layout.addWidget(self.base_convert, 2, 0, 1, 4)
        
        number_systems_layout.addLayout(base_layout)
        
        # Bitwise operations
        bitwise_layout = QGridLayout()
        self.bitwise_input1 = QLineEdit()
        self.bitwise_input2 = QLineEdit()
        self.bitwise_operation = QComboBox()
        self.bitwise_operation.addItems(["AND", "OR", "XOR", "NOT", "Left Shift", "Right Shift"])
        bitwise_layout.addWidget(QLabel("Number 1:"), 0, 0)
        bitwise_layout.addWidget(self.bitwise_input1, 0, 1)
        bitwise_layout.addWidget(QLabel("Number 2:"), 1, 0)
        bitwise_layout.addWidget(self.bitwise_input2, 1, 1)
        bitwise_layout.addWidget(QLabel("Operation:"), 2, 0)
        bitwise_layout.addWidget(self.bitwise_operation, 2, 1)
        self.bitwise_calculate = CalculatorButton("Calculate", "#2196f3", "black")
        self.bitwise_calculate.clicked.connect(self.perform_bitwise)
        bitwise_layout.addWidget(self.bitwise_calculate, 3, 0, 1, 2)
        
        number_systems_layout.addLayout(bitwise_layout)

        # Unit Converter tab
        unit_converter_tab = QWidget()
        unit_converter_layout = QVBoxLayout(unit_converter_tab)
        tools_tabs.addTab(unit_converter_tab, "Unit Converter")

        converter_layout = QGridLayout()
        self.convert_input = QLineEdit()
        self.convert_input.setPlaceholderText("Enter value")
        converter_layout.addWidget(QLabel("Value:"), 0, 0)
        converter_layout.addWidget(self.convert_input, 0, 1, 1, 3)
        
        self.convert_units = QComboBox()
        self.convert_units.addItems(["Length", "Mass", "Temperature", "Time", "Speed"])
        self.convert_units.currentIndexChanged.connect(self.update_unit_options)
        converter_layout.addWidget(QLabel("Category:"), 1, 0)
        converter_layout.addWidget(self.convert_units, 1, 1, 1, 3)
        
        self.convert_from = QComboBox()
        self.convert_to = QComboBox()
        converter_layout.addWidget(QLabel("From:"), 2, 0)
        converter_layout.addWidget(self.convert_from, 2, 1)
        converter_layout.addWidget(QLabel("To:"), 2, 2)
        converter_layout.addWidget(self.convert_to, 2, 3)
        
        self.convert_button = CalculatorButton("Convert", "#2196f3", "black")
        self.convert_button.clicked.connect(self.convert_units_func)
        converter_layout.addWidget(self.convert_button, 3, 0, 1, 4)
        
        unit_converter_layout.addLayout(converter_layout)

        # Date and Time tab
        date_time_tab = QWidget()
        date_time_layout = QVBoxLayout(date_time_tab)
        tools_tabs.addTab(date_time_tab, "Date & Time")

        # Date difference calculator
        date_diff_layout = QGridLayout()
        self.date1 = QLineEdit()
        self.date2 = QLineEdit()
        self.date1.setPlaceholderText("YYYY-MM-DD")
        self.date2.setPlaceholderText("YYYY-MM-DD")
        date_diff_layout.addWidget(QLabel("Start Date:"), 0, 0)
        date_diff_layout.addWidget(self.date1, 0, 1)
        date_diff_layout.addWidget(QLabel("End Date:"), 1, 0)
        date_diff_layout.addWidget(self.date2, 1, 1)
        self.calc_date_diff = CalculatorButton("Calculate Difference", "#2196f3", "black")
        self.calc_date_diff.clicked.connect(self.calculate_date_difference)
        date_diff_layout.addWidget(self.calc_date_diff, 2, 0, 1, 2)
        
        date_time_layout.addLayout(date_diff_layout)

        # Financial tab
        financial_tab = QWidget()
        financial_layout = QVBoxLayout(financial_tab)
        tools_tabs.addTab(financial_tab, "Financial")

        # Compound Interest Calculator
        interest_layout = QGridLayout()
        self.principal = QLineEdit()
        self.rate = QLineEdit()
        self.time = QLineEdit()
        self.compound_freq = QComboBox()
        self.compound_freq.addItems(["Annually", "Semi-annually", "Quarterly", "Monthly", "Daily"])
        interest_layout.addWidget(QLabel("Principal:"), 0, 0)
        interest_layout.addWidget(self.principal, 0, 1)
        interest_layout.addWidget(QLabel("Interest Rate (%):"), 1, 0)
        interest_layout.addWidget(self.rate, 1, 1)
        interest_layout.addWidget(QLabel("Time (years):"), 2, 0)
        interest_layout.addWidget(self.time, 2, 1)
        interest_layout.addWidget(QLabel("Compound Frequency:"), 3, 0)
        interest_layout.addWidget(self.compound_freq, 3, 1)
        self.calc_interest = CalculatorButton("Calculate Interest", "#2196f3", "black")
        self.calc_interest.clicked.connect(self.calculate_compound_interest)
        interest_layout.addWidget(self.calc_interest, 4, 0, 1, 2)
        
        financial_layout.addLayout(interest_layout)

        clear_btn = CalculatorButton('C', '#f44336', "black")
        clear_btn.clicked.connect(self.clear_display)
        main_layout.addWidget(clear_btn)

        history_label = QLabel("History:")
        main_layout.addWidget(history_label)
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("background-color: #3a3a3a; border: 1px solid #5a5a5a; border-radius: 5px;")
        self.history_list.itemDoubleClicked.connect(self.use_history_item)
        main_layout.addWidget(self.history_list)

    def on_button_click(self):
        clicked_button = self.sender()
        if clicked_button is None:
            self.calculate_result()
            return

        current_text = self.display.text()

        if clicked_button.text() == '=':
            self.calculate_result()
        elif clicked_button.text() in ('sin', 'cos', 'tan', 'log', 'ln', '√'):
            self.display.setText(current_text + clicked_button.text() + '(')
        elif clicked_button.text() == 'π':
            self.display.setText(current_text + 'pi')
        elif clicked_button.text() == 'e':
            self.display.setText(current_text + 'e')
        elif clicked_button.text() == 'C':
            self.clear_display()
        else:
            new_text = current_text + clicked_button.text()
            self.display.setText(new_text)

    def calculate_result(self):
        current_text = self.display.text()
        try:
            result = self.calculate(current_text)
            precision = self.precision_slider.value()
            formatted_result = f"{result:.{precision}f}"
            self.display.setText(formatted_result)
            self.add_to_history(f"{current_text} = {formatted_result}")
            self.calculation_performed.emit(current_text, formatted_result)
        except Exception as e:
            self.display.setText('Error')

    def clear_display(self):
        self.display.clear()

    def calculate(self, expression):
        return sympify(expression).evalf()

    def add_to_history(self, item):
        self.history_list.insertItem(0, item)

    def use_history_item(self, item):
        self.display.setText(item.text().split(' = ')[0])

    def convert_base(self):
        number = self.base_input.text()
        from_base = self.base_from.currentText()
        to_base = self.base_to.currentText()

        try:
            # Convert to decimal first
            if from_base == "Binary":
                decimal = int(number, 2)
            elif from_base == "Octal":
                decimal = int(number, 8)
            elif from_base == "Hexadecimal":
                decimal = int(number, 16)
            else:
                decimal = int(number)

            # Then convert to the target base
            if to_base == "Binary":
                result = bin(decimal)[2:]
            elif to_base == "Octal":
                result = oct(decimal)[2:]
            elif to_base == "Hexadecimal":
                result = hex(decimal)[2:]
            else:
                result = str(decimal)

            self.display.setText(result)
            self.add_to_history(f"{number} ({from_base}) = {result} ({to_base})")
        except ValueError:
            self.display.setText("Invalid input for the selected base")

    def perform_calculus(self):
        expr = self.calculus_input.text()
        operation = self.calculus_operation.currentText()

        try:
            x = Symbol('x')
            f = sympify(expr)

            if operation == "Derivative":
                result = diff(f, x)
            else:  # Integral
                result = integrate(f, x)

            self.display.setText(str(result))
            self.add_to_history(f"{operation} of {expr} = {result}")
        except Exception as e:
            self.display.setText(f"Error: {str(e)}")

    def update_precision(self, value):
        self.precision_label.setText(str(value))

    def solve_equation(self):
        equation = self.equation_input.text()
        try:
            x = Symbol('x')
            solutions = solve(sympify(equation), x)
            self.display.setText(str(solutions))
            self.add_to_history(f"Solutions of {equation} = {solutions}")
        except Exception as e:
            self.display.setText(f"Error: {str(e)}")

    def update_unit_options(self, index):
        # Implement unit conversion options update based on the selected unit type
        pass

    def convert_units_func(self):
        # Implement unit conversion functionality
        pass

    def perform_bitwise(self):
        try:
            num1 = int(self.bitwise_input1.text())
            num2 = int(self.bitwise_input2.text())
            operation = self.bitwise_operation.currentText()
            
            if operation == "AND":
                result = num1 & num2
            elif operation == "OR":
                result = num1 | num2
            elif operation == "XOR":
                result = num1 ^ num2
            elif operation == "NOT":
                result = ~num1
            elif operation == "Left Shift":
                result = num1 << num2
            elif operation == "Right Shift":
                result = num1 >> num2
            
            self.display.setText(f"Result: {result} (Decimal), {bin(result)} (Binary)")
        except ValueError:
            self.display.setText("Error: Invalid input")

    def calculate_date_difference(self):
        try:
            date1 = datetime.strptime(self.date1.text(), "%Y-%m-%d")
            date2 = datetime.strptime(self.date2.text(), "%Y-%m-%d")
            difference = abs((date2 - date1).days)
            self.display.setText(f"Difference: {difference} days")
        except ValueError:
            self.display.setText("Error: Invalid date format")

    def calculate_compound_interest(self):
        try:
            p = float(self.principal.text())
            r = float(self.rate.text()) / 100
            t = float(self.time.text())
            n = {"Annually": 1, "Semi-annually": 2, "Quarterly": 4, "Monthly": 12, "Daily": 365}[self.compound_freq.currentText()]
            
            amount = p * (1 + r/n)**(n*t)
            interest = amount - p
            
            self.display.setText(f"Final Amount: {amount:.2f}\nTotal Interest: {interest:.2f}")
        except ValueError:
            self.display.setText("Error: Invalid input")

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key in (Qt.Key.Key_0, Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4,
                   Qt.Key.Key_5, Qt.Key.Key_6, Qt.Key.Key_7, Qt.Key.Key_8, Qt.Key.Key_9,
                   Qt.Key.Key_Period, Qt.Key.Key_ParenLeft, Qt.Key.Key_ParenRight):
            self.display.setText(self.display.text() + event.text())
        elif key == Qt.Key.Key_Plus:
            self.display.setText(self.display.text() + '+')
        elif key == Qt.Key.Key_Minus:
            self.display.setText(self.display.text() + '-')
        elif key == Qt.Key.Key_Asterisk:
            self.display.setText(self.display.text() + '*')
        elif key == Qt.Key.Key_Slash:
            self.display.setText(self.display.text() + '/')
        elif key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self.calculate_result()
        elif key == Qt.Key.Key_Backspace:
            self.display.setText(self.display.text()[:-1])
        elif key == Qt.Key.Key_Escape:
            self.clear_display()
        elif key == Qt.Key.Key_C and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        # Handle any cleanup here
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    calc = CalculatorWidget()
    calc.setWindowTitle("Advanced Calculator")
    calc.setGeometry(100, 100, 400, 600)
    calc.show()
    sys.exit(app.exec())