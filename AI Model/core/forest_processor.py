import cv2
import numpy as np
import os
import time
from datetime import datetime
from typing import List, Optional
import torch
import torch.nn as nn
from torchvision import transforms

from models.ml_processor import MLProcessor
from models.data_structures import (
    TreeDetection, HealthClassification, TreeResult, 
    ProcessingResult, ImageMetadata, TreeStatus, BoundingBox
)
from core.cv_processor import ImageProcessor
from core.forest_monitor import ForestMonitor, GeoPoint
from config import settings
from logger import logger

# --- AI Model Definition ---
class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 56 * 56, 128),
            nn.ReLU(),
            nn.Linear(128, 2)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

class ForestMLProcessor(MLProcessor):
    """Complete ML processor for forest monitoring system using Trained CNN."""
    
    def __init__(self):
        """Initialize the forest ML processor with ForestMonitor + CNN."""
        self.monitor = ForestMonitor()
        self.image_processor = ImageProcessor()
        
        # Load AI Model
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = SimpleCNN().to(self.device)
        self.model_loaded = False
        
        model_path = "ml_models/forest_model.pth"
        if os.path.exists(model_path):
            try:
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.eval()
                self.model_loaded = True
                logger.info(f"✅ Trained AI Model loaded from {model_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load AI model: {e}")
        else:
            logger.warning(f"⚠️ Model not found at {model_path}. Using fallback logic.")

        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        self._is_loaded = True
        logger.info("ForestMLProcessor initialized.")
    
    def detect_trees(self, image: np.ndarray) -> List[TreeDetection]:
        """
        Uses Sliding Window with Trained CNN to find Saplings (Class 1).
        """
        if not self.model_loaded:
            logger.info("Using Fallback OpenCV Detection")
            # Fallback to older OpenCV logic if model missing
            points = self.monitor.detect_features(image, "OP3", datetime.now().year)
            detections = []
            for i, pt in enumerate(points):
                bbox = BoundingBox(pt.pixel_x - 20, pt.pixel_y - 20, 40, 40)
                detections.append(TreeDetection(i, bbox, pt.confidence, (pt.pixel_x, pt.pixel_y)))
            return detections
            
        # AI Model Inference
        h, w, c = image.shape
        stride = 224  # Non-overlapping for speed, or 112 for dense
        detections = []
        tree_id = 0
        
        # Sliding Window 
        # (Simplified: In prod, batch this!)
        logger.info(f"Running AI Inference on {w}x{h} image...")
        
        batch_crops = []
        coords = []
        
        for y in range(0, h - 224, stride):
            for x in range(0, w - 224, stride):
                crop = image[y:y+224, x:x+224]
                crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB) # Model expects RGB
                batch_crops.append(crop)
                coords.append((x, y))
                
                # Batch processing
                if len(batch_crops) >= 16:
                    self._process_batch(batch_crops, coords, detections, tree_id)
                    tree_id += len(batch_crops) # Approximate ID increment
                    batch_crops = []
                    coords = []
                    
        # Process remaining
        if batch_crops:
            self._process_batch(batch_crops, coords, detections, tree_id)
            
        return detections

    def _process_batch(self, crops, coords, detections, start_id):
        tensors = [self.transform(c) for c in crops]
        batch_tensor = torch.stack(tensors).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(batch_tensor)
            probs = torch.softmax(outputs, dim=1)
            preds = torch.argmax(probs, dim=1)
            
        for i, pred in enumerate(preds):
            if pred.item() == 1: # Class 1 = Sapling
                confidence = probs[i][1].item()
                if confidence > 0.5:
                    x, y = coords[i]
                    # Center of the tile
                    cx, cy = x + 112, y + 112
                    bbox = BoundingBox(x, y, 224, 224)
                    detections.append(TreeDetection(
                        tree_id=start_id + i,
                        bbox=bbox,
                        confidence=confidence,
                        center_coords=(cx, cy)
                    ))

    def classify_health(self, tree_crop: np.ndarray, tree_id: int) -> HealthClassification:
        # Since the detector only returns Class 1 (Sapling), 
        # implicitly it is "Alive" or "Present".
        # Future: Train 3-class model (Pit, Healthy, Dead)
        return HealthClassification(
            status=TreeStatus.ALIVE,
            confidence=0.9
        )
    
    def extract_metadata(self, image_path: str) -> ImageMetadata:
        return self.image_processor.extract_metadata(image_path)
    
    def process_image(self, image_path: str, patch_id: str) -> ProcessingResult:
        """Process operation for a single image."""
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
            
            logger.info(f"AI Model found {len(detections)} trees in {processing_time:.2f}s")
            
            return ProcessingResult(
                patch_id=patch_id,
                image_metadata=self.extract_metadata(image_path),
                tree_results=tree_results,
                processing_time=processing_time,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None

    def is_loaded(self) -> bool:
        return self._is_loaded
    
    def get_system_info(self) -> dict:
        return {
            'processor_type': 'CNN ResNet Custom',
            'description': 'Patch-based Sapling Detection',
            'is_loaded': self.model_loaded,
            'device': str(self.device)
        }
