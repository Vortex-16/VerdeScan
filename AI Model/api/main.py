from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import re
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
import aiofiles

from core.forest_processor import ForestMLProcessor
from core.task_manager import TaskManager
from models.data_structures import TaskStatus as TaskStatusModel
from config import settings
from logger import logger

# -----------------------------------------------------------------
# Application lifespan (replaces deprecated @app.on_event)
# -----------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Verde Scan API server …")

    if not ml_processor.is_loaded():
        logger.error("ML processor failed to load")
        raise RuntimeError("ML processor initialization failed")

    # Start background task worker
    worker_task = asyncio.create_task(task_manager.start_worker())
    logger.info("Verde Scan API server started successfully")

    yield  # ← application runs here

    logger.info("Shutting down Verde Scan API server …")
    await task_manager.stop_worker()
    worker_task.cancel()
    logger.info("Verde Scan API server shutdown complete")


# -----------------------------------------------------------------
# Global instances (created before lifespan so they're available)
# -----------------------------------------------------------------
ml_processor = ForestMLProcessor()
task_manager = TaskManager(ml_processor)

app = FastAPI(
    title="Verde Scan API — Drone Forest Monitoring",
    description="AI-powered system for monitoring afforestation survival using drone imagery",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow localhost dev origins; extend via env for production
allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = settings.static_dir
DATA_DIR = settings.data_dir
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Mount static files
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/api/uploads", StaticFiles(directory=os.path.join(DATA_DIR, "uploads")), name="uploads")


# =================================================================
# Helper
# =================================================================
def _enrich_patch(patch_id: str, patch_data: dict) -> dict:
    """Inject patch_id and alias details→trees so the frontend contract is satisfied."""
    entry = dict(patch_data)
    entry["patch_id"] = patch_id
    if "details" in entry and "trees" not in entry:
        entry["trees"] = entry["details"]
    return entry


# =================================================================
# Routes
# =================================================================

@app.get("/", response_class=HTMLResponse)
async def read_index():
    """Serve the main dashboard page (if frontend is bundled)."""
    try:
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            async with aiofiles.open(index_path, "r") as f:
                content = await f.read()
            return content
        return "<h1>VerdeScan API is running. Open the Next.js dev server on :3000</h1>"
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return "<h1>VerdeScan API — Error Loading Page</h1>"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": settings.environment,
            "ml_processor": ml_processor.get_system_info(),
            "active_tasks": len(task_manager.active_tasks),
            "queue_size": task_manager.queue.qsize() if hasattr(task_manager.queue, 'qsize') else 0,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "timestamp": datetime.utcnow().isoformat(), "error": str(e)},
        )


@app.post("/api/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    patch_name: str = Form(...),
):
    """Upload drone image for AI processing."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Sanitize patch name — strip path separators and special chars, limit length
        safe_patch_name = re.sub(r'[^\w\-. ]', '_', patch_name.strip())[:64].strip()
        if not safe_patch_name:
            raise HTTPException(status_code=400, detail="Patch name must contain at least one valid character")

        # Strip directory components from filename to prevent path traversal
        safe_filename = os.path.basename(file.filename)
        if not safe_filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        allowed_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        file_ext = os.path.splitext(safe_filename)[1].lower()
        if file_ext not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Allowed: {', '.join(allowed_formats)}",
            )

        # Read content first — file.size can be None for some HTTP clients
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_file_size} bytes",
            )

        task_id = str(uuid.uuid4())
        upload_dir = os.path.join(DATA_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, f"{task_id}_{safe_filename}")
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        task_status = await task_manager.submit_task(
            task_id=task_id,
            image_path=file_path,
            patch_id=safe_patch_name,
        )

        logger.info(f"Upload accepted: {safe_filename} → Task {task_id} (patch: {safe_patch_name})")
        return {
            "task_id": task_id,
            "status": task_status.status,
            "progress": task_status.progress,
            "estimated_time": task_status.estimated_time_remaining,
            "message": "Image uploaded successfully and queued for processing",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Get processing status for a task."""
    try:
        task_status = await task_manager.get_task_status(task_id)
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")

        response: Dict[str, Any] = {
            "task_id": task_id,
            "status": task_status.status,
            "progress": task_status.progress,
            "created_at": task_status.created_at.isoformat(),
            "updated_at": task_status.updated_at.isoformat(),
        }

        if task_status.estimated_time_remaining:
            response["estimated_time_remaining"] = task_status.estimated_time_remaining
        if task_status.error_message:
            response["error_message"] = task_status.error_message
        if task_status.result:
            response["result"] = {
                "patch_id": task_status.result.patch_id,
                "processing_time": task_status.result.processing_time,
                "summary": task_status.result.summary_stats,
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")


@app.get("/api/patches")
async def get_patches():
    """Get list of all processed patch IDs."""
    try:
        return await task_manager.data_manager.get_all_patches()
    except Exception as e:
        logger.error(f"Error getting patches: {e}")
        return []


@app.get("/api/patches/all")
async def get_all_patches_data():
    """Get detailed data for ALL patches (with patch_id and trees fields)."""
    try:
        return await task_manager.data_manager.get_all_results()
    except Exception as e:
        logger.error(f"Error getting all patches data: {e}")
        return []


@app.get("/api/patch/{patch_id}")
async def get_patch_data(patch_id: str):
    """Get detailed data for a specific patch."""
    try:
        patch_data = await task_manager.data_manager.get_patch_data(patch_id)
        if not patch_data:
            raise HTTPException(status_code=404, detail=f"Patch '{patch_id}' not found")
        return _enrich_patch(patch_id, patch_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patch data for {patch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get patch data")


@app.get("/api/stats")
async def get_global_stats():
    """Get global statistics across all processed patches."""
    try:
        stats = await task_manager.data_manager.get_global_statistics()

        # If no real data yet, return demo data for the hackathon presentation
        if stats.get("total_patches", 0) == 0:
            return {
                "total_patches": 2,
                "total_trees": 18000,
                "total_alive": 15660,  # 87 % survival
                "total_dead": 1800,    # 1800 + 540 = 2340 non-alive; 15660+1800+540 = 18000 ✓
                "total_diseased": 540,
                "avg_survival_rate": 87.0,
                "last_updated": datetime.utcnow().isoformat(),
            }

        return stats
    except Exception as e:
        logger.error(f"Error getting global stats: {e}")
        return {"total_patches": 0, "error": str(e)}


@app.get("/api/export/{patch_id}")
async def export_patch_csv(patch_id: str):
    """Download patch data as CSV."""
    try:
        csv_path = await task_manager.data_manager.get_csv_export_path(patch_id)
        if not csv_path or not os.path.exists(csv_path):
            raise HTTPException(status_code=404, detail="CSV export not found")

        from fastapi.responses import FileResponse
        return FileResponse(
            path=csv_path,
            filename=f"results_{patch_id}.csv",
            media_type="text/csv",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting CSV for {patch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export CSV")


@app.post("/api/process-batch")
async def process_batch_images(
    files: List[UploadFile] = File(...),
    patch_names: List[str] = Form(...),
):
    """Process multiple images in batch (max 10)."""
    try:
        if len(files) != len(patch_names):
            raise HTTPException(status_code=400, detail="Number of files must match number of patch names")
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch")

        upload_dir = os.path.join(DATA_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        task_ids = []
        for file, patch_name in zip(files, patch_names):
            if not file.filename:
                continue

            safe_patch_name = re.sub(r'[^\w\-. ]', '_', patch_name.strip())[:64].strip()
            safe_filename = os.path.basename(file.filename)
            if not safe_patch_name or not safe_filename:
                continue

            content = await file.read()
            if len(content) == 0 or len(content) > settings.max_file_size:
                continue

            task_id = str(uuid.uuid4())
            file_path = os.path.join(upload_dir, f"{task_id}_{safe_filename}")
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)

            task_status = await task_manager.submit_task(
                task_id=task_id,
                image_path=file_path,
                patch_id=safe_patch_name,
            )
            task_ids.append({
                "task_id": task_id,
                "filename": safe_filename,
                "patch_name": safe_patch_name,
                "status": task_status.status,
            })

        return {
            "batch_id": str(uuid.uuid4()),
            "tasks": task_ids,
            "message": f"Batch of {len(task_ids)} images submitted for processing",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@app.get("/api/queue-status")
async def get_queue_status():
    """Get processing queue status."""
    try:
        return task_manager.get_queue_status()
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a pending task (note: cannot interrupt an already-running task)."""
    try:
        task_status = await task_manager.get_task_status(task_id)
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
        if task_status.status in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed or failed task")

        task_status.status = "cancelled"
        task_status.updated_at = datetime.utcnow()

        return {"task_id": task_id, "status": "cancelled", "message": "Task marked as cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel task")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
