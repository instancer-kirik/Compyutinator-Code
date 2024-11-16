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
    error_occurred = pyqtSignal(str)

    def __init__(self, model_path, device_index=None, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.running = True
        self.paused = False
        self.device_index = device_index
        self.stream = None
        self.audio = None
        
        # Audio settings
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.SILENCE_THRESHOLD = 200
        
        try:
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.RATE)
        except Exception as e:
            self.error_occurred.emit(f"Failed to initialize STT model: {e}")
            raise

    def setup_audio_stream(self):
        """Initialize audio stream with error handling"""
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                input_device_index=self.device_index
            )
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to setup audio stream: {e}")
            return False

    def process_audio_chunk(self, data):
        """Process a single chunk of audio data"""
        data16 = np.frombuffer(data, dtype=np.int16)
        audio_level = np.linalg.norm(data16)
        self.audio_level_update.emit(int(audio_level))

        if audio_level > self.SILENCE_THRESHOLD:
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    self.transcription_update.emit(text, True)
            else:
                partial = json.loads(self.recognizer.PartialResult())
                text = partial.get("partial", "").strip()
                if text:
                    self.transcription_update.emit(text, False)

    def run(self):
        """Main processing loop"""
        if not self.setup_audio_stream():
            return

        try:
            while self.running:
                if not self.paused:
                    data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    self.process_audio_chunk(data)
        except Exception as e:
            self.error_occurred.emit(f"Error during transcription: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

    def stop(self):
        self.running = False
        self.paused = True

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
