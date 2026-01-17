import torch
import torch.nn as nn
from torchvision import transforms
import random
import os
from pathlib import Path
from PIL import Image

# Define Model (Must match training)
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

def test_single_image(model, img_path, true_label, device, transform):
    try:
        img = Image.open(img_path).convert('RGB')
        img_t = transform(img).unsqueeze(0).to(device)
        
        with torch.no_grad():
            output = model(img_t)
            probs = torch.softmax(output, dim=1)
            pred_idx = torch.argmax(probs).item()
            confidence = probs[0][pred_idx].item()
        
        # Class 0 = Pit, Class 1 = Sapling (Alphabetical order of folders: pit, sapling)
        classes = ['Pit', 'Sapling']
        pred_class = classes[pred_idx]
        
        icon = "✅" if pred_class == true_label else "❌"
        print(f"{icon} {os.path.basename(img_path)}")
        print(f"   True: {true_label} | Pred: {pred_class} ({confidence:.1%})")
        return pred_class == true_label
    except Exception as e:
        print(f"⚠️ Error testing {img_path}: {e}")
        return False

def main():
    print("🧪 Verifying Model on Training Data Samples...")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = SimpleCNN().to(device)
    
    model_path = "ml_models/forest_model.pth"
    if not os.path.exists(model_path):
        print(f"❌ Model not found at {model_path}")
        return

    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    print("✅ Model loaded.")
    
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    dataset_path = Path("processed_dataset")
    if not dataset_path.exists():
        print("❌ 'processed_dataset' folder not found. Cannot verify on training data.")
        return

    # Test Pits
    pit_dir = dataset_path / "pit"
    if pit_dir.exists():
        pits = list(pit_dir.glob("*.jpg"))
        sample_size = min(len(pits), 5)
        print(f"\n🕳️ Testing {sample_size} random Pit images:")
        correct = 0
        for img in random.sample(pits, sample_size):
            if test_single_image(model, img, "Pit", device, transform):
                correct += 1
        print(f"   Accuracy: {correct}/{sample_size}")
            
    # Test Saplings
    sapling_dir = dataset_path / "sapling"
    if sapling_dir.exists():
        saplings = list(sapling_dir.glob("*.jpg"))
        sample_size = min(len(saplings), 5)
        print(f"\n🌱 Testing {sample_size} random Sapling images:")
        correct = 0
        for img in random.sample(saplings, sample_size):
            if test_single_image(model, img, "Sapling", device, transform):
                correct += 1
        print(f"   Accuracy: {correct}/{sample_size}")

if __name__ == "__main__":
    main()