"""
Computer vision processing for tree detection and analysis.
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
from PIL import Image, ExifTags
from datetime import datetime
import os
import time

from models.data_structures import (
    TreeDetection, BoundingBox, ImageMetadata, GPSCoordinates
)
from models.ml_processor import MLProcessor
from config import settings
from logger import logger

class CVTreeDetector:
    """Computer vision-based tree detection using OpenCV."""
    
    def __init__(self, confidence_threshold: float = 0.5):
        """
        Initialize CV tree detector.
        
        Args:
            confidence_threshold: Minimum confidence for tree detection
        """
        self.confidence_threshold = confidence_threshold
        self.min_tree_area = 300
        self.max_tree_area = 5000
        
    def detect_trees(self, image: np.ndarray) -> List[TreeDetection]:
        """
        Detect trees using computer vision techniques.
        
        Args:
            image: Input drone image as numpy array
            
        Returns:
            List of tree detections
        """
        if image is None or image.size == 0:
            return []
        
        try:
            # Convert to grayscale for processing
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Use adaptive thresholding to find dark regions (potential trees)
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Apply morphological operations to clean up the image
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            detections = []
            tree_id = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Filter by area to remove noise and very large regions
                if self.min_tree_area <= area <= self.max_tree_area:
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Calculate aspect ratio to filter out non-tree shapes
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.3 <= aspect_ratio <= 3.0:  # Reasonable aspect ratio for trees
                        
                        # Calculate confidence based on area and shape
                        confidence = self._calculate_detection_confidence(contour, area)
                        
                        if confidence >= self.confidence_threshold:
                            bbox = BoundingBox(x=x, y=y, width=w, height=h)
                            center_coords = bbox.center
                            
                            detection = TreeDetection(
                                tree_id=tree_id,
                                bbox=bbox,
                                confidence=confidence,
                                center_coords=center_coords
                            )
                            
                            detections.append(detection)
                            tree_id += 1
            
            logger.info(f"Detected {len(detections)} trees using CV pipeline")
            return detections
            
        except Exception as e:
            logger.error(f"Error in tree detection: {e}")
            return []
    
    def _calculate_detection_confidence(self, contour: np.ndarray, area: float) -> float:
        """
        Calculate confidence score for a detected contour.
        
        Args:
            contour: OpenCV contour
            area: Contour area
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Calculate shape features
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                return 0.0
            
            # Circularity (4π * area / perimeter²)
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            
            # Solidity (area / convex hull area)
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0
            
            # Extent (area / bounding rectangle area)
            x, y, w, h = cv2.boundingRect(contour)
            rect_area = w * h
            extent = area / rect_area if rect_area > 0 else 0
            
            # Combine features to calculate confidence
            # Trees tend to be somewhat circular, solid, and fill their bounding box reasonably
            confidence = (
                min(circularity, 1.0) * 0.3 +  # Prefer circular shapes
                solidity * 0.4 +                # Prefer solid shapes
                extent * 0.3                    # Prefer shapes that fill bounding box
            )
            
            # Normalize area contribution (prefer medium-sized detections)
            area_score = 1.0 - abs(area - (self.min_tree_area + self.max_tree_area) / 2) / (self.max_tree_area - self.min_tree_area)
            confidence = confidence * 0.8 + area_score * 0.2
            
            return min(max(confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"Error calculating detection confidence: {e}")
            return 0.5

class ImageProcessor:
    """Image processing utilities for metadata extraction and preprocessing."""
    
    @staticmethod
    def extract_metadata(image_path: str) -> ImageMetadata:
        """
        Extract metadata from image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Image metadata including GPS coordinates if available
        """
        try:
            # Get file info
            file_size = os.path.getsize(image_path)
            filename = os.path.basename(image_path)
            
            # Open image to get dimensions and format
            with Image.open(image_path) as img:
                dimensions = img.size  # (width, height)
                format_name = img.format or 'UNKNOWN'
                
                # Extract EXIF data
                gps_coords = None
                timestamp = None
                
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif = img._getexif()
                    
                    # Extract GPS coordinates
                    gps_coords = ImageProcessor._extract_gps_from_exif(exif)
                    
                    # Extract timestamp
                    timestamp = ImageProcessor._extract_timestamp_from_exif(exif)
                
                return ImageMetadata(
                    filename=filename,
                    file_size=file_size,
                    dimensions=dimensions,
                    format=format_name,
                    gps_coords=gps_coords,
                    timestamp=timestamp
                )
                
        except Exception as e:
            logger.error(f"Error extracting metadata from {image_path}: {e}")
            return ImageMetadata(
                filename=os.path.basename(image_path),
                file_size=0,
                dimensions=(0, 0),
                format='UNKNOWN'
            )
    
    @staticmethod
    def _extract_gps_from_exif(exif: dict) -> Optional[GPSCoordinates]:
        """Extract GPS coordinates from EXIF data."""
        try:
            gps_info = exif.get(34853)  # GPS IFD tag
            if not gps_info:
                return None
            
            def convert_to_degrees(value):
                """Convert GPS coordinate to degrees."""
                d, m, s = value
                return d + (m / 60.0) + (s / 3600.0)
            
            # Extract latitude
            lat = gps_info.get(2)  # GPSLatitude
            lat_ref = gps_info.get(1)  # GPSLatitudeRef
            
            # Extract longitude
            lon = gps_info.get(4)  # GPSLongitude
            lon_ref = gps_info.get(3)  # GPSLongitudeRef
            
            if lat and lon and lat_ref and lon_ref:
                latitude = convert_to_degrees(lat)
                if lat_ref != 'N':
                    latitude = -latitude
                
                longitude = convert_to_degrees(lon)
                if lon_ref != 'E':
                    longitude = -longitude
                
                # Extract altitude if available
                altitude = None
                alt = gps_info.get(6)  # GPSAltitude
                if alt:
                    altitude = float(alt)
                
                return GPSCoordinates(
                    latitude=latitude,
                    longitude=longitude,
                    altitude=altitude
                )
        
        except Exception as e:
            logger.warning(f"Error extracting GPS from EXIF: {e}")
        
        return None
    
    @staticmethod
    def _extract_timestamp_from_exif(exif: dict) -> Optional[datetime]:
        """Extract timestamp from EXIF data."""
        try:
            # Try different timestamp tags
            timestamp_tags = [36867, 36868, 306]  # DateTimeOriginal, DateTimeDigitized, DateTime
            
            for tag in timestamp_tags:
                timestamp_str = exif.get(tag)
                if timestamp_str:
                    try:
                        return datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        continue
        
        except Exception as e:
            logger.warning(f"Error extracting timestamp from EXIF: {e}")
        
        return None
    
    @staticmethod
    def preprocess_image(image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for ML processing.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image
        """
        try:
            # Ensure image is in correct format
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            
            # Resize if too large (for performance)
            height, width = image.shape[:2]
            max_dimension = 2048
            
            if max(height, width) > max_dimension:
                scale = max_dimension / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Apply slight denoising
            if len(image.shape) == 3:
                image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
            else:
                image = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
            
            return image
            
        except Exception as e:
            logger.warning(f"Error in image preprocessing: {e}")
            return image
    
    @staticmethod
    def validate_image_file(image_path: str) -> bool:
        """
        Validate image file for processing.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if image is valid for processing
        """
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                return False
            
            # Check file size
            file_size = os.path.getsize(image_path)
            if file_size == 0 or file_size > settings.max_file_size:
                return False
            
            # Try to open image
            with Image.open(image_path) as img:
                # Check format
                if img.format not in ['JPEG', 'PNG', 'TIFF']:
                    return False
                
                # Check dimensions
                width, height = img.size
                if width < 100 or height < 100:
                    return False
                
                # Try to load image data
                img.load()
                
            return True
            
        except Exception as e:
            logger.warning(f"Image validation failed for {image_path}: {e}")
            return False