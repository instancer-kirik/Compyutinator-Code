from PyQt6.QtMultimedia import QAudioOutput, QAudioFormat, QMediaPlayer
from PyQt6.QtCore import QUrl, QIODevice, QByteArray
import pyogg

class AudioHandler:
    def __init__(self):
        self.audio_output = None
        self.audio_buffer = None
        self.media_player = QMediaPlayer()

    def play(self, file_path):
        if file_path.endswith('.ogg'):
            vorbis_file = pyogg.VorbisFile(file_path)
            data = vorbis_file.buffer
            channels = vorbis_file.channels
            sample_rate = vorbis_file.frequency
            self.play_buffer(data, channels, sample_rate)
        else:
            self.play_file(file_path)

    def play_buffer(self, data, channels, sample_rate):
        if self.audio_output:
            self.audio_output.stop()

        format = QAudioFormat()
        format.setSampleRate(sample_rate)
        format.setChannelCount(channels)
        format.setSampleSize(16)
        format.setCodec("audio/pcm")
        format.setByteOrder(QAudioFormat.ByteOrder.LittleEndian)
        format.setSampleType(QAudioFormat.SampleType.SignedInt)

        self.audio_output = QAudioOutput(format)
        self.audio_buffer = QBuffer()
        self.audio_buffer.setData(QByteArray(data))
        self.audio_buffer.open(QIODevice.OpenModeFlag.ReadOnly)

        self.audio_output.start(self.audio_buffer)

    def play_file(self, file_path):
        url = QUrl.fromLocalFile(file_path)
        self.media_player.setSource(url)
        self.media_player.play()

    def stop(self):
        if self.audio_output:
            self.audio_output.stop()
            self.audio_buffer.close()
        self.media_player.stop()
