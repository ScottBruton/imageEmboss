"""
Helper functions for image processing and DXF export
"""
import cv2
import numpy as np
import ezdxf


def find_edges_and_contours(img_bgr, params):
    """
    Find edges and contours from an image using bilateral filtering, Gaussian blur, and Canny edge detection.
    
    Args:
        img_bgr: Input image in BGR format
        params: Dictionary containing processing parameters
        
    Returns:
        numpy.ndarray: Processed edge mask
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Apply bilateral filter
    bilateral = cv2.bilateralFilter(
        gray,
        params["bilateral_diameter"],
        params["bilateral_sigma_color"],
        params["bilateral_sigma_space"]
    )

    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(
        bilateral,
        (params["gaussian_kernel_size"], params["gaussian_kernel_size"]),
        0
    )

    # Apply Canny edge detection
    edges = cv2.Canny(
        blurred,
        params["canny_lower_threshold"],
        params["canny_upper_threshold"]
    )

    # Create kernel based on edge thickness
    kernel_size = max(1, int(params["edge_thickness"]))
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    # Thicken edges using the kernel
    thickened_edges = cv2.dilate(edges, kernel, iterations=1)
    
    # Invert if needed (for silhouette-style output)
    if params["invert"]:
        thickened_edges = 255 - thickened_edges
    
    return thickened_edges


def contours_from_mask(mask, largest_n=3, simplify_pct=0.6, gap_threshold=5.0):
    """
    Extract contours from a binary mask with optional gap closing and simplification.
    
    Args:
        mask: Binary mask image
        largest_n: Number of largest contours to keep
        simplify_pct: Simplification percentage (0-100)
        gap_threshold: Gap closing threshold in pixels
        
    Returns:
        list: List of contours
    """
    # Find external contours only
    contours, _ = cv2.findContours(255 - mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # invert so dark = fill

    if not contours:
        return []

    # Keep N largest by area
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:max(1, int(largest_n))]

    # Apply gap threshold to connect nearby contour segments
    if gap_threshold > 0:
        # Apply gap closing to the entire mask first
        kernel_size = max(1, int(gap_threshold))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        # Create a mask from all contours
        combined_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(combined_mask, contours, -1, 255, -1)
        
        # Apply morphological closing to close gaps
        closed_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find new contours from the gap-closed mask
        new_contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if new_contours:
            # Keep the largest contours
            new_contours = sorted(new_contours, key=cv2.contourArea, reverse=True)[:max(1, int(largest_n))]
            contours = new_contours

    if simplify_pct and simplify_pct > 0:
        h, w = mask.shape[:2]
        diag = np.sqrt(w*w + h*h)
        eps = float(simplify_pct) * 0.01 * diag  # percent of diagonal
        simplified = []
        for c in contours:
            approx = cv2.approxPolyDP(c, eps, True)
            simplified.append(approx if len(approx) >= 3 else c)
        contours = simplified

    return contours


def export_dxf(contours, out_path, img_size, mm_per_px=0.25):
    """
    Export contours to a DXF file.
    
    Args:
        contours: List of contours to export
        out_path: Output file path
        img_size: Image size tuple (height, width)
        mm_per_px: Scale factor in mm per pixel
    """
    h, w = img_size
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Image coords have origin top-left, y down.
    # DXF uses origin bottom-left, y up.
    # Flip Y and scale to mm.
    for cnt in contours:
        pts = []
        for p in cnt:
            x = float(p[0][0])
            y = float(p[0][1])
            x_mm = x * mm_per_px
            y_mm = (h - y) * mm_per_px
            pts.append((x_mm, y_mm))
        if len(pts) >= 3:
            msp.add_lwpolyline(pts, close=True)

    doc.saveas(out_path)
