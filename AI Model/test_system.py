#!/usr/bin/env python3
"""
System test script to verify the complete ML pipeline works.
"""
import sys
import os
from pathlib import Path
import asyncio
import time

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        import cv2
        print("✅ OpenCV imported")
        
        import numpy as np
        print("✅ NumPy imported")
        
        from core.forest_processor import ForestMLProcessor
        print("✅ ForestMLProcessor imported")
        
        from models.data_structures import TreeStatus, ProcessingResult
        print("✅ Data structures imported")
        
        from config import settings
        print("✅ Configuration imported")
        
        from logger import logger
        print("✅ Logger imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_ml_processor():
    """Test the ML processor functionality."""
    print("\n🤖 Testing ML processor...")
    
    try:
        from core.forest_processor import ForestMLProcessor
        from ai.processor import ForestAIProcessor
        
        # Test new ML processor
        ml_processor = ForestMLProcessor()
        if not ml_processor.is_loaded():
            print("❌ ML processor failed to load")
            return False
        
        print("✅ ML processor loaded successfully")
        
        # Test legacy processor with new backend
        legacy_processor = ForestAIProcessor(base_dir="test_data")
        
        # Generate test image
        test_patch = "test_patch"
        image_path, coords = legacy_processor.generate_test_image(test_patch, num_trees=20)
        print(f"✅ Generated test image: {image_path}")
        
        # Process the patch
        summary, details = legacy_processor.process_patch(test_patch)
        print(f"✅ Processed patch: {summary['total_trees']} trees detected")
        
        return True
        
    except Exception as e:
        print(f"❌ ML processor test failed: {e}")
        return False

def test_api_components():
    """Test API components without starting the server."""
    print("\n🌐 Testing API components...")
    
    try:
        from core.task_manager import TaskManager
        from core.data_manager import DataManager
        from core.forest_processor import ForestMLProcessor
        
        # Test data manager
        data_manager = DataManager()
        print("✅ Data manager initialized")
        
        # Test task manager
        ml_processor = ForestMLProcessor()
        task_manager = TaskManager(ml_processor)
        print("✅ Task manager initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ API components test failed: {e}")
        return False

async def test_async_processing():
    """Test asynchronous processing capabilities."""
    print("\n⚡ Testing async processing...")
    
    try:
        from core.task_manager import TaskManager
        from core.forest_processor import ForestMLProcessor
        from ai.processor import ForestAIProcessor
        import uuid
        
        # Create test image
        legacy_processor = ForestAIProcessor(base_dir="test_data")
        test_patch = "async_test_patch"
        image_path, _ = legacy_processor.generate_test_image(test_patch, num_trees=15)
        
        # Test async task submission
        ml_processor = ForestMLProcessor()
        task_manager = TaskManager(ml_processor)
        
        task_id = str(uuid.uuid4())
        task_status = await task_manager.submit_task(
            task_id=task_id,
            image_path=image_path,
            patch_id=test_patch
        )
        
        print(f"✅ Async task submitted: {task_id}")
        print(f"✅ Task status: {task_status.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Async processing test failed: {e}")
        return False

def test_configuration():
    """Test configuration and environment setup."""
    print("\n⚙️ Testing configuration...")
    
    try:
        from config import settings
        
        print(f"✅ API Host: {settings.api_host}")
        print(f"✅ API Port: {settings.api_port}")
        print(f"✅ Environment: {settings.environment}")
        print(f"✅ Max concurrent: {settings.max_concurrent_requests}")
        print(f"✅ Data directory: {settings.data_dir}")
        print(f"✅ Static directory: {settings.static_dir}")
        
        # Check if directories exist
        if os.path.exists(settings.data_dir):
            print(f"✅ Data directory exists")
        else:
            print(f"⚠️ Data directory will be created")
        
        if os.path.exists(settings.static_dir):
            print(f"✅ Static directory exists")
        else:
            print(f"⚠️ Static directory will be created")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def cleanup_test_data():
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    
    try:
        import shutil
        test_dir = "test_data"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

async def main():
    """Run all system tests."""
    print("🌲 Verde Scan System Test")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("ML Processor", test_ml_processor),
        ("API Components", test_api_components),
    ]
    
    async_tests = [
        ("Async Processing", test_async_processing),
    ]
    
    passed = 0
    total = len(tests) + len(async_tests)
    
    # Run synchronous tests
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} test PASSED")
        else:
            print(f"❌ {test_name} test FAILED")
    
    # Run asynchronous tests
    for test_name, test_func in async_tests:
        print(f"\n📋 Running {test_name} test...")
        if await test_func():
            passed += 1
            print(f"✅ {test_name} test PASSED")
        else:
            print(f"❌ {test_name} test FAILED")
    
    # Cleanup
    cleanup_test_data()
    
    # Results
    print("\n" + "=" * 40)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready.")
        print("\n🚀 To start the server, run:")
        print("   python run_server.py")
        print("\n🐳 Or with Docker:")
        print("   docker-compose --profile development up")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)