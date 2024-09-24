from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtGui import QMovie, QPixmap
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QObject, QTimer
import logging
class MovieUpdater(QObject):
    frameChanged = pyqtSignal(QPixmap)

    def __init__(self, movie):
        super().__init__()
        self.movie = movie
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

    def start(self):
        self.movie.start()
        self.timer.start(33)  # Update approximately 30 times per second

    def stop(self):
        self.movie.stop()
        self.timer.stop()

    def update_frame(self):
        current_pixmap = self.movie.currentPixmap()
        self.frameChanged.emit(current_pixmap)
        self.movie.jumpToNextFrame()

class TransparentSplashScreen(QSplashScreen):
    def __init__(self, gif_path):
        logging.info(f"Initializing splash screen with GIF: {gif_path}")
        super().__init__(QPixmap(1, 1))  # Create with a dummy pixmap
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.movie = QMovie(gif_path)
        self.movie.setScaledSize(QSize(400, 400))  # Adjust size as needed
        self.movie.frameChanged.connect(self.update_frame)
        QTimer.singleShot(0, self.movie.start)  # Start the movie in the next event loop iteration
        logging.info("Splash screen initialized")

    def update_frame(self):
        logging.info("Updating splash screen frame")


        self.setPixmap(self.movie.currentPixmap())

    def finish(self, window):
        self.movie.stop()
        super().finish(window)