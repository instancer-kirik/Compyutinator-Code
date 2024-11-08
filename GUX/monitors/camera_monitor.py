import sys
import subprocess
from pathlib import Path
from datetime import datetime
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

class CameraMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Monitor")
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create display label
        self.display_label = QLabel()
        self.display_label.setMinimumSize(640, 480)
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.display_label)
        
        # Create status label
        self.status_label = QLabel("Initializing...")
        layout.addWidget(self.status_label)
        
        # Create camera selection dropdown
        self.camera_selector = QComboBox()
        self.camera_selector.addItems(self.get_camera_identifiers())
        layout.addWidget(self.camera_selector)
        
        # Create control buttons
        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.start_camera)
        layout.addWidget(self.start_button)
        
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.clicked.connect(self.capture_image)
        self.capture_button.setEnabled(False)
        layout.addWidget(self.capture_button)
        
        # Initialize pipeline variables
        self.input_pipeline = None
        
        # Create output directory
        self.output_dir = Path("captured_images")
        self.output_dir.mkdir(exist_ok=True)
        
        # Start camera automatically
        QTimer.singleShot(100, self.start_camera)

    def get_camera_identifiers(self):
        # Return hardcoded camera identifiers
        return [r"\\_SB_.PCI0.I2C2.CAMF", r"\\_SB_.PCI0.I2C3.CAMR"]

    def start_camera(self):
        if self.input_pipeline:
            self.input_pipeline.set_state(Gst.State.NULL)
        
        try:
            camera_identifier = self.camera_selector.currentText()
            
            # Adjust the pipeline based on the actual output format
            input_str = (
                f'libcamerasrc camera-name={camera_identifier} ! '
                'video/x-raw,width=1280,height=720,framerate=30/1 ! '
                'videoconvert ! videoscale ! '
                'video/x-raw,format=NV12 ! appsink name=sink emit-signals=true sync=false'
            )
            
            print(f"Creating input pipeline: {input_str}")
            self.input_pipeline = Gst.parse_launch(input_str)
            
            self.sink = self.input_pipeline.get_by_name('sink')
            self.sink.connect('new-sample', self.on_new_sample)
            
            ret = self.input_pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                raise Exception("Failed to start input pipeline")
            
            self.start_button.setText("Stop Camera")
            self.capture_button.setEnabled(True)
            self.status_label.setText("Camera running")
            
        except Exception as e:
            error_msg = f"Pipeline creation failed: {str(e)}"
            print(error_msg)
            self.status_label.setText(error_msg)
            if self.input_pipeline:
                self.input_pipeline.set_state(Gst.State.NULL)
            self.input_pipeline = None
            self.start_button.setText("Start Camera")
            self.capture_button.setEnabled(False)

    def on_new_sample(self, sink):
        if not self.display_label:  # Check if QLabel is still valid
            return Gst.FlowReturn.ERROR

        sample = sink.emit('pull-sample')
        if not sample:
            print("Failed to pull sample")
            return Gst.FlowReturn.ERROR
        
        buffer = sample.get_buffer()
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            print("Failed to map buffer")
            buffer.unmap(map_info)
            return Gst.FlowReturn.ERROR
        
        # Get the size of the data
        data_size = map_info.size
        print(f"Data size: {data_size}")

        # For NV12, the size should be width * height * 1.5
        expected_size = 1280 * 720 * 1.5
        if data_size != expected_size:
            print(f"Unexpected data size: {data_size}, expected: {expected_size}")
            buffer.unmap(map_info)
            return Gst.FlowReturn.ERROR

        # Convert NV12 to RGB using NumPy
        nv12_data = np.frombuffer(map_info.data, dtype=np.uint8).reshape((720 * 3 // 2, 1280))

        # Prepare an empty RGB array
        rgb_data = np.zeros((720, 1280, 3), dtype=np.uint8)

        # NV12 to RGB conversion
        for y in range(720):
            for x in range(1280):
                Y = nv12_data[y, x]
                U = nv12_data[720 + (y // 2), (x // 2)] - 128
                V = nv12_data[720 + (y // 2), (x // 2) + 1] - 128

                R = Y + 1.402 * V
                G = Y - 0.344136 * U - 0.714136 * V
                B = Y + 1.772 * U

                rgb_data[y, x] = [max(0, min(255, int(R))), max(0, min(255, int(G))), max(0, min(255, int(B)))]

        # Create QImage from RGB data
        image = QImage(
            rgb_data.data,
            1280, 720,  # Width, Height for 720p
            1280 * 3,  # Bytes per line (RGB = width * 3)
            QImage.Format.Format_RGB888  # Use RGB format
        )
        
        # Update display
        pixmap = QPixmap.fromImage(image)
        self.display_label.setPixmap(pixmap)
        
        buffer.unmap(map_info)
        return Gst.FlowReturn.OK

    def capture_image(self):
        if not self.display_label.pixmap():
            return
        
        # Save current image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"capture_{timestamp}.png"
        
        if self.display_label.pixmap().save(str(filename)):
            self.status_label.setText(f"Image saved: {filename}")
        else:
            self.status_label.setText("Failed to save image")

def main():
    app = QApplication(sys.argv)
    window = CameraMonitor()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
