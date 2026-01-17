"""
Asynchronous task management for image processing.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import json
import os

from models.data_structures import TaskStatus as TaskStatusModel, ProcessingResult
from core.forest_processor import ForestMLProcessor
from core.data_manager import DataManager
from config import settings
from logger import logger

class TaskManager:
    """Manage asynchronous image processing tasks."""
    
    def __init__(self, ml_processor: ForestMLProcessor):
        """
        Initialize task manager.
        
        Args:
            ml_processor: ML processor instance for image processing
        """
        self.ml_processor = ml_processor
        self.data_manager = DataManager()
        self.active_tasks: Dict[str, TaskStatusModel] = {}
        self.queue = asyncio.Queue(maxsize=settings.max_concurrent_requests * 2)
        self.worker_running = False
        self.max_concurrent = settings.max_concurrent_requests
        self.processing_semaphore = asyncio.Semaphore(self.max_concurrent)
        
        logger.info(f"TaskManager initialized with max {self.max_concurrent} concurrent tasks")
    
    async def submit_task(
        self, 
        task_id: str, 
        image_path: str, 
        patch_id: str
    ) -> TaskStatusModel:
        """
        Submit a new image processing task.
        
        Args:
            task_id: Unique task identifier
            image_path: Path to the image file
            patch_id: Forest patch identifier
            
        Returns:
            Initial task status
        """
        try:
            # Create initial task status
            task_status = TaskStatusModel(
                task_id=task_id,
                status="pending",
                progress=0.0,
                estimated_time_remaining=settings.processing_timeout,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Store task
            self.active_tasks[task_id] = task_status
            
            # Add to processing queue
            await self.queue.put({
                'task_id': task_id,
                'image_path': image_path,
                'patch_id': patch_id
            })
            
            logger.info(f"Task {task_id} submitted for processing")
            return task_status
            
        except Exception as e:
            logger.error(f"Error submitting task {task_id}: {e}")
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatusModel]:
        """
        Get current status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Current task status or None if not found
        """
        return self.active_tasks.get(task_id)
    
    async def start_worker(self):
        """Start the background worker for processing tasks."""
        if self.worker_running:
            return
        
        self.worker_running = True
        logger.info("Starting task processing worker")
        
        # Start multiple worker coroutines for concurrent processing
        workers = []
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            workers.append(worker)
        
        # Wait for all workers to complete (they run indefinitely)
        await asyncio.gather(*workers, return_exceptions=True)
    
    async def stop_worker(self):
        """Stop the background worker."""
        self.worker_running = False
        logger.info("Stopping task processing worker")
    
    async def _worker_loop(self, worker_name: str):
        """
        Main worker loop for processing tasks.
        
        Args:
            worker_name: Name identifier for this worker
        """
        logger.info(f"Worker {worker_name} started")
        
        while self.worker_running:
            try:
                # Wait for a task with timeout
                try:
                    task_data = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process the task with semaphore to limit concurrency
                async with self.processing_semaphore:
                    await self._process_task(task_data, worker_name)
                
                # Mark task as done in queue
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in worker {worker_name}: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _process_task(self, task_data: Dict[str, Any], worker_name: str):
        """
        Process a single task.
        
        Args:
            task_data: Task information dictionary
            worker_name: Name of the processing worker
        """
        task_id = task_data['task_id']
        image_path = task_data['image_path']
        patch_id = task_data['patch_id']
        
        try:
            logger.info(f"Worker {worker_name} processing task {task_id}")
            
            # Update task status to processing
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "processing"
                self.active_tasks[task_id].progress = 0.1
                self.active_tasks[task_id].updated_at = datetime.utcnow()
            
            # Process image using ML processor
            start_time = datetime.utcnow()
            
            # Run ML processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.ml_processor.process_image, 
                image_path, 
                patch_id
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update progress
            if task_id in self.active_tasks:
                self.active_tasks[task_id].progress = 0.8
                self.active_tasks[task_id].updated_at = datetime.utcnow()
            
            # Save results
            await self.data_manager.save_processing_result(result)
            
            # Update task status to completed
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "completed"
                self.active_tasks[task_id].progress = 1.0
                self.active_tasks[task_id].result = result
                self.active_tasks[task_id].updated_at = datetime.utcnow()
                self.active_tasks[task_id].estimated_time_remaining = None
            
            logger.info(
                f"Task {task_id} completed by {worker_name} in {processing_time:.2f}s"
            )
            
            # Clean up uploaded file
            # Clean up uploaded file (Disabled to allow frontend visualization)
            # try:
            #     if os.path.exists(image_path):
            #         os.remove(image_path)
            # except Exception as e:
            #     logger.warning(f"Failed to clean up uploaded file {image_path}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            
            # Update task status to failed
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "failed"
                self.active_tasks[task_id].error_message = str(e)
                self.active_tasks[task_id].updated_at = datetime.utcnow()
                self.active_tasks[task_id].estimated_time_remaining = None
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        Clean up old completed/failed tasks.
        
        Args:
            max_age_hours: Maximum age of tasks to keep in hours
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            tasks_to_remove = []
            
            for task_id, task_status in self.active_tasks.items():
                if (task_status.status in ["completed", "failed"] and 
                    task_status.updated_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.active_tasks[task_id]
            
            if tasks_to_remove:
                logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
                
        except Exception as e:
            logger.error(f"Error cleaning up old tasks: {e}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status information.
        
        Returns:
            Dictionary with queue status information
        """
        try:
            active_count = len([t for t in self.active_tasks.values() if t.status == "processing"])
            pending_count = len([t for t in self.active_tasks.values() if t.status == "pending"])
            completed_count = len([t for t in self.active_tasks.values() if t.status == "completed"])
            failed_count = len([t for t in self.active_tasks.values() if t.status == "failed"])
            
            return {
                "queue_size": self.queue.qsize() if hasattr(self.queue, 'qsize') else 0,
                "active_tasks": active_count,
                "pending_tasks": pending_count,
                "completed_tasks": completed_count,
                "failed_tasks": failed_count,
                "total_tasks": len(self.active_tasks),
                "max_concurrent": self.max_concurrent,
                "worker_running": self.worker_running
            }
            
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {"error": str(e)}