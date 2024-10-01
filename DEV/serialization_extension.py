import json
import yaml
from PyQt6.QtWidgets import QAction, QMessageBox
from PyQt6.QtCore import Qt
#wanted to add this to the code editor, and prettier json and yaml
class SerializationExtension:
    def __init__(self, editor):
        self.editor = editor
        self.supported_formats = {
            'json': {'load': json.loads, 'dump': json.dumps, 'extension': '.json'},
            'yaml': {'load': yaml.safe_load, 'dump': yaml.safe_dump, 'extension': '.yaml'}
        }
        self.current_format = None

    def setup_extension(self):
        self.editor.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.text_edit.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        context_menu = self.editor.text_edit.createStandardContextMenu()
        context_menu.addSeparator()

        if self.current_format:
            format_action = QAction(f"Format {self.current_format.upper()}", self.editor)
            format_action.triggered.connect(self.format_current)
            context_menu.addAction(format_action)

            convert_menu = context_menu.addMenu("Convert to")
            for format_name in self.supported_formats.keys():
                if format_name != self.current_format:
                    action = QAction(format_name.upper(), self.editor)
                    action.triggered.connect(lambda checked, f=format_name: self.convert_to(f))
                    convert_menu.addAction(action)

        context_menu.exec(self.editor.text_edit.mapToGlobal(position))

    def format_current(self):
        if not self.current_format:
            return

        try:
            # Parse the current text
            parsed = self.supported_formats[self.current_format]['load'](self.editor.text_edit.text())
            # Format the text
            formatted = self.supported_formats[self.current_format]['dump'](parsed, indent=4)
            # Set the formatted text back to the editor
            self.editor.text_edit.setText(formatted)
        except Exception as e:
            QMessageBox.warning(self.editor, f"{self.current_format.upper()} Error", f"Invalid {self.current_format.upper()}: {str(e)}")

    def convert_to(self, new_format):
        if self.current_format == new_format:
            return

        try:
            # Parse the current text
            parsed = self.supported_formats[self.current_format]['load'](self.editor.text_edit.text())
            # Convert to the new format
            converted = self.supported_formats[new_format]['dump'](parsed, indent=4)
            # Set the converted text back to the editor
            self.editor.text_edit.setText(converted)
            # Update the current format
            self.current_format = new_format
            # Update the file extension
            self.update_file_extension(new_format)
        except Exception as e:
            QMessageBox.warning(self.editor, "Conversion Error", f"Failed to convert: {str(e)}")

    def update_file_extension(self, new_format):
        if self.editor.file_path:
            new_extension = self.supported_formats[new_format]['extension']
            new_file_path = os.path.splitext(self.editor.file_path)[0] + new_extension
            self.editor.set_file_path(new_file_path)
            # You might want to trigger a file rename in your file system here

    def set_format_from_file_path(self, file_path):
        extension = os.path.splitext(file_path)[1].lower()
        for format_name, format_info in self.supported_formats.items():
            if extension == format_info['extension']:
                self.current_format = format_name
                return
        self.current_format = None