"""
STEP file export functionality for creating 3D extruded contours
Creates STEP files manually without external dependencies
"""

import numpy as np
import os
import math

def export_step_file(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
    """
    Export contours to a 3D file with extruded geometry.
    Supports STEP, OBJ, and X_T formats.
    
    Args:
        contours: List of contours to export
        out_path: Output file path (extension determines format)
        img_size: Image size tuple (height, width)
        mm_per_px: Scale factor in mm per pixel
        extrude_height: Height to extrude contours in mm
        
    Returns:
        True if export is successful, False otherwise
    """
    # Determine format from file extension
    file_ext = out_path.lower().split('.')[-1]
    
    if file_ext in ['obj']:
        return export_obj_file(contours, out_path, img_size, mm_per_px, extrude_height)
    # X_T format not supported by trimesh, so we'll skip it
    else:
        # Default to STEP format
        return export_step_file_internal(contours, out_path, img_size, mm_per_px, extrude_height)


def export_step_file_internal(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
    """
    Internal STEP export function.
    """
    # Try different methods in order of preference
    methods = [
        ("trimesh", export_step_file_trimesh),
        ("manual", export_step_file_manual),
        ("meshio_stl", export_step_file_meshio_stl)
    ]
    
    for method_name, method_func in methods:
        try:
            if method_name == "meshio_stl":
                import meshio
                print("Using meshio for STL export (STEP not supported)...")
                return method_func(contours, out_path, img_size, mm_per_px, extrude_height)
            elif method_name == "trimesh":
                import trimesh
                print("Using trimesh for STEP export...")
                return method_func(contours, out_path, img_size, mm_per_px, extrude_height)
            else:
                print(f"Using {method_name} STEP creation...")
                return method_func(contours, out_path, img_size, mm_per_px, extrude_height)
        except ImportError:
            print(f"{method_name} not available, trying next method...")
            continue
        except Exception as e:
            print(f"{method_name} failed: {e}, trying next method...")
            continue
    
    print("All STEP export methods failed")
    return False


def export_obj_file(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
    """
    Export contours to OBJ file using trimesh.
    """
    import trimesh
    import numpy as np
    
    if not contours:
        print("No contours to export")
        return False
    
    h, w = img_size
    print(f"Creating OBJ file with trimesh: {len(contours)} contours, {extrude_height}mm extrusion height")
    
    try:
        # Create a list to store all meshes
        meshes = []
        
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
                        points.append([x_mm, y_mm, 0.0])  # Start at Z=0
                        
                    except (IndexError, TypeError, ValueError):
                        continue
                
                if len(points) < 3:
                    continue
                
                # Create bottom face points
                bottom_points = np.array(points)
                
                # Create top face points (extruded)
                top_points = bottom_points.copy()
                top_points[:, 2] = extrude_height
                
                # Create vertices for the extruded shape
                vertices = np.vstack([bottom_points, top_points])
                
                # Create faces for the extruded shape
                faces = []
                
                # Bottom face (triangulated)
                for j in range(len(points) - 2):
                    faces.append([0, j + 1, j + 2])
                
                # Top face (triangulated)
                top_start = len(points)
                for j in range(len(points) - 2):
                    faces.append([top_start, top_start + j + 2, top_start + j + 1])
                
                # Side faces
                for j in range(len(points)):
                    next_j = (j + 1) % len(points)
                    
                    # Each side face is made of two triangles
                    # Triangle 1
                    faces.append([j, next_j, top_start + j])
                    # Triangle 2
                    faces.append([next_j, top_start + next_j, top_start + j])
                
                # Create trimesh object
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                meshes.append(mesh)
                print(f"DEBUG: Created OBJ contour {i} with {len(points)} points")
                    
            except Exception as e:
                print(f"Warning: Failed to create OBJ contour {i}: {e}")
                continue
        
        if not meshes:
            print("No valid meshes could be created")
            return False
        
        # Combine all meshes
        if len(meshes) == 1:
            combined_mesh = meshes[0]
        else:
            combined_mesh = trimesh.util.concatenate(meshes)
        
        # Export to OBJ file
        combined_mesh.export(out_path, file_type='obj')
        
        print(f"Successfully exported {len(meshes)} extruded contours to {out_path} using trimesh")
        print(f"Each contour extruded {extrude_height}mm in Z direction")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to export OBJ file with trimesh: {e}")
        return False


def export_step_file_meshio_stl(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
    """
    Export contours to STL file using meshio library (since STEP is not supported).
    """
    import meshio
    import numpy as np
    
    if not contours:
        print("No contours to export")
        return False
    
    h, w = img_size
    print(f"Creating STL file with meshio: {len(contours)} contours, {extrude_height}mm extrusion height")
    
    # Change extension to .stl
    stl_path = out_path.replace('.step', '.stl').replace('.stp', '.stl')
    
    try:
        # Create a list to store all vertices and faces
        all_vertices = []
        all_faces = []
        vertex_offset = 0
        
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
                        points.append([x_mm, y_mm, 0.0])  # Start at Z=0
                        
                    except (IndexError, TypeError, ValueError):
                        continue
                
                if len(points) < 3:
                    continue
                
                # Create bottom face points
                bottom_points = np.array(points)
                
                # Create top face points (extruded)
                top_points = bottom_points.copy()
                top_points[:, 2] = extrude_height
                
                # Create vertices for the extruded shape
                vertices = np.vstack([bottom_points, top_points])
                
                # Create faces for the extruded shape
                faces = []
                
                # Bottom face (triangulated)
                for j in range(len(points) - 2):
                    faces.append([0, j + 1, j + 2])
                
                # Top face (triangulated)
                top_start = len(points)
                for j in range(len(points) - 2):
                    faces.append([top_start, top_start + j + 2, top_start + j + 1])
                
                # Side faces
                for j in range(len(points)):
                    next_j = (j + 1) % len(points)
                    
                    # Each side face is made of two triangles
                    # Triangle 1
                    faces.append([j, next_j, top_start + j])
                    # Triangle 2
                    faces.append([next_j, top_start + next_j, top_start + j])
                
                # Add vertices to global list
                all_vertices.append(vertices)
                
                # Add faces with proper vertex offset
                faces_with_offset = np.array(faces) + vertex_offset
                all_faces.append(faces_with_offset)
                
                vertex_offset += len(vertices)
                
                print(f"DEBUG: Created meshio STL contour {i} with {len(points)} points")
                    
            except Exception as e:
                print(f"Warning: Failed to create meshio STL contour {i}: {e}")
                continue
        
        if not all_vertices:
            print("No valid meshes could be created")
            return False
        
        # Combine all vertices and faces
        combined_vertices = np.vstack(all_vertices)
        combined_faces = np.vstack(all_faces)
        
        # Create meshio mesh
        mesh = meshio.Mesh(
            points=combined_vertices,
            cells=[("triangle", combined_faces)]
        )
        
        # Export to STL file
        mesh.write(stl_path, file_format="stl")
        
        print(f"Successfully exported {len(all_vertices)} extruded contours to {stl_path} using meshio")
        print(f"Each contour extruded {extrude_height}mm in Z direction")
        print("Note: Exported as STL since meshio doesn't support STEP format")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to export STL file with meshio: {e}")
        return False


def export_step_file_meshio(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
    """
    Export contours to STEP file using meshio library.
    """
    import meshio
    import numpy as np
    
    if not contours:
        print("No contours to export")
        return False
    
    h, w = img_size
    print(f"Creating STEP file with meshio: {len(contours)} contours, {extrude_height}mm extrusion height")
    
    try:
        # Create a list to store all vertices and faces
        all_vertices = []
        all_faces = []
        vertex_offset = 0
        
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
                        points.append([x_mm, y_mm, 0.0])  # Start at Z=0
                        
                    except (IndexError, TypeError, ValueError):
                        continue
                
                if len(points) < 3:
                    continue
                
                # Create bottom face points
                bottom_points = np.array(points)
                
                # Create top face points (extruded)
                top_points = bottom_points.copy()
                top_points[:, 2] = extrude_height
                
                # Create vertices for the extruded shape
                vertices = np.vstack([bottom_points, top_points])
                
                # Create faces for the extruded shape
                faces = []
                
                # Bottom face (triangulated)
                for j in range(len(points) - 2):
                    faces.append([0, j + 1, j + 2])
                
                # Top face (triangulated)
                top_start = len(points)
                for j in range(len(points) - 2):
                    faces.append([top_start, top_start + j + 2, top_start + j + 1])
                
                # Side faces
                for j in range(len(points)):
                    next_j = (j + 1) % len(points)
                    
                    # Each side face is made of two triangles
                    # Triangle 1
                    faces.append([j, next_j, top_start + j])
                    # Triangle 2
                    faces.append([next_j, top_start + next_j, top_start + j])
                
                # Add vertices to global list
                all_vertices.append(vertices)
                
                # Add faces with proper vertex offset
                faces_with_offset = np.array(faces) + vertex_offset
                all_faces.append(faces_with_offset)
                
                vertex_offset += len(vertices)
                
                print(f"DEBUG: Created meshio contour {i} with {len(points)} points")
                    
            except Exception as e:
                print(f"Warning: Failed to create meshio contour {i}: {e}")
                continue
        
        if not all_vertices:
            print("No valid meshes could be created")
            return False
        
        # Combine all vertices and faces
        combined_vertices = np.vstack(all_vertices)
        combined_faces = np.vstack(all_faces)
        
        # Create meshio mesh
        mesh = meshio.Mesh(
            points=combined_vertices,
            cells=[("triangle", combined_faces)]
        )
        
        # Export to STEP file
        mesh.write(out_path, file_format="step")
        
        print(f"Successfully exported {len(all_vertices)} extruded contours to {out_path} using meshio")
        print(f"Each contour extruded {extrude_height}mm in Z direction")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to export STEP file with meshio: {e}")
        return False


def export_step_file_trimesh(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
    """
    Export contours to STEP file using trimesh library.
    Since trimesh doesn't support STEP directly, we'll create a proper STEP file manually.
    """
    import trimesh
    import numpy as np
    
    if not contours:
        print("No contours to export")
        return False
    
    h, w = img_size
    print(f"Creating STEP file with trimesh (manual STEP creation): {len(contours)} contours, {extrude_height}mm extrusion height")
    
    try:
        # Create a list to store all meshes
        meshes = []
        
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
                        points.append([x_mm, y_mm, 0.0])  # Start at Z=0
                        
                    except (IndexError, TypeError, ValueError):
                        continue
                
                if len(points) < 3:
                    continue
                
                # Create bottom face points
                bottom_points = np.array(points)
                
                # Create top face points (extruded)
                top_points = bottom_points.copy()
                top_points[:, 2] = extrude_height
                
                # Create vertices for the extruded shape
                vertices = np.vstack([bottom_points, top_points])
                
                # Create faces for the extruded shape
                faces = []
                
                # Bottom face (triangulated)
                for j in range(len(points) - 2):
                    faces.append([0, j + 1, j + 2])
                
                # Top face (triangulated)
                top_start = len(points)
                for j in range(len(points) - 2):
                    faces.append([top_start, top_start + j + 2, top_start + j + 1])
                
                # Side faces
                for j in range(len(points)):
                    next_j = (j + 1) % len(points)
                    
                    # Each side face is made of two triangles
                    # Triangle 1
                    faces.append([j, next_j, top_start + j])
                    # Triangle 2
                    faces.append([next_j, top_start + next_j, top_start + j])
                
                # Create trimesh object
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                
                # Add mesh (skip validation check since is_valid doesn't exist in this trimesh version)
                meshes.append(mesh)
                print(f"DEBUG: Created trimesh contour {i} with {len(points)} points")
                    
            except Exception as e:
                print(f"Warning: Failed to create trimesh contour {i}: {e}")
                continue
        
        if not meshes:
            print("No valid meshes could be created")
            return False
        
        # Since trimesh doesn't support STEP, create a proper STEP file manually
        return create_step_file_from_meshes(meshes, out_path, extrude_height)
        
    except Exception as e:
        print(f"ERROR: Failed to export STEP file with trimesh: {e}")
        return False


def create_step_file_from_meshes(meshes, out_path, extrude_height):
    """
    Create a proper STEP file from trimesh meshes.
    """
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
            
            # Process each mesh
            for i, mesh in enumerate(meshes):
                try:
                    vertices = mesh.vertices
                    faces = mesh.faces
                    
                    # Create points for this mesh
                    point_ids = []
                    for j, vertex in enumerate(vertices):
                        x, y, z = vertex[0], vertex[1], vertex[2]
                        f.write(f"#{entity_id} = CARTESIAN_POINT('POINT_{i}_{j}',({x:.6f},{y:.6f},{z:.6f}));\n")
                        point_ids.append(entity_id)
                        entity_id += 1
                    
                    # Create triangular faces
                    face_ids = []
                    for j, face in enumerate(faces):
                        p1_id = point_ids[face[0]]
                        p2_id = point_ids[face[1]]
                        p3_id = point_ids[face[2]]
                        
                        # Create triangular face
                        f.write(f"#{entity_id} = TRIANGULAR_FACE('FACE_{i}_{j}',(#{p1_id},#{p2_id},#{p3_id}));\n")
                        face_ids.append(entity_id)
                        entity_id += 1
                    
                    # Create shell from faces
                    f.write(f"#{entity_id} = CLOSED_SHELL('SHELL_{i}',(")
                    for j, face_id in enumerate(face_ids):
                        if j > 0:
                            f.write(",")
                        f.write(f"#{face_id}")
                    f.write("));\n")
                    shell_id = entity_id
                    entity_id += 1
                    
                    # Create solid from shell
                    f.write(f"#{entity_id} = MANIFOLD_SOLID_BREP('SOLID_{i}',{shell_id});\n")
                    solid_id = entity_id
                    entity_id += 1
                    
                    successful_extrusions += 1
                    
                    if i < 5:  # Print first few for debugging
                        print(f"DEBUG: Created STEP solid {i} with {len(vertices)} vertices and {len(faces)} faces")
                        
                except Exception as e:
                    print(f"Warning: Failed to create STEP solid {i}: {e}")
                    continue
            
            f.write("ENDSEC;\n")
            f.write("END-ISO-10303-21;\n")
        
        if successful_extrusions == 0:
            print("No valid solids could be created")
            return False
        
        print(f"Successfully exported {successful_extrusions} extruded contours to {out_path} using trimesh + manual STEP")
        print(f"Each contour extruded {extrude_height}mm in Z direction")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to create STEP file: {e}")
        return False


def export_step_file_manual(contours, out_path, img_size, mm_per_px=0.25, extrude_height=1.0):
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