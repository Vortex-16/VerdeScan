import os
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
import shutil

# Config
TILE_SIZE = 224
STRIDE = 224 # Non-overlapping
VARIANCE_THRESHOLD = 500 # Threshold to reject empty/flat tiles (soil/grass)
OUTPUT_DIR = Path("processed_dataset")
MAX_IMAGES_PER_CLASS = 1000 # Safety limit for speed

def variance_of_laplacian(image):
    return cv2.Laplacian(image, cv2.CV_64F).var()

def extract_smart_tiles(source_path, class_name, limit=50):
    print(f"📦 Processing {class_name} from {source_path}...")
    
    save_dir = OUTPUT_DIR / class_name
    save_dir.mkdir(parents=True, exist_ok=True)
    
    image_files = [f for f in os.listdir(source_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    # Limit source images to avoid processing thousands of 4k images
    image_files = image_files[:limit]
    
    count_saved = 0
    
    for img_name in tqdm(image_files):
        img_path = os.path.join(source_path, img_name)
        img = cv2.imread(img_path)
        if img is None: continue
        
        h, w, c = img.shape
        
        # Slide window
        for y in range(0, h - TILE_SIZE, STRIDE):
            for x in range(0, w - TILE_SIZE, STRIDE):
                tile = img[y:y+TILE_SIZE, x:x+TILE_SIZE]
                
                # Check if tile has "content" (features)
                gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
                fm = variance_of_laplacian(gray)
                
                if fm > VARIANCE_THRESHOLD:
                    # Save tile
                    tile_name = f"{Path(img_name).stem}_{x}_{y}.jpg"
                    cv2.imwrite(str(save_dir / tile_name), tile)
                    count_saved += 1
                    
    print(f"✅ Saved {count_saved} tiles for {class_name}")

def main():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    
    # 1. Process Pits
    pits_path = r"c:\Code\VerdeScan\Data\Image\Drone Data\Debadihi VF\Raw Data\Post-Pitting"
    extract_smart_tiles(pits_path, "pit", limit=20) # Use 20 large images
    
    # 2. Process Saplings
    saplings_path = r"c:\Code\VerdeScan\Data\Image\Drone Data\Debadihi VF\Raw Data\Post-Planting"
    extract_smart_tiles(saplings_path, "sapling", limit=20)

    print("\nDataset Preparation Complete!")
    print(f"Dataset location: {OUTPUT_DIR.absolute()}")

if __name__ == "__main__":
    main()
