from typing import Dict, Any, Optional
from pathlib import Path
import base64
from datetime import datetime
import logging
import json
from PIL import Image
import io
import uuid
import hashlib
from dataclasses import dataclass
import aiohttp
from aiohttp import web
import asyncio

@dataclass
class PixelHit:
    id: str
    timestamp: str
    ip: str
    user_agent: str
    referer: Optional[str]
    headers: Dict[str, str]
    geo_data: Optional[Dict[str, Any]] = None

class PixelTracker:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(exist_ok=True)
        self.pixels: Dict[str, Dict[str, Any]] = {}
        self.hits_path = storage_path / "pixel_hits"
        self.hits_path.mkdir(exist_ok=True)
        self._load_pixels()
        
    def create_tracking_pixel(self, campaign: str = None) -> tuple[str, bytes]:
        """Create a new tracking pixel"""
        try:
            # Create 1x1 transparent PNG
            img = Image.new('RGBA', (1,1), (0,0,0,0))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            pixel_data = buffer.getvalue()
            
            # Generate unique ID
            pixel_id = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:16]
            
            self.pixels[pixel_id] = {
                "created": datetime.now().isoformat(),
                "campaign": campaign,
                "hits": 0,
                "last_hit": None
            }
            
            self._save_pixels()
            
            return pixel_id, pixel_data
            
        except Exception as e:
            logging.error(f"Error creating tracking pixel: {e}")
            raise
            
    def get_html_pixel(self, pixel_id: str, base_url: str) -> str:
        """Get HTML for embedding tracking pixel"""
        return f'<img src="{base_url}/pixel/{pixel_id}.png" style="display:none" />'
        
    def get_email_pixel(self, pixel_id: str, base_url: str) -> str:
        """Get base64 encoded pixel for email tracking"""
        try:
            img = Image.new('RGBA', (1,1), (0,0,0,0))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            pixel_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f'<img src="data:image/png;base64,{pixel_b64}" />'
            
        except Exception as e:
            logging.error(f"Error creating email pixel: {e}")
            raise
            
    async def track_hit(self, pixel_id: str, request: web.Request) -> Optional[PixelHit]:
        """Record a pixel hit"""
        try:
            if pixel_id not in self.pixels:
                return None
                
            # Get request info
            hit = PixelHit(
                id=str(uuid.uuid4()),
                timestamp=datetime.now().isoformat(),
                ip=request.remote,
                user_agent=request.headers.get('User-Agent', ''),
                referer=request.headers.get('Referer'),
                headers=dict(request.headers)
            )
            
            # Get geo data if possible
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f'http://ip-api.com/json/{hit.ip}') as resp:
                        hit.geo_data = await resp.json()
            except:
                pass
                
            # Update pixel stats
            self.pixels[pixel_id]["hits"] += 1
            self.pixels[pixel_id]["last_hit"] = hit.timestamp
            
            # Save hit data
            hit_file = self.hits_path / f"{pixel_id}_{hit.id}.json"
            with open(hit_file, 'w') as f:
                json.dump(hit.__dict__, f, indent=2)
                
            self._save_pixels()
            
            return hit
            
        except Exception as e:
            logging.error(f"Error tracking pixel hit: {e}")
            return None
            
    def get_pixel_stats(self, pixel_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a tracking pixel"""
        if pixel_id not in self.pixels:
            return None
            
        stats = self.pixels[pixel_id].copy()
        
        # Get detailed hit data
        hits = []
        for hit_file in self.hits_path.glob(f"{pixel_id}_*.json"):
            with open(hit_file) as f:
                hits.append(json.load(f))
                
        stats["hit_details"] = hits
        return stats
        
    def detect_tracking_pixels(self, html_content: str) -> list[Dict[str, Any]]:
        """Detect potential tracking pixels in HTML content"""
        tracking_pixels = []
        
        # Common tracking pixel patterns
        patterns = [
            # 1x1 images
            r'<img[^>]+(?:width=["\']1["\'][^>]+height=["\']1["\']|height=["\']1["\'][^>]+width=["\']1["\'])[^>]*>',
            
            # Hidden images
            r'<img[^>]+style=["\'][^"\']*(?:visibility:\s*hidden|display:\s*none)[^"\']*["\'][^>]*>',
            
            # Common tracking domains
            r'<img[^>]+src=["\'](?:https?:)?//[^"\']*(?:analytics|tracking|pixel|beacon)[^"\']*["\'][^>]*>',
            
            # Base64 encoded tiny images
            r'<img[^>]+src=["\']data:image/[^;]+;base64,[A-Za-z0-9+/]{0,50}={0,2}["\'][^>]*>'
        ]
        
        for pattern in patterns:
            import re
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            for match in matches:
                pixel = {
                    "type": "tracking_pixel",
                    "html": match.group(0),
                    "position": match.span(),
                    "confidence": self._calculate_tracking_confidence(match.group(0))
                }
                tracking_pixels.append(pixel)
                
        return tracking_pixels
        
    def _calculate_tracking_confidence(self, pixel_html: str) -> float:
        """Calculate confidence score that this is a tracking pixel"""
        score = 0.0
        
        # Size indicators
        if 'width="1"' in pixel_html or "width='1'" in pixel_html:
            score += 0.3
        if 'height="1"' in pixel_html or "height='1'" in pixel_html:
            score += 0.3
            
        # Visibility
        if 'display:none' in pixel_html or 'visibility:hidden' in pixel_html:
            score += 0.2
            
        # Known tracking domains
        tracking_domains = ['analytics', 'tracking', 'pixel', 'beacon', 'stats']
        if any(domain in pixel_html.lower() for domain in tracking_domains):
            score += 0.2
            
        # Base64 encoded
        if 'data:image' in pixel_html and 'base64' in pixel_html:
            score += 0.1
            
        return min(score, 1.0)
        
    def _save_pixels(self):
        """Save pixel database"""
        with open(self.storage_path / "pixels.json", 'w') as f:
            json.dump(self.pixels, f, indent=2)
            
    def _load_pixels(self):
        """Load pixel database"""
        try:
            pixel_file = self.storage_path / "pixels.json"
            if pixel_file.exists():
                with open(pixel_file) as f:
                    self.pixels = json.load(f)
        except Exception as e:
            logging.error(f"Error loading pixels: {e}") 