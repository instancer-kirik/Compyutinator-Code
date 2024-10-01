from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtCore import QObject, pyqtSignal
import os
import logging

class FontManager(QObject):
    font_added = pyqtSignal(str)
    font_removed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.custom_fonts_dir = os.path.join(os.path.dirname(__file__), 'custom_fonts')
        os.makedirs(self.custom_fonts_dir, exist_ok=True)
        self.load_custom_fonts()

    def load_custom_fonts(self):
        for filename in os.listdir(self.custom_fonts_dir):
            if filename.lower().endswith(('.ttf', '.otf')):
                font_path = os.path.join(self.custom_fonts_dir, filename)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    for family in font_families:
                        logging.info(f"Loaded custom font: {family}")
                        self.font_added.emit(family)
                else:
                    logging.error(f"Failed to load font: {filename}")

    def add_font(self, font_path):
        if not os.path.exists(font_path):
            logging.error(f"Font file not found: {font_path}")
            return False

        filename = os.path.basename(font_path)
        destination = os.path.join(self.custom_fonts_dir, filename)
        
        try:
            os.copy(font_path, destination)
        except Exception as e:
            logging.error(f"Failed to copy font file: {e}")
            return False

        font_id = QFontDatabase.addApplicationFont(destination)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            for family in font_families:
                logging.info(f"Added new font: {family}")
                self.font_added.emit(family)
            return True
        else:
            logging.error(f"Failed to add font: {filename}")
            return False

    def remove_font(self, font_family):
        for filename in os.listdir(self.custom_fonts_dir):
            font_path = os.path.join(self.custom_fonts_dir, filename)
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if font_family in families:
                    QFontDatabase.removeApplicationFont(font_id)
                    os.remove(font_path)
                    logging.info(f"Removed font: {font_family}")
                    self.font_removed.emit(font_family)
                    return True
        logging.error(f"Font not found: {font_family}")
        return False

    def get_available_fonts(self):
        return QFontDatabase.families()

    def get_font(self, family, size=12, weight=QFont.Weight.Normal, italic=False):
        return QFont(family, size, weight, italic)