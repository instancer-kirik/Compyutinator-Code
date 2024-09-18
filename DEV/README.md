# Llama IDE Assistant

Llama IDE Assistant is a Python package that provides an AI-powered chat interface for programming assistance. It uses a Llama-based language model to offer intelligent responses to coding questions and software development inquiries.

## Features

- AI-powered chat interface for programming assistance
- Uses the Llama-3.1-SuperNova-Lite model for generating responses
- Automatic model download and management
- PyQt6-based GUI for easy integration into desktop applications
- Threaded model execution to prevent UI freezing

## Installation

You can install the Llama IDE Assistant package using pip:

## Usage

Here's a basic example of how to use the Llama IDE Assistant in a PyQt6 application:
python
from PyQt6.QtWidgets import QApplication, QMainWindow
from llama_ide_assistant import AIChatWidget
class MainWindow(QMainWindow):
def init(self):
super().init()
self.setWindowTitle("Llama IDE Assistant")
self.setCentralWidget(AIChatWidget())
if name == "main":
app = QApplication([])
window = MainWindow()
window.show()
app.exec()