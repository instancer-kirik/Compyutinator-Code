import logging
import pyautogui
from PyQt6.QtWidgets import QWidget, QTextEdit, QPushButton, QVBoxLayout, QLabel, QComboBox
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QTimer, Qt
from PyQt6.QtGui import QTextCursor
import keyboard  # For global hotkeys
from HMC.audio_handler import AudioHandler
from HMC.input_manager import InputManager, RealTimeTranscriptionThread
from GUX.widget_vault import AudioLevelWidget
from PyQt6.QtWidgets import QApplication

class VoiceTypingWidget(QWidget):
    transcription_updated = pyqtSignal(str, bool)

    def __init__(self, input_manager: InputManager, parent=None):
        super().__init__(parent)
        self.input_manager = input_manager
        self.setup_ui()
        self.setup_connections()
        self.audio_handler = AudioHandler()
        self.setup_hotkeys()
        self.partial_text = ""
        self.typing_flag = False
        self.transcribing = False
        self.spinner_active = False

    def setup_ui(self):
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.transcribe_button = QPushButton("Start Transcription", self)
        self.clear_button = QPushButton("Clear Text", self)
        self.audio_level = AudioLevelWidget(self)
        self.audio_level.setFixedHeight(50)
        self.spinner_label = QLabel(self)
        self.device_selector = QComboBox(self)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.device_selector)
        layout.addWidget(self.audio_level)
        layout.addWidget(self.spinner_label)
        layout.addWidget(self.transcribe_button)
        layout.addWidget(self.clear_button)

        self.setLayout(layout)

        self.list_audio_devices()

    def setup_connections(self):
        self.transcribe_button.clicked.connect(self.toggle_transcription)
        self.clear_button.clicked.connect(self.clear_text)
        self.device_selector.currentIndexChanged.connect(self.on_device_selected)
        self.input_manager.transcription_update.connect(self.update_transcription)
        self.input_manager.audio_level_update.connect(self.update_audio_level)
        #self.input_manager.typing_speed_update.connect(self.update_typing_speed)
        #this might be for typing effects
    def setup_hotkeys(self):
        keyboard.add_hotkey('ctrl+shift+p', self.play_audio)
        keyboard.add_hotkey('ctrl+shift+s', self.stop_audio)
        keyboard.add_hotkey('ctrl+shift+t', self.toggle_transcription)

    def list_audio_devices(self):
        devices = self.input_manager.get_audio_devices()
        for name, index in devices:
            self.device_selector.addItem(name, index)
        
        # Set the current index to the saved device index
        saved_index = self.input_manager.device_index
        if saved_index is not None:
            index = self.device_selector.findData(saved_index)
            if index >= 0:
                self.device_selector.setCurrentIndex(index)

    def on_device_selected(self, index):
        device_index = self.device_selector.currentData()
        self.input_manager.set_device_index(device_index)

    def play_audio(self):
        try:
            file_path = 'path/to/your/audio/file.ogg'  # Change this to your audio file path
            self.audio_handler.play(file_path)
        except Exception as e:
            logging.error("Error playing audio: %s", str(e))

    def stop_audio(self):
        try:
            self.audio_handler.stop()
        except Exception as e:
            logging.error("Error stopping audio: %s", str(e))

    @pyqtSlot()
    def toggle_transcription(self):
        try:
            if self.transcribing:
                self.stop_transcription()
            else:
                self.start_transcription()
        except Exception as e:
            logging.error("Error toggling transcription: %s", str(e))

    def start_transcription(self):
        try:
            self.transcribe_button.setText("Stop Transcription")
            self.transcribing = True
            self.input_manager.start_stt()
            self.start_spinner()
        except Exception as e:
            logging.error("Error starting transcription: %s", str(e))

    def stop_transcription(self):
        try:
            self.transcribe_button.setText("Start Transcription")
            self.transcribing = False
            self.input_manager.stop_stt()
            self.stop_spinner()
        except Exception as e:
            logging.error("Error stopping transcription: %s", str(e))

    def clear_text(self):
        try:
            self.text_edit.clear()
        except Exception as e:
            logging.error("Error clearing text: %s", str(e))

    @pyqtSlot(int)
    def update_audio_level(self, level):
        try:
            normalized_level = min(100, max(0, int(level / 100)))
            self.audio_level.setLevel(normalized_level)
        except Exception as e:
            logging.error("Error updating audio level: %s", str(e))

    @pyqtSlot(str, bool)
    def update_transcription(self, text, is_final):
        try:
            # Update the in-app text box for reference
            cursor = self.text_edit.textCursor()

            if is_final:
                # For final text, replace the previous partial text with the new final text
                if self.partial_text:
                    # Remove the previous partial text from the GUI and screen
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(self.partial_text))
                    cursor.removeSelectedText()

                    self.typing_flag = True
                    pyautogui.press('backspace', presses=len(self.partial_text))
                    self.typing_flag = False

                # Insert the new final text
                cursor.insertText(text + " ")
                self.text_edit.setTextCursor(cursor)
                self.text_edit.ensureCursorVisible()

                # Type the final text using pyautogui
                self.typing_flag = True
                pyautogui.write(text + " ")
                self.typing_flag = False

                self.partial_text = ""
            else:
                # Append the new partial text
                cursor.insertText(text[len(self.partial_text):])
                self.text_edit.setTextCursor(cursor)
                self.text_edit.ensureCursorVisible()

                # Type the partial text using pyautogui
                self.typing_flag = True
                pyautogui.write(text[len(self.partial_text):])
                self.typing_flag = False

                self.partial_text = text

            # Force the GUI to update
            QApplication.processEvents()
        except Exception as e:
            logging.error("Error updating transcription: %s", str(e))

    def keyPressEvent(self, event):
        try:
            if not self.typing_flag:
                super().keyPressEvent(event)
        except Exception as e:
            logging.error("Error in keyPressEvent: %s", str(e))

    def start_spinner(self):
        try:
            self.spinner_active = True
            self.spinner_sequence = ["|", "/", "-", "\\"]
            self.spinner_index = 0
            self.update_spinner()
        except Exception as e:
            logging.error("Error starting spinner: %s", str(e))

    def stop_spinner(self):
        try:
            self.spinner_active = False
            self.spinner_label.setText("")
        except Exception as e:
            logging.error("Error stopping spinner: %s", str(e))

    def update_spinner(self):
        try:
            if self.spinner_active:
                self.spinner_label.setText(self.spinner_sequence[self.spinner_index])
                self.spinner_index = (self.spinner_index + 1) % len(self.spinner_sequence)
                QTimer.singleShot(100, self.update_spinner)  # Update spinner every 100ms
        except Exception as e:
            logging.error("Error updating spinner: %s", str(e))
