"""
Spline generation processor - CRITICAL for smooth curves
"""
import numpy as np
from typing import List
from .base_processor import PipelineStep
from ..models.processing_result import ProcessingResult

# Try to import scipy for spline generation
try:
    from scipy.interpolate import splprep, splev
    SCIPY_AVAILABLE = True
    print("✅ SciPy available for spline generation")
except ImportError:
    SCIPY_AVAILABLE = False
    print("❌ SciPy not available - spline generation will be limited")


class SplineGenerator(PipelineStep):
    """Generates smooth splines from contours - CRITICAL COMPONENT"""
    
    def __init__(self):
        super().__init__()
        self.supports_gpu = False  # Spline generation is CPU-based
    
    def execute(self, result: ProcessingResult) -> ProcessingResult:
        """Generate smooth splines from contours"""
        if not result.contours:
            result.set_error("No contours available for spline generation")
            return result
        
        if not SCIPY_AVAILABLE:
            result.set_error("SciPy not available - cannot generate smooth splines")
            return result
        
        try:
            params = result.parameters
            splines = []
            
            print(f"🎨 Generating smooth splines from {len(result.contours)} contours...")
            
            for i, contour in enumerate(result.contours):
                if len(contour) < 4:  # Need at least 4 points for spline
                    continue
                
                try:
                    # Extract points from contour
                    points = contour.reshape(-1, 2).astype(np.float32)
                    
                    # Ensure contour is closed
                    if not np.allclose(points[0], points[-1]):
                        points = np.vstack([points, points[0]])
                    
                    # Generate smooth spline
                    spline_contour = self._create_smooth_spline(points, params)
                    
                    if spline_contour is not None:
                        splines.append(spline_contour)
                        if i < 3:  # Log first few
                            print(f"✅ Spline {i}: {len(spline_contour)} smooth points from {len(points)} original points")
                    else:
                        if i < 3:
                            print(f"❌ Spline {i}: Failed to create spline")
                        
                except Exception as e:
                    if i < 3:
                        print(f"❌ Spline {i}: Error - {e}")
                    continue
            
            result.splines = splines
            print(f"🎨 Generated {len(splines)} smooth spline contours")
            
            # Check closure rate
            closed_count = 0
            for spline in splines:
                if self._is_contour_closed(spline):
                    closed_count += 1
            
            closure_rate = (closed_count / len(splines) * 100) if splines else 0
            print(f"📊 Spline closure rate: {closure_rate:.1f}% ({closed_count}/{len(splines)})")
            
        except Exception as e:
            result.set_error(f"Spline generation failed: {str(e)}")
        
        return result
    
    def _create_smooth_spline(self, points: np.ndarray, params) -> np.ndarray:
        """Create smooth B-spline from points"""
        try:
            # Calculate smoothing factor based on quality setting
            if params.spline_quality == "high":
                smoothing_factor = len(points) * 0.01  # Light smoothing
                num_spline_points = max(30, len(points) // 2)
            elif params.spline_quality == "medium":
                smoothing_factor = len(points) * 0.05  # Medium smoothing
                num_spline_points = max(20, len(points) // 3)
            else:  # low
                smoothing_factor = len(points) * 0.1   # Heavy smoothing
                num_spline_points = max(15, len(points) // 4)
            
            # Fit B-spline to the points
            tck, u = splprep([points[:, 0], points[:, 1]], 
                           s=smoothing_factor, k=3, per=True)
            
            # Generate smooth spline points
            u_new = np.linspace(0, 1, num_spline_points)
            spline_points = splev(u_new, tck)
            
            # Convert back to contour format
            spline_contour = np.array([[x, y] for x, y in zip(spline_points[0], spline_points[1])], dtype=np.int32)
            spline_contour = spline_contour.reshape(-1, 1, 2)
            
            # Verify it's closed
            if self._is_contour_closed(spline_contour):
                return spline_contour
            else:
                # Force closure
                first_point = spline_contour[0][0]
                last_point = spline_contour[-1][0]
                gap = np.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
                
                if gap > 3.0:  # If gap is too large, add closing point
                    closing_point = np.array([[[first_point[0], first_point[1]]]], dtype=np.int32)
                    spline_contour = np.vstack([spline_contour, closing_point])
                
                return spline_contour
                
        except Exception as e:
            print(f"⚠️ Spline creation failed: {e}")
            return None
    
    def _is_contour_closed(self, contour: np.ndarray) -> bool:
        """Check if contour is properly closed"""
        if len(contour) < 3:
            return False
        
        first_point = contour[0][0]
        last_point = contour[-1][0]
        gap = np.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
        
        return gap < 3.0  # Within 3 pixels is considered closed
    
    def validate_input(self, result: ProcessingResult) -> bool:
        """Validate input for spline generation"""
        if not result.contours:
            result.set_error("No contours available")
            return False
        
        if not SCIPY_AVAILABLE:
            result.set_error("SciPy not available for spline generation")
            return False
        
        if result.parameters is None:
            result.set_error("No parameters provided")
            return False
        
        return True
    
    def get_progress_weight(self) -> float:
        """Spline generation is a significant step"""
        return 0.3
