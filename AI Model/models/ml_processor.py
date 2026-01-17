"""
Base ML processor interface and implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np
from PIL import Image

from models.data_structures import (
    TreeDetection, HealthClassification, TreeResult, 
    ProcessingResult, ImageMetadata, GeminiResponse
)

class MLProcessor(ABC):
    """Abstract base class for ML processing pipeline."""
    
    @abstractmethod
    def detect_trees(self, image: np.ndarray) -> List[TreeDetection]:
        """
        Detect individual trees in the drone image.
        
        Args:
            image: Input drone image as numpy array
            
        Returns:
            List of tree detections with bounding boxes and confidence scores
        """
        pass
    
    @abstractmethod
    def classify_health(self, tree_crop: np.ndarray, tree_id: int) -> HealthClassification:
        """
        Classify the health status of a detected tree.
        
        Args:
            tree_crop: Cropped image of individual tree
            tree_id: Unique identifier for the tree
            
        Returns:
            Health classification with status and confidence
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, image_path: str) -> ImageMetadata:
        """
        Extract metadata from image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Image metadata including GPS coordinates if available
        """
        pass
    
    @abstractmethod
    def process_image(self, image_path: str, patch_id: str) -> ProcessingResult:
        """
        Process complete drone image through the ML pipeline.
        
        Args:
            image_path: Path to the drone image
            patch_id: Identifier for the forest patch
            
        Returns:
            Complete processing result with all tree analyses
        """
        pass
    
    @abstractmethod
    def is_loaded(self) -> bool:
        """
        Check if ML models are properly loaded.
        
        Returns:
            True if models are loaded and ready for processing
        """
        pass
    
    def validate_image(self, image: np.ndarray) -> bool:
        """
        Validate input image for processing.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            True if image is valid for processing
        """
        if image is None or image.size == 0:
            return False
        
        # Check if image has valid dimensions
        if len(image.shape) not in [2, 3]:
            return False
        
        # Check if image has reasonable size
        height, width = image.shape[:2]
        if height < 100 or width < 100:
            return False
        
        # Check if image has valid data type
        if image.dtype not in [np.uint8, np.float32, np.float64]:
            return False
        
        return True
    
    def crop_tree_region(
        self, 
        image: np.ndarray, 
        detection: TreeDetection,
        padding: int = 20
    ) -> np.ndarray:
        """
        Crop tree region from full image with padding.
        
        Args:
            image: Full drone image
            detection: Tree detection with bounding box
            padding: Additional padding around bounding box
            
        Returns:
            Cropped image region containing the tree
        """
        height, width = image.shape[:2]
        bbox = detection.bbox
        
        # Calculate crop coordinates with padding
        x1 = max(0, bbox.x - padding)
        y1 = max(0, bbox.y - padding)
        x2 = min(width, bbox.x + bbox.width + padding)
        y2 = min(height, bbox.y + bbox.height + padding)
        
        return image[y1:y2, x1:x2]

class GeminiIntegration:
    """Integration with Google Gemini API for enhanced tree analysis."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro-vision"):
        """
        Initialize Gemini integration.
        
        Args:
            api_key: Google AI API key
            model: Gemini model to use
        """
        self.api_key = api_key
        self.model = model
        self.client = None
        
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(model)
            except ImportError:
                print("Warning: google-generativeai not installed. Gemini integration disabled.")
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini client: {e}")
    
    def analyze_tree_health(self, tree_crop: np.ndarray) -> Optional[GeminiResponse]:
        """
        Analyze tree health using Gemini Vision API.
        
        Args:
            tree_crop: Cropped image of individual tree
            
        Returns:
            Gemini analysis response or None if unavailable
        """
        if not self.client:
            return None
        
        try:
            import time
            from PIL import Image
            
            start_time = time.time()
            
            # Convert numpy array to PIL Image
            if tree_crop.dtype != np.uint8:
                tree_crop = (tree_crop * 255).astype(np.uint8)
            
            pil_image = Image.fromarray(tree_crop)
            
            # Prepare prompt for tree health analysis
            prompt = """
            Analyze this aerial view of a tree and determine its health status.
            Consider factors like:
            - Leaf color and density
            - Branch structure
            - Overall canopy appearance
            - Signs of disease or stress
            
            Respond with:
            1. Health status: ALIVE, DEAD, or DISEASED
            2. Confidence level (0-100%)
            3. Brief explanation of your assessment
            
            Format: STATUS|CONFIDENCE|EXPLANATION
            """
            
            response = self.client.generate_content([prompt, pil_image])
            processing_time = time.time() - start_time
            
            # Parse response
            parts = response.text.strip().split('|')
            if len(parts) >= 3:
                status_str = parts[0].strip().upper()
                confidence_str = parts[1].strip().replace('%', '')
                explanation = '|'.join(parts[2:]).strip()
                
                # Map status string to TreeStatus
                from models.data_structures import TreeStatus
                status_mapping = {
                    'ALIVE': TreeStatus.ALIVE,
                    'DEAD': TreeStatus.DEAD,
                    'DISEASED': TreeStatus.DISEASED
                }
                
                suggested_status = status_mapping.get(status_str, TreeStatus.ALIVE)
                confidence = float(confidence_str) / 100.0
                
                return GeminiResponse(
                    analysis=explanation,
                    confidence=confidence,
                    suggested_status=suggested_status,
                    processing_time=processing_time
                )
            
        except Exception as e:
            print(f"Gemini API error: {e}")
        
        return None
    
    def is_available(self) -> bool:
        """Check if Gemini integration is available."""
        return self.client is not None