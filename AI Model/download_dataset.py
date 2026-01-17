#!/usr/bin/env python3
"""
Download hackathon drone dataset from Google Drive.
"""
import os
import sys
from pathlib import Path
import requests
import zipfile
from urllib.parse import urlparse

def download_file_from_google_drive(file_id: str, destination: str):
    """Download file from Google Drive using file ID."""
    URL = "https://docs.google.com/uc?export=download"
    
    session = requests.Session()
    response = session.get(URL, params={'id': file_id}, stream=True)
    
    # Handle large files
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            params = {'id': file_id, 'confirm': value}
            response = session.get(URL, params=params, stream=True)
            break
    
    # Save file
    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size=32768):
            if chunk:
                f.write(chunk)

def extract_file_id_from_url(url: str) -> str:
    """Extract file ID from Google Drive URL."""
    if "drive.google.com" in url:
        if "/folders/" in url:
            return url.split("/folders/")[1].split("?")[0]
        elif "/file/d/" in url:
            return url.split("/file/d/")[1].split("/")[0]
    return ""

def download_with_gdown():
    """Download using gdown library."""
    try:
        import gdown
        
        print("📥 Downloading with gdown...")
        
        # Create directories
        data_dir = Path("hackathon_dataset")
        data_dir.mkdir(exist_ok=True)
        
        drone_data_dir = data_dir / "drone_data"
        drone_images_dir = data_dir / "drone_images"
        
        # Download drone data
        print("📁 Downloading drone data...")
        gdown.download_folder(
            "https://drive.google.com/drive/folders/1MiCG_suSBiDITGMqtTOl4-yGZ4Pz32Ob",
            output=str(drone_data_dir),
            quiet=False,
            use_cookies=False
        )
        
        # Download drone images
        print("📁 Downloading drone images...")
        gdown.download_folder(
            "https://drive.google.com/drive/folders/1eyZazeGt7TFbCwBvMjWzjtvQujPp0JMx",
            output=str(drone_images_dir),
            quiet=False,
            use_cookies=False
        )
        
        print("✅ Download completed!")
        return True
        
    except ImportError:
        print("❌ gdown not installed. Install with: pip install gdown")
        return False
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def manual_download_instructions():
    """Provide manual download instructions."""
    print("📋 Manual Download Instructions:")
    print("=" * 50)
    print()
    print("1. 📁 Drone Data:")
    print("   URL: https://drive.google.com/drive/folders/1MiCG_suSBiDITGMqtTOl4-yGZ4Pz32Ob?usp=sharing")
    print("   Download → Extract to: hackathon_dataset/drone_data/")
    print()
    print("2. 🖼️ Drone Images:")
    print("   URL: https://drive.google.com/drive/folders/1eyZazeGt7TFbCwBvMjWzjtvQujPp0JMx?usp=sharing")
    print("   Download → Extract to: hackathon_dataset/drone_images/")
    print()
    print("📂 Expected structure:")
    print("hackathon_dataset/")
    print("├── drone_data/")
    print("│   └── [CSV files, metadata, etc.]")
    print("└── drone_images/")
    print("    └── [JPG/PNG drone images]")
    print()
    print("🔄 After manual download, run: python train_forest_model.py")

def verify_dataset():
    """Verify downloaded dataset."""
    print("🔍 Verifying dataset...")
    
    data_dir = Path("hackathon_dataset")
    drone_data_dir = data_dir / "drone_data"
    drone_images_dir = data_dir / "drone_images"
    
    # Check directories exist
    if not data_dir.exists():
        print("❌ Dataset directory not found")
        return False
    
    # Count files
    data_files = list(drone_data_dir.rglob("*")) if drone_data_dir.exists() else []
    image_files = []
    
    if drone_images_dir.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
            image_files.extend(list(drone_images_dir.rglob(ext)))
    
    print(f"📊 Dataset verification:")
    print(f"   - Data files: {len(data_files)}")
    print(f"   - Image files: {len(image_files)}")
    
    if len(image_files) > 0:
        print("✅ Dataset verification successful!")
        return True
    else:
        print("⚠️ No image files found. Please check download.")
        return False

def main():
    """Main download function."""
    print("📥 Hackathon Dataset Downloader")
    print("=" * 40)
    
    # Try automatic download first
    success = download_with_gdown()
    
    if not success:
        print("\n🔄 Automatic download failed. Trying alternative method...")
        manual_download_instructions()
        
        # Wait for user to download manually
        input("\n⏳ Press Enter after manual download is complete...")
    
    # Verify dataset
    if verify_dataset():
        print("\n🎉 Dataset ready for training!")
        print("🚀 Run: python train_forest_model.py")
    else:
        print("\n❌ Dataset verification failed.")
        print("Please check the download and try again.")

if __name__ == "__main__":
    main()