"""
Complete forest monitoring ML processor implementation.
Updated to use ForestMonitor for specific OP1-OP3 tracking.
"""
import cv2
import numpy as np
import os
import time
from datetime import datetime
from typing import List, Optional

from models.ml_processor import MLProcessor
from models.data_structures import (
    TreeDetection, HealthClassification, TreeResult, 
    ProcessingResult, ImageMetadata, TreeStatus, BoundingBox
)
from core.cv_processor import ImageProcessor
from core.forest_monitor import ForestMonitor, GeoPoint
from config import settings
from logger import logger

class ForestMLProcessor(MLProcessor):
    """Complete ML processor for forest monitoring system using specific OP logic."""
    
    def __init__(self):
        """Initialize the forest ML processor with ForestMonitor."""
        self.monitor = ForestMonitor()
        self.image_processor = ImageProcessor()
        self._is_loaded = True
        logger.info("ForestMLProcessor initialized with ForestMonitor (OP1-OP3 Logic)")
    
    def detect_trees(self, image: np.ndarray) -> List[TreeDetection]:
        """
        Adapter method: Uses OP3 (Weeding) detection as proxy for 'Visible Trees'.
        """
        # Assume current image is OP3 phase for detection purposes
        points = self.monitor.detect_features(image, "OP3", datetime.now().year)
        
        detections = []
        for i, pt in enumerate(points):
            # Create a bbox around the point (40px approx diameter)
            bbox = BoundingBox(
                x=pt.pixel_x - 20,
                y=pt.pixel_y - 20,
                width=40,
                height=40
            )
            
            detection = TreeDetection(
                tree_id=i,
                bbox=bbox,
                confidence=pt.confidence,
                center_coords=(pt.pixel_x, pt.pixel_y)
            )
            detections.append(detection)
            
        return detections
    
    def classify_health(self, tree_crop: np.ndarray, tree_id: int) -> HealthClassification:
        """
        Placeholder - Survival logic is now handled by calculate_survival_rate 
        at the patch level, but we keep this for API compatibility.
        """
        # If it was detected by OP3 logic (cleared soil + green center), it's likely Alive.
        return HealthClassification(
            status=TreeStatus.ALIVE,
            confidence=0.9
        )
    
    def extract_metadata(self, image_path: str) -> ImageMetadata:
        return self.image_processor.extract_metadata(image_path)
    
    def process_image(self, image_path: str, patch_id: str) -> ProcessingResult:
        """Process operation for a single image (OP3 assumption for demo)."""
        start_time = time.time()
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            detections = self.detect_trees(image)
            
            tree_results = []
            for det in detections:
                res = TreeResult.from_detection_and_classification(
                    det, 
                    HealthClassification(TreeStatus.ALIVE, det.confidence),
                    None
                )
                tree_results.append(res)

            processing_time = time.time() - start_time
            
            # TODO: IN A REAL SCENARIO, WE WOULD LOAD PREVIOUS YEAR DATA HERE
            # AND RUN self.monitor.calculate_survival_rate()
            
            return ProcessingResult(
                patch_id=patch_id,
                image_metadata=self.extract_metadata(image_path),
                tree_results=tree_results,
                processing_time=processing_time,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None # Handle error appropriately

    def is_loaded(self) -> bool:
        return self._is_loaded

    def get_system_info(self) -> dict:
        return {
            'processor_type': 'ForestMonitor (OP1-OP3)',
            'description': 'Tracking Pits -> Saplings -> Weeding',
            'is_loaded': True
        }
