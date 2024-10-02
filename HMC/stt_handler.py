import pyaudio
import json
from vosk import Model, KaldiRecognizer
from PyQt6.QtCore import pyqtSignal
import numpy as np
from NITTY_GRITTY.ThreadTrackers import SafeQThread
#I want it to generate subtitles from audio out
#would be cool to do with midi too, but then I might have to implement a lot of other things too
#I am building my own workspace, what if it does DAW stuff too
class RealTimeTranscriptionThread(SafeQThread):
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
                self.audio_level_update.emit(audio_level)

                if audio_level > self.silence_threshold:
                    if self.recognizer.AcceptWaveform(data):
                        result = self.recognizer.Result()
                        text = json.loads(result)["text"]
                        if text:
                            self.transcription_update.emit(text.strip(), True)
                    else:
                        partial = self.recognizer.PartialResult()
                        partial_text = json.loads(partial)["partial"]
                        self.transcription_update.emit(partial_text.strip(), False)

        self.stream.stop_stream()
        self.stream.close()
        audio.terminate()

    def stop(self):
        self.running = False
        self.paused = True

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
