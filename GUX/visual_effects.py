from PyQt6.QtCore import QTimer, QPointF, QRectF, QObject
from PyQt6.QtGui import QPainter, QColor
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

class Particle:
    def __init__(self, pos, color):
        self.pos = QPointF(pos)  # Convert to QPointF
        self.velocity = QPointF(random.uniform(-1, 1), random.uniform(-1, 1))
        self.color = color
        self.life = 1.0

class ParticleEffect(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(16)  # 60 FPS

    def add_particles(self, pos, color, count=10):
        for _ in range(count):
            self.particles.append(Particle(pos, color))

    def update_particles(self):
        for particle in self.particles:
            particle.pos += particle.velocity
            particle.life -= 0.02

        self.particles = [p for p in self.particles if p.life > 0]
        if self.parent():
            self.parent().particle_overlay.update()

    def draw(self, painter):
        for particle in self.particles:
            painter.setPen(QColor(particle.color.red(), particle.color.green(), particle.color.blue(), int(255 * particle.life)))
            painter.setBrush(QColor(particle.color.red(), particle.color.green(), particle.color.blue(), int(255 * particle.life)))
            painter.drawEllipse(particle.pos, 2, 2)  # Draw slightly larger particles
            

class ParticleOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background-color: transparent;")
        self.shake_offset = QPointF(0, 0)
        self.particle_effect = None

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.particle_effect:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(self.shake_offset)
            
            painter.save()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            self.particle_effect.draw(painter)
            painter.restore()

    def set_shake_offset(self, offset):
        self.shake_offset = offset
        self.update()

