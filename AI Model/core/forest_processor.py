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

from models.ml_processor import MLProcessor, GeminiIntegration
from models.data_structures import (
    TreeDetection, HealthClassification, TreeResult,
    ProcessingResult, ImageMetadata, TreeStatus, BoundingBox
)
from core.cv_processor import ImageProcessor
from core.forest_monitor import ForestMonitor, GeoPoint
from core.health_classifier import TreeHealthClassifier
from config import settings
from logger import logger


# ---------------------------------------------------------------------------
# Legacy model (V1) — kept for backward-compat with old checkpoints
# ---------------------------------------------------------------------------
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 56 * 56, 128), nn.ReLU(),
            nn.Linear(128, 2),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


def _build_resnet18(num_classes: int) -> nn.Module:
    """ResNet18 pretrained backbone + custom head (matches train_improved.py)."""
    model = tv_models.resnet18(weights=None)
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(512, num_classes),
    )
    return model


def _probe_checkpoint(path: str, device):
    """
    Load the raw state-dict and infer:
      - architecture  ('resnet18' | 'simplecnn')
      - num_classes   (int)
    Returns (arch_str, num_classes).
    """
    sd = torch.load(path, map_location=device, weights_only=True)
    if 'fc.1.weight' in sd:            # ResNet18 with Sequential head
        return 'resnet18', sd['fc.1.weight'].shape[0]
    if 'classifier.3.weight' in sd:    # SimpleCNN
        return 'simplecnn', sd['classifier.3.weight'].shape[0]
    # Unknown — default to SimpleCNN 2-class
    return 'simplecnn', 2


# ---------------------------------------------------------------------------
# Class-index → TreeStatus mappings for each model version
# ---------------------------------------------------------------------------
# V1 SimpleCNN  (pit=0, sapling=1) — 'sapling' is the positive class
_V1_POSITIVE = 1          # pred==1  → detection; health done by HSV classifier

# V2 ResNet18   (alive=0, dead=1, no_sapling=2) — alphabetical ImageFolder order
_V2_STATUS = {
    0: TreeStatus.ALIVE,
    1: TreeStatus.DEAD,
    # 2 = no_sapling → skip
}


class ForestMLProcessor(MLProcessor):
    """
    Complete ML processor for forest monitoring.

    Supports two model generations automatically:

    V1 – SimpleCNN (2-class: pit / sapling)
         Detects sapling-positive tiles, then runs HSV health classifier.

    V2 – ResNet18  (3-class: alive / dead / no_sapling)
         Detects AND classifies health in a single CNN pass.
         Produces more accurate alive/dead counts with no HSV heuristics.
    """

    def __init__(self):
        self.monitor        = ForestMonitor()
        self.image_processor = ImageProcessor()
        self.device         = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_loaded   = False
        self.model_version  = 'none'   # 'v1_simplecnn' | 'v2_resnet18'
        self.num_classes    = 0

        # ------------------------------------------------------------------
        # Locate the model file
        # ------------------------------------------------------------------
        base_dir   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "ml_models", "forest_model.pth")
        if not os.path.exists(model_path):
            model_path = "ml_models/forest_model.pth"

        if os.path.exists(model_path):
            try:
                arch, num_cls = _probe_checkpoint(model_path, self.device)
                self.num_classes = num_cls

                if arch == 'resnet18':
                    self.model = _build_resnet18(num_cls).to(self.device)
                    self.model_version = 'v2_resnet18'
                else:
                    self.model = SimpleCNN().to(self.device)
                    self.model_version = 'v1_simplecnn'

                self.model.load_state_dict(
                    torch.load(model_path, map_location=self.device, weights_only=True)
                )
                self.model.eval()
                self.model_loaded = True
                logger.info(
                    f"[OK] Model loaded: {self.model_version} "
                    f"({num_cls} classes) from {model_path}"
                )
            except Exception as e:
                logger.error(f"[ERR] Failed to load model: {e}")
                self.model = SimpleCNN().to(self.device)
        else:
            logger.warning(f"[WARN] Model not found at {model_path}. Using geometric fallback.")
            self.model = SimpleCNN().to(self.device)

        # ------------------------------------------------------------------
        # Image transform (same for both architectures)
        # ------------------------------------------------------------------
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        # ------------------------------------------------------------------
        # Gemini (optional) + HSV health classifier (used for V1 and geometric)
        # ------------------------------------------------------------------
        gemini = None
        if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here":
            try:
                gemini = GeminiIntegration(settings.gemini_api_key)
                logger.info("Gemini integration enabled")
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")

        self.health_classifier = TreeHealthClassifier(gemini_integration=gemini)

        self._is_loaded = True
        logger.info(
            f"ForestMLProcessor ready | version={self.model_version} | "
            f"device={self.device}"
        )

    # ------------------------------------------------------------------
    # Tree Detection
    # ------------------------------------------------------------------
    def detect_trees(
        self,
        image: np.ndarray,
    ) -> Tuple[List[TreeDetection], List[Optional[Tuple[TreeStatus, float]]]]:
        """
        Sliding-window CNN detection.

        Returns
        -------
        detections : List[TreeDetection]
        health_info : List[Optional[Tuple[TreeStatus, float]]]
            V2 model → each entry is (status, confidence) from the CNN.
            V1 model or geometric → each entry is None (health resolved later by HSV).
        """
        h, w = image.shape[:2]

        if h < 224 or w < 224:
            logger.warning(f"Image {w}×{h} too small for CNN — geometric fallback")
            dets = self._detect_geometric(image)
            return dets, [None] * len(dets)

        if not self.model_loaded:
            logger.info("CNN not loaded — geometric fallback (Hough circles)")
            dets = self._detect_geometric(image)
            return dets, [None] * len(dets)

        stride    = 224
        tree_id   = 0
        is_v2     = (self.model_version == 'v2_resnet18')
        detections: List[TreeDetection] = []
        # V2 collects health from CNN; V1 leaves it None (HSV classifier runs later)
        health_out: Optional[List[Tuple[TreeStatus, float]]] = [] if is_v2 else None

        logger.info(f"CNN sliding-window ({self.model_version}) on {w}×{h}...")

        batch_crops: List[np.ndarray] = []
        coords: List[tuple] = []

        for y in range(0, h - 223, stride):
            for x in range(0, w - 223, stride):
                crop_rgb = cv2.cvtColor(image[y:y + 224, x:x + 224], cv2.COLOR_BGR2RGB)
                batch_crops.append(crop_rgb)
                coords.append((x, y))

                if len(batch_crops) >= 32:
                    self._process_batch(batch_crops, coords, detections,
                                        tree_id, health_out)
                    tree_id += len(batch_crops)
                    batch_crops, coords = [], []

        if batch_crops:
            self._process_batch(batch_crops, coords, detections,
                                tree_id, health_out)

        for idx, det in enumerate(detections):
            det.tree_id = idx

        n = len(detections)
        logger.info(f"CNN found {n} positive tiles")
        # Return parallel health list: real tuples for V2, None sentinels for V1
        h_list = health_out if is_v2 else [None] * n
        return detections, h_list

    def _detect_geometric(self, image: np.ndarray) -> List[TreeDetection]:
        """Fallback: OpenCV Hough-circle / contour detection via ForestMonitor."""
        points = self.monitor.detect_features(image, "OP3", datetime.now().year)
        detections = []
        for i, pt in enumerate(points):
            radius = 20
            bbox = BoundingBox(
                max(0, pt.pixel_x - radius),
                max(0, pt.pixel_y - radius),
                radius * 2,
                radius * 2
            )
            detections.append(TreeDetection(i, bbox, pt.confidence, (pt.pixel_x, pt.pixel_y)))
        # Hough circles can produce near-duplicates — IoU NMS (stride=0) cleans them
        detections = self._apply_nms(detections, iou_threshold=0.1, stride=0)
        logger.info(f"Geometric detection found {len(detections)} features after NMS")
        return detections

    def _process_batch(
        self,
        crops: List[np.ndarray],
        coords: List[tuple],
        detections: List[TreeDetection],
        start_id: int,
        # V2 output: parallel list of (status, conf) per detection, or None for V1
        health_out: Optional[List[Tuple[TreeStatus, float]]] = None,
    ):
        """
        Run a batch through the CNN and collect positive detections.

        V1 (SimpleCNN, 2-class pit/sapling):
            Class 1 (sapling) → detection, health determined later by HSV.

        V2 (ResNet18, 3-class alive/dead/no_sapling):
            Class 0 (alive) or Class 1 (dead) → detection + health in one pass.
            Class 2 (no_sapling) → skip.
        """
        tensors = [self.transform(c) for c in crops]
        batch_tensor = torch.stack(tensors).to(self.device)

        with torch.no_grad():
            outputs = self.model(batch_tensor)
            probs   = torch.softmax(outputs, dim=1)
            preds   = torch.argmax(probs, dim=1)

        thresh = settings.detection_confidence_threshold

        for i, pred in enumerate(preds):
            p = pred.item()

            if self.model_version == 'v2_resnet18':
                # V2: alive=0, dead=1, no_sapling=2
                if p not in _V2_STATUS:
                    continue
                status     = _V2_STATUS[p]
                confidence = probs[i][p].item()
            else:
                # V1: pit=0, sapling=1
                if p != _V1_POSITIVE:
                    continue
                confidence = probs[i][_V1_POSITIVE].item()
                status     = None   # health resolved later by HSV classifier

            if confidence < thresh:
                continue

            x, y = coords[i]
            bbox = BoundingBox(x, y, 224, 224)
            det  = TreeDetection(
                tree_id       = start_id + i,
                bbox          = bbox,
                confidence    = confidence,
                center_coords = (x + 112, y + 112),
            )
            detections.append(det)
            # Only populate health_out for V2 (it is None for V1)
            if health_out is not None and status is not None:
                health_out.append((status, confidence))

    # ------------------------------------------------------------------
    # Detection merging helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _iou(a: BoundingBox, b: BoundingBox) -> float:
        """Intersection-over-Union for two axis-aligned bounding boxes."""
        ix1 = max(a.x, b.x)
        iy1 = max(a.y, b.y)
        ix2 = min(a.x + a.width,  b.x + b.width)
        iy2 = min(a.y + a.height, b.y + b.height)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        union = a.area + b.area - inter
        return inter / union if union > 0 else 0.0

    def _apply_nms(
        self,
        detections: List[TreeDetection],
        iou_threshold: float = 0.3,
        stride: int = 224,
    ) -> List[TreeDetection]:
        """
        Merge detections for the CNN's non-overlapping sliding-window grid.

        Adjacent tiles (8-connected on the stride grid) that both fired are
        merged into one detection via connected-component analysis — the
        highest-confidence tile in each component is kept.  This prevents a
        single plant cluster from being counted multiple times.

        For overlapping-window / geometric detections pass iou_threshold < 1
        and stride=0 to fall back to standard greedy IoU NMS instead.
        """
        if len(detections) <= 1:
            for idx, d in enumerate(detections):
                d.tree_id = idx
            return detections

        # --- Connected-component merge (non-overlapping grid) ---
        if stride > 0:
            # Map each fired grid cell to its best-confidence detection
            grid: dict = {}
            for det in detections:
                gx = det.bbox.x // stride
                gy = det.bbox.y // stride
                if (gx, gy) not in grid or det.confidence > grid[(gx, gy)].confidence:
                    grid[(gx, gy)] = det

            # BFS over 8-connected neighbours to group touching sapling tiles
            visited: set = set()
            kept: List[TreeDetection] = []
            for pos in list(grid.keys()):
                if pos in visited:
                    continue
                component: List[tuple] = []
                queue = [pos]
                while queue:
                    p = queue.pop()
                    if p in visited:
                        continue
                    visited.add(p)
                    if p in grid:
                        component.append(p)
                        gx, gy = p
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                if dx == 0 and dy == 0:
                                    continue
                                nb = (gx + dx, gy + dy)
                                if nb in grid and nb not in visited:
                                    queue.append(nb)
                if component:
                    best = max(component, key=lambda p: grid[p].confidence)
                    kept.append(grid[best])

            for idx, d in enumerate(kept):
                d.tree_id = idx
            return kept

        # --- Standard greedy IoU NMS (overlapping detections / geometric) ---
        sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
        kept_iou: List[TreeDetection] = []
        for det in sorted_dets:
            if all(self._iou(det.bbox, k.bbox) <= iou_threshold for k in kept_iou):
                kept_iou.append(det)
        for idx, d in enumerate(kept_iou):
            d.tree_id = idx
        return kept_iou

    # ------------------------------------------------------------------
    # Health Classification
    # ------------------------------------------------------------------
    def classify_health(self, tree_crop: np.ndarray, tree_id: int) -> HealthClassification:
        """
        Classify tree health using TreeHealthClassifier (HSV colour analysis + optional Gemini).
        Falls back to ALIVE/0.9 if the crop is invalid.
        """
        return self.health_classifier.classify_health(tree_crop, tree_id)

    # ------------------------------------------------------------------
    # Metadata extraction
    # ------------------------------------------------------------------
    def extract_metadata(self, image_path: str) -> ImageMetadata:
        return self.image_processor.extract_metadata(image_path)

    # ------------------------------------------------------------------
    # Main processing entry point
    # ------------------------------------------------------------------
    def process_image(self, image_path: str, patch_id: str) -> Optional[ProcessingResult]:
        """
        Full pipeline: detect trees → classify health → build ProcessingResult.
        Returns None only on fatal errors (caller must handle this).
        """
        _MAX_DIM = 4096  # cap very large orthomosaics to avoid OOM / multi-minute runs

        start_time = time.time()
        try:
            image = cv2.imread(image_path)
            if image is None:
                # Try PIL for formats cv2 can't open (some TIFFs, etc.)
                try:
                    from PIL import Image as _PILImage
                    import PIL
                    PIL.Image.MAX_IMAGE_PIXELS = None
                    pil = _PILImage.open(image_path).convert("RGB")
                    image = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
                except Exception:
                    raise ValueError(f"Could not load image: {image_path}")

            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            h, w = image.shape[:2]
            logger.info(f"Processing {patch_id} | image={w}×{h}")

            # Resize large images — bounding boxes must be in the same coord space
            # as the image used for cropping, so we resize once here for the whole pipeline
            if max(h, w) > _MAX_DIM:
                scale = _MAX_DIM / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
                h, w = image.shape[:2]
                logger.info(f"Downscaled to {w}×{h} for processing (scale={scale:.3f})")

            # 1) Detect trees (returns health info too for V2 model)
            detections, health_info = self.detect_trees(image)
            logger.info(f"Detected {len(detections)} tiles in {patch_id}")

            # 2) Build TreeResult list
            tree_results: List[TreeResult] = []
            for det, h_info in zip(detections, health_info):
                if h_info is not None:
                    # V2 ResNet18: status + confidence already from CNN
                    status, conf = h_info
                    health = HealthClassification(status=status, confidence=round(conf, 3))
                else:
                    # V1 SimpleCNN or geometric: HSV health classifier
                    x1 = max(0, det.bbox.x)
                    y1 = max(0, det.bbox.y)
                    x2 = min(w, det.bbox.x + det.bbox.width)
                    y2 = min(h, det.bbox.y + det.bbox.height)
                    crop = (image[y1:y2, x1:x2]
                            if x2 > x1 and y2 > y1
                            else np.zeros((40, 40, 3), dtype=np.uint8))
                    health = self.classify_health(crop, det.tree_id)

                tree_results.append(
                    TreeResult.from_detection_and_classification(det, health, None)
                )

            processing_time = time.time() - start_time

            alive = sum(1 for r in tree_results if r.status == TreeStatus.ALIVE)
            dead = sum(1 for r in tree_results if r.status == TreeStatus.DEAD)
            diseased = sum(1 for r in tree_results if r.status == TreeStatus.DISEASED)
            logger.info(
                f"{patch_id}: {len(tree_results)} trees | alive={alive} dead={dead} "
                f"diseased={diseased} | {processing_time:.2f}s"
            )

            return ProcessingResult(
                patch_id=patch_id,
                image_metadata=self.extract_metadata(image_path),
                tree_results=tree_results,
                processing_time=processing_time,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}", exc_info=True)
            return None

    def is_loaded(self) -> bool:
        return self._is_loaded

    def get_system_info(self) -> dict:
        arch_label = {
            'v2_resnet18':  'ResNet18 (3-class: alive/dead/no_sapling)',
            'v1_simplecnn': 'SimpleCNN (2-class: pit/sapling)',
            'none':         'No model loaded',
        }.get(self.model_version, self.model_version)
        return {
            'processor_type': f'ForestMLProcessor — {arch_label}',
            'model_version':  self.model_version,
            'num_classes':    self.num_classes,
            'cnn_loaded': self.model_loaded,
            'device': str(self.device),
            'health_classifier': 'TreeHealthClassifier (HSV + Gemini)',
            'fallback': 'Geometric (Hough Circles)',
        }
