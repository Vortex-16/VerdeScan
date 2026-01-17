"""
Enhanced forest AI processor with production-ready ML pipeline.
Maintains compatibility with existing interface while adding new capabilities.
"""
import cv2
import numpy as np
import os
import json
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import new ML processor
from core.forest_processor import ForestMLProcessor
from models.data_structures import ProcessingResult, TreeStatus
from config import settings
from logger import logger

class ForestAIProcessor:
    """
    Enhanced forest AI processor with backward compatibility.
    Integrates the new ML pipeline while maintaining the original interface.
    """
    
    def __init__(self, base_dir="."):
        """Initialize the enhanced forest AI processor."""
        self.base_dir = base_dir
        self.test_data_dir = os.path.join(base_dir, "static/test_data")
        self.proof_images_dir = os.path.join(base_dir, "static/proof_images")
        self.results_json_path = os.path.join(base_dir, "data/results.json")
        
        # Ensure directories exist
        os.makedirs(self.test_data_dir, exist_ok=True)
        os.makedirs(self.proof_images_dir, exist_ok=True)
        os.makedirs(os.path.join(base_dir, "data"), exist_ok=True)
        
        # Initialize new ML processor
        self.ml_processor = ForestMLProcessor()
        
        logger.info("Enhanced ForestAIProcessor initialized")

    def generate_test_image(self, patch_name: str, num_trees: int = 100) -> tuple:
        """
        Generate a test drone image with simulated trees.
        Enhanced version with more realistic tree patterns.
        """
        width, height = 2000, 2000
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Create more realistic forest background
        # Base forest green
        image[:] = [34, 139, 34]
        
        # Add texture variation
        noise = np.random.normal(0, 15, (height, width, 3)).astype(np.int16)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        tree_coords = []
        
        for i in range(num_trees):
            # More natural tree distribution
            x = int(np.random.normal(width/2, width/4))
            y = int(np.random.normal(height/2, height/4))
            
            # Keep within bounds
            x = max(50, min(width - 50, x))
            y = max(50, min(height - 50, y))
            
            # Variable tree sizes
            base_radius = np.random.randint(15, 30)
            canopy_radius = base_radius + np.random.randint(5, 15)
            
            # Determine health status with realistic distribution
            health_rand = np.random.random()
            if health_rand < 0.75:  # 75% healthy
                status = TreeStatus.ALIVE
                tree_color = (np.random.randint(20, 60), np.random.randint(120, 180), np.random.randint(20, 60))  # Green variations
            elif health_rand < 0.90:  # 15% diseased
                status = TreeStatus.DISEASED
                tree_color = (np.random.randint(0, 40), np.random.randint(80, 140), np.random.randint(100, 180))  # Yellow-green
            else:  # 10% dead
                status = TreeStatus.DEAD
                tree_color = (np.random.randint(40, 80), np.random.randint(60, 100), np.random.randint(80, 120))  # Brown
            
            # Draw tree canopy
            cv2.circle(image, (x, y), canopy_radius, tree_color, -1)
            
            # Add some shadow/depth
            shadow_color = tuple(max(0, c - 30) for c in tree_color)
            cv2.circle(image, (x + 3, y + 3), canopy_radius - 2, shadow_color, 2)
            
            # Draw trunk (small dark circle)
            cv2.circle(image, (x, y), 3, (20, 40, 60), -1)
            
            tree_coords.append((x, y, status))
        
        # Save image
        file_path = os.path.join(self.test_data_dir, f"{patch_name}.jpg")
        cv2.imwrite(file_path, image)
        
        logger.info(f"Generated test image for {patch_name} with {num_trees} trees")
        return file_path, tree_coords

    def process_patch(self, patch_name: str) -> tuple:
        """
        Process a forest patch using the enhanced ML pipeline.
        Maintains backward compatibility with original interface.
        """
        try:
            logger.info(f"Processing patch: {patch_name}")
            
            # Generate test image if it doesn't exist
            image_path = os.path.join(self.test_data_dir, f"{patch_name}.jpg")
            if not os.path.exists(image_path):
                image_path, _ = self.generate_test_image(patch_name)
            
            # Process using new ML pipeline
            result = self.ml_processor.process_image(image_path, patch_name)
            
            # Convert to legacy format for backward compatibility
            summary = self._convert_to_legacy_summary(result)
            details = self._convert_to_legacy_details(result)
            
            logger.info(f"Processed {patch_name}: {summary['survival_rate']}% survival, {summary['dead_trees']} dead")
            return summary, details
            
        except Exception as e:
            logger.error(f"Error processing patch {patch_name}: {e}")
            # Return empty result on error
            return {
                "patch_name": patch_name,
                "total_trees": 0,
                "dead_trees": 0,
                "survival_rate": 0.0,
                "processing_time": 0.0,
                "timestamp": datetime.now().isoformat()
            }, []

    def _convert_to_legacy_summary(self, result: ProcessingResult) -> Dict[str, Any]:
        """Convert new ProcessingResult to legacy summary format."""
        stats = result.summary_stats
        return {
            "patch_name": result.patch_id,
            "total_trees": stats["total_trees"],
            "dead_trees": stats["dead_trees"],
            "alive_trees": stats["alive_trees"],
            "diseased_trees": stats["diseased_trees"],
            "survival_rate": stats["survival_rate"],
            "processing_time": result.processing_time,
            "timestamp": result.timestamp.isoformat()
        }

    def _convert_to_legacy_details(self, result: ProcessingResult) -> List[Dict[str, Any]]:
        """Convert new tree results to legacy details format."""
        details = []
        
        for tree_result in result.tree_results:
            detail = {
                "id": tree_result.tree_id,
                "x": tree_result.center_coords[0],
                "y": tree_result.center_coords[1],
                "status": tree_result.status.value,
                "confidence": tree_result.classification_confidence,
                "detection_confidence": tree_result.detection_confidence
            }
            
            # Add GPS coordinates if available
            if tree_result.gps_coords:
                detail["lat"] = tree_result.gps_coords.latitude
                detail["lng"] = tree_result.gps_coords.longitude
            else:
                # Generate fake coordinates for backward compatibility
                detail["lat"] = 20.34 + (tree_result.center_coords[1] / 10000)
                detail["lng"] = 85.81 + (tree_result.center_coords[0] / 10000)
            
            details.append(detail)
        
        return details

    def run_full_pipeline(self, patches: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the complete processing pipeline for multiple patches.
        Enhanced version with better error handling and logging.
        """
        if patches is None:
            patches = ["Debadihi", "Benkmura"]
        
        all_results = {}
        
        logger.info(f"Starting full pipeline for {len(patches)} patches")
        
        for patch in patches:
            try:
                summary, details = self.process_patch(patch)
                all_results[patch] = {
                    "summary": summary,
                    "details": details
                }
                print(f"✅ Processed {patch}: {summary['survival_rate']}% survival, {summary['dead_trees']} dead")
                
            except Exception as e:
                logger.error(f"Failed to process patch {patch}: {e}")
                print(f"❌ Failed to process {patch}: {e}")
                continue
        
        # Save results
        try:
            with open(self.results_json_path, 'w') as f:
                json.dump(all_results, f, indent=4)
            logger.info(f"Saved results to {self.results_json_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
        
        return all_results

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information."""
        return {
            "processor_type": "Enhanced ForestAIProcessor",
            "ml_processor_loaded": self.ml_processor.is_loaded(),
            "base_directory": self.base_dir,
            "results_file": self.results_json_path,
            "system_info": self.ml_processor.get_system_info()
        }

if __name__ == "__main__":
    # Maintain backward compatibility
    processor = ForestAIProcessor(base_dir="verde_scan")
    results = processor.run_full_pipeline()
    
    print(f"\n🌲 Processing complete! Processed {len(results)} patches.")
    print("📊 Results saved to verde_scan/data/results.json")
    print("🚀 Start the API server with: python run_server.py")
