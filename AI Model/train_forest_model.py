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
    print("🌲 Starting Real Forest Model Training (Patch-Based)...")
    
    # 1. Define Data Path (Processed Tiles)
    data_path = Path("processed_dataset")
    
    if not data_path.exists():
        print(f"❌ Dataset not found at {data_path}. Run dataset_preparer.py first.")
        return False
        
    # 2. Setup Training Logic
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Use ImageFolder which automatically assigns labels based on folders (pit=0, sapling=1)
    from torchvision.datasets import ImageFolder
    full_dataset = ImageFolder(root=data_path, transform=transform)
    
    print(f"✅ Found {len(full_dataset)} training tiles.")
    print(f"   Classes: {full_dataset.classes}")
    
    # Split Train/Val
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(full_dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    model = SimpleCNN().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    # 4. Train Loop (3 Epochs)
    epochs = 3
    print(f"🚀 Starting training for {epochs} epochs...")
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(output.data, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()
            
            if batch_idx % 10 == 0:
                print(f"Epoch {epoch+1} Batch {batch_idx}/{len(train_loader)} Loss: {loss.item():.4f}")
        
        avg_loss = total_loss / len(train_loader)
        acc = 100 * correct / total
        print(f"Epoch {epoch+1} Complete. Avg Loss: {avg_loss:.4f} | Accuracy: {acc:.2f}%")
        
    # 5. Validation
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for data, target in val_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            _, predicted = torch.max(output.data, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()
            
    val_acc = 100 * correct / total
    print(f"📊 Validation Accuracy: {val_acc:.2f}%")
            
    # 6. Save Model
    os.makedirs("ml_models", exist_ok=True)
    save_path = "ml_models/forest_model.pth"
    torch.save(model.state_dict(), save_path)
    print(f"💾 Model saved to {save_path}")
    return True

if __name__ == "__main__":
    main()
