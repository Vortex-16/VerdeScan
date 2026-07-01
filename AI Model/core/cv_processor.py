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

from models.data_structures import ImageMetadata, GPSCoordinates
from config import settings
from logger import logger



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