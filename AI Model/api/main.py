from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import re
import uuid
import tempfile
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
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

# CORS — always allow localhost dev origins; add production origins from the
# CORS_ORIGINS env var (comma-separated) so the deployed frontend (Render/Vercel)
# is not blocked. A lone "*" disables credentialed wildcard correctly.
allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
extra = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
allowed_origins.extend(o for o in extra if o not in allowed_origins)
use_wildcard = "*" in extra
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if use_wildcard else allowed_origins,
    # Credentials cannot be combined with a "*" origin per the CORS spec.
    allow_credentials=not use_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base paths
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # → AI Model/
REPO_DIR  = os.path.dirname(BASE_DIR)                                     # → VerdeScan/
STATIC_DIR = settings.static_dir
DATA_DIR = settings.data_dir
FRONTEND_DIR = os.path.join(REPO_DIR, "frontend")


def _pid_alive(pid: int) -> bool:
    """Cross-platform 'is this process still running?' check."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # NB: os.kill(pid, 0) on Windows TERMINATES the process — never use it.
        # Query liveness via OpenProcess + GetExitCodeProcess instead.
        import ctypes
        from ctypes import wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True   # exists but owned by another user
    return True


def _pipeline_running(flag_path: str) -> bool:
    """
    A site is genuinely running only if its `_running` flag exists AND the
    server process that created it is still alive. A flag whose owner PID is
    dead (server crashed/killed mid-run, so the cleanup `finally` never fired)
    is stale — we delete it and report not-running, so the site self-heals
    instead of being stuck on 'running' forever.
    """
    if not os.path.exists(flag_path):
        return False
    try:
        pid = int(Path(flag_path).read_text().strip() or "-1")
    except (ValueError, OSError):
        pid = -1
    if _pid_alive(pid):
        return True
    # Stale flag — owner gone. Clean it up and treat as not running.
    try:
        os.remove(flag_path)
    except OSError:
        pass
    return False

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


def _extract_gps_exif(image_bytes: bytes) -> Optional[Tuple[float, float]]:
    """
    Extract GPS coordinates from JPEG/TIFF EXIF data.
    Returns (lat, lon) in decimal degrees, or None if absent.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        import io

        img = Image.open(io.BytesIO(image_bytes))
        exif_data = img._getexif()
        if not exif_data:
            return None

        gps_info = None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                gps_info = {GPSTAGS.get(k, k): v for k, v in value.items()}
                break

        if not gps_info:
            return None

        def _dms_to_dd(dms, ref: str) -> float:
            d, m, s = dms
            # Pillow may return IFDRational or tuples — normalise to float
            d = float(d.numerator) / float(d.denominator) if hasattr(d, 'numerator') else float(d)
            m = float(m.numerator) / float(m.denominator) if hasattr(m, 'numerator') else float(m)
            s = float(s.numerator) / float(s.denominator) if hasattr(s, 'numerator') else float(s)
            dd = d + m / 60.0 + s / 3600.0
            return -dd if ref in ("S", "W") else dd

        lat = _dms_to_dd(gps_info["GPSLatitude"],  gps_info.get("GPSLatitudeRef",  "N"))
        lon = _dms_to_dd(gps_info["GPSLongitude"], gps_info.get("GPSLongitudeRef", "E"))
        return lat, lon
    except Exception:
        return None


# In-memory survey log: maps site → list of survey entries
# Each entry: {task_id, patch_id, lat, lon, uploaded_at}
# Persisted to disk so survey points survive server restarts.
_site_surveys: Dict[str, List[Dict[str, Any]]] = {}
_SURVEYS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "data", "site_surveys.json")


def _load_surveys():
    """Load persisted survey points from disk on startup."""
    global _site_surveys
    try:
        if os.path.exists(_SURVEYS_FILE):
            with open(_SURVEYS_FILE) as f:
                _site_surveys = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load site_surveys.json: {e}")


def _save_surveys():
    """Persist survey points to disk."""
    try:
        os.makedirs(os.path.dirname(_SURVEYS_FILE), exist_ok=True)
        with open(_SURVEYS_FILE, "w") as f:
            json.dump(_site_surveys, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Could not save site_surveys.json: {e}")


_load_surveys()


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
    site: Optional[str] = Form(default=None),
):
    """Upload drone image for AI processing. Optional 'site' links the image to the ortho site."""
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

        # Extract GPS from EXIF (best-effort — no error if absent)
        gps = _extract_gps_exif(content)

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

        # Register as a survey point if a site was specified
        valid_sites = {"benkmura", "debadihi"}
        safe_site = site.strip().lower() if site else None
        if safe_site and safe_site in valid_sites and gps:
            _site_surveys.setdefault(safe_site, []).append({
                "task_id": task_id,
                "patch_id": safe_patch_name,
                "lat": gps[0],
                "lon": gps[1],
                "uploaded_at": datetime.utcnow().isoformat(),
            })
            _save_surveys()  # persist immediately
            logger.info(f"Survey point registered for {safe_site}: {gps}")

        logger.info(f"Upload accepted: {safe_filename} → Task {task_id} (patch: {safe_patch_name}, site: {safe_site}, gps: {gps})")
        return {
            "task_id": task_id,
            "status": task_status.status,
            "progress": task_status.progress,
            "estimated_time": task_status.estimated_time_remaining,
            "message": "Image uploaded successfully and queued for processing",
            "camera_gps": {"lat": gps[0], "lon": gps[1]} if gps else None,
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
    """Get global statistics — merges uploaded-patch results with ortho site results."""
    try:
        stats = await task_manager.data_manager.get_global_statistics()

        # Pull ortho site results to augment/replace the counts
        ortho_trees = 0
        ortho_alive = 0
        ortho_dead  = 0
        ortho_sites = 0
        valid_sites = ["benkmura", "debadihi"]
        for site in valid_sites:
            geojson_path = os.path.join(BASE_DIR, "results", site, f"{site}_all_detections.geojson")
            if not os.path.exists(geojson_path):
                continue
            try:
                with open(geojson_path) as f:
                    features = json.load(f).get("features", [])
                alive = sum(1 for x in features if x["properties"]["status"] == "alive")
                dead  = sum(1 for x in features if x["properties"]["status"] == "dead")
                ortho_trees += alive + dead
                ortho_alive += alive
                ortho_dead  += dead
                ortho_sites += 1
            except Exception:
                pass

        if ortho_sites > 0:
            total_alive = ortho_alive + stats.get("total_alive", 0)
            total_dead  = ortho_dead  + stats.get("total_dead",  0)
            total_trees = ortho_trees + stats.get("total_trees", 0)
            survival    = round(total_alive / total_trees * 100, 1) if total_trees else 0.0
            return {
                "total_patches":   ortho_sites + stats.get("total_patches", 0),
                "total_trees":     total_trees,
                "total_alive":     total_alive,
                "total_dead":      total_dead,
                "total_diseased":  stats.get("total_diseased", 0),
                "avg_survival_rate": survival,
                "last_updated":    datetime.utcnow().isoformat(),
            }

        # No ortho data and no uploaded patches — return honest zeros, not demo
        # numbers. (Fabricated stats previously masked an empty system and would
        # mislead a judge into thinking 18,000 trees had been analysed.)
        if stats.get("total_patches", 0) == 0:
            return {
                "total_patches": 0,
                "total_trees": 0,
                "total_alive": 0,
                "total_dead": 0,
                "total_diseased": 0,
                "avg_survival_rate": 0.0,
                "last_updated": datetime.utcnow().isoformat(),
                "message": "No analyses yet — run the ortho pipeline or upload imagery.",
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


@app.get("/api/site-surveys/{site}")
async def get_site_surveys(site: str):
    """
    Return all uploaded-image survey points for a site.
    Each entry includes camera GPS + AI tree-count summary from that image.
    """
    valid_sites = {"benkmura", "debadihi"}
    if site not in valid_sites:
        raise HTTPException(status_code=400, detail=f"Unknown site: {site}")

    surveys = _site_surveys.get(site, [])
    enriched = []
    for s in surveys:
        entry = dict(s)
        # Attach AI result summary if available
        patch_data = await task_manager.data_manager.get_patch_data(s["patch_id"])
        if patch_data:
            summary = patch_data.get("summary", {})
            entry["total_trees"] = summary.get("total_trees", 0)
            entry["alive_trees"] = summary.get("alive_trees", 0)
            entry["dead_trees"]  = summary.get("dead_trees", 0)
            alive = summary.get("alive_trees", 0)
            total = summary.get("total_trees", 1) or 1
            entry["survival_pct"] = round(alive / total * 100, 1)
        enriched.append(entry)

    return {"site": site, "surveys": enriched}


@app.post("/api/analyze-site")
async def analyze_site(
    background_tasks: BackgroundTasks,
    site: str = "benkmura",
):
    """
    Trigger the orthomosaic-based full-field survival analysis pipeline.
    Runs asynchronously — poll /api/site-result/{site} for the result.

    site: 'benkmura' or 'debadihi'
    """
    valid_sites = {"benkmura", "debadihi"}
    if site not in valid_sites:
        raise HTTPException(status_code=400, detail=f"site must be one of {valid_sites}")

    result_path = os.path.join(BASE_DIR, "results", site, f"{site}_all_detections.geojson")
    flag_path   = os.path.join(BASE_DIR, "results", site, "_running")

    if _pipeline_running(flag_path):
        return {"status": "already_running", "site": site,
                "message": "Pipeline is already running for this site."}

    def run_pipeline(site_name: str):
        import subprocess, sys
        script = os.path.join(BASE_DIR, "ortho_pipeline.py")
        os.makedirs(os.path.dirname(flag_path), exist_ok=True)
        # Stamp the flag with this server's PID so a crash mid-run leaves a
        # *detectably* stale flag (its owner PID is dead) rather than one that
        # pins the site on 'running' forever.
        Path(flag_path).write_text(str(os.getpid()))
        try:
            # encoding/errors are required: the pipeline prints UTF-8 (→ ± ×) and a
            # Windows parent would otherwise decode the captured stream as cp1252,
            # garbling it and risking UnicodeDecodeError on undefined byte slots.
            proc = subprocess.run(
                [sys.executable, script, "--site", site_name],
                cwd=BASE_DIR, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=1800,
            )
            if proc.returncode != 0:
                logger.error(
                    f"Ortho pipeline for {site_name} exited {proc.returncode}. "
                    f"stderr tail: {(proc.stderr or '')[-500:]}"
                )
            else:
                logger.info(f"Ortho pipeline for {site_name} completed successfully")
        except Exception as e:
            logger.error(f"Ortho pipeline for {site_name} failed to run: {e}")
        finally:
            if os.path.exists(flag_path):
                os.remove(flag_path)

    background_tasks.add_task(run_pipeline, site)
    return {
        "status": "started",
        "site": site,
        "message": f"Ortho pipeline started for {site}. Poll /api/site-result/{site} for results.",
    }


@app.get("/api/site-result/{site}")
async def get_site_result(site: str):
    """
    Get the latest ortho-pipeline result for a site.
    Returns survival statistics + list of casualty GPS coordinates.
    """
    valid_sites = {"benkmura", "debadihi"}
    if site not in valid_sites:
        raise HTTPException(status_code=400, detail=f"Unknown site: {site}")

    flag_path    = os.path.join(BASE_DIR, "results", site, "_running")
    geojson_path = os.path.join(BASE_DIR, "results", site, f"{site}_all_detections.geojson")

    running = _pipeline_running(flag_path)

    if not os.path.exists(geojson_path):
        return {
            "site":    site,
            "status":  "running" if running else "not_started",
            "message": "No results yet. POST /api/analyze-site?site={site} to start.",
        }

    try:
        async with aiofiles.open(geojson_path, "r") as f:
            raw = await f.read()
        features = json.loads(raw).get("features", [])

        def _status(f): return f["properties"].get("status")
        alive    = [f for f in features if _status(f) == "alive"]
        dead     = [f for f in features if _status(f) == "dead"]
        no_data  = [f for f in features if _status(f) == "no_data"]
        oob      = [f for f in features if _status(f) == "out_of_bounds"]
        in_field = len(alive) + len(dead)
        survival_pct = round(len(alive) / in_field * 100, 1) if in_field else 0

        def _point(feat: dict) -> dict:
            coords = feat["geometry"]["coordinates"]
            props  = feat["properties"]
            return {
                "lat":  coords[1],
                "lon":  coords[0],
                "conf": props.get("confidence"),
                "green_center":  props.get("green_center"),
                "ring_contrast": props.get("ring_contrast"),
            }

        return {
            "site":           site,
            "status":         "running" if running else "complete",
            "total_detected": len(features),
            "in_field":       in_field,
            "alive":          len(alive),
            "dead":           len(dead),
            # Pits that could not be judged: nodata holes / outside the OP3 footprint.
            "no_data":        len(no_data),
            "out_of_bounds":  len(oob),
            "survival_pct":   survival_pct,
            "casualties":     [_point(f) for f in sorted(dead, key=lambda x: x["properties"]["confidence"], reverse=True)],
            "alive_locations": [_point(f) for f in sorted(alive, key=lambda x: x["properties"]["confidence"], reverse=True)],
        }
    except Exception as e:
        logger.error(f"Error reading site result for {site}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read results")


@app.post("/api/evaluate/{site}")
async def evaluate_site(
    site: str,
    file: UploadFile = File(...),
    tol: float = Form(1.5),
):
    """
    Score the pipeline's casualties against uploaded ground-truth dead locations
    — the brief's #1 judging criterion (recall of the 25-30 known dead points).

    Accepts the known-dead points as GeoJSON / CSV / KML / GPX and reuses the
    matching maths in evaluate.py. Returns recall, match distances, and a
    per-point hit/miss list (with the pipeline status at each truth point) so the
    frontend can render ground-truth markers on the map.
    """
    valid_sites = {"benkmura", "debadihi"}
    if site not in valid_sites:
        raise HTTPException(status_code=400, detail=f"Unknown site: {site}")

    results_dir   = os.path.join(BASE_DIR, "results", site)
    casualties    = os.path.join(results_dir, f"{site}_casualties.geojson")
    all_detections = os.path.join(results_dir, f"{site}_all_detections.geojson")
    if not os.path.exists(casualties):
        raise HTTPException(
            status_code=404,
            detail=f"No results for '{site}' yet — run the analysis pipeline first.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty ground-truth file")
    suffix = os.path.splitext(file.filename or "gt.geojson")[1].lower() or ".geojson"
    if suffix not in (".geojson", ".json", ".csv", ".kml", ".gpx", ".xml"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {suffix}")

    tmp_path = None
    try:
        import evaluate as ev  # AI Model/ is on sys.path (see config import above)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        truth = ev.load_points(tmp_path)
        pred  = ev.load_points(casualties)
        all_pts, all_props = ev._load_pred_with_props(all_detections) \
            if os.path.exists(all_detections) else ([], [])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evaluate parse error for {site}: {e}")
        raise HTTPException(status_code=400, detail=f"Could not parse ground-truth file: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not truth:
        raise HTTPException(status_code=400, detail="No points found in the ground-truth file")

    matches, missed = ev.greedy_match(truth, pred, tol)
    match_dist = {ti: d for ti, _, d in matches}

    points = []
    for ti, (lat, lon) in enumerate(truth):
        near_d, near_status = ev.nearest((lat, lon), all_pts, all_props) if all_pts else (None, None)
        matched = ti in match_dist
        points.append({
            "lat": lat, "lon": lon,
            "matched": matched,
            "distance": round(match_dist[ti] if matched else (near_d or 0.0), 2),
            "nearest_status": near_status,
        })

    dists = list(match_dist.values())
    return {
        "site": site,
        "tol": tol,
        "total_truth": len(truth),
        "matched": len(matches),
        "recall": round(len(matches) / len(truth) * 100, 1),
        "mean_dist":   round(sum(dists) / len(dists), 2) if dists else None,
        "median_dist": round(sorted(dists)[len(dists) // 2], 2) if dists else None,
        "max_dist":    round(max(dists), 2) if dists else None,
        "points": points,
    }


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
