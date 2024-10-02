import pyaudio
import json
import time
from vosk import Model, KaldiRecognizer
from PyQt6.QtCore import QObject, pyqtSignal
import numpy as np
import os
import logging
from NITTY_GRITTY.ThreadTrackers import SafeQThread
from HMC.audio_handler import AudioHandler
class InputManager(QObject):
    transcription_update = pyqtSignal(str, bool)
    audio_level_update = pyqtSignal(int)
    typing_speed_update = pyqtSignal(float)
    ##
    def __init__(self, model_path=None, device_index=None, parent=None):
        
        super(InputManager, self).__init__(parent)
        self.model_path = model_path if model_path else 'X:/_Work/Python/Qt/BigLinks/NITTY_GRITTY/vosk-model-small-en-us-0.15'
        self.device_index = device_index
        self.stt_thread = None
        self.last_key_press_time = 0
        self.typing_speed = 0
        logging.info(f"InputManager initialized with model_path: {self.model_path}")
        self.audio_handler = AudioHandler()
        self.config_file = os.path.join(os.path.dirname(__file__), 'audio_device_config.json')
        self.load_device_index()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def start_stt(self):
        if not self.stt_thread:
            self.stt_thread = RealTimeTranscriptionThread(self.model_path, self.device_index)
            self.stt_thread.transcription_update.connect(self.transcription_update)
            self.stt_thread.audio_level_update.connect(self.audio_level_update)
            self.stt_thread.start()

    def stop_stt(self):
        if self.stt_thread:
            self.stt_thread.stop()
            self.stt_thread.wait()
            self.stt_thread = None

    def pause_stt(self):
        if self.stt_thread:
            self.stt_thread.pause()

    def resume_stt(self):
        if self.stt_thread:
            self.stt_thread.resume()

    def update_typing_speed(self, key):
        self.logger.debug(f"Key received in InputManager: {key}")
        current_time = time.time()
        self.logger.debug(f"Current time: {current_time:.6f}")
        
        if self.last_key_press_time:
            time_diff = current_time - self.last_key_press_time
            self.logger.debug(f"Last key press time: {self.last_key_press_time:.6f}")
            self.logger.debug(f"Time difference: {time_diff:.6f}s")
            
            if time_diff > 0:
                instantaneous_speed = 1 / time_diff
                self.logger.debug(f"Instantaneous speed: {instantaneous_speed:.2f} char/s")
                
                # Implement a simple moving average
                alpha = 0.3  # Smoothing factor
                self.typing_speed = alpha * instantaneous_speed + (1 - alpha) * self.typing_speed
            else:
                self.logger.warning("Time difference is zero or negative")
                self.typing_speed = 0
        else:
            self.logger.debug("First key press, initializing typing speed")
            self.typing_speed = 0
        
        self.last_key_press_time = current_time
        self.typing_speed_update.emit(self.typing_speed)
        self.logger.debug(f"Updated typing speed: {self.typing_speed:.2f} char/s")

    def get_typing_speed(self):
        return self.typing_speed

    def play_audio(self, file_path):
        self.audio_handler.play(file_path)

    def stop_audio(self):
        self.audio_handler.stop()

    def set_device_index(self, index):
        self.device_index = index
        if self.stt_thread:
            self.stt_thread.device_index = index
        self.save_device_index()

    def get_audio_devices(self):
        audio = pyaudio.PyAudio()
        devices = []
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:
                devices.append((device_info["name"], device_info["index"]))
        audio.terminate()
        return devices

    def save_device_index(self):
        config = {'device_index': self.device_index}
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def load_device_index(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.device_index = config.get('device_index')

class RealTimeTranscriptionThread(SafeQThread):
    transcription_update = pyqtSignal(str, bool)
    audio_level_update = pyqtSignal(int)

    def __init__(self, model_path, device_index=None):
        super(RealTimeTranscriptionThread, self).__init__()
        self.model_path = model_path
        self.running = True
        self.paused = False
        self.device_index = device_index
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.silence_threshold = 200

    def run(self):
        audio_format = pyaudio.paInt16
        channels = 1
        rate = 16000
        chunk = 1024

        audio = pyaudio.PyAudio()
        stream = audio.open(format=audio_format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk, input_device_index=self.device_index)

        while self.running:
            if not self.paused:
                data = stream.read(chunk, exception_on_overflow=False)
                data16 = np.frombuffer(data, dtype=np.int16)
                audio_level = np.linalg.norm(data16)
                self.audio_level_update.emit(int(audio_level))

                if audio_level > self.silence_threshold:
                    if self.recognizer.AcceptWaveform(data):
                        result = self.recognizer.Result()
                        text = json.loads(result)["text"]
                        if text:
                            self.transcription_update.emit(text.strip(), True)
                    else:
                        partial = self.recognizer.PartialResult()
                        partial_text = json.loads(partial)["partial"]
                        if partial_text:
                            self.transcription_update.emit(partial_text.strip(), False)

        stream.stop_stream()
        stream.close()
        audio.terminate()

    def stop(self):
        self.running = False
        self.paused = True

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
   
  
    
   
         