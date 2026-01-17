#!/usr/bin/env python3
"""
Train the forest model using the manually downloaded dataset.
"""
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import cv2
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
import torchvision.transforms as transforms
from typing import List

class ForestDataset(Dataset):
    def __init__(self, image_paths: List[str], transform=None):
        self.image_paths = image_paths
        self.transform = transform
        # For this hackathon challenge, since we don't have explicit labels for every single image
        # readily available in a structured format in this script, we will create a dummy label
        # or Auto-Encoder approach. For now, let's assume we are training a feature extractor
        # or basic classification if we can deduce labels from folder names.
        # Since folder names are 'Raw Data', we will assign a dummy label 0.
        # REAL IMPLEMENTATION WOULD REQUIRE ANNOTATIONS.
        self.labels = [0] * len(image_paths) 
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        try:
            image_path = self.image_paths[idx]
            # Read image
            image = cv2.imread(str(image_path))
            if image is None:
                # Return black image if read fails to prevent crash
                return torch.zeros((3, 224, 224)), 0
                
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            if self.transform:
                image = self.transform(image)
                
            return image, self.labels[idx]
        except Exception as e:
            print(f"Error loading {self.image_paths[idx]}: {e}")
            return torch.zeros((3, 224, 224)), 0

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
            nn.Linear(32 * 56 * 56, 128),  # Assuming 224x224 input
            nn.ReLU(),
            nn.Linear(128, 2) # Dummy 2 classes
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

def find_images(base_paths):
    image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    all_images = []
    
    for base_path in base_paths:
        path_obj = Path(base_path)
        if path_obj.exists():
            print(f"Searching in {base_path}...")
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if Path(file).suffix in image_extensions:
                        all_images.append(os.path.join(root, file))
        else:
            print(f"Warning: Path not found: {base_path}")
            
    return all_images

def main():
    print("🌲 Starting Forest Model Training (Hackathon Mode)...")
    
    # 1. Define Data Paths based on user's manual download
    data_paths = [
        r"c:\Code\VerdeScan\Data\Image\Drone Data\Debadihi VF\Raw Data",
        r"c:\Code\VerdeScan\Data\Image\Drone image\Benkmura VF\Raw Data"
    ]
    
    # 2. Collect Images
    images = find_images(data_paths)
    print(f"✅ Found {len(images)} images total.")
    
    if len(images) == 0:
        print("❌ No images found! Check paths.")
        return False

    # 3. Setup Training
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])
    
    # Use a subset for quick proof-of-concept training if many images
    if len(images) > 500:
        print("Using subset of 500 images for speed...")
        images = images[:500]

    dataset = ForestDataset(images, transform=transform)
    loader = DataLoader(dataset, batch_size=16, shuffle=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    model = SimpleCNN().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    # 4. Train Loop (1 Epoch for Setup Check)
    print("🚀 Starting training loop...")
    model.train()
    for batch_idx, (data, target) in enumerate(loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        
        if batch_idx % 10 == 0:
            print(f"Batch {batch_idx}/{len(loader)} Loss: {loss.item():.4f}")
            
    # 5. Save Model
    os.makedirs("ml_models", exist_ok=True)
    save_path = "ml_models/forest_model.pth"
    torch.save(model.state_dict(), save_path)
    print(f"💾 Model saved to {save_path}")
    return True

if __name__ == "__main__":
    main()
