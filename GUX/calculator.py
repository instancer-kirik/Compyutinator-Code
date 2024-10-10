from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit,
                             QListWidget, QHBoxLayout, QTabWidget, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import math
from sympy import sympify, SympifyError

class CalculatorButton(QPushButton):
    def __init__(self, text, color=None):
        super().__init__(text)
        self.setFont(QFont('Arial', 12))
        self.setMinimumSize(50, 50)
        if color:
            self.setStyleSheet(f"background-color: {color}; color: white; border-radius: 25px;")
        else:
            self.setStyleSheet("background-color: #E0E0E0; border-radius: 25px;")

class CalculatorWidget(QWidget):
    calculation_performed = pyqtSignal(str, str)  # Signal to emit calculation history

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Create tabs for Standard and Scientific calculators
        self.tab_widget = QTabWidget()
        self.standard_tab = QWidget()
        self.scientific_tab = QWidget()
        self.tab_widget.addTab(self.standard_tab, "Standard")
        self.tab_widget.addTab(self.scientific_tab, "Scientific")
        main_layout.addWidget(self.tab_widget)

        # Create display
        self.display = QLineEdit()
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setReadOnly(True)
        self.display.setFont(QFont('Arial', 24))
        self.display.setStyleSheet("background-color: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 5px;")
        main_layout.addWidget(self.display)

        # Create Standard Calculator layout
        standard_layout = QGridLayout(self.standard_tab)
        standard_buttons = [
            ('7', None), ('8', None), ('9', None), ('/', '#FF9800'),
            ('4', None), ('5', None), ('6', None), ('*', '#FF9800'),
            ('1', None), ('2', None), ('3', None), ('-', '#FF9800'),
            ('0', None), ('.', None), ('=', '#4CAF50'), ('+', '#FF9800')
        ]

        positions = [(i, j) for i in range(4) for j in range(4)]

        for position, (button_text, color) in zip(positions, standard_buttons):
            button = CalculatorButton(button_text, color)
            button.clicked.connect(self.on_button_click)
            standard_layout.addWidget(button, *position)

        # Create Scientific Calculator layout
        scientific_layout = QGridLayout(self.scientific_tab)
        scientific_buttons = [
            ('sin', '#2196F3'), ('cos', '#2196F3'), ('tan', '#2196F3'), ('log', '#2196F3'),
            ('ln', '#2196F3'), ('e', '#2196F3'), ('π', '#2196F3'), ('^', '#2196F3'),
            ('(', '#FF9800'), (')', '#FF9800'), ('√', '#2196F3'), ('/', '#FF9800'),
            ('7', None), ('8', None), ('9', None), ('*', '#FF9800'),
            ('4', None), ('5', None), ('6', None), ('-', '#FF9800'),
            ('1', None), ('2', None), ('3', None), ('+', '#FF9800'),
            ('0', None), ('.', None), ('=', '#4CAF50'), ('C', '#F44336')
        ]

        positions = [(i, j) for i in range(7) for j in range(4)]

        for position, (button_text, color) in zip(positions, scientific_buttons):
            button = CalculatorButton(button_text, color)
            button.clicked.connect(self.on_button_click)
            scientific_layout.addWidget(button, *position)

        # Add clear button
        clear_btn = CalculatorButton('C', '#F44336')
        clear_btn.clicked.connect(self.clear_display)
        main_layout.addWidget(clear_btn)

        # Add history list
        history_label = QLabel("History:")
        main_layout.addWidget(history_label)
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.use_history_item)
        main_layout.addWidget(self.history_list)

    def on_button_click(self):
        clicked_button = self.sender()
        current_text = self.display.text()

        if clicked_button.text() == '=':
            try:
                result = self.calculate(current_text)
                self.display.setText(str(result))
                self.add_to_history(f"{current_text} = {result}")
                self.calculation_performed.emit(current_text, str(result))
            except SympifyError:
                self.display.setText('Error')
        elif clicked_button.text() in ('sin', 'cos', 'tan', 'log', 'ln', '√'):
            self.display.setText(current_text + clicked_button.text() + '(')
        elif clicked_button.text() == 'π':
            self.display.setText(current_text + 'pi')
        elif clicked_button.text() == 'e':
            self.display.setText(current_text + 'e')
        else:
            new_text = current_text + clicked_button.text()
            self.display.setText(new_text)

    def clear_display(self):
        self.display.clear()

    def calculate(self, expression):
        return sympify(expression).evalf()

    def add_to_history(self, item):
        self.history_list.insertItem(0, item)

    def use_history_item(self, item):
        self.display.setText(item.text().split(' = ')[0])

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_0, Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4,
                   Qt.Key.Key_5, Qt.Key.Key_6, Qt.Key.Key_7, Qt.Key.Key_8, Qt.Key.Key_9,
                   Qt.Key.Key_Plus, Qt.Key.Key_Minus, Qt.Key.Key_Asterisk, Qt.Key.Key_Slash,
                   Qt.Key.Key_Period, Qt.Key.Key_ParenLeft, Qt.Key.Key_ParenRight):
            self.display.setText(self.display.text() + event.text())
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.on_button_click()
        elif key == Qt.Key.Key_Backspace:
            self.display.setText(self.display.text()[:-1])
        elif key == Qt.Key.Key_Escape:
            self.clear_display()
        else:
            super().keyPressEvent(event)

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    calc = CalculatorWidget()
    calc.setWindowTitle("Advanced Calculator")
    calc.setGeometry(100, 100, 400, 600)
    calc.show()
    sys.exit(app.exec())