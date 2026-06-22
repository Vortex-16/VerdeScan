# VerdeScan — Drone-Based Afforestation Monitoring

AI-powered system for monitoring sapling survival in afforestation programs using drone orthomosaic imagery. Built for the Odisha Forest Department problem statement.

## Problem Statement

The Odisha Forest Department plants ~5 crore trees annually. After planting (OP2) and weeding (OP3), a survival walk is conducted. The question: **can drone imagery pinpoint exactly which saplings have died?**

The judging criteria: match the 25–30 exact GPS locations of dead saplings known on the ground.

---

## How It Works

```
OP1 Orthomosaic (Post-Pitting)
        |
  Detect all planting pits (Hough circles + darkness filter + 2.5m grid dedup)
  — streamed via rasterio windows, so multi-GB mosaics never load into RAM
        |
  Extract GPS lat/lon for every pit  (GeoTIFF CRS → WGS84, reprojected per pit
  when OP1 and OP3 use different CRSs)
        |  [thousands of GPS anchor points]
        |
OP3 Orthomosaic (Post-SW / Survival Walk = the weeding survey)
        |
  For each pit GPS → project to OP3 pixel → read a small window
        |
  Survival decision from the WEEDING signal, not greenness:
    • ring_contrast — a freshly-cleared ~1 m soil disc (the brief: weeding
      "clears a 1 m diameter of soil around the sapling, visible from the sky")
    • green_center  — localised foliage standing out against cleared soil
    • a ±0.8 m local search absorbs the ~1 m GPS error (no RTK)
  Why not the CNN / plain greenness?  Saplings have "minimal foliage" and a
  dead spot can be greener (weeds) than a weeded survivor — challenge #2.
  nodata holes and out-of-OP3-footprint pits are excluded, not guessed.
        |
  Output: survival % + GeoJSON of every casualty with GPS coordinates
        |
  evaluate.py → recall of the 25–30 known dead points (judging criterion #1)
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Build the training dataset
Requires the raw drone imagery in `../Data/Image/`:
```bash
python build_dataset_v2.py
# Outputs: processed_dataset_v2/{alive,dead,no_sapling}/ — 15,000 tiles
```

### 3. Train the model
```bash
python train_improved.py --dataset processed_dataset_v2 --batch 128 --num-workers 6 --cache
# Saves: ml_models/forest_model_improved.pth
#        ml_models/forest_model_improved.json  (metadata sidecar)
#
# NOTE: the reported val accuracy is high because the training LABELS are a
# green-vs-brown colour rule (build_dataset_v2.label_tile), so the CNN largely
# relearns that colour rule — it is NOT a measure of true survival accuracy.
# The orthomosaic survival pipeline below therefore does NOT use this CNN; it
# uses the physical weeding-circle signal and is scored by evaluate.py against
# the known dead GPS points. The CNN remains only for the single-image upload demo.
```

Deploy the trained model:
```bash
cp ml_models/forest_model_improved.pth ml_models/forest_model.pth
cp ml_models/forest_model_improved.json ml_models/forest_model.json
```

> **Pre-trained weights available on Kaggle** — skip steps 2–3 if you don't have the raw imagery:
> - Model: [dealer09/verdescan-forest-model](https://www.kaggle.com/models/dealer09/verdescan-forest-model)
> - Dataset: [dealer09/verdescan-afforestation-tiles](https://www.kaggle.com/datasets/dealer09/verdescan-afforestation-tiles)

### 4. Run the orthomosaic survival pipeline
```bash
python ortho_pipeline.py --site benkmura
python ortho_pipeline.py --site debadihi
```

Outputs (in `results/{site}/`):
- `{site}_casualties.geojson` — GPS coordinates of every dead sapling (the judged output)
- `{site}_all_detections.geojson` — full results: alive / dead / no_data / out_of_bounds,
  each with `green_center` + `ring_contrast` so thresholds can be recalibrated
- `{site}_summary.json` — counts + survival %

### 4b. Score against ground truth (judging criterion #1)
```bash
# Provide the 25–30 known dead GPS points as GeoJSON / CSV / KML / GPX:
python evaluate.py \
    --pred  results/benkmura/benkmura_casualties.geojson \
    --truth path/to/known_dead_benkmura.csv \
    --all   results/benkmura/benkmura_all_detections.geojson --tol 1.5
# Reports recall (of the known dead), match distances, and the pipeline status
# at each known-dead point. No ground-truth file yet? `--demo 30` self-tests it.
```

### 5. Start the API server
```bash
python run_server.py
```

Then start the Next.js frontend:
```bash
cd ../frontend && npm run dev
```

Dashboard: http://localhost:3000 | API docs: http://localhost:8000/docs

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload-image` | POST | Upload single drone image for processing |
| `/api/process-batch` | POST | Batch upload up to 10 images |
| `/api/task-status/{task_id}` | GET | Poll processing progress |
| `/api/analyze-site?site=benkmura` | POST | Run full orthomosaic pipeline |
| `/api/site-result/{site}` | GET | Survival stats + casualty GPS list |
| `/api/patches/all` | GET | All processed patch results |
| `/api/patch/{patch_id}` | GET | Single patch detail |
| `/api/stats` | GET | Global statistics |
| `/api/export/{patch_id}` | GET | Download CSV |
| `/health` | GET | System health check |

---

## Kaggle Resources

| Resource | Link |
|----------|------|
| **Trained Model** | [dealer09/verdescan-forest-model](https://www.kaggle.com/models/dealer09/verdescan-forest-model) |
| **Training Dataset** (15k tiles) | [dealer09/verdescan-afforestation-tiles](https://www.kaggle.com/datasets/dealer09/verdescan-afforestation-tiles) |

---

## ML Model

| | V1 (old) | V2 (current) |
|--|---------|-------------|
| Architecture | SimpleCNN (4 layers) | ResNet18 (pretrained ImageNet) |
| Classes | 2 (pit / sapling) | 3 (alive / dead / no_sapling) |
| Training data | 4,028 tiles, 2 dates | 15,000 tiles, all survey stages |
| What it learned | "June vs August" (date bias) | a green-vs-brown colour rule (labels are colour-derived) |
| Val accuracy | 100% (trivial task) | high, but tautological — measures relearning the colour labels, not survival |
| Used for survival? | no | **no** — the ortho pipeline uses the weeding-circle signal; the CNN is demo-only |
| Health classifier | Separate HSV rules | Built into CNN |

---

## Project Structure

```
AI Model/
├── api/main.py             — FastAPI server + all endpoints
├── core/
│   ├── forest_processor.py — CNN inference engine (V1/V2 auto-detect)
│   ├── health_classifier.py — HSV fallback health classifier
│   ├── task_manager.py     — Async task queue
│   ├── data_manager.py     — JSON persistence + CSV export
│   └── cv_processor.py     — Image metadata extraction
├── models/
│   ├── data_structures.py  — All dataclasses (TreeResult, ProcessingResult…)
│   └── ml_processor.py     — Abstract base + Gemini integration
├── ml_models/
│   └── forest_model.pth    — Active model (ResNet18, 3-class)
├── ortho_pipeline.py       — Full orthomosaic survival analysis pipeline
├── build_dataset_v2.py     — Dataset builder from raw drone imagery
├── train_improved.py       — Model training script
├── tests/test_pipeline.py  — Pipeline test suite (6 tests)
├── config.py               — Pydantic settings
├── logger.py               — Structured logging
└── requirements.txt        — Python dependencies
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | 0.0.0.0 | Server host |
| `API_PORT` | 8000 | Server port |
| `MAX_CONCURRENT_REQUESTS` | 5 | Concurrent image processing |
| `MAX_FILE_SIZE` | 10485760 | Upload limit (10 MB) |
| `DETECTION_CONFIDENCE_THRESHOLD` | 0.2 | CNN detection minimum confidence |
| `GEMINI_API_KEY` | None | Optional Gemini Vision enhancement |
| `GEMINI_MODEL` | gemini-1.5-flash | Gemini model (vision-capable) |
| `LOG_LEVEL` | INFO | Logging verbosity |

Copy `.env.example` to `.env` and set values as needed.

---

## Running Tests

```bash
pytest tests/test_pipeline.py -v
# 6 passed
```

---

## Performance

| Operation | Time |
|-----------|------|
| Single image upload + classification | ~1–3s (GPU) |
| Orthomosaic pit detection (27k×23k px) | ~6 min |
| Survival check (3,900 pits, GPU batch) | ~6s |
| Full Benkmura pipeline end-to-end | ~7 min |
