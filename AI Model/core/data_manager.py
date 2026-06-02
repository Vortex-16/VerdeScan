"""
Data management for storing and retrieving processing results.
"""
import json
import os
import asyncio
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiofiles

from models.data_structures import ProcessingResult, TreeResult, TreeStatus
from config import settings
from logger import logger

class DataManager:
    """Manage data persistence for processing results."""
    
    def __init__(self):
        """Initialize data manager."""
        self.results_file = os.path.join(settings.data_dir, settings.results_file)
        self.ensure_data_directory()
        self._cache = None
        self._cache_mtime = 0
        self._lock = asyncio.Lock()

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        # Remove directory separators and keep only safe characters
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        sanitized = "".join(c for c in filename if c in safe_chars)
        return sanitized if sanitized else "unnamed_patch"
    
    def ensure_data_directory(self):
        """Ensure all required data directories exist."""
        directories = [
            settings.data_dir,
            os.path.join(settings.data_dir, "patches"),
            os.path.join(settings.data_dir, "exports"),
            os.path.join(settings.data_dir, "cache")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    async def save_processing_result(self, result: ProcessingResult) -> bool:
        """
        Save processing result to persistent storage.
        
        Args:
            result: Processing result to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            async with self._lock:
                # Load existing results
                existing_data = await self._load_results_data()
                
                # Convert result to serializable format
                result_data = self._serialize_processing_result(result)
                
                # Update results
                existing_data[result.patch_id] = result_data
                
                # Save updated results
                async with aiofiles.open(self.results_file, 'w') as f:
                    await f.write(json.dumps(existing_data, indent=2, default=str))
                
                # Invalidate cache after writing
                self._cache = None
                self._cache_mtime = 0
            
            # Save CSV export (can be outside lock as it's per-file)
            await self._save_csv_export(result)
            
            logger.info(f"Saved processing result for patch {result.patch_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving processing result for {result.patch_id}: {e}")
            return False
    
    async def get_patch_data(self, patch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific patch.
        """
        try:
            async with self._lock:
                data = await self._load_results_data()
            return data.get(patch_id)
        except Exception as e:
            logger.error(f"Error getting patch data for {patch_id}: {e}")
            return None
    
    async def get_all_patches(self) -> List[str]:
        """Get list of all patch IDs."""
        try:
            async with self._lock:
                data = await self._load_results_data()
            return list(data.keys())
        except Exception as e:
            logger.error(f"Error getting patch list: {e}")
            return []
    
    async def get_global_statistics(self) -> Dict[str, Any]:
        """Get global statistics across all patches."""
        try:
            async with self._lock:
                data = await self._load_results_data()
            
            if not data:
                return {
                    "total_patches": 0,
                    "total_trees": 0,
                    "total_alive": 0,
                    "total_dead": 0,
                    "total_diseased": 0,
                    "avg_survival_rate": 0.0,
                    "avg_processing_time": 0.0
                }
            
            total_patches = len(data)
            total_trees = 0
            total_alive = 0
            total_dead = 0
            total_diseased = 0
            total_processing_time = 0.0
            
            for patch_data in data.values():
                summary = patch_data.get("summary", {})
                total_trees += summary.get("total_trees", 0)
                total_alive += summary.get("alive_trees", 0)
                total_dead += summary.get("dead_trees", 0)
                total_diseased += summary.get("diseased_trees", 0)
                total_processing_time += patch_data.get("processing_time", 0)
            
            avg_survival_rate = (total_alive / total_trees * 100) if total_trees > 0 else 0.0
            avg_processing_time = total_processing_time / total_patches if total_patches > 0 else 0.0
            
            return {
                "total_patches": total_patches,
                "total_trees": total_trees,
                "total_alive": total_alive,
                "total_dead": total_dead,
                "total_diseased": total_diseased,
                "avg_survival_rate": round(avg_survival_rate, 2),
                "avg_processing_time": round(avg_processing_time, 2),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating global statistics: {e}")
            return {"error": str(e)}

    async def get_all_results(self) -> List[Dict[str, Any]]:
        """Get all processing results, each with patch_id injected inside the object."""
        try:
            async with self._lock:
                data = await self._load_results_data()
                items = list(data.items())  # snapshot while lock is held — prevents dict-changed-during-iteration
            results = []
            for patch_id, patch_data in items:
                entry = dict(patch_data)
                entry["patch_id"] = patch_id
                # Alias: frontend expects 'trees' but we store as 'details'
                if "details" in entry and "trees" not in entry:
                    entry["trees"] = entry["details"]
                results.append(entry)
            return results
        except Exception as e:
            logger.error(f"Error getting all results: {e}")
            return []
    
    async def _load_results_data(self) -> Dict[str, Any]:
        """Load existing results data from file with caching. Must be called while holding self._lock."""
        try:
            if not os.path.exists(self.results_file):
                return {}

            current_mtime = os.path.getmtime(self.results_file)

            # Return cached data if file hasn't changed
            if self._cache is not None and current_mtime <= self._cache_mtime:
                return self._cache

            async with aiofiles.open(self.results_file, 'r') as f:
                content = await f.read()

            try:
                self._cache = json.loads(content)
            except json.JSONDecodeError as exc:
                import shutil
                backup = self.results_file + '.corrupt'
                shutil.copy2(self.results_file, backup)
                logger.error(
                    f"results.json is corrupted ({exc}) — "
                    f"backed up to {backup!r} and starting fresh"
                )
                self._cache = {}

            self._cache_mtime = current_mtime
            return self._cache
        except Exception as e:
            logger.warning(f"Error loading results data: {e}")
            return {}
    
    def _serialize_processing_result(self, result: ProcessingResult) -> Dict[str, Any]:
        """
        Convert ProcessingResult to serializable dictionary.
        
        Args:
            result: Processing result to serialize
            
        Returns:
            Serializable dictionary
        """
        # Convert tree results
        tree_details = []
        for tree_result in result.tree_results:
            tree_data = {
                "tree_id": tree_result.tree_id,
                "bbox": {
                    "x": tree_result.bbox.x,
                    "y": tree_result.bbox.y,
                    "width": tree_result.bbox.width,
                    "height": tree_result.bbox.height
                },
                "center": tree_result.center_coords,
                "status": tree_result.status.value,
                "detection_confidence": tree_result.detection_confidence,
                "classification_confidence": tree_result.classification_confidence
            }
            
            if tree_result.gps_coords:
                tree_data["gps"] = {
                    "lat": tree_result.gps_coords.latitude,
                    "lng": tree_result.gps_coords.longitude
                }
                if tree_result.gps_coords.altitude:
                    tree_data["gps"]["altitude"] = tree_result.gps_coords.altitude
            
            if tree_result.proof_image_path:
                tree_data["proof_image"] = tree_result.proof_image_path
            
            if tree_result.gemini_analysis:
                tree_data["gemini_analysis"] = tree_result.gemini_analysis
            
            tree_details.append(tree_data)
        
        # Create complete result structure
        return {
            "metadata": {
                "patch_id": result.patch_id,
                "filename": result.image_metadata.filename,
                "file_size": result.image_metadata.file_size,
                "dimensions": result.image_metadata.dimensions,
                "format": result.image_metadata.format,
                "processing_time": result.processing_time,
                "timestamp": result.timestamp.isoformat()
            },
            "summary": result.summary_stats,
            "details": tree_details
        }
    
    async def _save_csv_export(self, result: ProcessingResult):
        """
        Save CSV export for the processing result.
        
        Args:
            result: Processing result to export
        """
        try:
            if not result.tree_results:
                return
            
            # Prepare data for CSV
            csv_data = []
            for tree_result in result.tree_results:
                row = {
                    "tree_id": tree_result.tree_id,
                    "x": tree_result.center_coords[0],
                    "y": tree_result.center_coords[1],
                    "status": tree_result.status.value,
                    "detection_confidence": tree_result.detection_confidence,
                    "classification_confidence": tree_result.classification_confidence,
                    "bbox_x": tree_result.bbox.x,
                    "bbox_y": tree_result.bbox.y,
                    "bbox_width": tree_result.bbox.width,
                    "bbox_height": tree_result.bbox.height
                }
                
                if tree_result.gps_coords:
                    row["lat"] = tree_result.gps_coords.latitude
                    row["lng"] = tree_result.gps_coords.longitude
                    if tree_result.gps_coords.altitude:
                        row["altitude"] = tree_result.gps_coords.altitude
                else:
                    row["lat"] = None
                    row["lng"] = None
                    row["altitude"] = None
                
                row["proof_image"] = tree_result.proof_image_path or ""
                row["gemini_analysis"] = tree_result.gemini_analysis or ""
                
                csv_data.append(row)
            
            # Create DataFrame and save asynchronously (avoid blocking event loop)
            df = pd.DataFrame(csv_data)
            safe_patch_id = self._sanitize_filename(result.patch_id)
            csv_path = os.path.join(settings.data_dir, "exports", f"results_{safe_patch_id}.csv")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: df.to_csv(csv_path, index=False))
            
            logger.info(f"Saved CSV export for patch {result.patch_id}")
            
        except Exception as e:
            logger.error(f"Error saving CSV export for {result.patch_id}: {e}")
    
    async def get_csv_export_path(self, patch_id: str) -> Optional[str]:
        """
        Get path to CSV export file for a patch.
        
        Args:
            patch_id: Patch identifier
            
        Returns:
            Path to CSV file or None if not found
        """
        safe_patch_id = self._sanitize_filename(patch_id)
        csv_path = os.path.join(settings.data_dir, "exports", f"results_{safe_patch_id}.csv")
        return csv_path if os.path.exists(csv_path) else None
    
    async def cleanup_old_data(self, max_age_days: int = 30):
        """
        Clean up old data files.
        
        Args:
            max_age_days: Maximum age of data to keep in days
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
            
            # Clean up old CSV exports
            exports_dir = os.path.join(settings.data_dir, "exports")
            if os.path.exists(exports_dir):
                for filename in os.listdir(exports_dir):
                    filepath = os.path.join(exports_dir, filename)
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if file_time < cutoff_time:
                            os.remove(filepath)
                            logger.info(f"Cleaned up old export file: {filename}")
            
            # Clean up cache directory
            cache_dir = os.path.join(settings.data_dir, "cache")
            if os.path.exists(cache_dir):
                for filename in os.listdir(cache_dir):
                    filepath = os.path.join(cache_dir, filename)
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if file_time < cutoff_time:
                            os.remove(filepath)
                            logger.info(f"Cleaned up old cache file: {filename}")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")