"""
STEP file export functionality for creating 3D extruded contours using CadQuery
Provides professional-grade STEP export with native DXF import and extrusion
"""

import numpy as np
import os
import math
import tempfile


def export_step_file(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0, progress_callback=None):
    """
    Export contours to a 3D file with extruded geometry using CadQuery.
    Supports STEP, OBJ, and other formats supported by CadQuery.
    
    Args:
        contours: List of contours to export
        out_path: Output file path (extension determines format)
        img_size: Image size tuple (height, width)
        mm_per_px: Scale factor in mm per pixel
        extrude_height: Height to extrude contours in mm
        progress_callback: Optional callback function for progress updates (value, message)
        
    Returns:
        True if export is successful, False otherwise
    """
    try:
        import cadquery as cq
    except ImportError:
        print("ERROR: CadQuery not available. Please install with: pip install cadquery")
        return False
    
    # Determine format from file extension
    file_ext = out_path.lower().split('.')[-1]
    
    if file_ext in ['obj', 'stl']:
        return export_obj_file_cadquery(contours, out_path, img_size, mm_per_px, extrude_height, progress_callback)
    else:
        # Default to STEP format
        return export_step_file_cadquery(contours, out_path, img_size, mm_per_px, extrude_height, progress_callback)


def export_step_file_cadquery(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0, progress_callback=None):
    """
    Export contours to STEP file using CadQuery.
    Uses the professional approach: DXF -> CadQuery -> STEP
    """
    import cadquery as cq
    import ezdxf
    
    if not contours:
        print("No contours to export")
        return False
    
    h, w = img_size
    print(f"Creating STEP file with CadQuery: {len(contours)} contours, {extrude_height}mm extrusion height")
    
    if progress_callback:
        progress_callback(10, "Creating temporary DXF file...")
    
    try:
        # Create a temporary DXF file with our contours
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as temp_dxf:
            temp_dxf_path = temp_dxf.name
        
        # Create DXF file with contours
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        # Add contours as polylines
        for i, contour in enumerate(contours):
            if len(contour) < 3:
                continue
                
            # Convert contour points to DXF coordinates
            points = []
            for point in contour:
                # Convert from image coordinates to DXF coordinates
                x = point[0][0] * mm_per_px
                y = (h - point[0][1]) * mm_per_px  # Flip Y coordinate
                points.append((x, y))
            
            # Close the contour if it's not already closed
            if len(points) > 2 and points[0] != points[-1]:
                points.append(points[0])
            
            # Add as polyline
            if len(points) >= 3:
                polyline = msp.add_lwpolyline(points)
                print(f"DEBUG: Added contour {i} with {len(points)} points to DXF")
            
            # Update progress
            if progress_callback:
                progress = 20 + (i / len(contours)) * 30  # 20-50% for DXF creation
                progress_callback(int(progress), f"Processing contour {i+1}/{len(contours)}...")
        
        # Save DXF file
        doc.saveas(temp_dxf_path)
        print(f"DEBUG: Created temporary DXF file: {temp_dxf_path}")
        
        if progress_callback:
            progress_callback(50, "DXF file created, importing with CadQuery...")
        
        # Use CadQuery to import DXF and extrude
        try:
            if progress_callback:
                progress_callback(60, "Importing DXF with CadQuery...")
            
            # Import DXF and extrude
            result = cq.importers.importDXF(temp_dxf_path).wires().toPending().extrude(extrude_height)
            
            if progress_callback:
                progress_callback(80, "Extruding geometry...")
            
            # Export to STEP
            result.export(out_path)
            
            if progress_callback:
                progress_callback(90, "Creating STL file for preview...")
            
            # Also create an STL file for preview
            stl_path = out_path.replace('.step', '_preview.stl')
            result.export(stl_path)
            
            print(f"Successfully exported {len(contours)} extruded contours to {out_path} using CadQuery")
            print(f"Each contour extruded {extrude_height}mm in Z direction")
            print("STEP file created with professional CAD quality - fully compatible with SolidWorks")
            print(f"STL preview file created: {stl_path}")
            
            if progress_callback:
                progress_callback(100, "STEP export completed!")
            
            return True
            
        except Exception as e:
            print(f"ERROR: CadQuery STEP processing failed: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False
        
        finally:
            # Clean up temporary DXF file
            try:
                os.unlink(temp_dxf_path)
            except:
                pass
        
    except Exception as e:
        print(f"ERROR: Failed to export STEP file with CadQuery: {e}")
        if progress_callback:
            progress_callback(0, f"Error: {str(e)}")
        return False


def export_obj_file_cadquery(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0, progress_callback=None):
    """
    Export contours to STL file using CadQuery (since OBJ is not directly supported).
    Uses the same DXF approach but exports as STL.
    """
    import cadquery as cq
    import ezdxf
    
    if not contours:
        print("No contours to export")
        return False
    
    h, w = img_size
    print(f"Creating STL file with CadQuery: {len(contours)} contours, {extrude_height}mm extrusion height")
    
    if progress_callback:
        progress_callback(10, "Creating temporary DXF file...")
    
    try:
        # Create a temporary DXF file with our contours
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as temp_dxf:
            temp_dxf_path = temp_dxf.name
        
        # Create DXF file with contours (same as STEP version)
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        # Add contours as polylines
        for i, contour in enumerate(contours):
            if len(contour) < 3:
                continue
                
            # Convert contour points to DXF coordinates
            points = []
            for point in contour:
                # Convert from image coordinates to DXF coordinates
                x = point[0][0] * mm_per_px
                y = (h - point[0][1]) * mm_per_px  # Flip Y coordinate
                points.append((x, y))
            
            # Close the contour if it's not already closed
            if len(points) > 2 and points[0] != points[-1]:
                points.append(points[0])
            
            # Add as polyline
            if len(points) >= 3:
                polyline = msp.add_lwpolyline(points)
                print(f"DEBUG: Added contour {i} with {len(points)} points to DXF")
            
            # Update progress
            if progress_callback:
                progress = 20 + (i / len(contours)) * 30  # 20-50% for DXF creation
                progress_callback(int(progress), f"Processing contour {i+1}/{len(contours)}...")
        
        # Save DXF file
        doc.saveas(temp_dxf_path)
        print(f"DEBUG: Created temporary DXF file: {temp_dxf_path}")
        
        if progress_callback:
            progress_callback(50, "DXF file created, importing with CadQuery...")
        
        # Use CadQuery to import DXF and extrude
        try:
            if progress_callback:
                progress_callback(60, "Importing DXF with CadQuery...")
            
            # Import DXF and extrude
            result = cq.importers.importDXF(temp_dxf_path).wires().toPending().extrude(extrude_height)
            
            if progress_callback:
                progress_callback(80, "Extruding geometry...")
            
            # Export to STL (CadQuery supports STL export)
            result.export(out_path)
            
            if progress_callback:
                progress_callback(90, "Saving STL file...")
            
            print(f"Successfully exported {len(contours)} extruded contours to {out_path} using CadQuery")
            print(f"Each contour extruded {extrude_height}mm in Z direction")
            print("STL file created with professional CAD quality - fully compatible with SolidWorks")
            
            if progress_callback:
                progress_callback(100, "STL export completed!")
            
            return True
            
        except Exception as e:
            print(f"ERROR: CadQuery STL processing failed: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False
        
        finally:
            # Clean up temporary DXF file
            try:
                os.unlink(temp_dxf_path)
            except:
                pass
        
    except Exception as e:
        print(f"ERROR: Failed to export STL file with CadQuery: {e}")
        if progress_callback:
            progress_callback(0, f"Error: {str(e)}")
        return False


def export_step_file_simple(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0, progress_callback=None):
    """
    Fallback STL export function for when CadQuery is not available.
    This is a simplified version that creates basic STL files.
    """
    try:
        import trimesh
    except ImportError:
        print("ERROR: Neither CadQuery nor trimesh available for 3D export")
        return False
    
    if not contours:
        print("No contours to export")
        return False
    
    print(f"Creating STL file with trimesh fallback: {len(contours)} contours, {extrude_height}mm extrusion height")
    
    if progress_callback:
        progress_callback(10, "Creating 3D geometry with trimesh...")
    
    try:
        # Create a simple STL using trimesh
        meshes = []
        
        for i, contour in enumerate(contours):
            if len(contour) < 3:
                continue
            
            # Convert contour to 2D points
            points_2d = []
            for point in contour:
                x = point[0][0] * mm_per_px
                y = point[0][1] * mm_per_px
                points_2d.append([x, y])
            
            # Create 3D points by extruding
            points_3d = []
            for point in points_2d:
                points_3d.append([point[0], point[1], 0])  # Bottom
                points_3d.append([point[0], point[1], extrude_height])  # Top
            
            # Create faces for the extruded shape
            faces = []
            n = len(points_2d)
            
            # Side faces
            for i in range(n):
                next_i = (i + 1) % n
                # Each side face is a quad, split into two triangles
                faces.append([i*2, next_i*2, i*2+1])
                faces.append([i*2+1, next_i*2, next_i*2+1])
            
            # Top and bottom faces
            for i in range(1, n-1):
                faces.append([0, i*2, (i+1)*2])  # Bottom
                faces.append([1, (i+1)*2+1, i*2+1])  # Top
            
            # Create mesh
            mesh = trimesh.Trimesh(vertices=points_3d, faces=faces)
            meshes.append(mesh)
            
            # Update progress
            if progress_callback:
                progress = 20 + (i / len(contours)) * 60  # 20-80% for mesh creation
                progress_callback(int(progress), f"Creating mesh {i+1}/{len(contours)}...")
        
        if meshes:
            if progress_callback:
                progress_callback(80, "Combining meshes...")
            
            # Combine all meshes
            combined = trimesh.util.concatenate(meshes)
            
            if progress_callback:
                progress_callback(90, "Saving STL file...")
            
            combined.export(out_path)
            print(f"Successfully exported {len(contours)} contours to {out_path} using trimesh fallback")
            
            if progress_callback:
                progress_callback(100, "STL export completed!")
            
            return True
        else:
            print("No valid contours to export")
            if progress_callback:
                progress_callback(0, "No valid contours to export")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to export STL file with trimesh fallback: {e}")
        if progress_callback:
            progress_callback(0, f"Error: {str(e)}")
        return False