from PyQt6.QtWidgets import QSplashScreen, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtGui import QMovie, QPixmap
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer
import logging
from PyQt6.QtWidgets import QLabel
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
        super().__init__(QPixmap(400, 400))  # Create with a sized pixmap
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Create a central widget and layout
        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)

        # Create and set up the movie
        self.movie = QMovie(gif_path)
        self.movie.setScaledSize(QSize(400, 400))  # Adjust size as needed
        self.movie.frameChanged.connect(self.update_frame)

        # Create a label to display the movie
        self.movie_label = QLabel(self)
        self.movie_label.setMovie(self.movie)
        self.layout.addWidget(self.movie_label)

        # Create and add the button
        self.close_button = QPushButton("Proceed to Application", self)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 123, 255, 200);
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(0, 86, 179, 200);
            }
        """)
        self.close_button.clicked.connect(self.close_splash)
        self.layout.addWidget(self.close_button)

        # Set the central widget
        self.setLayout(self.layout)

        QTimer.singleShot(0, self.movie.start)  # Start the movie in the next event loop iteration
        logging.info("Splash screen initialized")

    def update_frame(self):
        current_pixmap = self.movie.currentPixmap()
        if not current_pixmap.isNull():
            self.setPixmap(current_pixmap)
        else:
            logging.warning("Received null pixmap from movie")

    def close_splash(self):
        self.movie.stop()
        self.close()

    def finish(self, window):
        self.movie.stop()
        super().finish(window)

    def mousePressEvent(self, event):
        # Prevent the default behavior of closing the splash screen on click
        pass