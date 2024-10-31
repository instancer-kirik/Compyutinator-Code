from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
from PIL import Image
from typing import List, Tuple, Optional, Dict
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QWidget, QTextEdit, QFileDialog, QLabel, QLineEdit, 
                            QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt

class KeyboardRecognizer:
    def __init__(self, subscription_key: str, endpoint: str):
        """Initialize with Azure credentials"""
        self.client = ComputerVisionClient(
            endpoint=endpoint,
            credentials=CognitiveServicesCredentials(subscription_key)
        )
        
        # Define known keyboard layouts and their characteristics
        self.known_layouts = {
            "QWERTY": {
                "top_row": ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
                "home_row": ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
                "bottom_row": ["Z", "X", "C", "V", "B", "N", "M"]
            },
            "DVORAK": {
                "top_row": ["'", ",", ".", "P", "Y", "F", "G", "C", "R", "L"],
                "home_row": ["A", "O", "E", "U", "I", "D", "H", "T", "N", "S"],
                "bottom_row": [";", "Q", "J", "K", "X", "B", "M", "W", "V", "Z"]
            }
            # Add more layouts as needed
        }

    def process_image(self, image_path: str) -> Dict[str, any]:
        """Process a single keyboard image and return layout information"""
        try:
            # Open image and get dimensions
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Call Azure's OCR
            result = self.client.recognize_printed_text_in_stream(image_data)
            
            if not result.regions:
                return {"error": "No text detected in image"}
            
            # Extract and organize detected text
            detected_keys = self._extract_keyboard_text(result)
            
            # Analyze layout
            layout_info = self._analyze_layout(detected_keys)
            
            return layout_info
            
        except Exception as e:
            return {"error": f"Error processing image: {str(e)}"}

    def _extract_keyboard_text(self, ocr_result) -> List[Dict[str, any]]:
        """Extract text and positions from OCR result"""
        detected_keys = []
        
        for region in ocr_result.regions:
            for line in region.lines:
                for word in line.words:
                    # Store both text and bounding box
                    detected_keys.append({
                        "text": word.text,
                        "box": word.bounding_box,
                        "confidence": word.confidence
                    })
        
        return detected_keys

    def _analyze_layout(self, detected_keys: List[Dict[str, any]]) -> Dict[str, any]:
        """Analyze detected keys to determine keyboard layout"""
        # Sort keys by vertical position to identify rows
        sorted_keys = sorted(detected_keys, key=lambda k: k['box'][1])  # Sort by Y coordinate
        
        # Group keys into rows
        rows = self._group_into_rows(sorted_keys)
        
        # Match against known layouts
        layout_matches = {}
        for layout_name, layout_pattern in self.known_layouts.items():
            match_score = self._calculate_layout_match(rows, layout_pattern)
            layout_matches[layout_name] = match_score
        
        # Find best match
        best_match = max(layout_matches.items(), key=lambda x: x[1])
        
        return {
            "detected_layout": best_match[0],
            "confidence": best_match[1],
            "detected_keys": detected_keys,
            "rows": rows
        }

    def _group_into_rows(self, keys: List[Dict[str, any]]) -> List[List[Dict[str, any]]]:
        """Group detected keys into rows based on vertical position"""
        rows = []
        current_row = []
        last_y = None
        y_threshold = 10  # Adjust based on image resolution
        
        for key in keys:
            y_pos = key['box'][1]
            
            if last_y is None or abs(y_pos - last_y) <= y_threshold:
                current_row.append(key)
            else:
                if current_row:
                    # Sort row by x position before adding
                    current_row.sort(key=lambda k: k['box'][0])
                    rows.append(current_row)
                current_row = [key]
            
            last_y = y_pos
        
        if current_row:
            current_row.sort(key=lambda k: k['box'][0])
            rows.append(current_row)
        
        return rows

    def _calculate_layout_match(self, detected_rows: List[List[Dict]], layout_pattern: Dict) -> float:
        """Calculate how well detected keys match a known layout"""
        if not detected_rows:
            return 0.0
        
        total_matches = 0
        total_keys = 0
        
        # Match each detected row against pattern rows
        for row_name, pattern_row in layout_pattern.items():
            best_row_match = 0
            
            for detected_row in detected_rows:
                matches = sum(1 for key in detected_row 
                            if key['text'].upper() in pattern_row)
                best_row_match = max(best_row_match, matches)
            
            total_matches += best_row_match
            total_keys += len(pattern_row)
        
        return total_matches / total_keys if total_keys > 0 else 0.0

class KeyboardMonitor(QMainWindow):
    def __init__(self, subscription_key: str, endpoint: str):
        super().__init__()
        self.setWindowTitle("Keyboard Layout Recognizer")
        self.recognizer = KeyboardRecognizer(subscription_key, endpoint)
        
        # Initialize UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.create_widgets()

    def create_widgets(self):
        # Image selection
        self.select_button = QPushButton("Select Keyboard Image")
        self.select_button.clicked.connect(self.select_image)
        self.layout.addWidget(self.select_button)

        # Preview group
        preview_group = QGroupBox("Image Preview")
        preview_layout = QVBoxLayout()
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        preview_group.setLayout(preview_layout)
        self.layout.addWidget(preview_group)

        # Results group
        results_group = QGroupBox("Recognition Results")
        results_layout = QVBoxLayout()
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        results_group.setLayout(results_layout)
        self.layout.addWidget(results_group)

    def select_image(self):
        """Handle image selection and processing"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Keyboard Image", "", 
            "Image files (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            # Show preview
            preview = Image.open(file_path)
            preview.thumbnail((400, 400))  # Resize for preview
            preview.save("temp_preview.png")
            self.preview_label.setPixmap(QPixmap("temp_preview.png"))
            
            # Process image
            results = self.recognizer.process_image(file_path)
            
            # Display results
            self.display_results(results)

    def display_results(self, results: Dict[str, any]):
        """Display recognition results"""
        if "error" in results:
            self.results_text.setText(f"Error: {results['error']}")
            return
        
        output = []
        output.append(f"Detected Layout: {results['detected_layout']}")
        output.append(f"Confidence: {results['confidence']:.2%}")
        output.append("\nDetected Keys by Row:")
        
        for i, row in enumerate(results['rows']):
            output.append(f"\nRow {i + 1}:")
            keys = [key['text'] for key in row]
            output.append(" ".join(keys))
        
        self.results_text.setText("\n".join(output))

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    import os
    
    # Load Azure credentials from .env file
    load_dotenv()
    subscription_key = os.getenv("AZURE_VISION_KEY")
    endpoint = os.getenv("AZURE_VISION_ENDPOINT")
    
    if not subscription_key or not endpoint:
        print("Error: Azure credentials not found in .env file")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    monitor = KeyboardMonitor(subscription_key, endpoint)
    monitor.show()
    sys.exit(app.exec())
