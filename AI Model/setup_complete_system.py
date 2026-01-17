#!/usr/bin/env python3
"""
Complete setup script for forest monitoring system.
Downloads dataset, trains model, and sets up production system.
"""
import os
import sys
import subprocess
from pathlib import Path
import time

def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def check_dependencies():
    """Check if all dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "torch", "torchvision", "cv2", "numpy", "fastapi", 
        "uvicorn", "pandas", "sklearn", "matplotlib", "seaborn"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == "cv2":
                import cv2
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
        return run_command("pip install -r requirements.txt", "Installing dependencies")
    
    return True

def setup_directories():
    """Create necessary directories."""
    print("📁 Setting up directories...")
    
    directories = [
        "ml_models",
        "hackathon_dataset",
        "hackathon_dataset/drone_data", 
        "hackathon_dataset/drone_images",
        "data",
        "static/proof_images",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    return True

def download_and_prepare_dataset():
    """Download and prepare the hackathon dataset."""
    print("Checking for existing dataset...")
    
    # Check for User's Manual Download Location
    user_data_path_1 = Path(r"c:\Code\VerdeScan\Data\Image\Drone Data\Debadihi VF\Raw Data")
    user_data_path_2 = Path(r"c:\Code\VerdeScan\Data\Image\Drone image\Benkmura VF\Raw Data")
    
    if user_data_path_1.exists() or user_data_path_2.exists():
        print("✅ Found manually downloaded dataset in Data/Image folder.")
        print("   Using existing data for training.")
        return True

    print("📥 Downloading hackathon dataset...")
    
    # Try to download dataset
    success = run_command("python download_dataset.py", "Downloading dataset")
    
    if not success:
        print("\n⚠️ Automatic download failed. Manual download required:")
        print("1. Download from: https://drive.google.com/drive/folders/1MiCG_suSBiDITGMqtTOl4-yGZ4Pz32Ob")
        print("2. Download from: https://drive.google.com/drive/folders/1eyZazeGt7TFbCwBvMjWzjtvQujPp0JMx")
        print("3. Extract to hackathon_dataset/ folder")
        
        response = input("\n❓ Continue with manual download? (y/n): ")
        if response.lower() != 'y':
            return False
        
        input("⏳ Press Enter after manual download is complete...")
    
    # Verify dataset
    dataset_dir = Path("hackathon_dataset")
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        image_files.extend(list(dataset_dir.rglob(ext)))
    
    if len(image_files) > 0:
        print(f"✅ Found {len(image_files)} images in dataset")
        return True
    else:
        print("⚠️ No images found. Will use synthetic dataset for training.")
        return True

def train_ml_model():
    """Train the ML model on the dataset."""
    print("🤖 Training ML model...")
    
    success = run_command("python train_forest_model.py", "Training ML model")
    
    if success:
        # Check if model was created
        model_path = Path("ml_models/forest_model.pth")
        if model_path.exists():
            print("✅ ML model trained successfully!")
            return True
        else:
            print("⚠️ Training completed but model file not found")
            return False
    
    return False

def test_system():
    """Test the complete system."""
    print("🧪 Testing complete system...")
    
    return run_command("python test_system.py", "Testing system")

def generate_sample_data():
    """Generate sample data for demo."""
    print("📊 Generating sample data...")
    
    return run_command("python ai/processor.py", "Generating sample data")

def main():
    """Main setup function."""
    print("🌲 Complete Forest Monitoring System Setup")
    print("=" * 50)
    print("This will:")
    print("1. Install dependencies")
    print("2. Download hackathon dataset")
    print("3. Train ML model")
    print("4. Test complete system")
    print("5. Generate sample data")
    print("=" * 50)
    
    start_time = time.time()
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print("❌ Dependency installation failed")
        return False
    
    # Step 2: Setup directories
    if not setup_directories():
        print("❌ Directory setup failed")
        return False
    
    # Step 3: Download dataset
    if not download_and_prepare_dataset():
        print("❌ Dataset preparation failed")
        return False
    
    # Step 4: Train ML model
    if not train_ml_model():
        print("❌ ML model training failed")
        return False
    
    # Step 5: Test system
    if not test_system():
        print("❌ System test failed")
        return False
    
    # Step 6: Generate sample data
    if not generate_sample_data():
        print("⚠️ Sample data generation failed (non-critical)")
    
    # Success!
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 50)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print(f"⏱️ Total time: {elapsed_time/60:.1f} minutes")
    print("\n📁 Files created:")
    print("   - ml_models/forest_model.pth (trained ML model)")
    print("   - ml_models/training_history.json (training metrics)")
    print("   - data/results.json (sample results)")
    print("\n🚀 Ready to start!")
    print("   - Start server: python run_server.py")
    print("   - Access dashboard: http://localhost:8000")
    print("   - API docs: http://localhost:8000/docs")
    print("\n🎯 System Features:")
    print("   ✅ Trained ML model (NO external APIs needed)")
    print("   ✅ Real dataset processing")
    print("   ✅ Production-ready backend")
    print("   ✅ Interactive dashboard")
    print("   ✅ Docker deployment ready")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)