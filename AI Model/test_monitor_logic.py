import sys
import os
import cv2
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath("."))

from core.forest_monitor import ForestMonitor, GeoPoint, PatchStats

def test_monitoring_logic():
    monitor = ForestMonitor()
    
    print("🌲 Testing Forest Monitoring Logic...")
    
    # 1. Create Synthetic Image for OP1 (Pits)
    # 512x512 image, with 10 pits
    op1_image = np.ones((512, 512, 3), dtype=np.uint8) * 200 # Light gray background
    
    # Draw 10 "Pits" (Dark squares, approx 18x18px)
    gt_pits = []
    for i in range(10):
        x = 50 + i * 40
        y = 50
        cv2.rectangle(op1_image, (x, y), (x+18, y+18), (50, 50, 50), -1) # Dark gray pit
        # Add to ground truth list (center)
        gt_pits.append((x+9, y+9))
        
    print("📸 Generated OP1 Image with 10 pits.")
    
    # 2. Run Detection on OP1
    detected_pits = monitor.detect_features(op1_image, "OP1", 2024)
    print(f"✅ OP1 Detection: Found {len(detected_pits)} pits (Expected 10).")
    
    if len(detected_pits) == 0:
        print("❌ Failed to detect any pits.")
        return

    # 3. Create Synthetic Image for OP3 (Weeding/Survival)
    # Simulate 80% survival (8 plants)
    # Weeding patch = Lighter circle
    op3_image = np.ones((512, 512, 3), dtype=np.uint8) * 100 # Darker background (vegetation)
    
    gt_survivors = []
    for i in range(8): # Only 8 surviving
        x = gt_pits[i][0]
        y = gt_pits[i][1]
        
        # Weeding patch: Circle radius ~20px
        cv2.circle(op3_image, (x, y), 20, (200, 255, 200), -1) # Light green patch
        gt_survivors.append((x, y))

    print("📸 Generated OP3 Image with 8 surviving plants.")

    # 4. Run Detection on OP3
    detected_patches = monitor.detect_features(op3_image, "OP3", 2025)
    print(f"✅ OP3 Detection: Found {len(detected_patches)} patches (Expected 8).")
    
    # 5. Calculate Survival
    stats = monitor.calculate_survival_rate(detected_pits, detected_patches)
    
    print("\n📊 Survival Statistics:")
    print(f"   Total Planted (OP1): {stats.total_planted}")
    print(f"   Surviving (OP3): {stats.current_surviving}")
    print(f"   Survival Rate: {stats.survival_rate:.2f}%")
    print(f"   Casualties: {len(stats.casualties)}")
    
    # Check accuracy
    if stats.total_planted == 10 and stats.current_surviving == 8:
        print("\n🎉 SUCCESS: Logic correctly identified 80% survival rate.")
    else:
        print("\n⚠️ FAILURE: Logic mismatched.")
        
    # Check casualty location
    if len(stats.casualties) == 2:
        print("✅ Casualty count correct.")
        c1 = stats.casualties[0]
        print(f"   Casualty detected at pixel: ({c1.pixel_x}, {c1.pixel_y})")
    
if __name__ == "__main__":
    test_monitoring_logic()
