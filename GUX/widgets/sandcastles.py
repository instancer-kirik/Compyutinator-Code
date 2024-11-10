from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QListWidget, QCheckBox, QInputDialog,
                            QLabel, QProgressBar, QComboBox, QSlider) 
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, pyqtSignal
import json
import os
from datetime import datetime
import random

class SandcastleBuilder(QWidget):
    save_signal = pyqtSignal(str)  # Signal to emit when castle is saved

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_castle = """
                                   |>>>
                                   |
                    |>>>      _  _|_  _         |>>>
                    |        |;| |;| |;|        |
                _  _|_  _    \\\\.    .  /    _  _|_  _
               |;|_|;|_|;|    \\\\:. ,  /    |;|_|;|_|;|
               \\\\..      /    ||;   . |    \\\\.    .  /
                \\\\.  ,  /     ||:  .  |     \\\\:  .  /
                 ||:   |_   _ ||_ . _ | _   _||:   |
                 ||:  .|||_|;|_|;|_|;|_|;|_|;||:.  |
                 ||:   ||.    .     .      . ||:  .|
                 ||: . || .     . .   .  ,   ||:   |       \\,/
                 ||:   ||:  ,  _______   .   ||: , |            /`\\
                 ||:   || .   /+++++++\\    . ||:   |
                 ||:   ||.    |+++++++| .    ||: . |
              __ ||: . ||: ,  |+++++++|.  . _||_   |
     ____--`~    '--~~__|.    |+++++__|----~    ~`---,              ___
-~--~                   ~---__|,--~'                  ~~----_____-~'   `~----~~
                 ≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈
         ≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈
"""

        self.decorations = {
            'seashell': 'C',
            'starfish': '✶',
            'crab': '🦀',
            'wave': '~',
            'bird': 'V',
            'sun': '☀',
            'cloud': '☁',
        }

        self.current_scene = self.base_castle
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Scene display
        self.scene_display = QTextEdit()
        self.scene_display.setReadOnly(True)
        self.scene_display.setFont(self.get_monospace_font())
        self.scene_display.setStyleSheet("""
            QTextEdit {
                background-color: #f0e68c;
                border: 2px solid #8b4513;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.scene_display.setText(self.current_scene)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Time of day slider
        time_label = QLabel("Time of Day:")
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(23)
        self.time_slider.setValue(12)
        self.time_slider.valueChanged.connect(self.update_lighting)
        
        # Weather combo
        weather_label = QLabel("Weather:")
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(["Sunny", "Cloudy", "Windy"])
        self.weather_combo.currentTextChanged.connect(self.update_weather)
        
        # Add decorations button
        decorate_btn = QPushButton("Add Random Decoration")
        decorate_btn.clicked.connect(self.add_random_decoration)
        
        # Save button
        save_btn = QPushButton("Save Scene")
        save_btn.clicked.connect(self.save_scene)
        
        # Add controls
        controls_layout.addWidget(time_label)
        controls_layout.addWidget(self.time_slider)
        controls_layout.addWidget(weather_label)
        controls_layout.addWidget(self.weather_combo)
        controls_layout.addWidget(decorate_btn)
        controls_layout.addWidget(save_btn)
        
        # Add everything to main layout
        layout.addWidget(self.scene_display)
        layout.addLayout(controls_layout)
        
        self.setLayout(layout)

    def update_lighting(self):
        """Update scene lighting based on time of day"""
        time = self.time_slider.value()
        if 6 <= time <= 18:  # Daytime
            self.scene_display.setStyleSheet("""
                QTextEdit {
                    background-color: #f0e68c;
                    color: #000000;
                    border: 2px solid #8b4513;
                    border-radius: 5px;
                }
            """)
        else:  # Nighttime
            self.scene_display.setStyleSheet("""
                QTextEdit {
                    background-color: #4a4a4a;
                    color: #c0c0c0;
                    border: 2px solid #2d2d2d;
                    border-radius: 5px;
                }
            """)

    def update_weather(self, weather):
        """Update scene based on weather"""
        scene = self.base_castle
        if weather == "Windy":
            scene = scene.replace('|', '/')
        elif weather == "Cloudy":
            scene = scene.replace('☀', '☁')
        self.current_scene = scene
        self.scene_display.setText(scene)

    def add_random_decoration(self):
        """Add a random decoration to the scene"""
        decor = random.choice(list(self.decorations.values()))
        scene_lines = self.current_scene.split('\n')
        # Add decoration to a random position in the lower third of the scene
        for i in range(len(scene_lines) - 5, len(scene_lines)):
            if '≈' in scene_lines[i]:
                pos = random.randint(0, len(scene_lines[i]))
                scene_lines[i] = scene_lines[i][:pos] + decor + scene_lines[i][pos:]
        self.current_scene = '\n'.join(scene_lines)
        self.scene_display.setText(self.current_scene)

    def save_scene(self):
        """Save the current scene as markdown"""
        scene_data = {
            "scene": self.current_scene,
            "time": self.time_slider.value(),
            "weather": self.weather_combo.currentText(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        markdown = self.to_markdown(scene_data)
        self.save_signal.emit(markdown)

    def to_markdown(self, scene_data):
        md = f"""# Sandcastle Project - {scene_data['date']}

## The Scene
```ascii
{scene_data['scene']}
```

## Time of Day
{scene_data['time']}

## Weather
{scene_data['weather']}
"""
        return md

    @staticmethod
    def get_monospace_font():
        font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(12)
        return font 