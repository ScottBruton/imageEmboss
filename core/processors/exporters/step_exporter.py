"""
STEP export processor using FreeCAD integration
"""
import os
import subprocess
import tempfile
from typing import Optional
from ..base_processor import PipelineStep
from ...models.processing_result import ProcessingResult


class STEPExporter(PipelineStep):
    """Exports 3D models to STEP format via FreeCAD"""
    
    def __init__(self):
        super().__init__()
        self.supports_gpu = False
        self.freecad_available = False
        self._check_freecad()
    
    def _check_freecad(self):
        """Check if FreeCAD is available"""
        try:
            # Try to find FreeCAD executable
            import shutil
            freecad_path = shutil.which('freecad')
            if freecad_path:
                self.freecad_available = True
                print(f"✅ FreeCAD found at: {freecad_path}")
            else:
                # Try common Windows paths
                common_paths = [
                    r"C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe",
                    r"C:\Program Files\FreeCAD 0.20\bin\FreeCAD.exe",
                    r"C:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe",
                    r"C:\Program Files\FreeCAD\bin\FreeCAD.exe"
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        self.freecad_available = True
                        self.freecad_path = path
                        print(f"✅ FreeCAD found at: {path}")
                        break
                
                if not self.freecad_available:
                    print("⚠️ FreeCAD not found - STEP export will be disabled")
                    
        except Exception as e:
            print(f"⚠️ Error checking FreeCAD: {e}")
            self.freecad_available = False
    
    def execute(self, result: ProcessingResult) -> ProcessingResult:
        """Export 3D model to STEP format"""
        if not result.splines:
            result.set_error("No splines available for STEP export")
            return result
        
        if not self.freecad_available:
            result.set_error("FreeCAD not available for STEP export")
            return result
        
        try:
            params = result.parameters
            
            # Generate output path
            base_name = os.path.splitext(os.path.basename(result.image_path))[0]
            output_dir = os.path.dirname(result.image_path)
            step_path = os.path.join(output_dir, f"{base_name}_3d_model.step")
            
            # Create temporary Python script for FreeCAD
            script_content = self._create_freecad_script(result, params, step_path)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            try:
                # Run FreeCAD script
                cmd = [self.freecad_path, '-c', script_path]
                result_process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result_process.returncode == 0:
                    if os.path.exists(step_path):
                        result.step_path = step_path
                        print(f"🎯 STEP exported: {step_path}")
                    else:
                        result.set_error("STEP file was not created")
                else:
                    result.set_error(f"FreeCAD script failed: {result_process.stderr}")
                    
            finally:
                # Clean up temporary script
                try:
                    os.unlink(script_path)
                except:
                    pass
            
        except subprocess.TimeoutExpired:
            result.set_error("FreeCAD export timed out")
        except Exception as e:
            result.set_error(f"STEP export failed: {str(e)}")
        
        return result
    
    def _create_freecad_script(self, result: ProcessingResult, params, step_path: str) -> str:
        """Create FreeCAD Python script for STEP export"""
        
        # Get image dimensions for scaling
        if result.original_image is not None:
            h, w = result.original_image.shape[:2]
        else:
            h, w = 1000, 1000
        
        script = f"""
import FreeCAD
import Part
import Draft

# Create new document
doc = FreeCAD.newDocument("ImageEmboss_3D")

# Scale factor
mm_per_px = {params.mm_per_px}
extrude_height = {params.extrude_height}

# Process each spline
shapes = []
"""
        
        # Add each spline to the script
        for i, spline_contour in enumerate(result.splines):
            script += f"""
# Spline {i}
points_{i} = ["""
            
            for point in spline_contour:
                x, y = point[0]
                dxf_x = x * params.mm_per_px
                dxf_y = (h - y) * params.mm_per_px
                script += f"FreeCAD.Vector({dxf_x}, {dxf_y}, 0), "
            
            script += f"""]
try:
    # Create wire from points
    wire_{i} = Draft.makeWire(points_{i}, closed=True)
    if wire_{i}.Shape.isClosed():
        # Extrude to create 3D shape
        face_{i} = Part.Face(wire_{i}.Shape)
        extrude_{i} = face_{i}.extrude(FreeCAD.Vector(0, 0, extrude_height))
        shapes.append(extrude_{i})
    else:
        print(f"Warning: Spline {i} is not closed")
except Exception as e:
    print(f"Error processing spline {i}: {{e}}")
"""
        
        script += f"""
# Combine all shapes
if shapes:
    if len(shapes) == 1:
        final_shape = shapes[0]
    else:
        # Union all shapes
        final_shape = shapes[0]
        for shape in shapes[1:]:
            try:
                final_shape = final_shape.fuse(shape)
            except:
                # If fusion fails, just add to compound
                pass
    
    # Create final object
    obj = doc.addObject("Part::Feature", "ImageEmboss_3D")
    obj.Shape = final_shape
    
    # Export to STEP
    import Part
    Part.export([obj], "{step_path}")
    print("STEP export completed successfully")
else:
    print("No valid shapes to export")

# Close document
FreeCAD.closeDocument(doc.Name)
"""
        
        return script
    
    def validate_input(self, result: ProcessingResult) -> bool:
        """Validate input for STEP export"""
        if not result.splines:
            result.set_error("No splines available")
            return False
        
        if not self.freecad_available:
            result.set_error("FreeCAD not available")
            return False
        
        if result.parameters is None:
            result.set_error("No parameters provided")
            return False
        
        return True
    
    def get_progress_weight(self) -> float:
        """STEP export is quick"""
        return 0.1
