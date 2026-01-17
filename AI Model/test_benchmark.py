import sys
import os
import cv2
import numpy as np
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath("."))

from core.forest_monitor import ForestMonitor

def benchmark_monitor():
    monitor = ForestMonitor()
    
    print("🚀 Benchmarking Forest Monitoring Logic...")
    
    # Create high-res synthetic image (4K resolution)
    width, height = 3840, 2160
    print(f"📊 Image Resolution: {width}x{height} pixels")
    
    # Synthetic OP1 (Pits) - 100 pits
    op1_image = np.ones((height, width, 3), dtype=np.uint8) * 200
    for i in range(100):
        x = np.random.randint(50, width-50)
        y = np.random.randint(50, height-50)
        cv2.rectangle(op1_image, (x, y), (x+18, y+18), (50, 50, 50), -1)

    # Synthetic OP3 (Weeding) - 80 survivors
    op3_image = np.ones((height, width, 3), dtype=np.uint8) * 100
    for i in range(80):
        x = np.random.randint(50, width-50)
        y = np.random.randint(50, height-50)
        cv2.circle(op3_image, (x, y), 20, (200, 255, 200), -1)

    # Benchmark OP1 Detection
    start_time = time.time()
    pits = monitor.detect_features(op1_image, "OP1", 2024)
    op1_time = time.time() - start_time
    print(f"⏱️  OP1 Detection (100 pits): {op1_time:.4f} seconds")

    # Benchmark OP3 Detection
    start_time = time.time()
    patches = monitor.detect_features(op3_image, "OP3", 2025)
    op3_time = time.time() - start_time
    print(f"⏱️  OP3 Detection (80 patches): {op3_time:.4f} seconds")

    # Benchmark Survival Calculation
    start_time = time.time()
    monitor.calculate_survival_rate(pits, patches)
    calc_time = time.time() - start_time
    print(f"⏱️  Survival Calculation: {calc_time:.4f} seconds")
    
    total_time = op1_time + op3_time + calc_time
    print(f"\n⚡ Total Processing Time: {total_time:.4f} seconds")
    
    if total_time < 2.0:
        print("✅ Performance: EXCELLENT (< 2s)")
    elif total_time < 5.0:
        print("⚠️ Performance: ACCEPTABLE (< 5s)")
    else:
        print("❌ Performance: SLOW (> 5s)")

if __name__ == "__main__":
    benchmark_monitor()
