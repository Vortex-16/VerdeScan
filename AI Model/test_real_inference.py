import torch
import cv2
import numpy as np
import torch.nn as nn
from pathlib import Path
from torchvision import transforms

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

def test_inference():
    print("🤖 Testing Real Inference on Full Image...")
    
    # 1. Load Model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = SimpleCNN().to(device)
    model.load_state_dict(torch.load("ml_models/forest_model.pth", map_location=device))
    model.eval()
    print("✅ Model loaded.")

    # 2. Load Real Image
    # Pick a random image from Post-Planting
    base_path = r"c:\Code\VerdeScan\Data\Image\Drone Data\Debadihi VF\Raw Data\Post-Planting"
    import os
    img_name = os.listdir(base_path)[0]
    img_path = os.path.join(base_path, img_name)
    
    img = cv2.imread(img_path)
    print(f"📸 Loaded image: {img_name} ({img.shape})")
    
    # 3. Sliding Window Inference (simplified)
    # We will just check 10 random crops to see predictions
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    print("\n🔍 Running Random Validations:")
    for i in range(5):
        # Crop random 224x224 tile
        y = np.random.randint(0, img.shape[0]-224)
        x = np.random.randint(0, img.shape[1]-224)
        crop = img[y:y+224, x:x+224]
        
        # Preprocess
        input_tensor = transform(crop).unsqueeze(0).to(device)
        
        # Inference
        with torch.no_grad():
            output = model(input_tensor)
            probs = torch.softmax(output, dim=1)
            pred_class = torch.argmax(probs).item()
            conf = probs[0][pred_class].item()
            
        label_map = {0: "Pit", 1: "Sapling"}
        print(f"   Tile {i+1} at ({x},{y}): Predicted {label_map.get(pred_class, 'Unknown')} ({conf:.2f})")

if __name__ == "__main__":
    test_inference()
