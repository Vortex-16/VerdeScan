#!/usr/bin/env python3
"""
Orthomosaic-based afforestation survival pipeline.

Problem-statement approach (verbatim from the hackathon brief)
--------------------------------------------------------------
  OP1 (Post-Pitting)  → detect every pit  → extract its GPS coordinate
  OP3 (Post-SW)       → at each pit GPS, decide whether the sapling survived
  Output              → survival %  +  exact GPS of every casualty

Why this architecture (matches the judging criteria)
----------------------------------------------------
  The brief recommends: "coordinate information from images after OP1 be used,
  as pits can easily be identified. These coordinates be matched with images
  after OP3 to check whether there is sapling survival at those points."
  Judging criterion #1 is finding the 25-30 KNOWN dead locations per patch, so
  the deliverable is a list of casualty GPS points (`*_casualties.geojson`),
  scored against ground truth by `evaluate.py`.

The OP3 survival signal — the weeding circle (not greenness)
------------------------------------------------------------
  OP3 is the *weeding* operation: "a diameter of 1m soil is cleared around the
  sapling, which is visible from the sky."  So the physical proof that a sapling
  survived is a freshly-cleared ~1 m soil disc, NOT how green the spot is:

    • Saplings are "4 to 6 ft tall with minimal foliage" → a live sapling shows
      very little green from 75 m up.
    • Challenge #2 in the brief: "existing greenery around the saplings might
      pose a challenge" → a DEAD spot can be greener (weeds) than a live, weeded
      one.  Pure green-fraction is therefore a weak, sometimes inverted signal.

  `check_survival` blends three independent cues per pit and stores all of them
  so the decision threshold can be calibrated against ground truth:
      green_center  - ExG vegetation in the central disc (the sapling itself)
      ring_contrast - cleared centre vs vegetated/textured surround (weeding)
      hough_ring    - a ~1 m circle detected near the centre (weeding boundary)

Speed (judging criterion #2)
----------------------------
  Mosaics are multi-GB (Benkmura OP1 is 27k×23k×4).  Everything uses rasterio
  *windowed* reads — pit detection streams tiles from disk, survival reads one
  small window per pit — so memory is bounded and thousands of patches stay
  tractable.

Usage
-----
  python "AI Model/ortho_pipeline.py" --site benkmura
  python "AI Model/ortho_pipeline.py" --site debadihi
  python "AI Model/ortho_pipeline.py" --site benkmura --limit-pits 500   # quick smoke test
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

# Windows consoles default to cp1252 and choke on the Unicode used in progress
# output (→, ±, ×).  Force UTF-8 so logs are clean on every platform.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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


# ── GeoTIFF metadata + coordinate helpers ─────────────────────────────────────

class RasterMeta:
    """Lightweight georeferencing handle — no pixel data held in RAM."""
    def __init__(self, path: str):
        import rasterio
        with rasterio.open(path) as ds:
            self.path    = path
            self.width   = ds.width
            self.height  = ds.height
            self.count   = ds.count
            t            = ds.transform
            self.ox      = t.c          # projected X of pixel (0,0)
            self.oy      = t.f          # projected Y of pixel (0,0)
            self.sx      = t.a          # pixel width  (units of CRS, positive)
            self.sy      = abs(t.e)     # pixel height (stored negative)
            self.crs_wkt = ds.crs.to_wkt() if ds.crs else None
            self.is_geographic = bool(ds.crs and ds.crs.is_geographic)
        # metres-per-pixel: for a geographic CRS (degrees) convert at scene latitude
        if self.is_geographic:
            scene_lat = self.oy - (self.height / 2) * self.sy
            self.m_per_px = self.sx * 111_000 * math.cos(math.radians(scene_lat))
        else:
            self.m_per_px = self.sx

    def pixel_to_proj(self, col: float, row: float) -> Tuple[float, float]:
        return self.ox + col * self.sx, self.oy - row * self.sy

    def proj_to_pixel(self, px: float, py: float) -> Tuple[int, int]:
        return int(round((px - self.ox) / self.sx)), int(round((self.oy - py) / self.sy))


def reproject_point(x: float, y: float, src_wkt: str, dst_wkt: str) -> Tuple[float, float]:
    """Reproject a single (x, y) from src CRS to dst CRS (any projected/geographic mix)."""
    from pyproj import Transformer, CRS
    t = Transformer.from_crs(CRS.from_wkt(src_wkt), CRS.from_wkt(dst_wkt), always_xy=True)
    return t.transform(x, y)


def to_wgs84(x: float, y: float, crs_wkt: str) -> Tuple[float, float]:
    """Convert any projected/geographic coordinate to WGS84 lat/lon."""
    from pyproj import Transformer, CRS
    t = Transformer.from_crs(CRS.from_wkt(crs_wkt), CRS.from_epsg(4326), always_xy=True)
    lon, lat = t.transform(x, y)
    return float(lat), float(lon)


def _read_window_bgr_alpha(ds, x: int, y: int, w: int, h: int):
    """
    Read a (h, w) window from an open rasterio dataset as (bgr, alpha).
    Uses boundless reads so windows clipped by the raster edge are zero-filled.
    alpha is band 4 if present, else all-255 (fully valid).
    """
    from rasterio.windows import Window
    win  = Window(x, y, w, h)
    n    = min(ds.count, 3)
    rgb  = ds.read(list(range(1, n + 1)), window=win, boundless=True, fill_value=0)
    if rgb.shape[0] == 1:
        rgb = np.repeat(rgb, 3, axis=0)
    bgr = cv2.cvtColor(np.transpose(rgb, (1, 2, 0)), cv2.COLOR_RGB2BGR)
    if ds.count >= 4:
        alpha = ds.read(4, window=win, boundless=True, fill_value=0)
    else:
        alpha = np.full((h, w), 255, np.uint8)
    return bgr, alpha


# ── Step 1: Pit detection on the OP1 orthomosaic (windowed / bounded RAM) ─────

def _is_dark_pit(gray_tile: np.ndarray, cx: int, cy: int, r: int,
                 darkness_margin: int = 12) -> bool:
    """True if the circle interior is meaningfully darker than its surrounding
    ring — real pits are dark holes dug into the soil."""
    h, w = gray_tile.shape
    inner = np.zeros((h, w), np.uint8)
    cv2.circle(inner, (cx, cy), max(1, r - 1), 255, -1)
    outer = np.zeros((h, w), np.uint8)
    cv2.circle(outer, (cx, cy), int(r * 1.8), 255, -1)
    cv2.circle(outer, (cx, cy), r, 0, -1)
    inner_px = gray_tile[inner > 0]
    outer_px = gray_tile[outer > 0]
    if inner_px.size == 0 or outer_px.size == 0:
        return False
    return float(inner_px.mean()) < float(outer_px.mean()) - darkness_margin


def _grid_dedup(circles: list, spacing_m: float, pixel_scale: float) -> list:
    """Keep at most one detection per 2.5 m planting slot (the most grid-central)."""
    if not circles:
        return []
    cell_px = spacing_m / pixel_scale
    best: Dict[Tuple[int, int], tuple] = {}
    for cx, cy, r in circles:
        gx, gy = int(round(cx / cell_px)), int(round(cy / cell_px))
        key = (gx, gy)
        if key not in best:
            best[key] = (cx, cy, r)
        else:
            gcx, gcy = gx * cell_px, gy * cell_px
            old = best[key]
            if (cx - gcx) ** 2 + (cy - gcy) ** 2 < (old[0] - gcx) ** 2 + (old[1] - gcy) ** 2:
                best[key] = (cx, cy, r)
    return list(best.values())


def _hough_tile_worker(args):
    """Detect dark circular pits in one tile (runs in a worker process).

    Receives the tile's RGB+alpha bytes (read from disk in the parent), so no
    process ever holds the full mosaic.  Rejects circles whose centre lands in
    the transparent nodata region using the tile's own alpha band."""
    (rgb_bytes, a_bytes, shape, x1, y1, ix1, iy1, ix2, iy2,
     min_r, max_r, min_dist, darkness_margin) = args

    tile_bgr = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape(shape)
    tile_a   = np.frombuffer(a_bytes,  dtype=np.uint8).reshape(shape[:2])
    gray     = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)

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
            if ix1 <= gcx < ix2 and iy1 <= gcy < iy2:                # own (non-overlap) region
                if 0 <= cy < tile_a.shape[0] and 0 <= cx < tile_a.shape[1] \
                        and tile_a[cy, cx] < 128:
                    continue                                          # nodata hole
                if _is_dark_pit(gray, cx, cy, r, darkness_margin):
                    results.append((int(gcx), int(gcy), int(r)))
    return results


def detect_pits(
    meta: "RasterMeta",
    spacing_m: float = 2.5,
    min_radius_m: float = 0.18,
    max_radius_m: float = 0.55,
    tile_px: int = 3000,
    overlap_px: int = 80,
) -> List[Dict]:
    """
    Detect planting pits in the OP1 orthomosaic via streamed, tiled Hough.

      1. Stream tiles from disk (rasterio windows) → bounded RAM.
      2. HoughCircles + darkness validation + nodata rejection per tile.
      3. Grid deduplication → ≤1 pit per 2.5 m planting slot.
    """
    import rasterio
    print("  Detecting pits via windowed Hough + darkness + grid dedup …")
    t0 = time.time()

    W, H   = meta.width, meta.height
    sx     = meta.sx
    min_r  = max(3, int(min_radius_m / sx))
    max_r  = max(5, int(max_radius_m / sx))
    min_d  = max(8, int(spacing_m / sx * 0.70))

    n_tx = math.ceil(W / tile_px)
    n_ty = math.ceil(H / tile_px)
    total_tiles = n_tx * n_ty
    n_workers   = max(1, multiprocessing.cpu_count() - 1)
    print(f"    {total_tiles} tiles · {n_workers} workers · pit r∈[{min_r},{max_r}]px")

    raw_circles: list = []
    done = 0
    with rasterio.open(meta.path) as ds, \
         ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = {}
        for ty in range(n_ty):
            for tx in range(n_tx):
                x1 = max(0, tx * tile_px - overlap_px)
                y1 = max(0, ty * tile_px - overlap_px)
                x2 = min(W, (tx + 1) * tile_px + overlap_px)
                y2 = min(H, (ty + 1) * tile_px + overlap_px)
                bgr, alpha = _read_window_bgr_alpha(ds, x1, y1, x2 - x1, y2 - y1)
                args = (
                    bgr.tobytes(), alpha.tobytes(), bgr.shape,
                    x1, y1,
                    tx * tile_px, ty * tile_px,
                    min(W, (tx + 1) * tile_px), min(H, (ty + 1) * tile_px),
                    min_r, max_r, min_d, 12,
                )
                futures[pool.submit(_hough_tile_worker, args)] = (tx, ty)
        for fut in as_completed(futures):
            raw_circles.extend(fut.result())
            done += 1
            if done % 10 == 0 or done == total_tiles:
                print(f"    tile {done}/{total_tiles}  raw dark circles: {len(raw_circles)}")

    print(f"  After Hough + darkness + nodata reject: {len(raw_circles)} circles")
    deduped = _grid_dedup(raw_circles, spacing_m, sx)
    print(f"  After grid dedup ({spacing_m}m cells): {len(deduped)} pits")

    pits = []
    for gcx, gcy, r in deduped:
        px, py = meta.pixel_to_proj(gcx, gcy)
        pits.append({
            "col": int(gcx), "row": int(gcy), "radius_px": int(r),
            "proj_x": round(px, 4), "proj_y": round(py, 4),   # in OP1's CRS
        })
    print(f"  Total pits detected: {len(pits)}  ({time.time()-t0:.1f}s)")
    return pits


# ── Step 2: Survival check on the OP3 orthomosaic (windowed) ──────────────────

# Decision thresholds.  These are DEFAULTS chosen from the visible OP3 imagery;
# the real value of storing every sub-signal (below) is that `evaluate.py` can
# re-tune them against the 25-30 known casualties without re-running detection.
EXG_THRESHOLD    = 20      # per-pixel excess-green (2G-R-B) vegetation cutoff
GREEN_FRAC_ALIVE = 0.06    # central-disc green fraction above which a sapling is "seen"
RING_ALIVE       = 0.10    # weeding-ring contrast above which a fresh clearing is "seen"
MIN_VALID_FRAC   = 0.50    # crops with less valid (non-nodata) centre coverage → no_data
SEARCH_RADIUS_M  = 0.8     # local search for the 1 m GPS error (kept < spacing/2 to
                           # avoid latching onto a neighbouring sapling at 2.5 m spacing)


def _disc_mask(size: int, r_in: float, r_out: float) -> np.ndarray:
    """Annulus mask r_in ≤ d < r_out about the window centre."""
    c = size // 2
    yy, xx = np.ogrid[:size, :size]
    d = (xx - c) ** 2 + (yy - c) ** 2
    return (d >= r_in * r_in) & (d < r_out * r_out)


def _survival_signals(crop_bgr: np.ndarray, crop_valid: np.ndarray,
                      res_m: float) -> Dict[str, float]:
    """
    Compute the three OP3 survival cues on a square crop centred on a pit.

      green_center  - ExG vegetation fraction in the central ~0.45 m disc
                      (a live sapling, even with minimal foliage, shows here)
      ring_contrast - weeding evidence: the cleared centre disc is *less*
                      vegetated and *smoother* than the surrounding annulus
      bright_center - cleared soil is brighter than the vegetated surround
    All are computed over valid (non-nodata) pixels only.
    """
    size = crop_bgr.shape[0]
    r_sap  = max(2.0, 0.45 / res_m)   # central sapling + immediate clearing
    r_weed = max(3.0, 0.55 / res_m)   # weeding clearing radius (~0.5 m)
    r_ctx  = max(5.0, 1.30 / res_m)   # surrounding context

    b, g, r = (crop_bgr[:, :, i].astype(np.int16) for i in range(3))
    exg  = (2 * g - r - b) > EXG_THRESHOLD
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    center = _disc_mask(size, 0, r_sap)      & crop_valid
    disc   = _disc_mask(size, 0, r_weed)     & crop_valid
    annul  = _disc_mask(size, r_weed, r_ctx) & crop_valid

    def frac(mask, sel):
        n = int(mask.sum())
        return float(sel[mask].mean()) if n else 0.0

    green_center = frac(center, exg)
    green_disc   = frac(disc,   exg)
    green_annul  = frac(annul,  exg)

    tex_disc  = float(gray[disc].std())  if disc.any()  else 0.0
    tex_annul = float(gray[annul].std()) if annul.any() else 0.0
    bri_disc  = float(gray[disc].mean())  if disc.any()  else 0.0
    bri_annul = float(gray[annul].mean()) if annul.any() else 0.0

    # Weeding ring: centre cleared of vegetation + smoother than the surround.
    ring_contrast = max(0.0, green_annul - green_disc) + max(0.0, tex_annul - tex_disc) / 60.0
    bright_center = max(0.0, (bri_disc - bri_annul) / 255.0)

    return {
        "green_center":  green_center,
        "green_annulus": green_annul,
        "ring_contrast": ring_contrast,
        "bright_center": bright_center,
    }


def classify_signals(sig: Dict[str, float], hough: bool) -> Tuple[str, float]:
    """
    Map the OP3 survival cues to a verdict.  Pure function of the signals so it
    can be unit-tested and recalibrated without touching the raster code.

      alive  if a sapling is visible (green LOCALISED to the centre — stands out
             against the surround) OR a fresh weeding clearing is present
      dead   otherwise (a casualty)

    Requiring the centre green to exceed the annulus is what stops a
    weed-overgrown casualty (uniformly green) being mistaken for a survivor.
    """
    sapling_seen = (sig["green_center"] >= GREEN_FRAC_ALIVE
                    and sig["green_center"] >= sig.get("green_annulus", 0.0) + 0.03)
    weeded = sig["ring_contrast"] >= RING_ALIVE or hough
    score = min(1.0, sig["green_center"] / GREEN_FRAC_ALIVE * 0.5
                     + sig["ring_contrast"] / max(RING_ALIVE, 1e-6) * 0.5)
    if sapling_seen or weeded:
        return "alive", min(0.99, 0.5 + 0.5 * score)
    return "dead", min(0.99, 0.5 + 0.5 * (1.0 - score))


def _hough_ring(crop_bgr: np.ndarray, res_m: float) -> bool:
    """True if a ~1 m-diameter circle (the weeding boundary) is found near centre."""
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    r1m  = 0.5 / res_m
    c    = crop_bgr.shape[0] // 2
    circ = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=crop_bgr.shape[0],
        param1=80, param2=30,
        minRadius=int(r1m * 0.6), maxRadius=int(r1m * 1.6),
    )
    if circ is None:
        return False
    for cx, cy, rr in np.round(circ[0]).astype(int):
        if (cx - c) ** 2 + (cy - c) ** 2 <= (0.5 / res_m) ** 2:   # centred within 0.5 m
            return True
    return False


def check_survival(
    pits: List[Dict],
    op3_meta: "RasterMeta",
    op1_crs_wkt: Optional[str] = None,
    tile_m: float = 1.4,
) -> List[Dict]:
    """
    For each OP1 pit, read a small OP3 window (windowed/bounded RAM), align it to
    the pit within the 1 m GPS error, and decide alive / dead from the weeding-ring
    + green-centre cues.

    Decision rule (calibratable — every sub-signal is stored in the output):
      no_data        if the pit's centre crop is mostly transparent nodata
      out_of_bounds  if the pit falls outside the OP3 footprint
      alive          if a sapling is visible (green_center ≥ GREEN_FRAC_ALIVE)
                     OR a fresh weeding clearing is present
                     (ring_contrast ≥ RING_ALIVE, or a Hough ring is found)
      dead           otherwise  → a casualty (the key output for judging)

    The alignment search MAXIMISES the weeding-ring evidence (the clearing is
    centred on *this* sapling), not greenness, so it does not drift onto a
    neighbour's foliage.
    """
    import rasterio
    op3_crs_wkt = op3_meta.crs_wkt
    res_m       = op3_meta.m_per_px
    half_px     = max(5, int(tile_m / res_m / 2))
    search_px   = max(0, int(SEARCH_RADIUS_M / res_m))
    pad         = half_px + search_px
    win_size    = 2 * pad

    print(f"  OP3 {'geographic' if op3_meta.is_geographic else 'projected'} CRS · "
          f"{res_m*100:.2f} cm/px · crop {2*half_px}px · search ±{search_px}px")
    print(f"  Checking {len(pits)} pit locations (windowed reads) …")
    t0 = time.time()

    need_reproj = bool(op1_crs_wkt and op3_crs_wkt and op1_crs_wkt != op3_crs_wkt)
    alive = dead = no_data = oob = 0
    results = []

    with rasterio.open(op3_meta.path) as ds:
        for i, pit in enumerate(pits):
            if need_reproj:
                ox3, oy3 = reproject_point(pit["proj_x"], pit["proj_y"], op1_crs_wkt, op3_crs_wkt)
            else:
                ox3, oy3 = pit["proj_x"], pit["proj_y"]
            col3, row3 = op3_meta.proj_to_pixel(ox3, oy3)

            # Reject pits clearly outside the raster (allow a partial edge window).
            if col3 < -pad or row3 < -pad or col3 >= op3_meta.width + pad or row3 >= op3_meta.height + pad:
                oob += 1
                results.append({**pit, "status": "out_of_bounds", "survival_conf": 0.0})
                continue

            bgr, a = _read_window_bgr_alpha(ds, col3 - pad, row3 - pad, win_size, win_size)
            valid_full = a > 32

            # Centre validity gate — pit sitting in a nodata hole.
            cyc = win_size // 2
            cgate = valid_full[cyc - half_px:cyc + half_px, cyc - half_px:cyc + half_px]
            if cgate.size == 0 or float(cgate.mean()) < MIN_VALID_FRAC:
                no_data += 1
                results.append({**pit, "status": "no_data", "survival_conf": 0.0})
                continue

            # Align to the weeding ring within the GPS error; keep the best cues.
            best = None
            step = max(1, search_px)
            for dy in range(-search_px, search_px + 1, step):
                for dx in range(-search_px, search_px + 1, step):
                    cy0, cy1 = cyc + dy - half_px, cyc + dy + half_px
                    cx0, cx1 = cyc + dx - half_px, cyc + dx + half_px
                    if cy0 < 0 or cx0 < 0 or cy1 > win_size or cx1 > win_size:
                        continue
                    sub_v = valid_full[cy0:cy1, cx0:cx1]
                    if sub_v.mean() < MIN_VALID_FRAC:
                        continue
                    sub = bgr[cy0:cy1, cx0:cx1]
                    sig = _survival_signals(sub, sub_v, res_m)
                    obj = sig["ring_contrast"] + 0.5 * sig["green_center"]
                    if best is None or obj > best[0]:
                        best = (obj, sig, sub)

            if best is None:
                no_data += 1
                results.append({**pit, "status": "no_data", "survival_conf": 0.0})
                continue

            _, sig, sub = best
            hough = _hough_ring(sub, res_m)
            status, conf = classify_signals(sig, hough)
            if status == "alive":
                alive += 1
            else:
                dead += 1

            lat, lon = to_wgs84(pit["proj_x"], pit["proj_y"], op1_crs_wkt)
            results.append({
                **pit,
                "status":        status,
                "green_center":  round(sig["green_center"], 4),
                "green_annulus": round(sig["green_annulus"], 4),
                "ring_contrast": round(sig["ring_contrast"], 4),
                "bright_center": round(sig["bright_center"], 4),
                "hough_ring":    bool(hough),
                "survival_conf": round(float(min(0.99, conf)), 4),
                "lat":           round(lat, 7),
                "lon":           round(lon, 7),
            })

            if (i + 1) % 500 == 0:
                print(f"    {i+1}/{len(pits)}  alive={alive} dead={dead} "
                      f"no_data={no_data} oob={oob}")

    print(f"  Done in {time.time()-t0:.1f}s  | alive={alive} dead={dead} "
          f"no_data={no_data} out_of_bounds={oob}")
    return results


# ── Step 3: Report ────────────────────────────────────────────────────────────

def generate_report(results: List[Dict], total_planted: int, site: str, out_dir: Path):
    """Save GeoJSON outputs and print the survival summary."""
    out_dir.mkdir(parents=True, exist_ok=True)

    alive   = [r for r in results if r["status"] == "alive"]
    dead    = [r for r in results if r["status"] == "dead"]
    no_data = [r for r in results if r["status"] == "no_data"]
    oob     = [r for r in results if r["status"] == "out_of_bounds"]
    classified = len(alive) + len(dead)
    survival_pct = len(alive) / classified * 100 if classified else 0.0

    print(f"\n{'='*60}")
    print(f"  SURVIVAL REPORT — {site.upper()}")
    print(f"{'='*60}")
    print(f"  Planted (ground truth) : {total_planted}")
    print(f"  Pits detected (OP1)    : {len(results)}")
    print(f"  Classified in OP3      : {classified}")
    print(f"  ALIVE                  : {len(alive)}  ({survival_pct:.1f}% of classified)")
    print(f"  DEAD / casualties      : {len(dead)}  ({100-survival_pct:.1f}%)")
    print(f"  Skipped (nodata hole)  : {len(no_data)}")
    print(f"  Skipped (out of bounds): {len(oob)}")
    print(f"{'='*60}")

    def make_geojson(items):
        feats = []
        for r in items:
            if "lat" not in r:
                continue
            feats.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                "properties": {
                    "status":        r["status"],
                    "confidence":    r.get("survival_conf", 0),
                    "green_center":  r.get("green_center"),
                    "ring_contrast": r.get("ring_contrast"),
                    "hough_ring":    r.get("hough_ring"),
                    "proj_x":        r.get("proj_x"),
                    "proj_y":        r.get("proj_y"),
                },
            })
        return {"type": "FeatureCollection", "features": feats}

    all_path = out_dir / f"{site}_all_detections.geojson"
    with open(all_path, "w") as f:
        json.dump(make_geojson(results), f, indent=2)
    print(f"  All detections : {all_path}")

    dead_path = out_dir / f"{site}_casualties.geojson"
    with open(dead_path, "w") as f:
        json.dump(make_geojson(dead), f, indent=2)
    print(f"  Casualties     : {dead_path}  ({len(dead)} points — judged vs ground truth)")

    summary = {
        "site": site, "total_planted": total_planted,
        "pits_detected": len(results), "classified": classified,
        "alive": len(alive), "dead": len(dead),
        "no_data": len(no_data), "out_of_bounds": len(oob),
        "survival_pct": round(survival_pct, 2),
    }
    with open(out_dir / f"{site}_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Highest-confidence casualties:")
    for r in sorted(dead, key=lambda x: x.get("survival_conf", 0), reverse=True)[:15]:
        print(f"    lat={r.get('lat'):.6f}  lon={r.get('lon'):.6f}  "
              f"green={r.get('green_center'):.3f}  ring={r.get('ring_contrast'):.3f}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--site", choices=["benkmura", "debadihi"], default="benkmura")
    p.add_argument("--out",  default=None)
    p.add_argument("--limit-pits", type=int, default=0,
                   help="Cap pits checked in OP3 (quick smoke test; 0 = all)")
    args = p.parse_args()

    cfg     = SITES[args.site]
    out_dir = Path(args.out) if args.out else SCRIPT_DIR / "results" / args.site

    print(f"\n{'='*60}\n  ORTHO PIPELINE — {args.site.upper()}")
    print(f"  OP1: {cfg['op1_mosaic'].name}\n  OP3: {cfg['op3_mosaic'].name}\n{'='*60}\n")
    t_total = time.time()

    # Step 1 — pits from OP1
    print("[Step 1] OP1 orthomosaic → detect pits")
    op1 = RasterMeta(str(cfg["op1_mosaic"]))
    print(f"  {op1.width}×{op1.height}px · {op1.m_per_px*100:.2f} cm/px · "
          f"CRS {op1.crs_wkt[:42] if op1.crs_wkt else '?'}…")
    pits = detect_pits(op1, spacing_m=cfg["spacing_m"])
    if not pits:
        print("  ERROR: no pits detected — check mosaic / Hough params."); return
    if args.limit_pits and len(pits) > args.limit_pits:
        print(f"  [smoke test] limiting {len(pits)} → {args.limit_pits} pits")
        pits = pits[:args.limit_pits]

    # Step 2 — survival from OP3
    print(f"\n[Step 2] OP3 orthomosaic → survival at {len(pits)} pits")
    op3 = RasterMeta(str(cfg["op3_mosaic"]))
    print(f"  {op3.width}×{op3.height}px · {op3.m_per_px*100:.2f} cm/px · "
          f"CRS {op3.crs_wkt[:42] if op3.crs_wkt else '?'}…")
    if op3.crs_wkt != op1.crs_wkt:
        print("  CRS differs OP1↔OP3 — reprojecting per pit on the fly")
    results = check_survival(pits, op3, op1_crs_wkt=op1.crs_wkt)

    # Step 3 — report
    print(f"\n[Step 3] Report")
    generate_report(results, cfg["total_planted"], args.site, out_dir)
    print(f"\n  Total pipeline time: {time.time()-t_total:.1f}s")


if __name__ == "__main__":
    main()
