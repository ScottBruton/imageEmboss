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
    Extract contours from a binary mask with improved closed contour detection.
    
    Args:
        mask: Binary mask image
        largest_n: Number of largest contours to keep
        simplify_pct: Simplification percentage (0-100)
        gap_threshold: Gap closing threshold in pixels
        
    Returns:
        list: List of contours
    """
    print(f"🔍 CONTOUR DETECTION: Starting with largest_n={largest_n}, simplify_pct={simplify_pct}, gap_threshold={gap_threshold}")
    
    # Use RETR_TREE to get all contours (external and internal) and preserve hierarchy
    # Use CHAIN_APPROX_NONE to preserve all points for better closure detection
    contours, hierarchy = cv2.findContours(255 - mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)  # invert so dark = fill

    if not contours:
        print("❌ CONTOUR DETECTION: No contours found")
        return []

    print(f"🔍 CONTOUR DETECTION: Found {len(contours)} raw contours")
    
    # Filter contours by area and keep more contours for better detail preservation
    min_area = 50  # Minimum area to avoid tiny artifacts
    filtered_contours = []
    
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area >= min_area:
            filtered_contours.append(contour)
            if i < 5:  # Log first few for debugging
                print(f"✅ Contour {i}: area={area:.1f}, points={len(contour)}")
        else:
            if i < 5:  # Log first few for debugging
                print(f"❌ Contour {i}: area={area:.1f} (too small, filtered out)")

    print(f"🔍 CONTOUR DETECTION: {len(filtered_contours)} contours after area filtering")

    # Sort by area and keep more contours for better detail
    contours = sorted(filtered_contours, key=cv2.contourArea, reverse=True)[:max(1, int(largest_n * 3))]  # Keep 3x more for better detail
    
    print(f"🔍 CONTOUR DETECTION: Keeping top {len(contours)} contours by area")

    # Apply gap threshold to connect nearby contour segments
    if gap_threshold > 0:
        print(f"🔍 CONTOUR DETECTION: Applying gap closing with threshold {gap_threshold}")
        # Apply gap closing to the entire mask first
        kernel_size = max(1, int(gap_threshold))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        # Create a mask from all contours
        combined_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(combined_mask, contours, -1, 255, -1)
        
        # Apply morphological closing to close gaps
        closed_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find new contours from the gap-closed mask
        new_contours, _ = cv2.findContours(closed_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        
        if new_contours:
            # Keep the largest contours
            new_contours = sorted(new_contours, key=cv2.contourArea, reverse=True)[:max(1, int(largest_n * 3))]
            contours = new_contours
            print(f"🔍 CONTOUR DETECTION: Gap closing resulted in {len(contours)} contours")

    if simplify_pct and simplify_pct > 0:
        h, w = mask.shape[:2]
        diag = np.sqrt(w*w + h*h)
        eps = float(simplify_pct) * 0.01 * diag  # percent of diagonal
        simplified = []
        for c in contours:
            approx = cv2.approxPolyDP(c, eps, True)
            simplified.append(approx if len(approx) >= 3 else c)
        contours = simplified

    # Check closure rate of detected contours
    closed_count = 0
    for i, contour in enumerate(contours):
        if len(contour) >= 3:
            first_point = contour[0][0]
            last_point = contour[-1][0]
            gap = np.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
            if gap < 1.0:  # Within 1 pixel
                closed_count += 1
    
    closure_rate = (closed_count / len(contours) * 100) if contours else 0
    print(f"📊 CONTOUR DETECTION SUMMARY:")
    print(f"   Total contours: {len(contours)}")
    print(f"   Closed contours: {closed_count}")
    print(f"   Closure rate: {closure_rate:.1f}%")

    return contours


def export_dxf(contours, out_path, img_size, mm_per_px=0.25):
    """
    Export contours to a DXF file using professional optimization.
    
    Args:
        contours: List of contours to export
        out_path: Output file path
        img_size: Image size tuple (height, width)
        mm_per_px: Scale factor in mm per pixel
    """
    print(f"🎨 PROFESSIONAL DXF EXPORT: Processing {len(contours)} contours...")
    
    try:
        # Use the professional DXF optimizer
        from methods.dxf_optimizer import optimize_contours_for_dxf, OptimizerConfig
        
        # Create optimizer configuration for high quality
        config = OptimizerConfig(
            endpoint_tolerance=0.05,  # 0.05mm tolerance for endpoint snapping
            max_deviation=0.02,       # 0.02mm max deviation for simplification
            min_segment_length=0.005, # 0.005mm minimum segment length
            preserve_curves=True,     # Preserve curves and arcs
            auto_close_loops=True,    # Automatically close loops
            remove_duplicates=True,   # Remove duplicate segments
            max_gap_to_close=0.1      # 0.1mm max gap to close
        )
        
        # Optimize contours using professional algorithms
        optimized_contours = optimize_contours_for_dxf(contours, img_size, mm_per_px, config)
        
        print(f"🔧 OPTIMIZATION: {len(contours)} original → {len(optimized_contours)} optimized contours")
        
        # Create DXF document
        h, w = img_size
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        successful_contours = 0
        
        # Export optimized contours as high-quality splines
        for i, contour_points in enumerate(optimized_contours):
            if len(contour_points) >= 3:
                try:
                    # Create smooth B-spline for professional quality
                    if len(contour_points) >= 4:
                        # Use fewer control points for smoother curves
                        if len(contour_points) > 20:
                            # Sample points evenly for large contours
                            step = len(contour_points) / 20
                            control_points = []
                            for j in range(20):
                                idx = int(j * step)
                                if idx < len(contour_points):
                                    control_points.append(contour_points[idx])
                        else:
                            control_points = contour_points
                        
                        # Create B-spline for smooth curves
                        spline = msp.add_spline(control_points, degree=3)
                        spline.closed = True
                        successful_contours += 1
                        
                        if i < 3:  # Log first few for debugging
                            print(f"✅ Spline {i}: {len(control_points)} control points")
                    else:
                        # Fallback to polyline for simple contours
                        polyline = msp.add_lwpolyline(contour_points, close=True)
                        polyline.closed = True
                        successful_contours += 1
                        
                except Exception as e:
                    # Final fallback to basic polyline
                    try:
                        polyline = msp.add_lwpolyline(contour_points, close=True)
                        polyline.closed = True
                        successful_contours += 1
                    except Exception as e2:
                        print(f"⚠️ Failed to export contour {i}: {e2}")

        # Print summary
        print(f"📊 PROFESSIONAL DXF EXPORT SUMMARY:")
        print(f"   Original contours: {len(contours)}")
        print(f"   Optimized contours: {len(optimized_contours)}")
        print(f"   Successfully exported: {successful_contours}")
        print(f"   Success rate: {(successful_contours/len(optimized_contours)*100):.1f}%")

        doc.saveas(out_path)
        print(f"💾 Professional DXF file saved to: {out_path}")
        
    except Exception as e:
        print(f"⚠️ Professional optimization failed: {e}, falling back to simple export")
        # Fallback to simple export
        _export_dxf_simple(contours, out_path, img_size, mm_per_px)


def _export_dxf_simple(contours, out_path, img_size, mm_per_px=0.25):
    """
    Simple DXF export fallback.
    """
    h, w = img_size
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Check contour closure before export
    closed_count = 0
    open_count = 0
    total_contours = len(contours)
    
    print(f"🔍 SIMPLE DXF Export: Processing {total_contours} contours...")

    # Image coords have origin top-left, y down.
    # DXF uses origin bottom-left, y up.
    # Flip Y and scale to mm.
    for i, cnt in enumerate(contours):
        pts = []
        for p in cnt:
            # Handle the nested array structure: [[x, y]]
            x = float(p[0][0])
            y = float(p[0][1])
            x_mm = x * mm_per_px
            y_mm = (h - y) * mm_per_px
            pts.append((x_mm, y_mm))
        
        if len(pts) >= 3:
            # Check if contour is closed
            is_closed = _is_contour_closed(pts)
            if is_closed:
                closed_count += 1
                if i < 5:  # Log first few for debugging
                    print(f"✅ Contour {i}: CLOSED ({len(pts)} points)")
            else:
                open_count += 1
                if i < 5:  # Log first few for debugging
                    print(f"❌ Contour {i}: OPEN ({len(pts)} points) - closing with smart interpolation")
                # Close the contour using smart interpolation
                pts = _close_contour_smart(pts, max_gap=5.0)  # 5mm max gap
            
            # Add as closed polyline
            polyline = msp.add_lwpolyline(pts, close=True)
            polyline.closed = True

    # Print summary
    print(f"📊 SIMPLE DXF Export Summary:")
    print(f"   Total contours: {total_contours}")
    print(f"   Closed contours: {closed_count}")
    print(f"   Open contours: {open_count}")
    print(f"   Closure rate: {(closed_count/total_contours)*100:.1f}%")

    doc.saveas(out_path)
    print(f"💾 Simple DXF file saved to: {out_path}")


def _is_contour_closed(points, tolerance=2.0):
    """Check if a contour is closed by comparing first and last points"""
    if len(points) < 3:
        return False
    
    first_point = points[0]
    last_point = points[-1]
    
    # Calculate actual distance between first and last points
    import math
    distance = math.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
    
    return distance < tolerance


def _close_contour_smart(points, max_gap=5.0):
    """
    Intelligently close a contour by connecting endpoints.
    
    Args:
        points: List of (x, y) points
        max_gap: Maximum distance to consider for closing (in same units as points)
    
    Returns:
        List of points with the contour properly closed
    """
    if len(points) < 3:
        return points
    
    first_point = points[0]
    last_point = points[-1]
    
    # Calculate distance between first and last points
    import math
    gap_distance = math.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
    
    # If already closed (within tolerance), return as-is
    if gap_distance < 1e-6:
        return points
    
    # If gap is small, just add the first point to close it
    if gap_distance <= max_gap:
        return points + [first_point]
    
    # For larger gaps, create a smooth connection
    # Use a simple linear interpolation for now (could be enhanced with splines)
    num_interpolation_points = max(2, int(gap_distance / max_gap))
    
    interpolated_points = []
    for i in range(1, num_interpolation_points):
        t = i / num_interpolation_points
        x = last_point[0] + t * (first_point[0] - last_point[0])
        y = last_point[1] + t * (first_point[1] - last_point[1])
        interpolated_points.append((x, y))
    
    return points + interpolated_points + [first_point]


def _close_contour_spline(points, max_gap=5.0):
    """
    Close a contour using spline interpolation for smooth curves.
    
    Args:
        points: List of (x, y) points
        max_gap: Maximum distance to consider for closing
    
    Returns:
        List of points with the contour properly closed using spline
    """
    if len(points) < 3:
        return points
    
    first_point = points[0]
    last_point = points[-1]
    
    # Calculate distance between first and last points
    import math
    gap_distance = math.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
    
    # If already closed, return as-is
    if gap_distance < 1e-6:
        return points
    
    # If gap is small, just add the first point
    if gap_distance <= max_gap:
        return points + [first_point]
    
    try:
        # Use scipy for spline interpolation if available
        import numpy as np
        from scipy.interpolate import CubicSpline
        
        # Create closed loop by adding first point at the end
        closed_points = points + [first_point]
        
        # Convert to numpy arrays
        x_coords = np.array([p[0] for p in closed_points])
        y_coords = np.array([p[1] for p in closed_points])
        
        # Create parameter array (cumulative distance along the curve)
        distances = np.zeros(len(closed_points))
        for i in range(1, len(closed_points)):
            distances[i] = distances[i-1] + math.sqrt(
                (x_coords[i] - x_coords[i-1])**2 + (y_coords[i] - y_coords[i-1])**2
            )
        
        # Create spline interpolations
        cs_x = CubicSpline(distances, x_coords, bc_type='periodic')
        cs_y = CubicSpline(distances, y_coords, bc_type='periodic')
        
        # Generate smooth points along the entire curve
        total_distance = distances[-1]
        num_points = max(len(points), int(total_distance / max_gap))
        t_new = np.linspace(0, total_distance, num_points)
        
        x_new = cs_x(t_new)
        y_new = cs_y(t_new)
        
        # Convert back to list of tuples
        return [(float(x), float(y)) for x, y in zip(x_new, y_new)]
        
    except ImportError:
        # Fallback to simple linear interpolation if scipy not available
        return _close_contour_smart(points, max_gap)


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
        
        # Check closure for this simplification level
        closed_count = 0
        open_count = 0
        
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
                # Check if contour is closed
                is_closed = _is_contour_closed(dxf_points)
                if is_closed:
                    closed_count += 1
                else:
                    open_count += 1
                    # Close the contour using smart interpolation
                    dxf_points = _close_contour_smart(dxf_points, max_gap=5.0)
                
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
                        polyline = msp.add_lwpolyline(dxf_points, close=True)
                        polyline.closed = True
                        total_vertices_after += len(dxf_points)
                        successful_contours += 1
                    except Exception as e2:
                        pass
        
        # Save DXF file
        doc.saveas(level_path)
        created_files.append(level_path)
        
        # Print statistics including closure info
        reduction = ((total_vertices_before - total_vertices_after) / total_vertices_before * 100) if total_vertices_before > 0 else 0
        closure_rate = (closed_count / (closed_count + open_count) * 100) if (closed_count + open_count) > 0 else 0
        print(f"{percentage}% DXF: {len(contours)} → {successful_contours} contours, {total_vertices_before} → {total_vertices_after} vertices ({reduction:.1f}% reduction)")
        print(f"   Closure: {closed_count} closed, {open_count} open ({closure_rate:.1f}% closed)")
    
    print(f"Created {len(created_files)} lightweight DXF versions")
    return created_files