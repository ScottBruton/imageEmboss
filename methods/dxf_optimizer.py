"""
DXF Optimizer - Professional path merging and simplification for DXF export
Based on algorithms used by Adobe Illustrator and professional CAD software
"""
import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict
import math


@dataclass
class OptimizerConfig:
    """Configuration for DXF optimization"""
    # Endpoint snapping tolerance (in mm)
    endpoint_tolerance: float = 0.1
    
    # Maximum deviation for simplification (in mm)
    max_deviation: float = 0.05
    
    # Minimum segment length (in mm)
    min_segment_length: float = 0.01
    
    # Whether to preserve arcs/splines
    preserve_curves: bool = True
    
    # Whether to close loops automatically
    auto_close_loops: bool = True
    
    # Whether to remove duplicates
    remove_duplicates: bool = True
    
    # Maximum gap to close (in mm)
    max_gap_to_close: float = 0.2


class PathSegment:
    """Represents a single path segment (line, arc, etc.)"""
    
    def __init__(self, start_point: Tuple[float, float], end_point: Tuple[float, float], 
                 segment_type: str = "line", control_points: List[Tuple[float, float]] = None):
        self.start_point = np.array(start_point)
        self.end_point = np.array(end_point)
        self.segment_type = segment_type  # "line", "arc", "spline"
        self.control_points = control_points or []
        self.length = self._calculate_length()
    
    def _calculate_length(self) -> float:
        """Calculate segment length"""
        if self.segment_type == "line":
            return np.linalg.norm(self.end_point - self.start_point)
        elif self.segment_type == "arc" and len(self.control_points) >= 1:
            # Approximate arc length
            center = self.control_points[0]
            radius = np.linalg.norm(self.start_point - center)
            # This is a simplified calculation
            return radius * math.pi / 2  # Approximate quarter circle
        else:
            # For splines, approximate with straight line
            return np.linalg.norm(self.end_point - self.start_point)
    
    def reverse(self):
        """Reverse the direction of the segment"""
        self.start_point, self.end_point = self.end_point, self.start_point
        if self.control_points:
            self.control_points.reverse()
    
    def get_points(self, num_points: int = 10) -> List[Tuple[float, float]]:
        """Get interpolated points along the segment"""
        if self.segment_type == "line":
            points = []
            for i in range(num_points + 1):
                t = i / num_points
                point = self.start_point + t * (self.end_point - self.start_point)
                points.append((float(point[0]), float(point[1])))
            return points
        else:
            # For arcs and splines, return start and end points for now
            return [(float(self.start_point[0]), float(self.start_point[1])),
                    (float(self.end_point[0]), float(self.end_point[1]))]


class Path:
    """Represents a connected path of segments"""
    
    def __init__(self):
        self.segments: List[PathSegment] = []
        self.is_closed = False
    
    def add_segment(self, segment: PathSegment):
        """Add a segment to the path"""
        self.segments.append(segment)
    
    def can_connect_to(self, other_segment: PathSegment, tolerance: float) -> bool:
        """Check if this path can connect to another segment"""
        if not self.segments:
            return True
        
        last_segment = self.segments[-1]
        # Check if endpoints are close enough
        dist1 = np.linalg.norm(last_segment.end_point - other_segment.start_point)
        dist2 = np.linalg.norm(last_segment.end_point - other_segment.end_point)
        
        return min(dist1, dist2) <= tolerance
    
    def connect_segment(self, segment: PathSegment, tolerance: float):
        """Connect a segment to this path"""
        if not self.segments:
            self.segments.append(segment)
            return
        
        last_segment = self.segments[-1]
        dist1 = np.linalg.norm(last_segment.end_point - segment.start_point)
        dist2 = np.linalg.norm(last_segment.end_point - segment.end_point)
        
        if dist1 <= tolerance:
            # Normal connection
            self.segments.append(segment)
        elif dist2 <= tolerance:
            # Reverse and connect
            segment.reverse()
            self.segments.append(segment)
        else:
            # Gap too large, start new path
            raise ValueError("Cannot connect segment - gap too large")
    
    def get_all_points(self) -> List[Tuple[float, float]]:
        """Get all points in the path"""
        points = []
        for segment in self.segments:
            segment_points = segment.get_points()
            if not points:
                points.extend(segment_points)
            else:
                # Skip first point to avoid duplicates
                points.extend(segment_points[1:])
        return points
    
    def simplify(self, max_deviation: float) -> List[Tuple[float, float]]:
        """Simplify the path using Douglas-Peucker algorithm"""
        points = self.get_all_points()
        if len(points) < 3:
            return points
        
        # Convert to numpy array for processing
        points_array = np.array(points, dtype=np.float32)
        
        # Use OpenCV's Douglas-Peucker algorithm
        epsilon = max_deviation
        simplified = cv2.approxPolyDP(points_array, epsilon, self.is_closed)
        
        return [(float(p[0]), float(p[1])) for p in simplified]
    
    def check_and_close(self, tolerance: float):
        """Check if path should be closed and close it if so"""
        if len(self.segments) < 2:
            return
        
        first_segment = self.segments[0]
        last_segment = self.segments[-1]
        
        dist = np.linalg.norm(last_segment.end_point - first_segment.start_point)
        if dist <= tolerance:
            self.is_closed = True


class DXFOptimizer:
    """Main optimizer class for DXF path merging and simplification"""
    
    def __init__(self, config: OptimizerConfig = None):
        self.config = config or OptimizerConfig()
        self.paths: List[Path] = []
        self.segments: List[PathSegment] = []
    
    def add_contour(self, contour_points: List[Tuple[float, float]], is_closed: bool = True):
        """Add a contour as line segments"""
        if len(contour_points) < 2:
            print(f"DEBUG: Skipping contour with {len(contour_points)} points")
            return
        
        segments_added = 0
        # Convert contour to line segments
        for i in range(len(contour_points)):
            start_point = contour_points[i]
            end_point = contour_points[(i + 1) % len(contour_points)] if is_closed else contour_points[i + 1]
            
            # Calculate segment length
            segment_length = np.linalg.norm(np.array(end_point) - np.array(start_point))
            
            # Skip if segment is too short (but be more lenient)
            if segment_length < self.config.min_segment_length:
                print(f"DEBUG: Skipping short segment: {segment_length:.6f}mm < {self.config.min_segment_length}mm")
                continue
            
            segment = PathSegment(start_point, end_point, "line")
            self.segments.append(segment)
            segments_added += 1
            
            if not is_closed and i == len(contour_points) - 2:
                break
        
        print(f"DEBUG: Added {segments_added} segments from contour with {len(contour_points)} points")
    
    def optimize(self) -> List[List[Tuple[float, float]]]:
        """Main optimization process"""
        print(f"DEBUG: Starting optimization with {len(self.segments)} segments")
        
        # Step 1: Remove duplicate segments
        if self.config.remove_duplicates:
            self._remove_duplicates()
        
        # Step 2: Build connected paths
        self._build_paths()
        
        # Step 3: Close loops if requested
        if self.config.auto_close_loops:
            self._close_loops()
        
        # Step 4: Simplify paths
        optimized_contours = []
        for path in self.paths:
            if len(path.segments) > 0:
                simplified_points = path.simplify(self.config.max_deviation)
                if len(simplified_points) >= 3:
                    optimized_contours.append(simplified_points)
        
        print(f"DEBUG: Optimization complete: {len(self.segments)} segments → {len(optimized_contours)} paths")
        return optimized_contours
    
    def _remove_duplicates(self):
        """Remove duplicate segments"""
        unique_segments = []
        seen = set()
        
        for segment in self.segments:
            # Create a hashable representation
            key = (tuple(segment.start_point), tuple(segment.end_point))
            reverse_key = (tuple(segment.end_point), tuple(segment.start_point))
            
            if key not in seen and reverse_key not in seen:
                unique_segments.append(segment)
                seen.add(key)
        
        print(f"DEBUG: Removed {len(self.segments) - len(unique_segments)} duplicate segments")
        self.segments = unique_segments
    
    def _build_paths(self):
        """Build connected paths from segments"""
        self.paths = []
        remaining_segments = self.segments.copy()
        
        while remaining_segments:
            # Start a new path
            current_path = Path()
            current_segment = remaining_segments.pop(0)
            current_path.add_segment(current_segment)
            
            # Try to extend the path
            changed = True
            while changed and remaining_segments:
                changed = False
                for i, segment in enumerate(remaining_segments):
                    if current_path.can_connect_to(segment, self.config.endpoint_tolerance):
                        try:
                            current_path.connect_segment(segment, self.config.endpoint_tolerance)
                            remaining_segments.pop(i)
                            changed = True
                            break
                        except ValueError:
                            continue
            
            self.paths.append(current_path)
        
        print(f"DEBUG: Built {len(self.paths)} connected paths")
    
    def _close_loops(self):
        """Close paths that form loops"""
        for path in self.paths:
            path.check_and_close(self.config.endpoint_tolerance)
        
        closed_count = sum(1 for path in self.paths if path.is_closed)
        print(f"DEBUG: Closed {closed_count} loops")


def optimize_contours_for_dxf(contours: List, img_size: Tuple[int, int], 
                            mm_per_px: float, config: OptimizerConfig = None) -> List[List[Tuple[float, float]]]:
    """
    Optimize contours for DXF export using professional path merging and simplification
    
    Args:
        contours: List of contours to optimize
        img_size: Image size tuple (height, width)
        mm_per_px: Scale factor in mm per pixel
        config: Optimization configuration
    
    Returns:
        List of optimized contours as point lists
    """
    h, w = img_size
    optimizer = DXFOptimizer(config)
    
    print(f"DEBUG: Processing {len(contours)} contours for optimization")
    print(f"DEBUG: Image size: {w}x{h}, mm_per_px: {mm_per_px}")
    
    # Convert contours to optimizer format
    processed_contours = 0
    for i, cnt in enumerate(contours):
        if len(cnt) < 3:
            print(f"DEBUG: Skipping contour {i} with {len(cnt)} points")
            continue
        
        # Convert contour points to DXF coordinates
        points = []
        for j, p in enumerate(cnt):
            try:
                # Debug: Print first few points to understand structure
                if i < 3 and j < 3:
                    print(f"DEBUG: Contour {i}, Point {j}: {p} (type: {type(p)})")
                
                if len(p) >= 2:
                    if isinstance(p[0], (list, tuple, np.ndarray)) and len(p[0]) >= 2:
                        # Format: [[x, y], ...]
                        x, y = float(p[0][0]), float(p[0][1])
                    else:
                        # Format: [x, y]
                        x, y = float(p[0]), float(p[1])
                    
                    # Convert to DXF coordinates
                    x_mm = x * mm_per_px
                    y_mm = (h - y) * mm_per_px
                    points.append((x_mm, y_mm))
            except (IndexError, TypeError, ValueError) as e:
                print(f"DEBUG: Error processing point {j} in contour {i}: {e}, point: {p}")
                continue
        
        if len(points) >= 3:
            print(f"DEBUG: Adding contour {i} with {len(points)} points")
            optimizer.add_contour(points, is_closed=True)
            processed_contours += 1
        else:
            print(f"DEBUG: Skipping contour {i} - only {len(points)} valid points")
    
    print(f"DEBUG: Successfully processed {processed_contours} contours")
    
    # Run optimization
    return optimizer.optimize()
