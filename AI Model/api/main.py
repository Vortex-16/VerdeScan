from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import json
import os
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

app = FastAPI(
    title="Verde Scan API - Drone Forest Monitoring",
    description="Production-ready API for drone-based forest health monitoring using AI/ML",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure appropriately for production
    )

# Global instances
ml_processor = ForestMLProcessor()
task_manager = TaskManager(ml_processor)

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = settings.static_dir
DATA_DIR = settings.data_dir
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Verde Scan API server...")
    
    # Validate dependencies
    if not ml_processor.is_loaded():
        logger.error("ML processor failed to load")
        raise RuntimeError("ML processor initialization failed")
    
    # Start background task worker
    asyncio.create_task(task_manager.start_worker())
    
    logger.info("Verde Scan API server started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down Verde Scan API server...")
    await task_manager.stop_worker()
    logger.info("Verde Scan API server shutdown complete")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    """Serve the main dashboard page."""
    try:
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            async with aiofiles.open(index_path, "r") as f:
                content = await f.read()
            return content
        return "<h1>Verde Scan Dashboard - Frontend File Not Found</h1>"
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return "<h1>Verde Scan Dashboard - Error Loading Page</h1>"

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        system_info = ml_processor.get_system_info()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": settings.environment,
            "ml_processor": system_info,
            "active_tasks": len(task_manager.active_tasks),
            "queue_size": task_manager.queue.qsize() if hasattr(task_manager.queue, 'qsize') else 0
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )

@app.post("/api/upload-image")
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patch_name: str = Form(...)
):
    """
    Upload drone image for processing.
    
    Args:
        file: Uploaded image file
        patch_name: Name/identifier for the forest patch
        
    Returns:
        Task information for tracking processing status
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
            )
        
        # Check file format
        allowed_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Allowed: {', '.join(allowed_formats)}"
            )
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_dir = os.path.join(DATA_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{task_id}_{file.filename}")
        
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        
        # Submit processing task
        task_status = await task_manager.submit_task(
            task_id=task_id,
            image_path=file_path,
            patch_id=patch_name
        )
        
        logger.info(f"Image upload successful: {file.filename} -> Task {task_id}")
        
        return {
            "task_id": task_id,
            "status": task_status.status,
            "progress": task_status.progress,
            "estimated_time": task_status.estimated_time_remaining,
            "message": "Image uploaded successfully and queued for processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get processing status for a specific task.
    
    Args:
        task_id: Unique task identifier
        
    Returns:
        Current task status and progress information
    """
    try:
        task_status = await task_manager.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        response = {
            "task_id": task_id,
            "status": task_status.status,
            "progress": task_status.progress,
            "created_at": task_status.created_at.isoformat(),
            "updated_at": task_status.updated_at.isoformat()
        }
        
        if task_status.estimated_time_remaining:
            response["estimated_time_remaining"] = task_status.estimated_time_remaining
        
        if task_status.error_message:
            response["error_message"] = task_status.error_message
        
        if task_status.result:
            response["result"] = {
                "patch_id": task_status.result.patch_id,
                "processing_time": task_status.result.processing_time,
                "summary": task_status.result.summary_stats
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")

@app.get("/api/patches")
async def get_patches():
    """Get list of all processed patches."""
    try:
        results_path = os.path.join(DATA_DIR, settings.results_file)
        if not os.path.exists(results_path):
            return []
        
        async with aiofiles.open(results_path, "r") as f:
            content = await f.read()
            data = json.loads(content)
            return list(data.keys())
            
    except Exception as e:
        logger.error(f"Error getting patches: {e}")
        return []

@app.get("/api/patch/{patch_id}")
async def get_patch_data(patch_id: str):
    """Get detailed data for a specific patch."""
    try:
        results_path = os.path.join(DATA_DIR, settings.results_file)
        if not os.path.exists(results_path):
            raise HTTPException(status_code=404, detail="No results found")
        
        async with aiofiles.open(results_path, "r") as f:
            content = await f.read()
            data = json.loads(content)
            
            if patch_id not in data:
                raise HTTPException(status_code=404, detail=f"Patch {patch_id} not found")
            
            return data[patch_id]
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patch data for {patch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get patch data")

@app.get("/api/stats")
async def get_global_stats():
    """Get global statistics across all processed patches."""
    try:
        results_path = os.path.join(DATA_DIR, settings.results_file)
        if not os.path.exists(results_path):
            return {"total_patches": 0}
        
        async with aiofiles.open(results_path, "r") as f:
            content = await f.read()
            data = json.loads(content)
            
            if not data:
                return {"total_patches": 0}
            
            total_patches = len(data)
            total_trees = sum(p.get("summary", {}).get("total_trees", 0) for p in data.values())
            total_dead = sum(p.get("summary", {}).get("dead_trees", 0) for p in data.values())
            total_alive = sum(p.get("summary", {}).get("alive_trees", 0) for p in data.values())
            total_diseased = sum(p.get("summary", {}).get("diseased_trees", 0) for p in data.values())
            
            avg_survival = (total_alive / total_trees * 100) if total_trees > 0 else 0
            
            return {
                "total_patches": total_patches,
                "total_trees": total_trees,
                "total_alive": total_alive,
                "total_dead": total_dead,
                "total_diseased": total_diseased,
                "avg_survival_rate": round(avg_survival, 2),
                "last_updated": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting global stats: {e}")
        return {"total_patches": 0, "error": str(e)}

@app.get("/api/export/{patch_id}")
async def export_patch_csv(patch_id: str):
    """Export patch data as CSV file."""
    try:
        csv_path = await task_manager.data_manager.get_csv_export_path(patch_id)
        if not csv_path or not os.path.exists(csv_path):
            raise HTTPException(status_code=404, detail="CSV export not found")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=csv_path,
            filename=f"results_{patch_id}.csv",
            media_type="text/csv"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting CSV for {patch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export CSV")

@app.post("/api/process-batch")
async def process_batch_images(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    patch_names: List[str] = Form(...)
):
    """
    Process multiple images in batch.
    
    Args:
        files: List of uploaded image files
        patch_names: List of corresponding patch names
        
    Returns:
        List of task IDs for tracking batch processing
    """
    try:
        if len(files) != len(patch_names):
            raise HTTPException(
                status_code=400, 
                detail="Number of files must match number of patch names"
            )
        
        if len(files) > 10:  # Limit batch size
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 files allowed per batch"
            )
        
        task_ids = []
        
        for file, patch_name in zip(files, patch_names):
            # Validate each file
            if not file.filename:
                continue
            
            if file.size and file.size > settings.max_file_size:
                continue
            
            # Generate task ID and save file
            task_id = str(uuid.uuid4())
            upload_dir = os.path.join(DATA_DIR, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, f"{task_id}_{file.filename}")
            
            async with aiofiles.open(file_path, "wb") as f:
                content = await file.read()
                await f.write(content)
            
            # Submit task
            task_status = await task_manager.submit_task(
                task_id=task_id,
                image_path=file_path,
                patch_id=patch_name
            )
            
            task_ids.append({
                "task_id": task_id,
                "filename": file.filename,
                "patch_name": patch_name,
                "status": task_status.status
            })
        
        logger.info(f"Batch processing submitted: {len(task_ids)} tasks")
        
        return {
            "batch_id": str(uuid.uuid4()),
            "tasks": task_ids,
            "message": f"Batch of {len(task_ids)} images submitted for processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@app.get("/api/queue-status")
async def get_queue_status():
    """Get current processing queue status."""
    try:
        return task_manager.get_queue_status()
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return {"error": str(e)}

@app.delete("/api/task/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a pending or processing task.
    
    Args:
        task_id: Task identifier to cancel
        
    Returns:
        Cancellation status
    """
    try:
        task_status = await task_manager.get_task_status(task_id)
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task_status.status in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed or failed task")
        
        # Mark task as cancelled (implementation would depend on specific cancellation logic)
        task_status.status = "cancelled"
        task_status.updated_at = datetime.utcnow()
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancelled successfully"
        }
        
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
        log_level=settings.log_level.lower()
    )
