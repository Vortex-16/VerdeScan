# VerdeScan — AI-Powered Afforestation Monitoring

Proof-of-concept for the Odisha Forest Department's drone-based afforestation monitoring program.

**Problem:** 5 crore saplings planted annually across Odisha. Are they surviving? Manual survival walks are slow, expensive, and imprecise. The department needs to know *exactly* which GPS locations have casualties.

**Solution:** VerdeScan analyses orthomosaic drone imagery to produce a GeoJSON file of every dead sapling's GPS coordinates — directly verifiable against field ground truth.

---

## How It Works

```
OP1 orthomosaic  →  Detect all planting pits  →  GPS coordinates for ~8,000 pits
                                                            |
OP3 orthomosaic  →  Classify each pit location  →  alive / dead / no_sapling
                                                            |
                                              Casualties GeoJSON (lat/lon per dead sapling)
```

This architecture matches the problem statement recommendation: *"use coordinate information from OP1 images, as pits can easily be identified. Match with OP3 to check sapling survival."*

---

## Technology Stack

### Backend
| Component | Technology |
|-----------|------------|
| API Framework | FastAPI + Uvicorn |
| ML Model | ResNet18 pretrained (PyTorch) — 3-class: alive / dead / no_sapling |
| Computer Vision | OpenCV — Hough circles, CLAHE, darkness validation |
| Georeferencing | rasterio + pyproj — GeoTIFF CRS → WGS84 lat/lon |
| Async Processing | asyncio task queue with GPU batched inference |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | Next.js 14 + TypeScript |
| Styling | Tailwind CSS |
| Animations | Framer Motion + GSAP |

### ML Model (V2)
- **Architecture:** ResNet18 + ImageNet pretrained weights + custom 3-class head
- **Training data:** 15,000 tiles from all survey stages (Pre-Pitting, Post-Pitting, Post-Planting, Post-SW)
- **Validation accuracy:** 99.9% on held-out source images
- **Classes:** `alive` (live sapling) / `dead` (died sapling) / `no_sapling` (bare ground)

---

## Running the System

### Prerequisites
- Python 3.10+ with CUDA-capable GPU (recommended)
- Node.js 18+

### Backend
```bash
cd "AI Model"
pip install -r requirements.txt
python run_server.py
```
API available at http://localhost:8000 | Docs at http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Dashboard at http://localhost:3000

### Full Orthomosaic Pipeline (primary analysis)
```bash
cd "AI Model"
python ortho_pipeline.py --site benkmura
python ortho_pipeline.py --site debadihi
```
Outputs: `results/{site}/{site}_casualties.geojson` — load in Google Earth or QGIS to verify against ground truth.

### (Re)train the model
```bash
cd "AI Model"
python build_dataset_v2.py           # builds 15k-tile dataset from raw imagery
python train_improved.py --dataset processed_dataset_v2
cp ml_models/forest_model_improved.pth ml_models/forest_model.pth
```

---

## Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze-site?site=benkmura` | POST | Run full orthomosaic pipeline (background) |
| `/api/site-result/{site}` | GET | Survival stats + full casualty GPS list |
| `/api/upload-image` | POST | Upload single image for quick analysis |
| `/api/task-status/{task_id}` | GET | Poll processing progress |
| `/api/stats` | GET | Global statistics |
| `/health` | GET | System health |

---

## Project Structure

```
VerdeScan/
├── AI Model/
│   ├── api/main.py              — FastAPI server + all endpoints
│   ├── core/
│   │   ├── forest_processor.py  — CNN inference (auto-detects V1/V2 model)
│   │   ├── task_manager.py      — Async processing queue
│   │   ├── data_manager.py      — JSON persistence + CSV export
│   │   └── health_classifier.py — HSV fallback classifier
│   ├── models/
│   │   ├── data_structures.py   — Dataclasses (TreeResult, ProcessingResult…)
│   │   └── ml_processor.py      — Abstract base + Gemini integration
│   ├── ml_models/
│   │   └── forest_model.pth     — Active model (ResNet18, 3-class, 99.9% val acc)
│   ├── ortho_pipeline.py        — Orthomosaic pit-detection + survival pipeline
│   ├── build_dataset_v2.py      — Dataset builder from raw drone imagery
│   ├── train_improved.py        — Model training script
│   ├── tests/test_pipeline.py   — Test suite (6 tests, all passing)
│   ├── config.py                — Pydantic settings
│   └── requirements.txt
├── frontend/                    — Next.js dashboard
│   └── src/
│       ├── app/dashboard/       — Dashboard pages
│       ├── components/          — Shared UI components
│       ├── hooks/useCounter.ts  — Animated counter
│       └── lib/api.ts           — API client
├── Data/                        — Raw drone imagery (not committed)
├── render.yaml                  — Render.com deployment config
└── README.md
```

---

## Results (Benkmura VF)

| Metric | Value |
|--------|-------|
| Pits detected on OP1 mosaic | 3,900 |
| In-field detections on OP3 | 2,921 |
| Alive | 881 (30.2%) |
| Dead / Casualties | 2,040 (69.8%) |
| Inference time (GPU batch=256) | 6 seconds |
| Total pipeline time | ~7 minutes |
| Output | `results/benkmura/benkmura_casualties.geojson` |

---

## Cloud Deployment

Configured for Render.com via `render.yaml`.

```bash
# Backend
pip install -r "AI Model/requirements.txt"
python "AI Model/run_server.py"

# Frontend
cd frontend && npm install && npm run build && npm start
```

Set `NEXT_PUBLIC_API_URL` env var to your deployed backend URL.
