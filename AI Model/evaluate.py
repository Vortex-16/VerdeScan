#!/usr/bin/env python3
"""
Casualty-detection evaluation — judging criterion #1.

The brief: "In Patch 1 and Patch 2, we know the exact locations (25-30 in each)
where the saplings have died on the ground.  So, the accuracy of the
participant's algorithm is a critical factor — whether it is able to detect
those 30 locations where the sapling has died."

So the headline metric is RECALL: of the known dead locations, how many did we
flag as a casualty within the GPS tolerance?  (Tolerance defaults to 1.5 m
because the drone metadata is only ~1 m accurate — no RTK — per challenge #3.)

Ground truth can be supplied as GeoJSON, CSV, KML or GPX (point geometries /
lat-lon columns).  Predictions are the pipeline's `*_casualties.geojson`; pass
`--all *_all_detections.geojson` too and the report also shows what status the
pipeline actually assigned at each known-dead location (alive = a real miss).

Usage
-----
  python "AI Model/evaluate.py" \
      --pred  "AI Model/results/benkmura/benkmura_casualties.geojson" \
      --truth path/to/known_dead_benkmura.csv \
      --all   "AI Model/results/benkmura/benkmura_all_detections.geojson" \
      --tol   1.5

  # No ground-truth file yet?  Prove the harness works end-to-end:
  python "AI Model/evaluate.py" \
      --pred "AI Model/results/benkmura/benkmura_casualties.geojson" --demo 30
"""

import os, sys, json, math, csv, argparse, xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ── geometry ──────────────────────────────────────────────────────────────────

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


# ── loaders (return list of (lat, lon)) ──────────────────────────────────────

def _from_geojson(path: str) -> List[Tuple[float, float]]:
    data = json.load(open(path, encoding="utf-8"))
    pts = []
    for feat in data.get("features", []):
        geom = feat.get("geometry") or {}
        if geom.get("type") == "Point":
            lon, lat = geom["coordinates"][:2]
            pts.append((float(lat), float(lon)))
    return pts


def _from_csv(path: str) -> List[Tuple[float, float]]:
    pts = []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return pts
    header = [h.strip().lower() for h in rows[0]]
    lat_i = lon_i = None
    for i, h in enumerate(header):
        if h in ("lat", "latitude", "y"):
            lat_i = i
        elif h in ("lon", "lng", "long", "longitude", "x"):
            lon_i = i
    start = 1
    if lat_i is None or lon_i is None:        # headerless → assume lat,lon
        lat_i, lon_i, start = 0, 1, 0
    for r in rows[start:]:
        if len(r) <= max(lat_i, lon_i):
            continue
        try:
            pts.append((float(r[lat_i]), float(r[lon_i])))
        except ValueError:
            continue
    return pts


def _from_kml_gpx(path: str) -> List[Tuple[float, float]]:
    """Parse KML <coordinates>lon,lat[,alt]</coordinates> or GPX wpt/trkpt lat/lon."""
    pts = []
    txt = open(path, encoding="utf-8").read()
    root = ET.fromstring(txt)
    def local(tag): return tag.split("}")[-1].lower()
    for el in root.iter():
        t = local(el.tag)
        if t == "coordinates" and el.text:                 # KML
            for tok in el.text.replace("\n", " ").split():
                parts = tok.split(",")
                if len(parts) >= 2:
                    pts.append((float(parts[1]), float(parts[0])))
        elif t in ("wpt", "trkpt", "rtept"):               # GPX
            la, lo = el.get("lat"), el.get("lon")
            if la and lo:
                pts.append((float(la), float(lo)))
    return pts


def load_points(path: str) -> List[Tuple[float, float]]:
    ext = Path(path).suffix.lower()
    if ext in (".geojson", ".json"):
        return _from_geojson(path)
    if ext == ".csv":
        return _from_csv(path)
    if ext in (".kml", ".gpx", ".xml"):
        return _from_kml_gpx(path)
    raise ValueError(f"Unsupported ground-truth format: {ext}")


# ── matching ──────────────────────────────────────────────────────────────────

def greedy_match(truth, pred, tol_m: float):
    """
    Greedily match each ground-truth point to its nearest unused prediction
    within tol_m.  Returns (matches, unmatched_truth_idx).
    matches: list of (truth_idx, pred_idx, distance_m)
    """
    used = set()
    matches, missed = [], []
    for ti, (tlat, tlon) in enumerate(truth):
        best_j, best_d = -1, tol_m + 1e9
        for pj, (plat, plon) in enumerate(pred):
            if pj in used:
                continue
            d = haversine_m(tlat, tlon, plat, plon)
            if d < best_d:
                best_d, best_j = d, pj
        if best_j >= 0 and best_d <= tol_m:
            used.add(best_j)
            matches.append((ti, best_j, best_d))
        else:
            missed.append(ti)
    return matches, missed


def nearest(truth_pt, pred, props):
    """Nearest prediction (any status) to a truth point → (dist, status)."""
    tlat, tlon = truth_pt
    best_d, best_status = 1e18, None
    for (plat, plon), pr in zip(pred, props):
        d = haversine_m(tlat, tlon, plat, plon)
        if d < best_d:
            best_d, best_status = d, pr.get("status")
    return best_d, best_status


def _load_pred_with_props(path: str):
    data = json.load(open(path, encoding="utf-8"))
    pts, props = [], []
    for feat in data.get("features", []):
        g = feat.get("geometry") or {}
        if g.get("type") == "Point":
            lon, lat = g["coordinates"][:2]
            pts.append((float(lat), float(lon)))
            props.append(feat.get("properties", {}))
    return pts, props


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred",  required=True, help="predicted casualties GeoJSON")
    ap.add_argument("--truth", help="ground-truth dead locations (geojson/csv/kml/gpx)")
    ap.add_argument("--all",   dest="all_path",
                    help="all-detections GeoJSON → also report predicted status at each truth point")
    ap.add_argument("--tol", type=float, default=1.5,
                    help="match tolerance in metres (default 1.5 ≈ 1 m GPS error)")
    ap.add_argument("--demo", type=int, default=0,
                    help="no truth file: synthesise N jittered truth points from --pred to self-test")
    args = ap.parse_args()

    pred = load_points(args.pred)
    print(f"Predicted casualties : {len(pred)}  ({args.pred})")

    if args.demo and not args.truth:
        # Self-test: jitter N real predictions by < tol and confirm we recover them.
        import random
        rng = random.Random(0)
        chosen = pred[:args.demo] if len(pred) >= args.demo else pred
        truth = []
        for lat, lon in chosen:
            dm = args.tol * 0.5
            dlat = (rng.random() - 0.5) * 2 * dm / 111_000
            dlon = (rng.random() - 0.5) * 2 * dm / (111_000 * math.cos(math.radians(lat)))
            truth.append((lat + dlat, lon + dlon))
        print(f"[demo] synthesised {len(truth)} jittered truth points (±{args.tol*0.5:.2f} m)")
    else:
        if not args.truth:
            print("\nNo --truth file supplied.  Provide the 25-30 known dead GPS points as\n"
                  "GeoJSON/CSV/KML/GPX, or run with --demo 30 to self-test the harness.")
            return
        truth = load_points(args.truth)
        print(f"Ground-truth dead    : {len(truth)}  ({args.truth})")

    if not truth:
        print("No ground-truth points loaded — nothing to score."); return

    matches, missed = greedy_match(truth, pred, args.tol)
    recall = len(matches) / len(truth) if truth else 0.0
    dists  = [d for _, _, d in matches]
    mean_d = sum(dists) / len(dists) if dists else float("nan")

    print(f"\n{'='*56}\n  CASUALTY DETECTION — recall vs known dead\n{'='*56}")
    print(f"  Tolerance            : {args.tol:.2f} m")
    print(f"  Known dead locations : {len(truth)}")
    print(f"  Detected (recall)    : {len(matches)}/{len(truth)}  = {recall*100:.1f}%")
    print(f"  Missed               : {len(missed)}")
    if dists:
        print(f"  Match distance (m)   : mean {mean_d:.2f} · "
              f"median {sorted(dists)[len(dists)//2]:.2f} · max {max(dists):.2f}")

    # If we have all detections, explain WHY each truth point was hit/missed.
    if args.all_path and os.path.exists(args.all_path):
        all_pts, all_props = _load_pred_with_props(args.all_path)
        print(f"\n  Per-truth-point diagnosis (nearest detection of any status):")
        hit = {ti for ti, _, _ in matches}
        for ti, tpt in enumerate(truth):
            d, status = nearest(tpt, all_pts, all_props)
            tag = "HIT " if ti in hit else "MISS"
            print(f"    [{tag}] truth#{ti:02d}  nearest={d:5.2f}m  pipeline_status={status}")
        # A miss whose nearest detection is 'alive' = false-negative we could fix
        # by recalibrating thresholds; a miss with no nearby detection = pit missed.

    print(f"\n  NOTE: recall is the headline metric.  Precision over all predicted\n"
          f"  casualties is not meaningful here — ground truth marks only the 25-30\n"
          f"  confirmed deaths, not every real casualty in the patch.")


if __name__ == "__main__":
    main()
