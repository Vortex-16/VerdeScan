import sqlite3
import json
import os
import re
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from models.data_structures import ProcessingResult
from config import settings
from logger import logger

class DataManager:
    """Manage data persistence for processing results. ponytail: replaced custom JSON lock with sqlite3 stdlib."""
    
    def __init__(self):
        os.makedirs(settings.data_dir, exist_ok=True)
        os.makedirs(os.path.join(settings.data_dir, "exports"), exist_ok=True)
        self.db_path = os.path.join(settings.data_dir, "results.db")
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS results (patch_id TEXT PRIMARY KEY, data TEXT)')
                            
    def _execute(self, query: str, args: tuple = (), fetch: bool = False, fetchall: bool = False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, args)
            if fetch:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            conn.commit()
            
    async def save_processing_result(self, result: ProcessingResult) -> bool:
        try:
            data_dict = self._serialize_processing_result(result)
            data_json = json.dumps(data_dict)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._execute, 
                'INSERT OR REPLACE INTO results (patch_id, data) VALUES (?, ?)', 
                (result.patch_id, data_json))
            await self._save_csv_export(result)
            logger.info(f"Saved processing result for patch {result.patch_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving processing result for {result.patch_id}: {e}")
            return False
            
    async def get_patch_data(self, patch_id: str) -> Optional[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        row = await loop.run_in_executor(None, self._execute, 
            'SELECT data FROM results WHERE patch_id = ?', (patch_id,), True)
        return json.loads(row[0]) if row else None
        
    async def get_all_patches(self) -> List[str]:
        loop = asyncio.get_running_loop()
        rows = await loop.run_in_executor(None, self._execute, 
            'SELECT patch_id FROM results', (), False, True)
        return [r[0] for r in rows] if rows else []

    async def get_all_results(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        rows = await loop.run_in_executor(None, self._execute, 
            'SELECT patch_id, data FROM results', (), False, True)
        results = []
        for patch_id, data_str in rows:
            entry = json.loads(data_str)
            entry["patch_id"] = patch_id
            if "details" in entry and "trees" not in entry:
                entry["trees"] = entry["details"]
            results.append(entry)
        return results

    async def get_global_statistics(self) -> Dict[str, Any]:
        results = await self.get_all_results()
        if not results:
            return { "total_patches": 0, "total_trees": 0, "total_alive": 0, "total_dead": 0, "total_diseased": 0, "avg_survival_rate": 0.0, "avg_processing_time": 0.0 }
        
        total_trees = total_alive = total_dead = total_diseased = 0
        total_time = 0.0
        
        for p in results:
            s = p.get("summary", {})
            total_trees += s.get("total_trees", 0)
            total_alive += s.get("alive_trees", 0)
            total_dead += s.get("dead_trees", 0)
            total_diseased += s.get("diseased_trees", 0)
            total_time += p.get("metadata", {}).get("processing_time", 0)
            
        avg_survival = (total_alive / total_trees * 100) if total_trees > 0 else 0.0
        return {
            "total_patches": len(results),
            "total_trees": total_trees,
            "total_alive": total_alive,
            "total_dead": total_dead,
            "total_diseased": total_diseased,
            "avg_survival_rate": round(avg_survival, 2),
            "avg_processing_time": round(total_time / len(results), 2) if results else 0,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _serialize_processing_result(self, result: ProcessingResult) -> Dict[str, Any]:
        tree_details = []
        for t in result.tree_results:
            tree_data = {
                "tree_id": t.tree_id,
                "bbox": {"x": t.bbox.x, "y": t.bbox.y, "width": t.bbox.width, "height": t.bbox.height},
                "center": t.center_coords,
                "status": t.status.value,
                "detection_confidence": t.detection_confidence,
                "classification_confidence": t.classification_confidence
            }
            if t.gps_coords:
                tree_data["gps"] = {"lat": t.gps_coords.latitude, "lng": t.gps_coords.longitude}
            tree_details.append(tree_data)
        
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
        if not result.tree_results:
            return
        import csv
        safe_patch_id = re.sub(r'[^\w\-. ]', '_', result.patch_id).strip() or "unnamed"
        csv_path = os.path.join(settings.data_dir, "exports", f"results_{safe_patch_id}.csv")
        data = []
        for t in result.tree_results:
            row = {
                "tree_id": t.tree_id, "x": t.center_coords[0], "y": t.center_coords[1],
                "status": t.status.value, "detection_confidence": t.detection_confidence,
                "bbox_x": t.bbox.x, "bbox_y": t.bbox.y,
                "lat": t.gps_coords.latitude if t.gps_coords else None,
                "lng": t.gps_coords.longitude if t.gps_coords else None
            }
            data.append(row)
        def _write():
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _write)

    async def get_csv_export_path(self, patch_id: str) -> Optional[str]:
        safe_patch_id = re.sub(r'[^\w\-. ]', '_', patch_id).strip() or "unnamed"
        csv_path = os.path.join(settings.data_dir, "exports", f"results_{safe_patch_id}.csv")
        return csv_path if os.path.exists(csv_path) else None

    async def cleanup_old_data(self, max_age_days: int = 30):
        pass # ponytail: skip background GC for exports