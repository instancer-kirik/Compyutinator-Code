from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtMultimedia import QAudioOutput, QAudioFormat, QMediaPlayer
from PyQt6.QtCore import Qt, QTimer
from HMC.audio_handler import AudioHandler

class MediaPlayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Media Player")
        self.setGeometry(300, 100, 400, 200)

        self.audio_handler = AudioHandler()

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_pause)
        self.layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop)
        self.layout.addWidget(self.stop_button)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.layout.addWidget(self.position_slider)

        self.position_label = QLabel("00:00")
        self.layout.addWidget(self.position_label)

        self.audio_handler.media_player.positionChanged.connect(self.update_position)
        self.audio_handler.media_player.durationChanged.connect(self.update_duration)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_position_label)
        self.timer.start()

    def play(self, file_path):
        self.audio_handler.play(file_path)

    def play_pause(self):
        if self.audio_handler.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.audio_handler.media_player.pause()
        else:
            self.audio_handler.media_player.play()

    def stop(self):
        self.audio_handler.stop()

    def set_position(self, position):
        self.audio_handler.media_player.setPosition(position)

    def update_position(self, position):
        self.position_slider.setValue(position)

    def update_duration(self, duration):
        self.position_slider.setRange(0, duration)

    def update_position_label(self):
        position = self.audio_handler.media_player.position() // 1000
        minutes = position // 60
        seconds = position % 60
        self.position_label.setText(f"{minutes:02}:{seconds:02}")
