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


def export_dxf_lightweight(contours, out_path, img_size, mm_per_px=0.25, 
                          simplify_factor=0.02, min_distance=0.5):
    """
    Export contours to multiple lightweight DXF files with different simplification levels.
    
    Args:
        contours: List of contours to export
        out_path: Base output file path (will create multiple versions)
        img_size: Image size tuple (height, width)
        mm_per_px: Scale factor in mm per pixel
        simplify_factor: Contour simplification factor (0.01-0.1)
        min_distance: Minimum distance between points in mm
    """
    import cv2
    import numpy as np
    import os
    
    if not contours:
        print("No contours to export")
        return []
    
    # Define simplification levels (percentage of original points to keep)
    simplification_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
    
    # Get base filename and extension
    base_path = os.path.splitext(out_path)[0]
    extension = os.path.splitext(out_path)[1]
    
    h, w = img_size
    created_files = []
    
    for level in simplification_levels:
        # Create filename with percentage
        percentage = int(level * 100)
        level_path = f"{base_path}_{percentage}pct{extension}"
        
        # Create DXF document
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        total_vertices_before = 0
        total_vertices_after = 0
        successful_contours = 0
        
        print(f"DEBUG: Creating {percentage}% version with {len(contours)} contours")
        
        for i, cnt in enumerate(contours):
            if len(cnt) < 3:
                continue
            
            # Convert contour to points
            points = []
            for j, p in enumerate(cnt):
                try:
                    # Handle numpy array format: [[x, y]]
                    if isinstance(p, np.ndarray) and p.shape == (1, 2):
                        # Format: [[x, y]]
                        x, y = float(p[0][0]), float(p[0][1])
                        points.append([x, y])
                    elif len(p) >= 2:
                        if isinstance(p[0], (list, tuple, np.ndarray)) and len(p[0]) >= 2:
                            # Format: [[x, y], ...]
                            x, y = float(p[0][0]), float(p[0][1])
                        else:
                            # Format: [x, y]
                            x, y = float(p[0]), float(p[1])
                        points.append([x, y])
                except (IndexError, TypeError, ValueError) as e:
                    continue
            
            if len(points) < 3:
                continue
            
            # Convert to numpy array
            points_array = np.array(points, dtype=np.float32)
            total_vertices_before += len(points_array)
            
            # Convert to DXF coordinates
            dxf_points = []
            for j, p in enumerate(points):
                try:
                    # Handle numpy array format: [[x, y]]
                    if isinstance(p, np.ndarray) and p.shape == (1, 2):
                        x, y = float(p[0][0]), float(p[0][1])
                    else:
                        x, y = float(p[0]), float(p[1])
                    
                    x_mm = x * mm_per_px
                    y_mm = (h - y) * mm_per_px
                    dxf_points.append((x_mm, y_mm))
                except Exception as e:
                    continue
            
            if len(dxf_points) >= 3:
                try:
                    # Calculate how many points to keep based on simplification level
                    target_points = max(3, int(len(dxf_points) * level))
                    
                    # Sample points evenly to achieve target count
                    if len(dxf_points) > target_points:
                        step = len(dxf_points) / target_points
                        control_points = []
                        for k in range(target_points):
                            idx = int(k * step)
                            if idx < len(dxf_points):
                                control_points.append(dxf_points[idx])
                    else:
                        control_points = dxf_points
                    
                    # Add spline with control points
                    msp.add_spline(control_points, degree=3)
                    total_vertices_after += len(control_points)
                    successful_contours += 1
                    
                except Exception as e:
                    # Fallback to polyline if spline fails
                    try:
                        msp.add_lwpolyline(dxf_points, close=True)
                        total_vertices_after += len(dxf_points)
                        successful_contours += 1
                    except Exception as e2:
                        pass
        
        # Save DXF file
        doc.saveas(level_path)
        created_files.append(level_path)
        
        # Print statistics
        reduction = ((total_vertices_before - total_vertices_after) / total_vertices_before * 100) if total_vertices_before > 0 else 0
        print(f"{percentage}% DXF: {len(contours)} → {successful_contours} contours, {total_vertices_before} → {total_vertices_after} vertices ({reduction:.1f}% reduction)")
    
    print(f"Created {len(created_files)} lightweight DXF versions")
    return created_files