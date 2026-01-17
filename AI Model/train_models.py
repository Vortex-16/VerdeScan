#!/usr/bin/env python3
"""
Training script for custom forest monitoring models.
This shows how to train YOLO and CNN models on your dataset.
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from ultralytics import YOLO
import cv2
import numpy as np
from pathlib import Path
import json
from typing import List, Tuple
from sklearn.model_selection import train_test_split

class ForestDataset(Dataset):
    """Dataset class for forest health classification."""
    
    def __init__(self, image_paths: List[str], labels: List[int], transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        # Load image
        image = cv2.imread(self.image_paths[idx])
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if self.transform:
            image = self.transform(image)
        
        return image, self.labels[idx]

class TreeHealthCNN(nn.Module):
    """Simple CNN for tree health classification."""
    
    def __init__(self, num_classes=3):
        super(TreeHealthCNN, self).__init__()
        
        self.features = nn.Sequential(
            # First conv block
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            
            # Second conv block
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            
            # Third conv block
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            
            # Fourth conv block
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )
        
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d((7, 7)),
            nn.Flatten(),
            nn.Linear(256 * 7 * 7, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

def train_yolo_detection_model(dataset_path: str, epochs: int = 100):
    """
    Train YOLO model for tree detection.
    
    Args:
        dataset_path: Path to YOLO format dataset
        epochs: Number of training epochs
    """
    print("🌲 Training YOLO Tree Detection Model...")
    
    try:
        # Initialize YOLO model
        model = YOLO('yolov8n.pt')  # Start with pretrained weights
        
        # Train the model
        results = model.train(
            data=f"{dataset_path}/data.yaml",  # Dataset config file
            epochs=epochs,
            imgsz=640,
            batch=16,
            name='forest_tree_detection',
            patience=10,
            save=True,
            plots=True
        )
        
        # Save the trained model
        model.save('models/forest_yolo.pt')
        print("✅ YOLO model training completed!")
        print(f"📊 Best mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ YOLO training failed: {e}")
        return False

def train_cnn_classification_model(
    image_paths: List[str], 
    labels: List[int], 
    epochs: int = 50
):
    """
    Train CNN model for tree health classification.
    
    Args:
        image_paths: List of image file paths
        labels: List of corresponding labels (0=Alive, 1=Dead, 2=Diseased)
        epochs: Number of training epochs
    """
    print("🤖 Training CNN Health Classification Model...")
    
    try:
        import torchvision.transforms as transforms
        
        # Data transforms
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Split dataset
        X_train, X_val, y_train, y_val = train_test_split(
            image_paths, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Create datasets
        train_dataset = ForestDataset(X_train, y_train, transform=transform)
        val_dataset = ForestDataset(X_val, y_val, transform=transform)
        
        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
        
        # Initialize model
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = TreeHealthCNN(num_classes=3).to(device)
        
        # Loss and optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.1)
        
        # Training loop
        best_val_acc = 0.0
        
        for epoch in range(epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for images, labels in train_loader:
                images, labels = images.to(device), labels.to(device)
                
                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                train_total += labels.size(0)
                train_correct += (predicted == labels).sum().item()
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for images, labels in val_loader:
                    images, labels = images.to(device), labels.to(device)
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    
                    val_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    val_total += labels.size(0)
                    val_correct += (predicted == labels).sum().item()
            
            # Calculate accuracies
            train_acc = 100 * train_correct / train_total
            val_acc = 100 * val_correct / val_total
            
            print(f"Epoch [{epoch+1}/{epochs}]:")
            print(f"  Train Loss: {train_loss/len(train_loader):.4f}, Train Acc: {train_acc:.2f}%")
            print(f"  Val Loss: {val_loss/len(val_loader):.4f}, Val Acc: {val_acc:.2f}%")
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save(model, 'models/forest_health_cnn.pth')
                print(f"  ✅ New best model saved! Val Acc: {val_acc:.2f}%")
            
            scheduler.step()
        
        print(f"🎯 CNN training completed! Best validation accuracy: {best_val_acc:.2f}%")
        return True
        
    except Exception as e:
        print(f"❌ CNN training failed: {e}")
        return False

def create_sample_dataset():
    """Create a sample dataset for demonstration."""
    print("📁 Creating sample dataset...")
    
    # This is just a demonstration - replace with your actual dataset
    sample_data = {
        "yolo_dataset": {
            "description": "YOLO format dataset for tree detection",
            "structure": {
                "images/": "Drone images",
                "labels/": "YOLO format annotations (.txt files)",
                "data.yaml": "Dataset configuration"
            },
            "data_yaml_example": {
                "train": "path/to/train/images",
                "val": "path/to/val/images", 
                "nc": 1,  # number of classes
                "names": ["tree"]
            }
        },
        "cnn_dataset": {
            "description": "Image classification dataset for tree health",
            "structure": {
                "alive/": "Images of healthy trees",
                "dead/": "Images of dead trees",
                "diseased/": "Images of diseased trees"
            },
            "label_mapping": {
                "alive": 0,
                "dead": 1, 
                "diseased": 2
            }
        }
    }
    
    # Save dataset info
    with open('dataset_info.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print("✅ Sample dataset structure created!")
    print("📋 Check dataset_info.json for format details")

def main():
    """Main training function."""
    print("🌲 Forest Monitoring Model Training")
    print("=" * 40)
    
    # Create models directory
    Path("models").mkdir(exist_ok=True)
    
    # Create sample dataset info
    create_sample_dataset()
    
    print("\n🎯 Training Instructions:")
    print("1. Prepare your dataset in the required format")
    print("2. Update the paths in this script")
    print("3. Run training functions")
    print("\n📊 Expected Results with Good Dataset:")
    print("- YOLO Detection: 90-95% mAP")
    print("- CNN Classification: 85-90% accuracy")
    print("- Combined System: 90-95% overall accuracy")
    
    # Uncomment these lines when you have your dataset ready:
    
    # Train YOLO model (uncomment when dataset is ready)
    # train_yolo_detection_model("path/to/yolo/dataset", epochs=100)
    
    # Train CNN model (uncomment when dataset is ready)
    # Example data - replace with your actual data
    # image_paths = ["path/to/image1.jpg", "path/to/image2.jpg", ...]
    # labels = [0, 1, 2, ...]  # 0=Alive, 1=Dead, 2=Diseased
    # train_cnn_classification_model(image_paths, labels, epochs=50)
    
    print("\n🚀 Ready to train! Update paths and uncomment training calls.")

if __name__ == "__main__":
    main()