#!/usr/bin/env python3
"""
Build the V2 3-class training dataset from ALL available raw drone imagery.

Class design
------------
  alive       - Live sapling present
                Sources: Post-Planting (green tiles) + Post-SW (green tiles)

  dead        - Dead sapling / died planting location
                Sources: Post-SW (brown/low-green tiles)

  no_sapling  - No planted content (empty ground, pits, paths)
                Sources: Pre-Pitting + Post-Pitting (brown tiles)

Why 3 classes?
--------------
  The old 2-class model (pit vs sapling) only tells you WHEN the image was
  taken (June=pit, August=sapling).  The 3-class model teaches the CNN to
  recognise alive vs dead vs empty from visual content alone, which is what
  the health monitoring application actually needs.

Usage
-----
  python "AI Model/build_dataset_v2.py"

  Outputs to: AI Model/processed_dataset_v2/{alive,dead,no_sapling}/
  Then run:   python "AI Model/train_improved.py"
"""

import os, cv2, numpy as np, random, time
from pathlib import Path
from collections import defaultdict

# ── configuration ─────────────────────────────────────────────────────────────

SCRIPT_DIR      = Path(__file__).resolve().parent
DATA_ROOT       = SCRIPT_DIR.parent / "Data" / "Image"
OUT_ROOT        = SCRIPT_DIR / "processed_dataset_v2"

TARGET_PER_CLASS = 5_000   # tiles saved per class
STRIDE           = 224
TILE             = 224
JPEG_Q           = 85
SEED             = 42

# ── colour helpers (HSV) ──────────────────────────────────────────────────────

def _green(hsv: np.ndarray) -> float:
    m = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
    return cv2.countNonZero(m) / (TILE * TILE)

def _brown(hsv: np.ndarray) -> float:
    m = cv2.inRange(hsv, np.array([5, 30, 20]), np.array([25, 255, 200]))
    return cv2.countNonZero(m) / (TILE * TILE)

def _bright(hsv: np.ndarray) -> float:
    return float(np.mean(hsv[:, :, 2])) / 255.0


# ── tile labeller ─────────────────────────────────────────────────────────────

def label_tile(bgr: np.ndarray, stage: str):
    """
    Return 'alive', 'dead', 'no_sapling', or None (skip / ambiguous).
    stage is a normalised key: prepitting | postpitting | postplanting | postsw
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    g   = _green(hsv)
    b   = _brown(hsv)
    br  = _bright(hsv)

    if stage == 'prepitting':
        # Virgin ground — definitely no sapling.
        # Accept brownish tiles; skip green patches (existing native vegetation
        # that was already there — we don't want the model to confuse it with saplings).
        if b > 0.30:
            return 'no_sapling'
        return None

    if stage == 'postpitting':
        # Dug pits, no saplings yet.
        # Bare brown soil or straw — all counts as no_sapling.
        if b > 0.35 or (br < 0.55 and g < 0.08):
            return 'no_sapling'
        return None

    if stage == 'postplanting':
        # Freshly planted saplings — should be predominantly green.
        if g > 0.28:
            return 'alive'
        # Path / bare patch within the planting area.
        if b > 0.45 and g < 0.05:
            return 'no_sapling'
        return None   # mixed / uncertain — skip

    if stage == 'postsw':
        # Survival-walk survey: the same field months later.
        # Green → still alive.  Brown + no green → died.
        if g > 0.25:
            return 'alive'
        if b > 0.28 and g < 0.08:
            return 'dead'
        return None   # ambiguous mid-state — skip

    return None


# ── source discovery ──────────────────────────────────────────────────────────

def find_sources() -> dict:
    """
    Walk DATA_ROOT and return {stage_key: [img_path, ...]} with duplicates removed.
    stage_key ∈ {'prepitting', 'postpitting', 'postplanting', 'postsw'}
    """
    IMG_EXTS = {'.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG'}
    buckets: dict = defaultdict(dict)   # stage → {filename: path}

    for root, _dirs, files in os.walk(DATA_ROOT):
        rl = root.lower().replace('\\', '/')

        if   'pre-pitting'  in rl or 'pre_pitting'  in rl:
            key = 'prepitting'
        elif 'post-pitting' in rl or 'postpitting'  in rl or \
             ('pitting' in rl and '/pre' not in rl):
            key = 'postpitting'
        elif 'planting' in rl:
            key = 'postplanting'
        elif 'post-sw' in rl or 'postsw' in rl or \
             ('/sw' in rl and 'post' in rl):
            key = 'postsw'
        else:
            continue

        for f in files:
            if Path(f).suffix in IMG_EXTS:
                # De-duplicate: same filename from nested/duplicate folder structure
                # is the same physical image — keep only one path per filename.
                if f not in buckets[key]:
                    buckets[key][f] = os.path.join(root, f)

    sources = {k: list(v.values()) for k, v in buckets.items()}

    print("Source images discovered (after de-duplication):")
    for k in ('prepitting', 'postpitting', 'postplanting', 'postsw'):
        print(f"  {k:15s}: {len(sources.get(k, [])):5d} images")
    return sources


# ── tile extractor ────────────────────────────────────────────────────────────

def yield_tiles(img_path: str, stage: str, rng: random.Random):
    """
    Yield (bgr_tile, label) for every passing tile in the image.
    Positions are shuffled so early exits give spatially diverse samples.
    """
    img = cv2.imread(img_path)
    if img is None:
        return
    h, w = img.shape[:2]
    if h < TILE or w < TILE:
        return

    positions = [
        (x, y)
        for y in range(0, h - TILE + 1, STRIDE)
        for x in range(0, w - TILE + 1, STRIDE)
    ]
    rng.shuffle(positions)

    for x, y in positions:
        tile  = img[y:y + TILE, x:x + TILE]
        label = label_tile(tile, stage)
        if label:
            yield tile, label


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    rng = random.Random(SEED)

    # ── prepare output dirs ───────────────────────────────────────────────────
    classes = ['alive', 'dead', 'no_sapling']
    out_dirs = {}
    for cls in classes:
        d = OUT_ROOT / cls
        d.mkdir(parents=True, exist_ok=True)
        out_dirs[cls] = d

    counts: dict = {c: 0 for c in classes}
    t_start = time.time()

    # ── discover all source images ────────────────────────────────────────────
    sources = find_sources()

    # ── stage processing order ────────────────────────────────────────────────
    # Each stage is paired with the classes it can contribute to.
    # We stop scanning a stage's images once all its target classes are full.
    stage_plan = [
        ('prepitting',   ['no_sapling']),
        ('postpitting',  ['no_sapling']),
        ('postplanting', ['alive', 'no_sapling']),
        ('postsw',       ['alive', 'dead']),
    ]

    for stage_key, relevant_classes in stage_plan:
        img_paths = sources.get(stage_key, [])
        if not img_paths:
            print(f"\n[{stage_key}] No images found — skipping")
            continue

        # Skip entire stage if every class it feeds is already full
        if all(counts[c] >= TARGET_PER_CLASS for c in relevant_classes):
            print(f"\n[{stage_key}] All target classes full — skipping")
            continue

        rng.shuffle(img_paths)
        n_imgs = len(img_paths)
        print(f"\n[{stage_key}] Scanning up to {n_imgs} images "
              f"(targets: {', '.join(relevant_classes)})")

        imgs_done = 0
        for img_path in img_paths:
            # Early exit when all relevant classes for this stage are full
            if all(counts[c] >= TARGET_PER_CLASS for c in relevant_classes):
                break

            try:
                for tile, label in yield_tiles(img_path, stage_key, rng):
                    if counts[label] < TARGET_PER_CLASS:
                        fn  = f"{label}_{counts[label]:06d}.jpg"
                        out = str(out_dirs[label] / fn)
                        cv2.imwrite(out, tile, [cv2.IMWRITE_JPEG_QUALITY, JPEG_Q])
                        counts[label] += 1
            except Exception as e:
                print(f"  [warn] {os.path.basename(img_path)}: {e}")

            imgs_done += 1
            if imgs_done % 100 == 0:
                status = "  |  ".join(f"{c}={counts[c]}/{TARGET_PER_CLASS}" for c in classes)
                elapsed = time.time() - t_start
                print(f"  {imgs_done:4d}/{n_imgs} images  |  {status}  |  {elapsed:.0f}s")

        status = "  |  ".join(f"{c}={counts[c]}" for c in classes)
        print(f"  Done ({imgs_done} images).  {status}")

    # ── summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    total   = sum(counts.values())
    print(f"\n{'='*60}")
    print(f"Dataset V2 built in {elapsed:.0f}s")
    print(f"{'='*60}")
    for cls in classes:
        pct = counts[cls] / total * 100 if total else 0
        print(f"  {cls:12s}: {counts[cls]:6d} tiles  ({pct:.1f}%)")
    print(f"  {'TOTAL':12s}: {total:6d} tiles")
    print(f"\nOutput: {OUT_ROOT}")
    print("\nNext step:")
    print('  python "AI Model/train_improved.py" --dataset processed_dataset_v2')


if __name__ == "__main__":
    main()
