#!/usr/bin/env python3
"""
Orthomosaic-based afforestation survival pipeline.

Problem statement approach (from the hackathon brief):
  OP1 (Post-Pitting)  → detect all pit locations  → extract GPS coordinates
  OP3 (Post-SW)       → for each pit GPS, check sapling survival with V2 CNN
  Output              → survival % + exact GPS of every dead sapling

This is the correct architecture for the judging criteria:
  "25–30 exact locations where saplings have died" — must be found by GPS, not just counted.

Usage
-----
  python "AI Model/ortho_pipeline.py" --site benkmura
  python "AI Model/ortho_pipeline.py" --site debadihi
"""

import os, sys, cv2, json, math, time
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# ── path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from models.data_structures import TreeStatus

# ── site config ───────────────────────────────────────────────────────────────
DATA_ROOT = SCRIPT_DIR.parent / "Data" / "Image" / "Drone image"

SITES = {
    "benkmura": {
        "op1_mosaic": DATA_ROOT / "Benkmura VF" / "Ortho" / "Post Pitting"  / "Pitting.tif",
        "op3_mosaic": DATA_ROOT / "Benkmura VF" / "Ortho" / "Post-SW"       / "Post-SW.tif",
        "total_planted": 8_000,
        "spacing_m": 2.5,
    },
    "debadihi": {
        "op1_mosaic": DATA_ROOT / "Debadihi VF" / "Ortho Data" / "Post-Pitting"  / "Post-Pitting.tif",
        "op3_mosaic": DATA_ROOT / "Debadihi VF" / "Ortho Data" / "Post-SW"       / "map.tif",
        "total_planted": 10_000,
        "spacing_m": 2.5,
    },
}

# ── GeoTIFF helpers (no rasterio required) ────────────────────────────────────

def read_geotiff(path: str):
    """
    Load a GeoTIFF using rasterio and extract the affine georeferencing.

    Returns
    -------
    img_bgr   : np.ndarray  BGR image
    origin_x  : float       projected X of pixel (0,0)
    origin_y  : float       projected Y of pixel (0,0)
    scale_x   : float       metres per pixel in X
    scale_y   : float       metres per pixel in Y (stored positive)
    crs_wkt   : str         coordinate reference system as WKT (for pyproj)
    """
    import rasterio
    print(f"  Loading {Path(path).name} …", end=" ", flush=True)
    t0 = time.time()

    with rasterio.open(path) as ds:
        # Read as RGB (bands 1-3); ignore alpha if present
        n_bands = min(ds.count, 3)
        data = ds.read(list(range(1, n_bands + 1)))   # (bands, H, W) uint8
        transform = ds.transform
        crs_wkt   = ds.crs.to_wkt() if ds.crs else None

    # rasterio returns (bands, H, W) — reshape to (H, W, bands)
    arr = np.transpose(data, (1, 2, 0))
    if arr.shape[2] == 1:
        arr = np.repeat(arr, 3, axis=2)

    img_bgr  = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    origin_x = transform.c         # X of top-left pixel
    origin_y = transform.f         # Y of top-left pixel
    scale_x  = transform.a         # pixel width  (positive)
    scale_y  = abs(transform.e)    # pixel height (stored negative in transform)

    print(f"{img_bgr.shape[1]}×{img_bgr.shape[0]} px  ({time.time()-t0:.1f}s)")
    return img_bgr, origin_x, origin_y, scale_x, scale_y, crs_wkt


def pixel_to_projected(col: float, row: float,
                       ox: float, oy: float,
                       sx: float, sy: float) -> Tuple[float, float]:
    """Convert pixel (col, row) → projected coordinates in whatever CRS the file uses."""
    return ox + col * sx, oy - row * sy


def projected_to_pixel(px: float, py: float,
                       ox: float, oy: float,
                       sx: float, sy: float) -> Tuple[int, int]:
    """Convert projected (x, y) → pixel (col, row). Works for any CRS."""
    col = (px - ox) / sx
    row = (oy - py) / sy
    return int(round(col)), int(round(row))


def reproject_point(x: float, y: float,
                    src_wkt: str, dst_wkt: str) -> Tuple[float, float]:
    """
    Reproject a single point from src CRS to dst CRS.
    Handles any combination of projected / geographic CRS.
    """
    from pyproj import Transformer, CRS
    src = CRS.from_wkt(src_wkt)
    dst = CRS.from_wkt(dst_wkt)
    t   = Transformer.from_crs(src, dst, always_xy=True)
    rx, ry = t.transform(x, y)
    return rx, ry


def to_wgs84(x: float, y: float, crs_wkt: str) -> Tuple[float, float]:
    """Convert any projected coordinate to WGS84 lat/lon."""
    from pyproj import Transformer, CRS
    src = CRS.from_wkt(crs_wkt)
    dst = CRS.from_epsg(4326)
    t   = Transformer.from_crs(src, dst, always_xy=True)
    lon, lat = t.transform(x, y)
    return float(lat), float(lon)


# ── Step 1: Pit detection on OP1 orthomosaic ─────────────────────────────────

def _is_dark_pit(gray_tile: np.ndarray, cx: int, cy: int, r: int,
                 darkness_margin: int = 12) -> bool:
    """
    Return True if the circle interior is meaningfully darker than
    the surrounding ring (real pits are dark holes in the soil).
    """
    h, w = gray_tile.shape
    # Inner mask
    inner = np.zeros((h, w), np.uint8)
    cv2.circle(inner, (cx, cy), max(1, r - 1), 255, -1)
    # Outer ring mask (1.8× radius annulus)
    outer = np.zeros((h, w), np.uint8)
    cv2.circle(outer, (cx, cy), int(r * 1.8), 255, -1)
    cv2.circle(outer, (cx, cy), r, 0, -1)

    inner_px = gray_tile[inner > 0]
    outer_px = gray_tile[outer > 0]
    if inner_px.size == 0 or outer_px.size == 0:
        return False
    return float(inner_px.mean()) < float(outer_px.mean()) - darkness_margin


def _grid_dedup(circles: list, spacing_m: float, pixel_scale: float) -> list:
    """
    Spatial deduplication on the planting grid.
    Assigns each detected circle to the nearest 2.5m × 2.5m grid cell
    and keeps only the best (most central) candidate per cell.
    Reduces false positives that cluster together by returning at most
    one detection per expected planting slot.
    """
    if not circles:
        return []
    cell_px = spacing_m / pixel_scale   # pixels per grid cell
    best: Dict[Tuple[int, int], tuple] = {}  # (gx,gy) → (cx,cy,r)

    for cx, cy, r in circles:
        gx = int(round(cx / cell_px))
        gy = int(round(cy / cell_px))
        key = (gx, gy)
        if key not in best:
            best[key] = (cx, cy, r)
        else:
            # Keep the one closer to the grid cell centre
            gcx, gcy = gx * cell_px, gy * cell_px
            old = best[key]
            d_old = (old[0] - gcx) ** 2 + (old[1] - gcy) ** 2
            d_new = (cx    - gcx) ** 2 + (cy    - gcy) ** 2
            if d_new < d_old:
                best[key] = (cx, cy, r)

    return list(best.values())


def _hough_tile_worker(args):
    """Process one tile — runs in a subprocess to parallelise CPU-bound Hough."""
    (tile_bgr_bytes, shape, x1, y1, ix1, iy1, ix2, iy2,
     min_r, max_r, min_dist, darkness_margin) = args

    tile_bgr = np.frombuffer(tile_bgr_bytes, dtype=np.uint8).reshape(shape)
    gray     = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2GRAY)
    clahe    = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    circles = cv2.HoughCircles(
        enhanced, cv2.HOUGH_GRADIENT,
        dp=1.2, minDist=min_dist,
        param1=60, param2=28,
        minRadius=min_r, maxRadius=max_r,
    )
    results = []
    if circles is not None:
        for cx, cy, r in np.round(circles[0]).astype(int):
            gcx, gcy = cx + x1, cy + y1
            if ix1 <= gcx < ix2 and iy1 <= gcy < iy2:
                if _is_dark_pit(gray, cx, cy, r, darkness_margin):
                    results.append((int(gcx), int(gcy), int(r)))
    return results


def detect_pits_on_mosaic(
    img_bgr: np.ndarray,
    ox: float, oy: float, sx: float, sy: float,
    spacing_m: float = 2.5,
    min_radius_m: float = 0.18,
    max_radius_m: float = 0.55,
    tile_px: int = 3000,
    overlap_px: int = 80,
) -> List[Dict]:
    """
    Detect planting pits (dark circular depressions) in the OP1 orthomosaic.

    Three-stage filtering to reach a realistic pit count:
      1. Tiled HoughCircles (handles large mosaics without OOM)
      2. Darkness validation (real pits are darker than surroundings)
      3. Grid deduplication (≤1 detection per 2.5m planting slot)
    """
    print("  Detecting pits via tiled Hough + darkness + grid dedup …")
    t0 = time.time()

    h, w      = img_bgr.shape[:2]
    min_r     = max(3, int(min_radius_m / sx))
    max_r     = max(5, int(max_radius_m / sx))
    min_dist  = max(8, int(spacing_m / sx * 0.70))

    raw_circles = []

    n_tx = math.ceil(w / tile_px)
    n_ty = math.ceil(h / tile_px)
    total_tiles = n_tx * n_ty
    n_workers   = max(1, multiprocessing.cpu_count() - 1)

    # Build tile argument list
    tile_args = []
    for ty in range(n_ty):
        for tx in range(n_tx):
            x1 = max(0, tx * tile_px - overlap_px)
            y1 = max(0, ty * tile_px - overlap_px)
            x2 = min(w, (tx + 1) * tile_px + overlap_px)
            y2 = min(h, (ty + 1) * tile_px + overlap_px)
            tile_bgr = img_bgr[y1:y2, x1:x2]
            tile_args.append((
                tile_bgr.tobytes(), tile_bgr.shape,
                x1, y1,
                tx * tile_px, ty * tile_px,
                min(w, (tx + 1) * tile_px), min(h, (ty + 1) * tile_px),
                min_r, max_r, min_dist, 12,  # darkness_margin=12
            ))

    raw_circles = []
    done = 0
    print(f"    Using {n_workers} CPU workers for {total_tiles} tiles …")

    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_hough_tile_worker, a): i for i, a in enumerate(tile_args)}
        for fut in as_completed(futures):
            raw_circles.extend(fut.result())
            done += 1
            if done % 10 == 0 or done == total_tiles:
                print(f"    tile {done}/{total_tiles}  raw (dark) circles: {len(raw_circles)}")

    print(f"  After Hough + darkness: {len(raw_circles)} circles")

    # Stage 3: grid deduplication — ≤1 pit per 2.5m planting slot
    deduped = _grid_dedup(raw_circles, spacing_m, sx)
    print(f"  After grid dedup ({spacing_m}m cells): {len(deduped)} pits")

    pits = []
    for gcx, gcy, r in deduped:
        px, py = pixel_to_projected(gcx, gcy, ox, oy, sx, sy)
        pits.append({
            "col":       int(gcx),
            "row":       int(gcy),
            "radius_px": int(r),
            "proj_x":    round(px, 4),   # in OP1's own CRS
            "proj_y":    round(py, 4),
        })

    print(f"  Total pits detected: {len(pits)}  ({time.time()-t0:.1f}s)")
    return pits


# ── Step 2: Survival check on OP3 orthomosaic ────────────────────────────────

def check_survival(
    pits: List[Dict],
    op3_img: np.ndarray,
    op3_ox: float, op3_oy: float,
    op3_sx: float, op3_sy: float,
    op1_crs_wkt: Optional[str] = None,
    op3_crs_wkt: Optional[str] = None,
    tile_m: float = 2.0,
) -> List[Dict]:
    """
    For each pit coordinate, project into the OP3 mosaic, crop a tile,
    and classify alive/dead with the V2 CNN.

    Returns pits list enriched with 'status' and 'survival_conf' fields.
    """
    from core.forest_processor import ForestMLProcessor
    proc = ForestMLProcessor()
    print(f"  CNN model: {proc.model_version}  classes={proc.num_classes}")

    h3, w3 = op3_img.shape[:2]

    # Compute half_px correctly for the OP3 CRS.
    # If OP3 is geographic (degrees), convert metres → degrees at the scene latitude.
    # Otherwise OP3 is projected (metres) and sx is already metres/pixel.
    from pyproj import CRS as _CRS
    op3_is_geographic = _CRS.from_wkt(op3_crs_wkt).is_geographic if op3_crs_wkt else False
    if op3_is_geographic:
        # approximate: 1 degree ≈ 111,000 m at the equator; use scene centre lat
        scene_lat = op3_oy - (h3 / 2) * op3_sy   # rough centre latitude (degrees)
        import math as _math
        metres_per_deg = 111_000 * _math.cos(_math.radians(scene_lat))
        half_px = max(5, int(tile_m / (op3_sx * metres_per_deg) / 2))
    else:
        half_px = max(5, int(tile_m / op3_sx / 2))

    print(f"  Tile half-size: {half_px} px  "
          f"({'geographic' if op3_is_geographic else 'projected'} CRS)")

    alive_count = dead_count = out_of_bounds = 0
    results = []

    import torch
    BATCH = 256   # GPU batched inference — much faster than one-by-one

    print(f"  Checking {len(pits)} pit locations in OP3 mosaic (batch={BATCH}) …")
    t0 = time.time()

    # Build (pit_index, crop_tensor) list — skip out-of-bounds up front
    valid_idx:   List[int]         = []
    crop_tensors: List[torch.Tensor] = []

    for i, pit in enumerate(pits):
        # Reproject OP1 projected coords → OP3 CRS → OP3 pixel
        if op1_crs_wkt and op3_crs_wkt and op1_crs_wkt != op3_crs_wkt:
            op3_px, op3_py = reproject_point(
                pit["proj_x"], pit["proj_y"], op1_crs_wkt, op3_crs_wkt
            )
        else:
            op3_px, op3_py = pit["proj_x"], pit["proj_y"]

        col3, row3 = projected_to_pixel(op3_px, op3_py, op3_ox, op3_oy, op3_sx, op3_sy)
        x1, y1 = col3 - half_px, row3 - half_px
        x2, y2 = col3 + half_px, row3 + half_px

        if x1 < 0 or y1 < 0 or x2 >= w3 or y2 >= h3:
            out_of_bounds += 1
            results.append({**pits[i], "status": "out_of_bounds", "survival_conf": 0.0})
            continue

        crop = op3_img[y1:y2, x1:x2]
        if crop.size == 0:
            out_of_bounds += 1
            results.append({**pits[i], "status": "out_of_bounds", "survival_conf": 0.0})
            continue

        tile = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_AREA)
        rgb  = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
        crop_tensors.append(proc.transform(rgb))
        valid_idx.append(i)

    # Batched GPU inference
    preds_all  = []
    confs_all  = []
    for b_start in range(0, len(crop_tensors), BATCH):
        batch = torch.stack(crop_tensors[b_start:b_start + BATCH]).to(proc.device)
        with torch.no_grad():
            out  = proc.model(batch)
            prob = torch.softmax(out, dim=1)
            pred = torch.argmax(prob, dim=1)
            conf = prob[torch.arange(len(pred)), pred]
        preds_all.extend(pred.cpu().tolist())
        confs_all.extend(conf.cpu().tolist())
        if (b_start // BATCH) % 20 == 0:
            pct = min(100, b_start / max(1, len(crop_tensors)) * 100)
            print(f"    inference {pct:.0f}%  "
                  f"alive={alive_count}  dead={dead_count}")

    # Map predictions back to pits
    for rank, pit_i in enumerate(valid_idx):
        pred = preds_all[rank]
        conf = confs_all[rank]
        pit  = pits[pit_i]

        if pred == 0:
            status = "alive";      alive_count += 1
        elif pred == 1:
            status = "dead";       dead_count  += 1
        else:
            status = "no_sapling"

        lat, lon = to_wgs84(pit["proj_x"], pit["proj_y"], op1_crs_wkt)
        results.append({
            **pit,
            "status":        status,
            "survival_conf": round(float(conf), 4),
            "lat":           round(lat, 7),
            "lon":           round(lon, 7),
        })

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s  "
          f"| alive={alive_count}  dead={dead_count}  out_of_bounds={out_of_bounds}")
    return results


# ── Step 3: Report ────────────────────────────────────────────────────────────

def generate_report(results: List[Dict], total_planted: int, site: str, out_dir: Path):
    """Save GeoJSON files and print summary."""
    out_dir.mkdir(parents=True, exist_ok=True)

    alive    = [r for r in results if r["status"] == "alive"]
    dead     = [r for r in results if r["status"] == "dead"]
    no_sap   = [r for r in results if r["status"] == "no_sapling"]
    detected = len(alive) + len(dead)

    survival_pct = len(alive) / detected * 100 if detected else 0

    print(f"\n{'='*60}")
    print(f"  SURVIVAL REPORT — {site.upper()}")
    print(f"{'='*60}")
    print(f"  Total pits detected   : {len(results)}")
    print(f"  In-field detections   : {detected}")
    print(f"  ALIVE                 : {len(alive)}  ({survival_pct:.1f}%)")
    print(f"  DEAD / Casualties     : {len(dead)}  ({100-survival_pct:.1f}%)")
    print(f"  No-sapling zones      : {len(no_sap)}")
    print(f"{'='*60}")

    # ── GeoJSON with ALL results ──────────────────────────────────────────────
    def make_geojson(items, label):
        features = []
        for r in items:
            if "lat" not in r:
                continue
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["lon"], r["lat"]],
                },
                "properties": {
                    "status":       r["status"],
                    "confidence":   r.get("survival_conf", 0),
                    "proj_x":       r.get("proj_x"),
                    "proj_y":       r.get("proj_y"),
                },
            })
        return {"type": "FeatureCollection", "features": features}

    # All results
    all_path = out_dir / f"{site}_all_detections.geojson"
    with open(all_path, "w") as f:
        json.dump(make_geojson(results, "all"), f, indent=2)
    print(f"  All detections saved : {all_path}")

    # Casualties only (the key output for judging)
    dead_path = out_dir / f"{site}_casualties.geojson"
    with open(dead_path, "w") as f:
        json.dump(make_geojson(dead, "dead"), f, indent=2)
    print(f"  Casualties GeoJSON   : {dead_path}")
    print(f"\n  Top 30 casualty GPS coordinates:")
    for r in sorted(dead, key=lambda x: x.get("survival_conf", 0), reverse=True)[:30]:
        print(f"    lat={r.get('lat','?'):.6f}  lon={r.get('lon','?'):.6f}  "
              f"conf={r.get('survival_conf',0):.3f}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--site", choices=["benkmura", "debadihi"], default="benkmura")
    p.add_argument("--out",  default=None, help="Output directory (default: AI Model/results/{site})")
    args = p.parse_args()

    cfg     = SITES[args.site]
    out_dir = Path(args.out) if args.out else SCRIPT_DIR / "results" / args.site

    print(f"\n{'='*60}")
    print(f"  ORTHO PIPELINE — {args.site.upper()}")
    print(f"  OP1: {cfg['op1_mosaic'].name}")
    print(f"  OP3: {cfg['op3_mosaic'].name}")
    print(f"{'='*60}\n")

    t_total = time.time()

    # ── Step 1: Load OP1 and detect pits ─────────────────────────────────────
    print("[Step 1] Load OP1 orthomosaic and detect pits")
    op1_img, op1_ox, op1_oy, op1_sx, op1_sy, op1_crs_wkt = read_geotiff(str(cfg["op1_mosaic"]))
    print(f"  CRS: {op1_crs_wkt[:60] if op1_crs_wkt else 'unknown'}…")
    pits = detect_pits_on_mosaic(
        op1_img, op1_ox, op1_oy, op1_sx, op1_sy,
        spacing_m=cfg["spacing_m"],
    )

    if not pits:
        print("  ERROR: No pits detected. Check mosaic quality or Hough parameters.")
        return

    # ── Step 2: Load OP3 and check survival ──────────────────────────────────
    print(f"\n[Step 2] Load OP3 orthomosaic and check survival at {len(pits)} pit locations")
    op3_img, op3_ox, op3_oy, op3_sx, op3_sy, op3_crs_wkt = read_geotiff(str(cfg["op3_mosaic"]))
    if op3_crs_wkt != op1_crs_wkt:
        print(f"  CRS mismatch detected -- reprojecting OP1->OP3 on the fly")
        print(f"    OP1: {op1_crs_wkt[:50]}…")
        print(f"    OP3: {op3_crs_wkt[:50]}…")
    results = check_survival(
        pits, op3_img, op3_ox, op3_oy, op3_sx, op3_sy,
        op1_crs_wkt=op1_crs_wkt,
        op3_crs_wkt=op3_crs_wkt,
        tile_m=2.0,
    )

    # ── Step 3: Report ───────────────────────────────────────────────────────
    print(f"\n[Step 3] Generating report")
    generate_report(results, cfg["total_planted"], args.site, out_dir)

    print(f"\n  Total pipeline time: {time.time()-t_total:.1f}s")


if __name__ == "__main__":
    main()
