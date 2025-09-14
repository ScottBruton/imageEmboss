"""
STEP file export functionality for creating 3D extruded contours
Creates STEP files manually without external dependencies
"""

import numpy as np
import os
import math

def export_step_file(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
    """
    Export contours to a STEP file with extruded geometry.
    Creates a basic STEP file format manually.
    
    Args:
        contours: List of contours to export
        out_path: Output STEP file path
        img_size: Image size tuple (height, width)
        mm_per_px: Scale factor in mm per pixel
        extrude_height: Height to extrude contours in mm
        
    Returns:
        True if export is successful, False otherwise
    """
    if not contours:
        print("No contours to export")
        return False
    
    h, w = img_size
    print(f"Creating STEP file with {len(contours)} contours, {extrude_height}mm extrusion height")
    
    try:
        with open(out_path, 'w') as f:
            # Write STEP file header
            f.write("ISO-10303-21;\n")
            f.write("HEADER;\n")
            f.write("FILE_DESCRIPTION(('STEP AP214'),'2;1');\n")
            f.write("FILE_NAME('contour_export','2024-01-01T00:00:00',(''),(''),'STEP AP214','','');\n")
            f.write("FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\n")
            f.write("ENDSEC;\n\n")
            
            f.write("DATA;\n")
            
            # Write basic entities
            entity_id = 1
            
            # Write units
            f.write(f"#{entity_id} = LENGTH_UNIT('MILLIMETRE',.LENGTH_UNIT.);\n")
            entity_id += 1
            
            f.write(f"#{entity_id} = PLANE_ANGLE_UNIT('DEGREE',.PLANE_ANGLE_UNIT.);\n")
            entity_id += 1
            
            # Write coordinate system
            f.write(f"#{entity_id} = CARTESIAN_POINT('ORIGIN',(0.0,0.0,0.0));\n")
            origin_id = entity_id
            entity_id += 1
            
            f.write(f"#{entity_id} = DIRECTION('Z_AXIS',(0.0,0.0,1.0));\n")
            z_axis_id = entity_id
            entity_id += 1
            
            f.write(f"#{entity_id} = DIRECTION('X_AXIS',(1.0,0.0,0.0));\n")
            x_axis_id = entity_id
            entity_id += 1
            
            f.write(f"#{entity_id} = AXIS2_PLACEMENT_3D('PLACEMENT',{origin_id},{z_axis_id},{x_axis_id});\n")
            placement_id = entity_id
            entity_id += 1
            
            successful_extrusions = 0
            
            for i, cnt in enumerate(contours):
                if len(cnt) < 3:
                    continue
                
                try:
                    # Convert contour to points
                    points = []
                    for j, p in enumerate(cnt):
                        try:
                            # Handle numpy array format: [[x, y]]
                            if isinstance(p, np.ndarray) and p.shape == (1, 2):
                                x, y = float(p[0][0]), float(p[0][1])
                            elif len(p) >= 2:
                                if isinstance(p[0], (list, tuple, np.ndarray)) and len(p[0]) >= 2:
                                    x, y = float(p[0][0]), float(p[0][1])
                                else:
                                    x, y = float(p[0]), float(p[1])
                            else:
                                continue
                            
                            # Convert to CAD coordinates
                            x_mm = x * mm_per_px
                            y_mm = (h - y) * mm_per_px  # Flip Y coordinate for CAD systems
                            points.append((x_mm, y_mm, 0.0))  # Start at Z=0
                            
                        except (IndexError, TypeError, ValueError):
                            continue
                    
                    if len(points) < 3:
                        continue
                    
                    # Create bottom face points
                    bottom_points = []
                    for point_id, (x, y, z) in enumerate(points):
                        f.write(f"#{entity_id} = CARTESIAN_POINT('BOTTOM_{i}_{point_id}',({x:.6f},{y:.6f},{z:.6f}));\n")
                        bottom_points.append(entity_id)
                        entity_id += 1
                    
                    # Create top face points (extruded)
                    top_points = []
                    for point_id, (x, y, z) in enumerate(points):
                        f.write(f"#{entity_id} = CARTESIAN_POINT('TOP_{i}_{point_id}',({x:.6f},{y:.6f},{z + extrude_height:.6f}));\n")
                        top_points.append(entity_id)
                        entity_id += 1
                    
                    # Create bottom face
                    f.write(f"#{entity_id} = POLY_LOOP('BOTTOM_LOOP_{i}',(")
                    for j, point_id in enumerate(bottom_points):
                        if j > 0:
                            f.write(",")
                        f.write(f"{point_id}")
                    f.write("));\n")
                    bottom_loop_id = entity_id
                    entity_id += 1
                    
                    # Create top face
                    f.write(f"#{entity_id} = POLY_LOOP('TOP_LOOP_{i}',(")
                    for j, point_id in enumerate(top_points):
                        if j > 0:
                            f.write(",")
                        f.write(f"{point_id}")
                    f.write("));\n")
                    top_loop_id = entity_id
                    entity_id += 1
                    
                    # Create face bounds
                    f.write(f"#{entity_id} = FACE_BOUND('BOTTOM_BOUND_{i}',{bottom_loop_id},.T.);\n")
                    bottom_bound_id = entity_id
                    entity_id += 1
                    
                    f.write(f"#{entity_id} = FACE_BOUND('TOP_BOUND_{i}',{top_loop_id},.T.);\n")
                    top_bound_id = entity_id
                    entity_id += 1
                    
                    # Create faces
                    f.write(f"#{entity_id} = PLANE('BOTTOM_FACE_{i}',{placement_id});\n")
                    bottom_plane_id = entity_id
                    entity_id += 1
                    
                    f.write(f"#{entity_id} = PLANE('TOP_FACE_{i}',{placement_id});\n")
                    top_plane_id = entity_id
                    entity_id += 1
                    
                    f.write(f"#{entity_id} = ADVANCED_FACE('BOTTOM_FACE_{i}',(#{bottom_bound_id}),{bottom_plane_id},.T.);\n")
                    bottom_face_id = entity_id
                    entity_id += 1
                    
                    f.write(f"#{entity_id} = ADVANCED_FACE('TOP_FACE_{i}',(#{top_bound_id}),{top_plane_id},.T.);\n")
                    top_face_id = entity_id
                    entity_id += 1
                    
                    # Create side faces (simplified - just create a basic solid)
                    f.write(f"#{entity_id} = CLOSED_SHELL('SHELL_{i}',(#{bottom_face_id},#{top_face_id}));\n")
                    shell_id = entity_id
                    entity_id += 1
                    
                    f.write(f"#{entity_id} = MANIFOLD_SOLID_BREP('SOLID_{i}',{shell_id});\n")
                    solid_id = entity_id
                    entity_id += 1
                    
                    successful_extrusions += 1
                    
                    if i < 5:  # Print first few for debugging
                        print(f"DEBUG: Created extruded contour {i} with {len(points)} points")
                        
                except Exception as e:
                    print(f"Warning: Failed to create extruded contour {i}: {e}")
                    continue
            
            f.write("ENDSEC;\n")
            f.write("END-ISO-10303-21;\n")
        
        if successful_extrusions == 0:
            print("No valid contours could be processed")
            return False
        
        print(f"Successfully exported {successful_extrusions} extruded contours to {out_path}")
        print(f"Each contour extruded {extrude_height}mm in Z direction")
        print("Note: This is a basic STEP file format. For full compatibility, consider using a CAD library.")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to export STEP file: {e}")
        return False


def export_step_file_simple(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
    """
    Alternative: Export as STL file (3D mesh format) which is simpler and widely supported
    """
    if not contours:
        print("No contours to export")
        return False
    
    # Change extension to .stl
    stl_path = out_path.replace('.step', '.stl').replace('.stp', '.stl')
    
    h, w = img_size
    print(f"Creating STL file with {len(contours)} contours, {extrude_height}mm extrusion height")
    
    try:
        with open(stl_path, 'w') as f:
            f.write("solid contour_export\n")
            
            for i, cnt in enumerate(contours):
                if len(cnt) < 3:
                    continue
                
                try:
                    # Convert contour to points
                    points = []
                    for j, p in enumerate(cnt):
                        try:
                            if isinstance(p, np.ndarray) and p.shape == (1, 2):
                                x, y = float(p[0][0]), float(p[0][1])
                            elif len(p) >= 2:
                                if isinstance(p[0], (list, tuple, np.ndarray)) and len(p[0]) >= 2:
                                    x, y = float(p[0][0]), float(p[0][1])
                                else:
                                    x, y = float(p[0]), float(p[1])
                            else:
                                continue
                            
                            x_mm = x * mm_per_px
                            y_mm = (h - y) * mm_per_px
                            points.append((x_mm, y_mm, 0.0))
                            
                        except (IndexError, TypeError, ValueError):
                            continue
                    
                    if len(points) < 3:
                        continue
                    
                    # Create triangles for bottom face
                    for j in range(len(points) - 2):
                        p1 = points[0]
                        p2 = points[j + 1]
                        p3 = points[j + 2]
                        
                        # Calculate normal (pointing down)
                        normal = (0, 0, -1)
                        
                        f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                        f.write("    outer loop\n")
                        f.write(f"      vertex {p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f}\n")
                        f.write(f"      vertex {p2[0]:.6f} {p2[1]:.6f} {p2[2]:.6f}\n")
                        f.write(f"      vertex {p3[0]:.6f} {p3[1]:.6f} {p3[2]:.6f}\n")
                        f.write("    endloop\n")
                        f.write("  endfacet\n")
                    
                    # Create triangles for top face
                    for j in range(len(points) - 2):
                        p1 = (points[0][0], points[0][1], points[0][2] + extrude_height)
                        p2 = (points[j + 1][0], points[j + 1][1], points[j + 1][2] + extrude_height)
                        p3 = (points[j + 2][0], points[j + 2][1], points[j + 2][2] + extrude_height)
                        
                        # Calculate normal (pointing up)
                        normal = (0, 0, 1)
                        
                        f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                        f.write("    outer loop\n")
                        f.write(f"      vertex {p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f}\n")
                        f.write(f"      vertex {p2[0]:.6f} {p2[1]:.6f} {p2[2]:.6f}\n")
                        f.write(f"      vertex {p3[0]:.6f} {p3[1]:.6f} {p3[2]:.6f}\n")
                        f.write("    endloop\n")
                        f.write("  endfacet\n")
                    
                    # Create side faces (simplified)
                    for j in range(len(points)):
                        p1 = points[j]
                        p2 = points[(j + 1) % len(points)]
                        p3 = (p1[0], p1[1], p1[2] + extrude_height)
                        p4 = (p2[0], p2[1], p2[2] + extrude_height)
                        
                        # Create two triangles for each side face
                        # Triangle 1
                        normal = calculate_normal(p1, p2, p3)
                        f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                        f.write("    outer loop\n")
                        f.write(f"      vertex {p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f}\n")
                        f.write(f"      vertex {p2[0]:.6f} {p2[1]:.6f} {p2[2]:.6f}\n")
                        f.write(f"      vertex {p3[0]:.6f} {p3[1]:.6f} {p3[2]:.6f}\n")
                        f.write("    endloop\n")
                        f.write("  endfacet\n")
                        
                        # Triangle 2
                        normal = calculate_normal(p2, p4, p3)
                        f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                        f.write("    outer loop\n")
                        f.write(f"      vertex {p2[0]:.6f} {p2[1]:.6f} {p2[2]:.6f}\n")
                        f.write(f"      vertex {p4[0]:.6f} {p4[1]:.6f} {p4[2]:.6f}\n")
                        f.write(f"      vertex {p3[0]:.6f} {p3[1]:.6f} {p3[2]:.6f}\n")
                        f.write("    endloop\n")
                        f.write("  endfacet\n")
                        
                except Exception as e:
                    print(f"Warning: Failed to create STL contour {i}: {e}")
                    continue
            
            f.write("endsolid contour_export\n")
        
        print(f"Successfully exported STL file: {stl_path}")
        print("STL files can be imported into most CAD software including SolidWorks")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to export STL file: {e}")
        return False


def calculate_normal(p1, p2, p3):
    """Calculate normal vector for a triangle"""
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(p3) - np.array(p1)
    normal = np.cross(v1, v2)
    length = np.linalg.norm(normal)
    if length > 0:
        normal = normal / length
    return normal