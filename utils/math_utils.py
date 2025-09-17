"""
Mathematical utility functions
"""
import numpy as np
from typing import List, Tuple


def calculate_contour_area(contour: np.ndarray) -> float:
    """Calculate area of a contour"""
    return abs(cv2.contourArea(contour))


def calculate_contour_perimeter(contour: np.ndarray) -> float:
    """Calculate perimeter of a contour"""
    return cv2.arcLength(contour, True)


def is_contour_closed(contour: np.ndarray, tolerance: float = 3.0) -> bool:
    """Check if contour is closed within tolerance"""
    if len(contour) < 3:
        return False
    
    first_point = contour[0][0]
    last_point = contour[-1][0]
    gap = np.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
    
    return gap < tolerance


def close_contour(contour: np.ndarray) -> np.ndarray:
    """Ensure contour is closed"""
    if is_contour_closed(contour):
        return contour
    
    # Add closing point
    first_point = contour[0][0]
    closing_point = np.array([[[first_point[0], first_point[1]]]], dtype=np.int32)
    return np.vstack([contour, closing_point])


def simplify_contour(contour: np.ndarray, epsilon: float) -> np.ndarray:
    """Simplify contour using Douglas-Peucker algorithm"""
    return cv2.approxPolyDP(contour, epsilon, True)


def calculate_contour_center(contour: np.ndarray) -> Tuple[float, float]:
    """Calculate center point of contour"""
    M = cv2.moments(contour)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return cx, cy
    else:
        # Fallback to centroid of points
        points = contour.reshape(-1, 2)
        return np.mean(points, axis=0)


def calculate_bounding_rect(contour: np.ndarray) -> Tuple[int, int, int, int]:
    """Calculate bounding rectangle of contour"""
    x, y, w, h = cv2.boundingRect(contour)
    return x, y, w, h


def calculate_contour_aspect_ratio(contour: np.ndarray) -> float:
    """Calculate aspect ratio of contour"""
    x, y, w, h = calculate_bounding_rect(contour)
    if h == 0:
        return float('inf')
    return w / h


def calculate_contour_extent(contour: np.ndarray) -> float:
    """Calculate extent (area ratio) of contour"""
    area = calculate_contour_area(contour)
    x, y, w, h = calculate_bounding_rect(contour)
    rect_area = w * h
    if rect_area == 0:
        return 0.0
    return area / rect_area


def calculate_contour_solidity(contour: np.ndarray) -> float:
    """Calculate solidity of contour"""
    area = calculate_contour_area(contour)
    hull = cv2.convexHull(contour)
    hull_area = calculate_contour_area(hull)
    if hull_area == 0:
        return 0.0
    return area / hull_area


def sort_contours_by_area(contours: List[np.ndarray], reverse: bool = True) -> List[np.ndarray]:
    """Sort contours by area"""
    return sorted(contours, key=calculate_contour_area, reverse=reverse)


def filter_contours_by_area(contours: List[np.ndarray], min_area: float, max_area: float = float('inf')) -> List[np.ndarray]:
    """Filter contours by area range"""
    filtered = []
    for contour in contours:
        area = calculate_contour_area(contour)
        if min_area <= area <= max_area:
            filtered.append(contour)
    return filtered


def calculate_image_scale_factor(original_size: Tuple[int, int], target_size: Tuple[int, int]) -> float:
    """Calculate scale factor to fit image in target size"""
    orig_w, orig_h = original_size
    target_w, target_h = target_size
    
    scale_w = target_w / orig_w
    scale_h = target_h / orig_h
    
    return min(scale_w, scale_h)


def convert_image_coords_to_dxf(image_coords: Tuple[float, float], image_size: Tuple[int, int], mm_per_px: float) -> Tuple[float, float]:
    """Convert image coordinates to DXF coordinates"""
    x, y = image_coords
    img_w, img_h = image_size
    
    # Convert to DXF coordinates
    dxf_x = x * mm_per_px
    dxf_y = (img_h - y) * mm_per_px  # Flip Y coordinate
    
    return dxf_x, dxf_y


def convert_dxf_coords_to_image(dxf_coords: Tuple[float, float], image_size: Tuple[int, int], mm_per_px: float) -> Tuple[float, float]:
    """Convert DXF coordinates to image coordinates"""
    dxf_x, dxf_y = dxf_coords
    img_w, img_h = image_size
    
    # Convert to image coordinates
    x = dxf_x / mm_per_px
    y = img_h - (dxf_y / mm_per_px)  # Flip Y coordinate
    
    return x, y


# Import cv2 for contour operations
try:
    import cv2
except ImportError:
    print("⚠️ OpenCV not available - some math utilities will be limited")
    cv2 = None
