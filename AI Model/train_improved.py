#!/usr/bin/env python3
"""
Improved forest model training.

Key improvements over train_forest_model.py:
  1. ResNet18 with pretrained ImageNet weights (replaces 4-layer SimpleCNN)
  2. Source-image-level train/val split (prevents tile leakage from same flight)
  3. Comprehensive data augmentation (flips, rotation, colour jitter, erasing)
  4. Learning-rate scheduling (ReduceLROnPlateau)
  5. Early stopping on validation loss
  6. Full confusion matrix, F1, precision, recall output
  7. Saves best checkpoint (not just last epoch)
"""

import os, re, random, time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
import torchvision.transforms as transforms
import cv2
from pathlib import Path
from collections import defaultdict

# ── helpers ───────────────────────────────────────────────────────────────────

def source_name(filename: str) -> str:
    """Strip the _x_y.jpg tile coordinates to get the source drone image name."""
    return re.sub(r'_\d+_\d+\.jpg$', '', filename)


def load_tiles_by_source(data_path: str):
    """
    Returns tiles grouped by source image name.
    Class mapping: pit → 0, sapling → 1  (alphabetical = ImageFolder order)
    """
    by_source = defaultdict(list)   # source_name → [(path, label)]
    class_dirs = sorted(os.listdir(data_path))          # ['pit', 'sapling']
    for label, cls in enumerate(class_dirs):
        cls_dir = os.path.join(data_path, cls)
        if not os.path.isdir(cls_dir):
            continue
        for f in os.listdir(cls_dir):
            if not f.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            src = source_name(f)
            by_source[src].append((os.path.join(cls_dir, f), label))
    return by_source, class_dirs


class TileDataset(Dataset):
    def __init__(self, tile_list, transform=None, cache_in_ram=False):
        self.tiles     = tile_list
        self.transform = transform
        self._cache    = {}          # path → decoded numpy array

        if cache_in_ram:
            print(f"  Caching {len(tile_list)} images in RAM...", flush=True)
            for path, _ in tile_list:
                if path not in self._cache:
                    img = cv2.imread(path)
                    if img is not None:
                        self._cache[path] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            print(f"  Cache complete — {len(self._cache)} images in RAM (zero disk I/O from now on)",
                  flush=True)

    def __len__(self):
        return len(self.tiles)

    def __getitem__(self, idx):
        path, label = self.tiles[idx]
        # Serve from RAM cache if available, otherwise read from disk
        if path in self._cache:
            img = self._cache[path].copy()   # copy so augmentation doesn't corrupt cache
        else:
            img = cv2.imread(path)
            if img is None:
                return torch.zeros(3, 224, 224), label
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if self.transform:
            img = self.transform(img)
        return img, label


# ── augmentation ──────────────────────────────────────────────────────────────

TRAIN_TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05),
    transforms.RandomGrayscale(p=0.05),          # rare grayscale = lighting robustness
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    transforms.RandomErasing(p=0.1, scale=(0.02, 0.08)),   # simulate occlusion
])

VAL_TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


# ── model ─────────────────────────────────────────────────────────────────────

def build_model(num_classes: int, device):
    """ResNet18 pretrained on ImageNet, final FC replaced for num_classes."""
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    # Replace classifier head
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(in_features, num_classes),
    )
    return model.to(device)


# ── metrics ───────────────────────────────────────────────────────────────────

def evaluate(model, loader, criterion, device, class_names):
    model.eval()
    loss_sum = 0.0
    all_preds, all_labels = [], []
    with torch.no_grad():
        for data, labels in loader:
            data, labels = data.to(device), labels.to(device)
            out = model(data)
            loss_sum += criterion(out, labels).item()
            preds = torch.argmax(out, 1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    n = len(class_names)
    cm = np.zeros((n, n), dtype=int)
    for p, l in zip(all_preds, all_labels):
        cm[l][p] += 1

    acc = np.diag(cm).sum() / cm.sum()
    metrics = {}
    for i, cls in enumerate(class_names):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec  = tp / (tp + fn) if (tp + fn) else 0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        metrics[cls] = dict(precision=prec, recall=rec, f1=f1)

    return loss_sum / len(loader), acc, cm, metrics


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="processed_dataset_v2",
                        help="Dataset folder name (relative to script dir)")
    parser.add_argument("--epochs",      type=int,   default=20)
    parser.add_argument("--batch",       type=int,   default=128,
                        help="Batch size. 128 is optimal for RTX 4050 6GB + 16GB RAM.")
    parser.add_argument("--lr",          type=float, default=1e-4)
    parser.add_argument("--num-workers", type=int,   default=6,
                        help="DataLoader workers. 6 is optimal when RAM < 80%%.")
    parser.add_argument("--cache",       action="store_true", default=False,
                        help="Cache entire dataset in RAM before training (needs ~3 GB free).")
    args = parser.parse_args()

    random.seed(42)
    torch.manual_seed(42)

    SCRIPT_DIR = Path(__file__).resolve().parent
    DATA_PATH  = str(SCRIPT_DIR / args.dataset)
    SAVE_PATH  = str(SCRIPT_DIR / "ml_models" / "forest_model_improved.pth")
    BATCH        = args.batch
    EPOCHS       = args.epochs
    LR           = args.lr
    NUM_WORKERS  = args.num_workers
    CACHE_RAM    = args.cache
    PATIENCE     = 5
    VAL_FRAC     = 0.20

    # ── Hardware summary ──────────────────────────────────────────────────
    print(f"Workers : {NUM_WORKERS}  |  RAM cache: {'ON' if CACHE_RAM else 'OFF'}")
    print(f"Batch   : {BATCH}")
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        print(f"GPU     : {props.name}  VRAM={props.total_memory//1024**2} MB")
        # Enable TF32 for ~2x throughput on Ampere/Ada GPUs (RTX 40-series)
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32       = True
        torch.backends.cudnn.benchmark        = True
        # Allocate a fixed CUDA memory pool to avoid fragmentation across epochs
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"Dataset: {DATA_PATH}")

    # ── split by SOURCE IMAGE (not random tile) ────────────────────────────
    by_source, class_names = load_tiles_by_source(DATA_PATH)
    print(f"Classes: {class_names}")

    # Group source names by class
    sources_by_class = defaultdict(list)
    for src, tiles in by_source.items():
        cls_label = tiles[0][1]
        sources_by_class[cls_label].append(src)

    train_tiles, val_tiles = [], []
    for cls_label, srcs in sources_by_class.items():
        random.shuffle(srcs)
        n_val = max(1, int(len(srcs) * VAL_FRAC))
        val_srcs  = set(srcs[:n_val])
        train_srcs = set(srcs[n_val:])
        for src in train_srcs:
            train_tiles.extend(by_source[src])
        for src in val_srcs:
            val_tiles.extend(by_source[src])

    # Count per class
    for split_name, split in [("Train", train_tiles), ("Val", val_tiles)]:
        counts = defaultdict(int)
        for _, l in split: counts[class_names[l]] += 1
        print(f"  {split_name}: {dict(counts)}")

    train_ds = TileDataset(train_tiles, TRAIN_TRANSFORM, cache_in_ram=CACHE_RAM)
    val_ds   = TileDataset(val_tiles,   VAL_TRANSFORM,   cache_in_ram=CACHE_RAM)

    # ── DataLoader ────────────────────────────────────────────────────────
    # num_workers=4  → safe ceiling for 16 GB RAM with 15k-image dataset.
    #   8 workers caused RAM paging (92 %+) → Windows writes to SSD → GPU valley.
    # batch=128      → larger batches keep the RTX 4050 fed between worker round-trips.
    # prefetch_factor=2 → 2 batches staged per worker (4 workers × 2 = 8 batches max in RAM).
    # persistent_workers=True → workers stay alive between epochs (avoids re-spawn cost).
    # pin_memory=True → fast CPU→GPU DMA transfer (still safe at 4 workers).
    _loader_kwargs = dict(
        num_workers=NUM_WORKERS,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=(NUM_WORKERS > 0),
        prefetch_factor=2 if NUM_WORKERS > 0 else None,
    )
    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True,  **_loader_kwargs)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH, shuffle=False, **_loader_kwargs)

    # ── model + optimizer ─────────────────────────────────────────────────
    model     = build_model(len(class_names), device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min',
                                                      patience=2, factor=0.5)

    # Mixed-precision (AMP) — cuts VRAM usage ~50% so batch=128 fits in 6 GB
    # and gives ~1.5–2x throughput on RTX 40-series Tensor Cores.
    use_amp   = torch.cuda.is_available()
    scaler    = torch.amp.GradScaler('cuda', enabled=use_amp)

    total_params = sum(p.numel() for p in model.parameters())
    print(f"Model: ResNet18 pretrained  |  params: {total_params:,}")
    print(f"Training for up to {EPOCHS} epochs (early stop patience={PATIENCE})\n")

    best_val_loss = float('inf')
    stale = 0
    os.makedirs("ml_models", exist_ok=True)

    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()
        # ── train ────────────────────────────────────────────────────────
        model.train()
        train_loss = 0.0; correct = 0; total = 0
        for data, labels in train_loader:
            data, labels = data.to(device), labels.to(device)
            optimizer.zero_grad()
            # AMP forward pass — FP16 on GPU, FP32 on CPU
            with torch.amp.autocast('cuda', enabled=use_amp):
                out  = model(data)
                loss = criterion(out, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_loss += loss.item()
            correct += (torch.argmax(out, 1) == labels).sum().item()
            total   += labels.size(0)

        train_acc  = correct / total
        train_loss /= len(train_loader)

        val_loss, val_acc, cm, per_class = evaluate(
            model, val_loader, criterion, device, class_names)

        scheduler.step(val_loss)

        elapsed = time.time() - t0
        print(f"Ep {epoch:02d}/{EPOCHS}  "
              f"train_loss={train_loss:.4f} train_acc={train_acc:.3f}  "
              f"val_loss={val_loss:.4f} val_acc={val_acc:.3f}  "
              f"({elapsed:.1f}s)")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            stale = 0
            torch.save(model.state_dict(), SAVE_PATH)
            print(f"  [best] saved to {SAVE_PATH}")
        else:
            stale += 1
            if stale >= PATIENCE:
                print(f"  Early stop (no improvement for {PATIENCE} epochs)")
                break

    # ── final evaluation on best checkpoint ──────────────────────────────
    print("\n=== Final evaluation (best checkpoint) ===")
    model.load_state_dict(torch.load(SAVE_PATH, map_location=device, weights_only=True))
    val_loss, val_acc, cm, per_class = evaluate(
        model, val_loader, criterion, device, class_names)

    print(f"Val accuracy: {val_acc*100:.1f}%\n")
    print("Confusion matrix (rows=actual, cols=predicted):")
    print(f"{'':12s}" + "  ".join(f"{c:>8s}" for c in class_names))
    for i, cls in enumerate(class_names):
        print(f"  {cls:10s}  " + "  ".join(f"{cm[i,j]:>8d}" for j in range(len(class_names))))

    print("\nPer-class metrics:")
    for cls, m in per_class.items():
        print(f"  {cls:10s}  precision={m['precision']:.3f}  recall={m['recall']:.3f}  f1={m['f1']:.3f}")

    print(f"\nBest model saved to: {SAVE_PATH}")
    print("To deploy: copy ml_models/forest_model_improved.pth → ml_models/forest_model.pth")


if __name__ == "__main__":
    main()