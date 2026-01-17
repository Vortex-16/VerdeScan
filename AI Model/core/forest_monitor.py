"""
Forest Monitor Core Logic
Specifically designed for the Odisha Forest Department Problem Statement.

Tracks lifecycle:
1. OP1 (March-May): Pit Detection (45x45x45cm)
2. OP2 (July): Sapling Planting (4-6ft, minimal foliage)
3. OP3 (Oct-Nov): Weeding (1m cleared soil)

Implements Year-over-Year survival monitoring.
"""

import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import math
from logger import logger

@dataclass
class GeoPoint:
    """Represents a physical location on the earth."""
    lat: float
    lon: float
    pixel_x: int
    pixel_y: int
    confidence: float
    type: str  # 'PIT', 'SAPLING', 'WEEDING_PATCH'
    year: int

@dataclass
class PatchStats:
    total_pits: int
    total_planted: int
    current_surviving: int
    survival_rate: float
    casualties: List[GeoPoint]

class ForestMonitor:
    def __init__(self):
        self.reference_year = 1
        self.pixel_resolution_cm = 2.5  # Approx from PS (2.46 - 2.81 cm)
        
    def detect_features(self, image: np.ndarray, operation_type: str, year: int) -> List[GeoPoint]:
        """
        Detect features based on the specific Operation (OP) type.
        """
        if operation_type == "OP1":
            return self._detect_pits(image, year)
        elif operation_type == "OP3":
            return self._detect_weeding_patches(image, year)
        else:
            logger.warning(f"Operation {operation_type} not supported explicitly, using generic fallback")
            return []

    def _detect_pits(self, image: np.ndarray, year: int) -> List[GeoPoint]:
        """
        OP1: Detect 45x45cm pits.
        In a 2.5cm/px image, 45cm is approx 18 pixels.
        Pits are likely square/rectangular dark or shadowed patches.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding to find dark pit-like shapes
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY_INV, 51, 5)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        pits = []
        expected_size_px = (45 / self.pixel_resolution_cm) ** 2  # Area in pixels
        min_area = expected_size_px * 0.5
        max_area = expected_size_px * 2.0
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Filter by expected size of a pit
            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = float(w)/h
                
                # Pits are roughly square (0.7 - 1.3 aspect ratio)
                if 0.7 < aspect_ratio < 1.3:
                    # Calculate centroid
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        
                        pits.append(GeoPoint(
                            lat=0.0, lon=0.0, # Placeholder, needs GeoTIFF metadata
                            pixel_x=cX, pixel_y=cY,
                            confidence=0.85,
                            type='PIT',
                            year=year
                        ))
        
        logger.info(f"OP1 Analysis: Detected {len(pits)} pits.")
        return pits

    def _detect_weeding_patches(self, image: np.ndarray, year: int) -> List[GeoPoint]:
        """
        OP3: Detect 1m diameter cleared soil circles.
        1m = 100cm. At 2.5cm/px, diameter is 40 pixels.
        Likely brighter or different texture than surrounding vegetation.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        # Hough Circle Transform
        # 40px diameter => 20px radius. Look for radius 15-25.
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=60,
                                 param1=50, param2=30, minRadius=15, maxRadius=25)
        
        patches = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                patches.append(GeoPoint(
                    lat=0.0, lon=0.0,
                    pixel_x=int(x), pixel_y=int(y),
                    confidence=0.9,
                    type='WEEDING_PATCH',
                    year=year
                ))
                
        logger.info(f"OP3 Analysis: Detected {len(patches)} weeding patches (surviving saplings).")
        return patches

    def calculate_survival_rate(self, 
                              initial_features: List[GeoPoint], 
                              current_features: List[GeoPoint], 
                              pixel_tolerance: int = 50) -> PatchStats:
        """
        Compare Year 1 (Pits/Planting) vs Year X (Weeding/Survival).
        Uses simple distance matching since we lack full GeoTIFF logic here.
        """
        
        if not initial_features:
            return PatchStats(0, 0, 0, 0.0, [])

        matched_count = 0
        casualties = []
        
        # For each initial pit, look for a matching survival patch
        for pit in initial_features:
            found_match = False
            for patch in current_features:
                dist = math.sqrt((pit.pixel_x - patch.pixel_x)**2 + (pit.pixel_y - patch.pixel_y)**2)
                if dist < pixel_tolerance:
                    found_match = True
                    break
            
            if found_match:
                matched_count += 1
            else:
                casualties.append(pit)
        
        total = len(initial_features)
        rate = (matched_count / total * 100) if total > 0 else 0.0
        
        return PatchStats(
            total_pits=total,
            total_planted=total, # Assuming all pits planted
            current_surviving=matched_count,
            survival_rate=rate,
            casualties=casualties
        )

    def align_coordinates(self, base_image: np.ndarray, target_image: np.ndarray) -> np.ndarray:
        """
        Registers (aligns) target_image to base_image using ORB feature matching.
        Essential for comparing Year 1 vs Year 2 images if they aren't perfectly georeferenced.
        """
        # Convert to grayscale
        gray_base = cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY)
        gray_target = cv2.cvtColor(target_image, cv2.COLOR_BGR2GRAY)

        # Detect ORB features
        orb = cv2.ORB_create(5000)
        kp1, des1 = orb.detectAndCompute(gray_base, None)
        kp2, des2 = orb.detectAndCompute(gray_target, None)

        if des1 is None or des2 is None:
            logger.warning("Could not find features for alignment")
            return target_image

        # Match features
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = matcher.match(des1, des2)
        
        # Sort by distance
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Keep top 15% matches
        num_good_matches = int(len(matches) * 0.15)
        matches = matches[:num_good_matches]

        # Extract location of good matches
        points1 = np.zeros((len(matches), 2), dtype=np.float32)
        points2 = np.zeros((len(matches), 2), dtype=np.float32)

        for i, match in enumerate(matches):
            points1[i, :] = kp1[match.queryIdx].pt
            points2[i, :] = kp2[match.trainIdx].pt

        # Find homography
        h, mask = cv2.findHomography(points2, points1, cv2.RANSAC)

        # Warp image
        height, width, channels = base_image.shape
        aligned_image = cv2.warpPerspective(target_image, h, (width, height))

        return aligned_image
