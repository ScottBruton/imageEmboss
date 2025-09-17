"""
DXF export processor with smooth splines
"""
import ezdxf
import numpy as np
import os
from typing import Optional
from ..base_processor import PipelineStep
from ...models.processing_result import ProcessingResult


class DXFExporter(PipelineStep):
    """Exports smooth splines to DXF format"""
    
    def __init__(self):
        super().__init__()
        self.supports_gpu = False
    
    def execute(self, result: ProcessingResult) -> ProcessingResult:
        """Export splines to DXF file"""
        if not result.splines:
            result.set_error("No splines available for DXF export")
            return result
        
        try:
            params = result.parameters
            
            # Generate output path
            base_name = os.path.splitext(os.path.basename(result.image_path))[0]
            output_dir = os.path.dirname(result.image_path)
            dxf_path = os.path.join(output_dir, f"{base_name}_smooth_splines.dxf")
            
            # Create DXF document
            doc = ezdxf.new('R2010')  # Use newer DXF version for better spline support
            msp = doc.modelspace()
            
            # Get image dimensions for scaling
            if result.original_image is not None:
                h, w = result.original_image.shape[:2]
            else:
                h, w = 1000, 1000  # Default size
            
            # Export each spline
            successful_exports = 0
            for i, spline_contour in enumerate(result.splines):
                try:
                    # Convert contour points to DXF coordinates
                    points = []
                    for point in spline_contour:
                        x, y = point[0]
                        # Convert image coordinates to DXF coordinates
                        # Image: origin top-left, y down
                        # DXF: origin bottom-left, y up
                        dxf_x = x * params.mm_per_px
                        dxf_y = (h - y) * params.mm_per_px  # Flip Y coordinate
                        points.append((dxf_x, dxf_y))
                    
                    if len(points) >= 3:
                        if params.use_splines and len(points) >= 4:
                            # Create smooth B-spline
                            try:
                                # Create control points for spline
                                if len(points) > 20:
                                    # Sample points for large contours
                                    step = len(points) / 20
                                    control_points = []
                                    for j in range(20):
                                        idx = int(j * step)
                                        if idx < len(points):
                                            control_points.append(points[idx])
                                else:
                                    control_points = points
                                
                                # Create B-spline
                                spline = msp.add_spline(control_points)
                                spline.closed = True
                                successful_exports += 1
                                
                                if i < 3:  # Log first few
                                    print(f"✅ DXF Spline {i}: {len(control_points)} control points")
                                    
                            except Exception as e:
                                # Fallback to polyline
                                polyline = msp.add_lwpolyline(points, close=True)
                                polyline.closed = True
                                successful_exports += 1
                                print(f"⚠️ DXF Spline {i} failed, used polyline: {e}")
                        else:
                            # Use polyline
                            polyline = msp.add_lwpolyline(points, close=True)
                            polyline.closed = True
                            successful_exports += 1
                            
                            if i < 3:  # Log first few
                                print(f"✅ DXF Polyline {i}: {len(points)} points")
                
                except Exception as e:
                    print(f"❌ DXF export failed for contour {i}: {e}")
                    continue
            
            # Save DXF file
            doc.saveas(dxf_path)
            result.dxf_path = dxf_path
            
            print(f"💾 DXF exported: {successful_exports}/{len(result.splines)} splines to {dxf_path}")
            
        except Exception as e:
            result.set_error(f"DXF export failed: {str(e)}")
        
        return result
    
    def validate_input(self, result: ProcessingResult) -> bool:
        """Validate input for DXF export"""
        if not result.splines:
            result.set_error("No splines available")
            return False
        
        if result.parameters is None:
            result.set_error("No parameters provided")
            return False
        
        if not result.image_path:
            result.set_error("No image path for output naming")
            return False
        
        return True
    
    def get_progress_weight(self) -> float:
        """DXF export is quick"""
        return 0.1
