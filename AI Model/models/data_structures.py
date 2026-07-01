"""
Data structures for ML processing pipeline.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import numpy as np

class TreeStatus(Enum):
    """Tree health status enumeration."""
    ALIVE = "ALIVE"
    DEAD = "DEAD"
    DISEASED = "DISEASED"

@dataclass
class BoundingBox:
    """Bounding box coordinates for detected objects."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center coordinates of bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        """Get area of bounding box."""
        return self.width * self.height
    
    def is_valid(self, image_width: int, image_height: int) -> bool:
        """Check if bounding box is valid within image dimensions."""
        return (
            0 <= self.x < image_width and
            0 <= self.y < image_height and
            self.x + self.width <= image_width and
            self.y + self.height <= image_height and
            self.width > 0 and
            self.height > 0
        )

@dataclass
class GPSCoordinates:
    """GPS coordinates from image metadata."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    
    def is_valid(self) -> bool:
        """Check if GPS coordinates are valid."""
        return (
            -90 <= self.latitude <= 90 and
            -180 <= self.longitude <= 180
        )

@dataclass
class TreeDetection:
    """Individual tree detection result."""
    tree_id: int
    bbox: BoundingBox
    confidence: float
    center_coords: Tuple[int, int]
    
    def __post_init__(self):
        """Validate detection data after initialization."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

@dataclass
class HealthClassification:
    """Tree health classification result."""
    status: TreeStatus
    confidence: float
    proof_image_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate classification data after initialization."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

@dataclass
class TreeResult:
    """Complete tree analysis result combining detection and classification."""
    tree_id: int
    bbox: BoundingBox
    detection_confidence: float
    status: TreeStatus
    classification_confidence: float
    center_coords: Tuple[int, int]
    gps_coords: Optional[GPSCoordinates] = None
    proof_image_path: Optional[str] = None
    
    @classmethod
    def from_detection_and_classification(
        cls,
        detection: TreeDetection,
        classification: HealthClassification,
        gps_coords: Optional[GPSCoordinates] = None
    ) -> 'TreeResult':
        """Create TreeResult from detection and classification."""
        return cls(
            tree_id=detection.tree_id,
            bbox=detection.bbox,
            detection_confidence=detection.confidence,
            status=classification.status,
            classification_confidence=classification.confidence,
            center_coords=detection.center_coords,
            gps_coords=gps_coords,
            proof_image_path=classification.proof_image_path
        )

@dataclass
class ImageMetadata:
    """Metadata extracted from drone images."""
    filename: str
    file_size: int
    dimensions: Tuple[int, int]  # (width, height)
    format: str
    gps_coords: Optional[GPSCoordinates] = None
    timestamp: Optional[datetime] = None
    
    def is_valid_format(self) -> bool:
        """Check if image format is supported."""
        supported_formats = {'JPEG', 'PNG', 'TIFF', 'JPG'}
        return self.format.upper() in supported_formats

@dataclass
class ProcessingResult:
    """Complete processing result for a drone image."""
    patch_id: str
    image_metadata: ImageMetadata
    tree_results: List[TreeResult]
    processing_time: float
    timestamp: datetime
    
    @property
    def summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the processing result."""
        total_trees = len(self.tree_results)
        if total_trees == 0:
            return {
                "total_trees": 0,
                "alive_trees": 0,
                "dead_trees": 0,
                "diseased_trees": 0,
                "survival_rate": 0.0,
                "average_confidence": 0.0
            }
        
        status_counts = {status: 0 for status in TreeStatus}
        total_confidence = 0.0
        
        for result in self.tree_results:
            status_counts[result.status] += 1
            total_confidence += result.classification_confidence
        
        alive_trees = status_counts[TreeStatus.ALIVE]
        dead_trees = status_counts[TreeStatus.DEAD]
        diseased_trees = status_counts[TreeStatus.DISEASED]
        
        survival_rate = (alive_trees / total_trees) * 100 if total_trees > 0 else 0.0
        average_confidence = total_confidence / total_trees if total_trees > 0 else 0.0
        
        return {
            "total_trees": total_trees,
            "alive_trees": alive_trees,
            "dead_trees": dead_trees,
            "diseased_trees": diseased_trees,
            "survival_rate": round(survival_rate, 2),
            "average_confidence": round(average_confidence, 3)
        }



@dataclass
class TaskStatus:
    """Status of an asynchronous processing task."""
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float  # 0.0 to 1.0
    estimated_time_remaining: Optional[int] = None  # seconds
    error_message: Optional[str] = None
    result: Optional[ProcessingResult] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        """Set timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        
        if not (0.0 <= self.progress <= 1.0):
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {self.progress}")