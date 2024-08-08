import sys
import pyaudio
import json
import numpy as np
import pyautogui
from vosk import Model, KaldiRecognizer
from PyQt6.QtWidgets import QApplication, QWidget, QTextEdit, QPushButton, QVBoxLayout, QProgressBar, QLabel, QComboBox
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QTimer, Qt
from PyQt6.QtGui import QTextCursor, QPainter
import keyboard  # For global hotkeys
from HMC.audio_handler import AudioHandler

class RealTimeTranscriptionThread(QThread):
    transcription_update = pyqtSignal(str, bool)
    audio_level_update = pyqtSignal(int)

    def __init__(self, model_path, device_index=None, parent=None):
        super(RealTimeTranscriptionThread, self).__init__(parent)
        self.model_path = model_path
        self.running = True
        self.paused = False
        self.device_index = device_index
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.silence_threshold = 200  # Adjust this threshold based on your environment

    def run(self):
        audio_format = pyaudio.paInt16
        channels = 1
        rate = 16000
        chunk = 1024

        audio = pyaudio.PyAudio()
        self.stream = audio.open(format=audio_format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk, input_device_index=self.device_index)

        while self.running:
            if not self.paused:
                data = self.stream.read(chunk, exception_on_overflow=False)
                data16 = np.frombuffer(data, dtype=np.int16)
                audio_level = np.linalg.norm(data16)
                self.audio_level_update.emit(int(audio_level))

                if audio_level > self.silence_threshold:
                    if self.recognizer.AcceptWaveform(data):
                        result = self.recognizer.Result()
                        text = json.loads(result)["text"]
                        if text:
                            self.emit_transcription_update(text, is_final=True)
                    else:
                        partial = self.recognizer.PartialResult()
                        partial_text = json.loads(partial)["partial"]
                        if partial_text:
                            self.emit_transcription_update(partial_text, is_final=False)

        self.stream.stop_stream()
        self.stream.close()
        audio.terminate()

    def emit_transcription_update(self, text, is_final):
        self.transcription_update.emit(text.strip(), is_final)

    def stop(self):
        self.running = False
        self.paused = True

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

class AudioLevelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0

    def setLevel(self, level):
        self.level = level
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # Draw the background
        painter.setBrush(Qt.GlobalColor.black)
        painter.drawRect(rect)

        # Draw the level bar
        if self.level > 0:
            bar_height = rect.height() * (self.level / 100)
            painter.setBrush(Qt.GlobalColor.green)
            painter.drawRect(0, rect.height() - int(bar_height), rect.width(), int(bar_height))

class VoiceTypingWidget(QWidget):
    transcription_updated = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.transcribe_button = QPushButton("Start Transcription", self)
        self.transcribe_button.clicked.connect(self.toggle_transcription)
        self.clear_button = QPushButton("Clear Text", self)
        self.clear_button.clicked.connect(self.clear_text)
        self.audio_level = AudioLevelWidget(self)
        self.audio_level.setFixedHeight(50)
        self.spinner_label = QLabel(self)
        self.spinner_label.setText("")
        self.device_selector = QComboBox(self)
        self.device_selector.currentIndexChanged.connect(self.on_device_selected)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.device_selector)
        layout.addWidget(self.audio_level)
        layout.addWidget(self.spinner_label)
        layout.addWidget(self.transcribe_button)
        layout.addWidget(self.clear_button)

        self.setLayout(layout)

        self.audio_handler = AudioHandler()
        self.setup_hotkeys()
        self.list_audio_devices()
        self.partial_text = ""
        self.typing_flag = False
        self.transcribing = False
        self.thread = None
        self.spinner_active = False
        self.selected_device_index = None

    def list_audio_devices(self):
        audio = pyaudio.PyAudio()
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:
                self.device_selector.addItem(device_info["name"], device_info["index"])
        audio.terminate()

    def on_device_selected(self, index):
        self.selected_device_index = self.device_selector.currentData()

    def setup_hotkeys(self):
        keyboard.add_hotkey('ctrl+shift+p', self.play_audio)
        keyboard.add_hotkey('ctrl+shift+s', self.stop_audio)
        keyboard.add_hotkey('ctrl+shift+t', self.toggle_transcription)

    def play_audio(self):
        file_path = 'path/to/your/audio/file.ogg'  # Change this to your audio file path
        self.audio_handler.play(file_path)

    def stop_audio(self):
        self.audio_handler.stop()

    @pyqtSlot()
    def toggle_transcription(self):
        if self.transcribing:
            self.stop_transcription()
        else:
            self.start_transcription()

    def start_transcription(self):
        self.transcribe_button.setText("Stop Transcription")
        self.transcribing = True
        model_path = 'X:/_Work/Python/kivy/BigLinks/NITTY_GRITTY/vosk-model-small-en-us-0.15'
        
        if not self.thread:
            self.thread = RealTimeTranscriptionThread(model_path, device_index=self.selected_device_index)
            self.thread.transcription_update.connect(self.update_transcription)
            self.thread.audio_level_update.connect(self.update_audio_level)
            self.thread.start()
        else:
            self.thread.device_index = self.selected_device_index
            self.thread.resume()

        self.start_spinner()

    def stop_transcription(self):
        self.transcribe_button.setText("Start Transcription")
        self.transcribing = False
        if self.thread:
            self.thread.pause()
        self.stop_spinner()

    def clear_text(self):
        self.text_edit.clear()

    @pyqtSlot(int)
    def update_audio_level(self, level):
        normalized_level = min(100, max(0, int(level / 100)))
        self.audio_level.setLevel(normalized_level)

    @pyqtSlot(str, bool)
    def update_transcription(self, text, is_final):
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

    def keyPressEvent(self, event):
        if not self.typing_flag:
            super().keyPressEvent(event)

    def start_spinner(self):
        self.spinner_active = True
        self.spinner_sequence = ["|", "/", "-", "\\"]
        self.spinner_index = 0
        self.update_spinner()

    def stop_spinner(self):
        self.spinner_active = False
        self.spinner_label.setText("")

    def update_spinner(self):
        if self.spinner_active:
            self.spinner_label.setText(self.spinner_sequence[self.spinner_index])
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_sequence)
            QTimer.singleShot(100, self.update_spinner)  # Update spinner every 100ms
