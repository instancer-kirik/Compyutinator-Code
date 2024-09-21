import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from GUX.splash_screen import TransparentSplashScreen

def run_splash():
    app = QApplication(sys.argv)
    
    splash_path = os.path.join(os.path.dirname(__file__), 'resources', 'splash.gif')
    splash = TransparentSplashScreen(splash_path)
    splash.show()

    # Exit the splash screen after a timeout (adjust as needed)
    QTimer.singleShot(30000, app.quit)  # 30 seconds timeout

    sys.exit(app.exec())

if __name__ == '__main__':
    run_splash()