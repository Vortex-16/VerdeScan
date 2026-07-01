import cv2
import numpy as np
import os
import time
from datetime import datetime
from typing import List, Optional, Tuple
import torch
import torch.nn as nn
import torchvision.models as tv_models
from torchvision import transforms

from models.data_structures import (
    TreeDetection, HealthClassification, TreeResult,
    ProcessingResult, ImageMetadata, TreeStatus, BoundingBox
)
from core.cv_processor import ImageProcessor
from config import settings
from logger import logger

def _build_resnet18(num_classes: int) -> nn.Module:
    model = tv_models.resnet18(weights=None)
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(512, num_classes),
    )
    return model

_V2_STATUS = {
    0: TreeStatus.ALIVE,
    1: TreeStatus.DEAD,
}

class ForestMLProcessor:
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_loaded = False
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "ml_models", "forest_model.pth")
        
        if os.path.exists(model_path):
            try:
                sd = torch.load(model_path, map_location=self.device, weights_only=True)
                num_cls = sd['fc.1.weight'].shape[0] if 'fc.1.weight' in sd else 3
                self.model = _build_resnet18(num_cls).to(self.device)
                self.model.load_state_dict(sd)
                self.model.eval()
                self.model_loaded = True
                logger.info(f"[OK] Model loaded: ResNet18 ({num_cls} classes) from {model_path}")
            except Exception as e:
                logger.error(f"[ERR] Failed to load model: {e}")
        else:
            logger.error(f"[ERR] Model not found at {model_path}. Failing explicitly.")

        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        self._is_loaded = True

    def detect_trees(self, image: np.ndarray) -> Tuple[List[TreeDetection], List[Tuple[TreeStatus, float]]]:
        if not self.model_loaded:
            raise RuntimeError("Cannot process image: ML model is not loaded. ponytail: removed hough circle geometric fallback.")

        h, w = image.shape[:2]
        stride = 224
        tree_id = 0
        detections: List[TreeDetection] = []
        health_out: List[Tuple[TreeStatus, float]] = []

        batch_crops = []
        coords = []

        for y in range(0, h - 223, stride):
            for x in range(0, w - 223, stride):
                crop_rgb = cv2.cvtColor(image[y:y + 224, x:x + 224], cv2.COLOR_BGR2RGB)
                batch_crops.append(crop_rgb)
                coords.append((x, y))

                if len(batch_crops) >= 32:
                    self._process_batch(batch_crops, coords, detections, tree_id, health_out)
                    tree_id += len(batch_crops)
                    batch_crops, coords = [], []

        if batch_crops:
            self._process_batch(batch_crops, coords, detections, tree_id, health_out)

        for idx, det in enumerate(detections):
            det.tree_id = idx

        return detections, health_out

    def _process_batch(self, crops, coords, detections, start_id, health_out):
        tensors = [self.transform(c) for c in crops]
        batch_tensor = torch.stack(tensors).to(self.device)

        with torch.no_grad():
            outputs = self.model(batch_tensor)
            probs = torch.softmax(outputs, dim=1)
            preds = torch.argmax(probs, dim=1)

        thresh = settings.detection_confidence_threshold

        for i, pred in enumerate(preds):
            p = pred.item()
            if p not in _V2_STATUS:
                continue
                
            status = _V2_STATUS[p]
            confidence = probs[i][p].item()
            if confidence < thresh:
                continue

            x, y = coords[i]
            bbox = BoundingBox(x, y, 224, 224)
            det = TreeDetection(
                tree_id=start_id + i,
                bbox=bbox,
                confidence=confidence,
                center_coords=(x + 112, y + 112),
            )
            detections.append(det)
            health_out.append((status, confidence))

    def process_image(self, image_path: str, patch_id: str) -> Optional[ProcessingResult]:
        _MAX_DIM = 4096
        start_time = time.time()
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            h, w = image.shape[:2]
            if max(h, w) > _MAX_DIM:
                scale = _MAX_DIM / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

            detections, health_info = self.detect_trees(image)

            tree_results = []
            for det, h_info in zip(detections, health_info):
                status, conf = h_info
                health = HealthClassification(status=status, confidence=round(conf, 3))
                tree_results.append(TreeResult.from_detection_and_classification(det, health, None))

            processing_time = time.time() - start_time
            return ProcessingResult(
                patch_id=patch_id,
                image_metadata=self.image_processor.extract_metadata(image_path),
                tree_results=tree_results,
                processing_time=processing_time,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}", exc_info=True)
            return None

    def is_loaded(self) -> bool:
        return self._is_loaded

    def predict_crop(self, bgr_image: np.ndarray) -> Tuple[str, float]:
        if not self.model_loaded:
            return "dead", 0.0
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        tensor = self.transform(rgb).unsqueeze(0).to(self.device)
        with torch.no_grad():
            outputs = self.model(tensor)
            probs = torch.softmax(outputs, dim=1)
            pred = torch.argmax(probs, dim=1).item()
            
        # 0: alive, 1: dead
        status = "alive" if pred == 0 else "dead"
        conf = probs[0][pred].item()
        return status, conf

    def classify_health(self, tree_crop: np.ndarray, tree_id: int) -> HealthClassification:
        raise NotImplementedError("CNN outputs health directly")

    def extract_metadata(self, image_path: str) -> ImageMetadata:
        return self.image_processor.extract_metadata(image_path)

    def get_system_info(self) -> dict:
        return {
            'processor_type': 'ForestMLProcessor — ResNet18',
            'cnn_loaded': self.model_loaded,
            'device': str(self.device),
        }
