#!/usr/bin/env python3
"""
Production server startup script for Verde Scan API.
"""
import os
import sys
import asyncio
from pathlib import Path

# Windows consoles default to cp1252 and crash on the emoji/Unicode in the
# startup banner below.  Force UTF-8 so `python run_server.py` works everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import settings
from logger import setup_logging
import uvicorn

def validate_environment():
    """Validate environment and dependencies."""
    print("🔍 Validating environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    # Check required directories
    required_dirs = [
        settings.data_dir,
        settings.static_dir,
        settings.ml_model_path
    ]
    
    for directory in required_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory: {directory}")
    
    # Check dependencies
    try:
        import cv2
        import numpy as np
        import fastapi
        import uvicorn
        print("✅ Core dependencies available")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        sys.exit(1)
    
    print("✅ Environment validation complete")

def setup_logging_config():
    """Setup logging configuration."""
    print("📝 Setting up logging...")
    
    # Create logs directory
    if settings.log_file:
        log_dir = Path(settings.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = setup_logging(
        level=settings.log_level,
        log_file=settings.log_file
    )
    
    logger.info("Verde Scan server starting up...")
    print("✅ Logging configured")

def main():
    """Main server startup function."""
    print("🌲 Verde Scan - Drone Forest Monitoring System")
    print("=" * 50)
    
    # Validate environment
    validate_environment()
    
    # Setup logging
    setup_logging_config()
    
    # Print configuration
    print(f"🚀 Starting server on {settings.api_host}:{settings.api_port}")
    print(f"📊 Environment: {settings.environment}")
    print(f"🔧 Max concurrent requests: {settings.max_concurrent_requests}")
    print(f"⏱️  Processing timeout: {settings.processing_timeout}s")
    print(f"📁 Data directory: {settings.data_dir}")
    print(f"🖼️  Static directory: {settings.static_dir}")
    
    if settings.gemini_api_key:
        print("🤖 Gemini API integration: Enabled")
    else:
        print("🤖 Gemini API integration: Disabled (no API key)")
    
    print("=" * 50)
    
    # Start server
    try:
        uvicorn.run(
            "api.main:app",
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level.lower(),
            reload=(settings.environment == "development"),
            workers=1 if settings.environment == "development" else 4
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()