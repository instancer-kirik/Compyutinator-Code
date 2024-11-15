from pathlib import Path
import base64
from datetime import datetime
import logging
import json
from PIL import Image
import io
import re

class EmailPixelTracker:
    def __init__(self, log_path: Path = Path("email_tracking")):
        self.log_path = log_path
        self.log_path.mkdir(exist_ok=True)

    def create_tracking_pixel(self) -> str:
        """Create a 1x1 transparent tracking pixel for emails"""
        try:
            # Create transparent 1x1 pixel
            img = Image.new('RGBA', (1,1), (0,0,0,0))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            
            # Convert to base64 for email embedding
            pixel_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f'<img src="data:image/png;base64,{pixel_base64}" alt="" />'
            
        except Exception as e:
            logging.error(f"Error creating tracking pixel: {e}")
            return ""

    def detect_tracking_pixels(self, email_content: str) -> list:
        """Detect potential tracking pixels in email"""
        tracking_pixels = []
        
        # Common tracking pixel patterns
        patterns = [
            # 1x1 pixel images
            r'<img[^>]+(?:width=["\']1["\']|height=["\']1["\'])[^>]*>',
            
            # Base64 encoded images
            r'<img[^>]+src=["\']data:image/[^>]+>',
            
            # Common tracking domains
            r'<img[^>]+src=["\'](?:https?:)?//[^"\']*(?:mailtrack|openrate|emailopen)[^"\']*["\'][^>]*>',
            
            # Hidden images
            r'<img[^>]+style=["\'][^"\']*(?:display:\s*none|visibility:\s*hidden)[^"\']*["\'][^>]*>'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, email_content, re.IGNORECASE)
            for match in matches:
                tracking_pixels.append({
                    "pixel": match.group(0),
                    "position": match.span(),
                    "type": "tracking_pixel"
                })
                
        return tracking_pixels

    def log_tracking_attempt(self, email_subject: str, sender: str):
        """Log when a tracking pixel is detected"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "tracking_detected",
                "email_subject": email_subject,
                "sender": sender
            }
            
            with open(self.log_path / "tracking_attempts.log", "a") as f:
                json.dump(log_entry, f)
                f.write("\n")
                
        except Exception as e:
            logging.error(f"Error logging tracking attempt: {e}") 