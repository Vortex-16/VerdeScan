"""
Tree health classification system using computer vision and ML techniques.
"""
import cv2
import numpy as np
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import time

from models.data_structures import (
    HealthClassification, TreeStatus, TreeDetection, GeminiResponse
)
from models.ml_processor import GeminiIntegration
from config import settings
from logger import logger

class TreeHealthClassifier:
    """Classify tree health status using computer vision and ML techniques."""
    
    def __init__(self, gemini_integration: Optional[GeminiIntegration] = None):
        """
        Initialize tree health classifier.
        
        Args:
            gemini_integration: Optional Gemini API integration for enhanced analysis
        """
        self.gemini = gemini_integration
        self.confidence_threshold = settings.classification_confidence_threshold
        
        # Color ranges for health classification (HSV)
        # Healthy green foliage
        self.healthy_green_range = {
            'lower': np.array([35, 40, 40]),
            'upper': np.array([85, 255, 255])
        }

        # Dead / bare-soil — broader saturation min (was 50→30) and wider hue (was 10-25→5-25)
        self.dead_brown_range = {
            'lower': np.array([5, 30, 20]),
            'upper': np.array([25, 255, 200])
        }

        # Diseased / yellowing — lower saturation min (was 100→30), wider hue (was 20-35→20-45)
        self.diseased_yellow_range = {
            'lower': np.array([20, 30, 80]),
            'upper': np.array([45, 255, 255])
        }

        # Stressed / pale-green foliage (low saturation green = water stress / early disease)
        self.stressed_green_range = {
            'lower': np.array([35, 15, 50]),
            'upper': np.array([85, 55, 200])
        }
    
    def classify_health(self, tree_crop: np.ndarray, tree_id: int) -> HealthClassification:
        """
        Classify tree health status from cropped image.
        
        Args:
            tree_crop: Cropped image of individual tree
            tree_id: Unique identifier for the tree
            
        Returns:
            Health classification with status and confidence
        """
        try:
            if tree_crop is None or tree_crop.size == 0:
                return HealthClassification(
                    status=TreeStatus.ALIVE,
                    confidence=0.0
                )
            
            # Primary classification using computer vision
            cv_status, cv_confidence = self._classify_with_cv(tree_crop)
            
            # Enhanced classification with Gemini if available
            gemini_response = None
            if self.gemini and self.gemini.is_available():
                gemini_response = self.gemini.analyze_tree_health(tree_crop)
            
            # Combine results
            final_status, final_confidence = self._combine_classifications(
                cv_status, cv_confidence, gemini_response
            )
            
            # Save proof image if tree is dead or diseased
            proof_image_path = None
            if final_status in [TreeStatus.DEAD, TreeStatus.DISEASED]:
                proof_image_path = self._save_proof_image(tree_crop, tree_id, final_status)
            
            return HealthClassification(
                status=final_status,
                confidence=final_confidence,
                gemini_analysis=gemini_response.analysis if gemini_response else None,
                proof_image_path=proof_image_path
            )
            
        except Exception as e:
            logger.error(f"Error in health classification for tree {tree_id}: {e}")
            return HealthClassification(
                status=TreeStatus.ALIVE,
                confidence=0.0
            )
    
    def _classify_with_cv(self, tree_crop: np.ndarray) -> Tuple[TreeStatus, float]:
        """
        Classify tree health using computer vision techniques.
        
        Args:
            tree_crop: Cropped tree image
            
        Returns:
            Tuple of (status, confidence)
        """
        try:
            # Convert to HSV for better color analysis
            if len(tree_crop.shape) == 3:
                hsv = cv2.cvtColor(tree_crop, cv2.COLOR_BGR2HSV)
            else:
                # Convert grayscale to HSV
                bgr = cv2.cvtColor(tree_crop, cv2.COLOR_GRAY2BGR)
                hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            
            # Calculate color percentages
            total_pixels = hsv.shape[0] * hsv.shape[1]
            
            # Healthy green pixels
            green_mask = cv2.inRange(hsv, self.healthy_green_range['lower'], self.healthy_green_range['upper'])
            green_percentage = cv2.countNonZero(green_mask) / total_pixels

            # Dead brown pixels
            brown_mask = cv2.inRange(hsv, self.dead_brown_range['lower'], self.dead_brown_range['upper'])
            brown_percentage = cv2.countNonZero(brown_mask) / total_pixels

            # Diseased / yellowing pixels
            yellow_mask = cv2.inRange(hsv, self.diseased_yellow_range['lower'], self.diseased_yellow_range['upper'])
            yellow_percentage = cv2.countNonZero(yellow_mask) / total_pixels

            # Stressed / pale-green pixels (low saturation green = early disease or water stress)
            stressed_mask = cv2.inRange(hsv, self.stressed_green_range['lower'], self.stressed_green_range['upper'])
            stressed_percentage = cv2.countNonZero(stressed_mask) / total_pixels

            # Per-pixel mean brightness and saturation
            brightness = float(np.mean(hsv[:, :, 2]))
            saturation = float(np.mean(hsv[:, :, 1]))

            # --- Decision tree ---

            # ALIVE: substantial saturated green present
            if green_percentage > 0.25 and brightness > 60 and saturation > 40:
                confidence = round(
                    min(0.92, 0.55 + green_percentage * 0.25
                        + saturation / 255 * 0.10
                        + brightness / 255 * 0.07),
                    3,
                )
                return TreeStatus.ALIVE, confidence

            # DEAD: dominated by brown OR very dark with almost no green
            elif brown_percentage > 0.25 or (brightness < 45 and green_percentage < 0.10):
                confidence = round(
                    min(0.92, 0.55 + brown_percentage * 0.25
                        + (1 - brightness / 255) * 0.07),
                    3,
                )
                return TreeStatus.DEAD, confidence

            # DISEASED: yellowing foliage OR stressed pale-green cover
            elif yellow_percentage > 0.10 or stressed_percentage > 0.20:
                combined = max(yellow_percentage, stressed_percentage)
                confidence = round(min(0.85, 0.55 + combined * 0.20), 3)
                return TreeStatus.DISEASED, confidence

            # Low-confidence ALIVE: mixed scene, some green present but not dominant
            else:
                confidence = round(0.55 + green_percentage * 0.10, 3)
                return TreeStatus.ALIVE, confidence
                
        except Exception as e:
            logger.warning(f"Error in CV classification: {e}")
            return TreeStatus.ALIVE, 0.5
    
    def _combine_classifications(
        self, 
        cv_status: TreeStatus, 
        cv_confidence: float,
        gemini_response: Optional[GeminiResponse]
    ) -> Tuple[TreeStatus, float]:
        """
        Combine computer vision and Gemini classifications.
        
        Args:
            cv_status: CV classification status
            cv_confidence: CV classification confidence
            gemini_response: Optional Gemini response
            
        Returns:
            Tuple of (final_status, final_confidence)
        """
        if not gemini_response:
            return cv_status, cv_confidence
        
        try:
            # Weight the classifications
            cv_weight = 0.4
            gemini_weight = 0.6
            
            # If both agree, increase confidence
            if cv_status == gemini_response.suggested_status:
                combined_confidence = min(0.95, cv_confidence * cv_weight + gemini_response.confidence * gemini_weight + 0.1)
                return cv_status, combined_confidence
            
            # If they disagree, use the one with higher confidence
            if gemini_response.confidence > cv_confidence:
                # Trust Gemini more, but reduce confidence due to disagreement
                final_confidence = gemini_response.confidence * 0.8
                return gemini_response.suggested_status, final_confidence
            else:
                # Trust CV more, but reduce confidence due to disagreement
                final_confidence = cv_confidence * 0.8
                return cv_status, final_confidence
                
        except Exception as e:
            logger.warning(f"Error combining classifications: {e}")
            return cv_status, cv_confidence
    
    def _save_proof_image(
        self, 
        tree_crop: np.ndarray, 
        tree_id: int, 
        status: TreeStatus
    ) -> Optional[str]:
        """
        Save proof image for dead or diseased trees.
        
        Args:
            tree_crop: Cropped tree image
            tree_id: Tree identifier
            status: Tree health status
            
        Returns:
            Path to saved proof image or None if failed
        """
        try:
            # Single flat directory — keyed by status, filename includes tree_id + timestamp
            proof_dir = os.path.join(settings.static_dir, "proof_images")
            os.makedirs(proof_dir, exist_ok=True)

            # Generate filename
            status_str = status.value.lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{status_str}_{tree_id:03d}_{timestamp}.jpg"
            filepath = os.path.join(proof_dir, filename)
            
            # Save image
            success = cv2.imwrite(filepath, tree_crop)
            
            if success:
                # Return POSIX-style relative path for URL serving (/static/proof_images/...)
                relative_path = Path(filepath).relative_to(settings.static_dir).as_posix()
                logger.info(f"Saved proof image: {relative_path}")
                return relative_path
            else:
                logger.error(f"Failed to save proof image: {filepath}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving proof image for tree {tree_id}: {e}")
            return None
    
    def get_health_statistics(self, tree_crops: list) -> dict:
        """
        Get health statistics for a batch of tree crops.
        
        Args:
            tree_crops: List of cropped tree images
            
        Returns:
            Dictionary with health statistics
        """
        if not tree_crops:
            return {
                'total_trees': 0,
                'alive_count': 0,
                'dead_count': 0,
                'diseased_count': 0,
                'average_confidence': 0.0
            }
        
        status_counts = {status: 0 for status in TreeStatus}
        total_confidence = 0.0
        
        for i, crop in enumerate(tree_crops):
            classification = self.classify_health(crop, i)
            status_counts[classification.status] += 1
            total_confidence += classification.confidence
        
        total_trees = len(tree_crops)
        average_confidence = total_confidence / total_trees if total_trees > 0 else 0.0
        
        return {
            'total_trees': total_trees,
            'alive_count': status_counts[TreeStatus.ALIVE],
            'dead_count': status_counts[TreeStatus.DEAD],
            'diseased_count': status_counts[TreeStatus.DISEASED],
            'average_confidence': round(average_confidence, 3)
        }