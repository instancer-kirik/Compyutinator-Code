from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox, QPushButton
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Typing effect enabled
        self.typing_effect_checkbox = QCheckBox("Enable Typing Effect")
        self.typing_effect_checkbox.setChecked(self.settings_manager.get_typing_effect_enabled())
        layout.addWidget(self.typing_effect_checkbox)

        # Typing effect speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Typing Effect Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 500)
        self.speed_slider.setValue(self.settings_manager.get_typing_effect_speed())
        speed_layout.addWidget(self.speed_slider)
        layout.addLayout(speed_layout)

        # Particle count
        particle_layout = QHBoxLayout()
        particle_layout.addWidget(QLabel("Particle Count:"))
        self.particle_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_slider.setRange(1, 50)
        self.particle_slider.setValue(self.settings_manager.get_typing_effect_particle_count())
        particle_layout.addWidget(self.particle_slider)
        layout.addLayout(particle_layout)

        # Save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def save_settings(self):
        self.settings_manager.set_typing_effect_enabled(self.typing_effect_checkbox.isChecked())
        self.settings_manager.set_typing_effect_speed(self.speed_slider.value())
        self.settings_manager.set_typing_effect_particle_count(self.particle_slider.value())
        self.accept()