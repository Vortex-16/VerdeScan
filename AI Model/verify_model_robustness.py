import torch
import cv2
import numpy as np
import torch.nn as nn
from pathlib import Path
from torchvision import transforms
from tqdm import tqdm
import os

# --- Model Definition (Must match training) ---
class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 56 * 56, 128),
            nn.ReLU(),
            nn.Linear(128, 2)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

def scan_full_image(model, img_path, device, transform, stride=224):
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"❌ Could not load {img_path}")
        return {}
        
    h, w, c = img.shape
    print(f"📸 Scanning {os.path.basename(img_path)} ({w}x{h})...")
    
    counts = {0: 0, 1: 0} # 0: Pit, 1: Sapling
    
    # Simple sliding window
    tiles = []
    
    # We will sample efficiently (every 224px) to cover the whole image
    # Note: In a real sliding window for detection, we might overlap. 
    # Here we just want to see if the overall classification is correct for the scene.
    for y in range(0, h - 224, stride):
        for x in range(0, w - 224, stride):
            crop = img[y:y+224, x:x+224]
            # Convert BGR to RGB
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            tiles.append(crop_rgb)
            
    # Batch processing for speed
    batch_size = 16
    for i in range(0, len(tiles), batch_size):
        batch_crops = tiles[i:i+batch_size]
        if not batch_crops: continue
        
        # Transform batch
        tensors = []
        for crop in batch_crops:
            # Resize is technically redundant if we crop 224, but safe to keep
            pil_img = transforms.ToPILImage()(crop)
            t_img = transform(pil_img)
            tensors.append(t_img)
            
        batch_tensor = torch.stack(tensors).to(device)
        
        with torch.no_grad():
            outputs = model(batch_tensor)
            _, preds = torch.max(outputs, 1)
            
            for pred in preds:
                counts[pred.item()] += 1
                
    return counts

def main():
    print("🌲 Robust Model Verification")
    print("==========================")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = SimpleCNN().to(device)
    try:
        model.load_state_dict(torch.load("ml_models/forest_model.pth", map_location=device))
        model.eval()
        print("✅ Model loaded successfully.")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # 1. Test on a PITTING image (Should see mostly Pits/Class 0)
    pit_dir = Path(r"c:\Code\VerdeScan\Data\Image\Drone Data\Debadihi VF\Raw Data\Post-Pitting")
    # Get first image
    pit_img = next(pit_dir.glob("*.JPG"))
    
    results_pit = scan_full_image(model, pit_img, device, transform)
    
    # 2. Test on a PLANTING image (Should see mostly Saplings/Class 1)
    # Note: Correct path based on previous listing
    plant_dir = Path(r"c:\Code\VerdeScan\Data\Image\Drone Data\Debadihi VF\Raw Data\Post-Planting")
    plant_img = next(plant_dir.glob("*.JPG"))

    results_plant = scan_full_image(model, plant_img, device, transform)
    
    print("\n📊 VERIFICATION RESULTS")
    print("------------------------")
    
    print(f"\n1. Post-Pitting Image Test:")
    print(f"   - Predicted Pits (Class 0): {results_pit.get(0, 0)}")
    print(f"   - Predicted Saplings (Class 1): {results_pit.get(1, 0)}")
    total_pit_tiles = sum(results_pit.values())
    if total_pit_tiles > 0:
        pit_ratio = results_pit.get(0, 0) / total_pit_tiles
        print(f"   -> Pit Dominance: {pit_ratio:.1%}")
    
    print(f"\n2. Post-Planting Image Test:")
    print(f"   - Predicted Pits (Class 0): {results_plant.get(0, 0)}")
    print(f"   - Predicted Saplings (Class 1): {results_plant.get(1, 0)}")
    total_plant_tiles = sum(results_plant.values())
    if total_plant_tiles > 0:
        plant_ratio = results_plant.get(1, 0) / total_plant_tiles
        print(f"   -> Sapling Dominance: {plant_ratio:.1%}")
        
    print("\n------------------------")
    if results_pit.get(0, 0) > results_pit.get(1, 0) and results_plant.get(1, 0) > results_plant.get(0, 0):
        print("✅ SUCCESS: Model correctly identifies the dominant feature in both phases.")
    else:
        print("❌ FAILURE: Model confusion detected.")

if __name__ == "__main__":
    main()
