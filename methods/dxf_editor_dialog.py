"""
DXF Editor Dialog - Enhanced DXF preview with FreeCAD integration for spline conversion and export options
"""
import os
import sys
import logging
from typing import List, Tuple, Optional, Callable
import numpy as np

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTextEdit, QFileDialog, QMessageBox, 
                               QProgressBar, QGroupBox, QGridLayout, QSpinBox,
                               QDoubleSpinBox, QCheckBox, QComboBox, QSplitter,
                               QScrollArea, QFrame, QToolBar, QSlider, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPoint, QRect
from PySide6.QtGui import QFont, QPixmap, QPainter, QPen, QColor, QPainterPath, QWheelEvent, QMouseEvent

# Try to add FreeCAD to Python path
FREECAD_PATHS = [
    r"C:\Program Files\FreeCAD 1.0\bin",
    r"C:\Program Files\FreeCAD 0.21\bin",
    r"C:\Program Files\FreeCAD 0.20\bin",
]

FREECAD_AVAILABLE = False
FREECAD_PATH = None

for path in FREECAD_PATHS:
    if os.path.exists(path) and path not in sys.path:
        sys.path.append(path)
    
    # Try to create PySide2 compatibility layer
    try:
        import pyside2_compat
    except ImportError:
        pass
    
    try:
        import FreeCAD
        import Part
        import Draft
        FREECAD_AVAILABLE = True
        FREECAD_PATH = path
        print(f"✅ FreeCAD API loaded successfully from {path}")
        break
    except ImportError as e:
        print(f"❌ FreeCAD API not available from {path}: {e}")
        continue

if not FREECAD_AVAILABLE:
    print("❌ FreeCAD API not available from any standard location")
    print("   Please ensure FreeCAD is installed and compatible with Python 3.11")


class DXFPreviewWidget(QLabel):
    """Custom preview widget with zoom and pan functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        
        # Zoom and pan state
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.pan_offset = QPoint(0, 0)
        self.last_pan_point = QPoint(0, 0)
        self.is_panning = False
        
        # Original pixmap
        self.original_pixmap = None
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
    def set_pixmap(self, pixmap):
        """Set the original pixmap and update display"""
        self.original_pixmap = pixmap
        self.update_display()
        
    def update_display(self):
        """Update the display with current zoom and pan"""
        if self.original_pixmap is None:
            return
            
        # Calculate scaled size
        scaled_size = self.original_pixmap.size() * self.zoom_factor
        
        # Choose transformation based on rendering quality setting
        # Get the crisp rendering setting from parent dialog
        use_crisp = True
        if hasattr(self.parent(), 'crisp_rendering'):
            use_crisp = self.parent().crisp_rendering.isChecked()
        
        if use_crisp:
            # Use FastTransformation for crisp lines (no anti-aliasing)
            scaled_pixmap = self.original_pixmap.scaled(
                scaled_size, 
                Qt.KeepAspectRatio, 
                Qt.FastTransformation
            )
        else:
            # Use SmoothTransformation for smooth curves (with anti-aliasing)
            scaled_pixmap = self.original_pixmap.scaled(
                scaled_size, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
        
        # Apply pan offset
        if self.pan_offset != QPoint(0, 0):
            # Create a new pixmap with pan offset
            final_pixmap = QPixmap(scaled_pixmap.size())
            final_pixmap.fill(QColor(255, 255, 255))
            
            painter = QPainter(final_pixmap)
            painter.drawPixmap(self.pan_offset, scaled_pixmap)
            painter.end()
            
            super().setPixmap(final_pixmap)
        else:
            super().setPixmap(scaled_pixmap)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel zoom"""
        # Get mouse position relative to widget
        mouse_pos = event.position().toPoint()
        
        # Calculate zoom factor
        zoom_in = event.angleDelta().y() > 0
        zoom_factor = 1.2 if zoom_in else 1.0 / 1.2
        
        # Apply zoom
        new_zoom = self.zoom_factor * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        
        if new_zoom != self.zoom_factor:
            # Adjust pan offset to zoom towards mouse position
            if self.original_pixmap:
                widget_center = QPoint(self.width() // 2, self.height() // 2)
                mouse_offset = mouse_pos - widget_center
                
                # Calculate the zoom center offset
                zoom_ratio = new_zoom / self.zoom_factor
                self.pan_offset = QPoint(
                    int(self.pan_offset.x() * zoom_ratio + mouse_offset.x() * (zoom_ratio - 1)),
                    int(self.pan_offset.y() * zoom_ratio + mouse_offset.y() * (zoom_ratio - 1))
                )
            
            self.zoom_factor = new_zoom
            self.update_display()
            
            # Emit zoom changed signal if parent has it
            if hasattr(self.parent(), 'zoom_changed'):
                self.parent().zoom_changed(self.zoom_factor)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning"""
        if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
            self.is_panning = True
            self.last_pan_point = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning"""
        if self.is_panning:
            current_pos = event.position().toPoint()
            delta = current_pos - self.last_pan_point
            self.pan_offset += delta
            self.last_pan_point = current_pos
            self.update_display()
        else:
            # Show open hand cursor when hovering
            if event.buttons() == Qt.NoButton:
                self.setCursor(Qt.OpenHandCursor)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
            self.is_panning = False
            self.setCursor(Qt.OpenHandCursor)
    
    def reset_view(self):
        """Reset zoom and pan to default"""
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        self.update_display()
        
    def fit_to_window(self):
        """Fit the image to window size"""
        if self.original_pixmap is None:
            return
            
        # Calculate zoom to fit window
        widget_size = self.size()
        pixmap_size = self.original_pixmap.size()
        
        zoom_x = widget_size.width() / pixmap_size.width()
        zoom_y = widget_size.height() / pixmap_size.height()
        
        self.zoom_factor = min(zoom_x, zoom_y) * 0.9  # 90% to leave some margin
        self.pan_offset = QPoint(0, 0)
        self.update_display()
        
    def zoom_in(self):
        """Zoom in"""
        new_zoom = self.zoom_factor * 1.2
        new_zoom = min(self.max_zoom, new_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.update_display()
            
    def zoom_out(self):
        """Zoom out"""
        new_zoom = self.zoom_factor / 1.2
        new_zoom = max(self.min_zoom, new_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.update_display()


class FreeCADWorker(QThread):
    """Worker thread for FreeCAD operations"""
    progress_updated = Signal(int, str)
    finished = Signal(bool, str)
    
    def __init__(self, dxf_path, operation, extrude_height=1.0, contours=None, img_size=None, mm_per_px=None, dialog=None):
        super().__init__()
        self.dxf_path = dxf_path
        self.operation = operation
        self.extrude_height = extrude_height
        self.contours = contours
        self.img_size = img_size
        self.mm_per_px = mm_per_px
        self.dialog = dialog  # Reference to the dialog for updating current DXF path
        
    def run(self):
        try:
            if self.operation == "convert_splines":
                self.convert_to_splines()
            elif self.operation == "export_step":
                self.export_step()
            elif self.operation == "export_stl":
                self.export_stl()
            elif self.operation == "export_obj":
                self.export_obj()
        except Exception as e:
            self.finished.emit(False, f"Operation failed: {str(e)}")
    
    def convert_to_splines(self):
        """Convert DXF entities to closed splines - using efficient direct method"""
        # Skip FreeCAD for now since it's too slow with large DXF files
        # Use the reliable fallback method instead
        self.convert_to_splines_fallback()
    
    def convert_to_splines_with_timeout(self):
        """Convert with timeout protection"""
        import threading
        import time
        
        # Set a timeout of 5 minutes
        timeout_seconds = 300
        
        def run_conversion():
            try:
                self.convert_to_splines()
            except Exception as e:
                self.finished.emit(False, f"Conversion failed: {str(e)}")
        
        # Start conversion in a separate thread
        conversion_thread = threading.Thread(target=run_conversion)
        conversion_thread.daemon = True
        conversion_thread.start()
        
        # Wait for completion or timeout
        conversion_thread.join(timeout_seconds)
        
        if conversion_thread.is_alive():
            # Timeout occurred
            self.finished.emit(False, f"Conversion timed out after {timeout_seconds} seconds. FreeCAD is taking too long to process the DXF entities. Falling back to direct contour method.")
            # Force fallback
            self.convert_to_splines_fallback()
    
    def _import_dxf_manually(self, doc, dxf_path=None):
        """Manually import DXF using ezdxf and create FreeCAD objects"""
        import ezdxf
        import Part
        import FreeCAD
        
        # Use provided path or default to self.dxf_path
        if dxf_path is None:
            dxf_path = self.dxf_path
        
        # Read DXF file
        doc_dxf = ezdxf.readfile(dxf_path)
        msp = doc_dxf.modelspace()
        
        # Process entities
        for entity in msp:
            if entity.dxftype() in ['LINE', 'LWPOLYLINE', 'POLYLINE', 'SPLINE']:
                try:
                    # Convert entity to FreeCAD shape
                    if entity.dxftype() == 'LINE':
                        start = FreeCAD.Vector(entity.dxf.start.x, entity.dxf.start.y, 0)
                        end = FreeCAD.Vector(entity.dxf.end.x, entity.dxf.end.y, 0)
                        edge = Part.makeLine(start, end)
                        Part.show(edge)
                    elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                        points = []
                        for point in entity.get_points():
                            points.append(FreeCAD.Vector(point[0], point[1], 0))
                        if len(points) > 1:
                            wire = Part.makePolygon(points)
                            Part.show(wire)
                except:
                    pass
    
    def _export_dxf_manually(self, doc, output_path):
        """Manually export FreeCAD objects to DXF"""
        import ezdxf
        import FreeCAD
        
        # Create new DXF document
        doc_dxf = ezdxf.new('R2010')
        msp = doc_dxf.modelspace()
        
        # Export objects
        for obj in doc.Objects:
            if hasattr(obj, 'Shape') and obj.Shape:
                try:
                    if obj.Shape.ShapeType == 'Edge':
                        # Export as line
                        start = obj.Shape.Vertexes[0].Point
                        end = obj.Shape.Vertexes[1].Point
                        msp.add_line((start.x, start.y), (end.x, end.y))
                    elif obj.Shape.ShapeType == 'Wire':
                        # Export as polyline
                        points = [(v.Point.x, v.Point.y) for v in obj.Shape.Vertexes]
                        if len(points) > 1:
                            msp.add_lwpolyline(points)
                    elif obj.Shape.ShapeType == 'BSplineCurve':
                        # Export B-spline curves as splines
                        try:
                            # Get control points from the B-spline
                            curve = obj.Shape.Curve
                            if hasattr(curve, 'getPoles'):
                                poles = curve.getPoles()
                                # Convert to DXF spline
                                control_points = [(p.x, p.y, 0) for p in poles]
                                if len(control_points) > 2:
                                    spline = msp.add_spline(control_points)
                                    spline.dxf.degree = curve.Degree if hasattr(curve, 'Degree') else 3
                        except:
                            # Fallback: sample points and create polyline
                            points = []
                            for i in range(20):  # Sample 20 points
                                param = i / 19.0
                                try:
                                    point = obj.Shape.valueAt(obj.Shape.FirstParameter + param * (obj.Shape.LastParameter - obj.Shape.FirstParameter))
                                    points.append((point.x, point.y))
                                except:
                                    pass
                            if len(points) > 1:
                                msp.add_lwpolyline(points)
                except Exception as e:
                    # Debug: print error for troubleshooting
                    print(f"Export error for {obj.Name}: {e}")
                    pass
        
        # Save DXF
        doc_dxf.saveas(output_path)
    
    def _create_spline_dxf_from_contours(self, output_path):
        """Create a DXF with splines from contours (fallback method) with overlap detection"""
        import ezdxf
        import numpy as np
        
        # Create new DXF document
        doc_dxf = ezdxf.new('R2010')
        msp = doc_dxf.modelspace()
        
        spline_count = 0
        
        print(f"Processing {len(self.contours)} contours for spline conversion...")
        
        for i, contour in enumerate(self.contours):
            if len(contour) < 3:
                print(f"Contour {i}: Skipped - too few points ({len(contour)})")
                continue
                
            try:
                # Extract points from contour
                points = []
                for point in contour:
                    x = float(point[0][0]) * self.mm_per_px
                    y = float(point[0][1]) * self.mm_per_px
                    points.append((x, y))
                
                if len(points) < 3:
                    print(f"Contour {i}: Skipped - too few valid points ({len(points)})")
                    continue
                
                print(f"Contour {i}: Processing {len(points)} points")
                
                # Check for self-intersections and split if needed
                # Skip overlap detection for simple contours to avoid over-processing
                if len(points) > 20:  # Only check complex contours for overlaps
                    try:
                        split_contours = self._detect_and_split_overlaps(points, i)
                        if len(split_contours) > 1:
                            print(f"   📊 Contour {i}: Split into {len(split_contours)} contours")
                        else:
                            print(f"   ✅ Contour {i}: No overlaps detected, using original")
                    except Exception as split_error:
                        print(f"   ❌ Contour {i}: Split detection failed ({split_error}), using original")
                        split_contours = [points]
                else:
                    print(f"   ⚡ Contour {i}: Simple contour, skipping overlap detection")
                    split_contours = [points]
                
                # Process each split contour
                for split_idx, split_points in enumerate(split_contours):
                    if len(split_points) < 3:
                        print(f"   ⚠️ Contour {i}-{split_idx}: Skipped - too few points ({len(split_points)})")
                        continue
                    
                    print(f"   🔄 Processing split contour {i}-{split_idx} with {len(split_points)} points")
                        
                    try:
                        # Try scipy spline first
                        try:
                            from scipy.interpolate import splprep, splev
                            
                            # Convert to numpy array
                            points_array = np.array(split_points)
                            
                            # Create closed spline (like SolidWorks workflow)
                            # Add the first point at the end to close the curve
                            if not np.allclose(points_array[0], points_array[-1]):
                                points_array = np.vstack([points_array, points_array[0]])
                            
                            # Create B-spline using scipy with better parameters for smooth curves
                            # Use adaptive smoothing based on contour complexity
                            num_points = len(split_points)
                            
                            # Adaptive smoothing factor - more smoothing for complex contours
                            if num_points > 100:
                                smoothing_factor = num_points * 0.001  # Light smoothing for complex contours
                            elif num_points > 50:
                                smoothing_factor = num_points * 0.005  # Medium smoothing
                            else:
                                smoothing_factor = num_points * 0.01   # More smoothing for simple contours
                            
                            # Fit spline with adaptive smoothing
                            tck, u = splprep([points_array[:, 0], points_array[:, 1]], 
                                           s=smoothing_factor,  # Adaptive smoothing
                                           k=min(3, num_points-1),  # Degree 3, but not more than points-1
                                           per=True)  # Periodic (closed curve)
                            
                            # Generate many more smooth spline points for better curve quality
                            num_spline_points = max(100, num_points * 4)  # 4x more points for smoothness
                            u_new = np.linspace(0, 1, num_spline_points)
                            spline_points = splev(u_new, tck)
                            
                            # Convert to DXF spline with proper control points
                            control_points = [(x, y, 0) for x, y in zip(spline_points[0], spline_points[1])]
                            
                            if len(control_points) > 2:
                                spline = msp.add_spline(control_points)
                                spline.dxf.degree = 3
                                spline_count += 1
                                if len(split_contours) > 1:
                                    print(f"Contour {i}-{split_idx}: Created spline with {len(control_points)} control points (split from overlapping contour)")
                                else:
                                    print(f"Contour {i}: Created spline with {len(control_points)} control points")
                                    
                        except ImportError:
                            print("Scipy not available, using simple polyline")
                            # Fallback: create polyline if scipy not available
                            msp.add_lwpolyline(split_points)
                            spline_count += 1
                            
                        except Exception as e:
                            print(f"Contour {i}-{split_idx}: Scipy spline failed ({e}), using polyline")
                            # Fallback: create polyline if spline fails
                            try:
                                # Try to create a smooth polyline with fewer points
                                if len(split_points) > 50:
                                    # Simplify polyline for better performance
                                    simplified_points = self._simplify_polyline(split_points, tolerance=0.1)
                                    msp.add_lwpolyline(simplified_points)
                                else:
                                    msp.add_lwpolyline(split_points)
                                spline_count += 1
                            except Exception as poly_error:
                                print(f"Contour {i}-{split_idx}: Polyline creation also failed ({poly_error})")
                                continue
                            
                    except Exception as e:
                        print(f"Contour {i}-{split_idx}: Error processing split ({e})")
                        continue
                    
            except Exception as e:
                print(f"Contour {i}: Error processing ({e})")
                continue
        
        # Save DXF
        doc_dxf.saveas(output_path)
        print(f"Created DXF with {spline_count} splines from {len(self.contours)} contours")
        return spline_count
    
    def _detect_and_split_overlaps(self, points, contour_idx):
        """Detect self-intersections in a contour and split into separate contours"""
        import numpy as np
        
        if len(points) < 4:
            return [points]  # Too few points to have overlaps
        
        # Convert to numpy array for easier manipulation
        points_array = np.array(points)
        
        # Check for self-intersections using line segment intersection
        intersections = []
        
        # Check each line segment against all others
        for i in range(len(points_array) - 1):
            for j in range(i + 2, len(points_array) - 1):  # Skip adjacent segments
                # Get line segments
                p1, p2 = points_array[i], points_array[i + 1]
                p3, p4 = points_array[j], points_array[j + 1]
                
                # Check if segments intersect
                intersection = self._line_segment_intersection(p1, p2, p3, p4)
                if intersection is not None:
                    intersections.append((i, j, intersection))
                    print(f"   🔍 Contour {contour_idx}: Found intersection at segment {i}-{i+1} with {j}-{j+1}")
        
        if not intersections:
            # No intersections found, return original contour
            return [points]
        
        # Split contour at intersection points
        split_contours = []
        used_points = set()
        
        for start_idx in range(len(points_array)):
            if start_idx in used_points:
                continue
                
            # Start a new contour from this point
            current_contour = []
            current_idx = start_idx
            
            while current_idx not in used_points and len(current_contour) < len(points_array):
                current_contour.append(points_array[current_idx])
                used_points.add(current_idx)
                
                # Check if this point is an intersection point
                intersection_found = False
                for int_i, int_j, int_point in intersections:
                    if current_idx == int_i or current_idx == int_j:
                        # Add intersection point (ensure it's a list)
                        if hasattr(int_point, 'tolist'):
                            current_contour.append(int_point.tolist())
                        else:
                            current_contour.append(list(int_point))
                        intersection_found = True
                        break
                
                if intersection_found:
                    break
                    
                current_idx = (current_idx + 1) % len(points_array)
            
            if len(current_contour) >= 3:
                # Convert numpy arrays to lists if needed
                contour_list = []
                for point in current_contour:
                    if hasattr(point, 'tolist'):
                        contour_list.append(point.tolist())
                    else:
                        contour_list.append(list(point))
                split_contours.append(contour_list)
        
        if split_contours:
            print(f"   ✂️ Contour {contour_idx}: Split into {len(split_contours)} separate contours")
            return split_contours
        else:
            return [points]
    
    def _line_segment_intersection(self, p1, p2, p3, p4):
        """Find intersection point of two line segments"""
        import numpy as np
        
        # Convert to numpy arrays
        p1, p2, p3, p4 = np.array(p1), np.array(p2), np.array(p3), np.array(p4)
        
        # Calculate direction vectors
        d1 = p2 - p1
        d2 = p4 - p3
        
        # Calculate denominator
        denom = d1[0] * d2[1] - d1[1] * d2[0]
        
        if abs(denom) < 1e-10:  # Lines are parallel
            return None
        
        # Calculate parameters
        t1 = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / denom
        t2 = ((p3[0] - p1[0]) * d1[1] - (p3[1] - p1[1]) * d1[0]) / denom
        
        # Check if intersection is within both line segments
        if 0 <= t1 <= 1 and 0 <= t2 <= 1:
            intersection = p1 + t1 * d1
            return [float(intersection[0]), float(intersection[1])]
        
        return None
    
    def _simplify_polyline(self, points, tolerance=0.1):
        """Simplify a polyline using Douglas-Peucker algorithm"""
        import numpy as np
        
        if len(points) <= 2:
            return points
        
        # Convert to numpy array
        points_array = np.array(points)
        
        # Find the point with maximum distance from the line between first and last points
        if len(points_array) <= 2:
            return points
        
        # Calculate distances from all points to the line between first and last
        first_point = points_array[0]
        last_point = points_array[-1]
        
        # Vector from first to last point
        line_vector = last_point - first_point
        line_length = np.linalg.norm(line_vector)
        
        if line_length < 1e-10:  # Degenerate case
            return [points[0], points[-1]]
        
        # Normalize line vector
        line_unit = line_vector / line_length
        
        max_distance = 0
        max_index = 0
        
        for i in range(1, len(points_array) - 1):
            # Vector from first point to current point
            point_vector = points_array[i] - first_point
            
            # Project point onto line
            projection_length = np.dot(point_vector, line_unit)
            projection = first_point + projection_length * line_unit
            
            # Distance from point to line
            distance = np.linalg.norm(points_array[i] - projection)
            
            if distance > max_distance:
                max_distance = distance
                max_index = i
        
        # If max distance is greater than tolerance, recursively simplify
        if max_distance > tolerance:
            # Recursively simplify the two segments
            left_simplified = self._simplify_polyline(points[:max_index + 1], tolerance)
            right_simplified = self._simplify_polyline(points[max_index:], tolerance)
            
            # Combine results (avoid duplicate middle point)
            return left_simplified[:-1] + right_simplified
        else:
            # All points are within tolerance, return just endpoints
            return [points[0], points[-1]]
    
    def convert_to_splines_fallback(self):
        """Convert contours to splines using direct contour processing"""
        try:
            self.progress_updated.emit(10, "Converting contours to splines...")
            
            # Create a DXF with splines directly from contours
            output_path = self.dxf_path.replace('.dxf', '_splines.dxf')
            spline_count = self._create_spline_dxf_from_contours(output_path)
            
            self.progress_updated.emit(80, f"Created {spline_count} splines...")
            
            # Update the dialog's current DXF path
            if self.dialog:
                self.dialog.current_dxf_path = output_path
                # Reload the preview with the new DXF
                self.dialog.load_dxf_preview()
            
            self.progress_updated.emit(100, "Spline conversion complete!")
            self.finished.emit(True, f"Successfully converted {spline_count} contours to splines!\nSaved to: {output_path}\nPreview updated to show spline version.")
                
        except Exception as e:
            self.finished.emit(False, f"Spline conversion failed: {str(e)}")
    
    def export_step(self):
        """Export to STEP using FreeCAD with detailed logging"""
        if not FREECAD_AVAILABLE:
            self.export_step_fallback()
            return
        
        try:
            self.progress_updated.emit(10, "Loading DXF into FreeCAD...")
            print("🔧 FreeCAD STEP Export: Starting...")
            
            # Create new FreeCAD document
            import FreeCAD
            doc = FreeCAD.newDocument("DXF_Export")
            
            # Import DXF using manual method (use current DXF path)
            self._import_dxf_manually(doc, self.dxf_path)
            
            # Count total objects first
            total_objects = len([obj for obj in doc.Objects if hasattr(obj, 'Shape')])
            print(f"📊 Found {total_objects} objects in DXF")
            
            self.progress_updated.emit(30, f"Extruding {total_objects} contours...")
            
            # Get all objects and extrude them with detailed logging
            objects = doc.Objects
            extruded_count = 0
            failed_count = 0
            extruded_solids = []
            
            for i, obj in enumerate(objects):
                if hasattr(obj, 'Shape'):
                    try:
                        progress = 30 + int((i / total_objects) * 40)  # 30-70% range
                        self.progress_updated.emit(progress, f"Extruding contour {i + 1}/{total_objects}...")
                        
                        print(f"🔄 Processing object {i + 1}/{total_objects}: {obj.Name}")
                        print(f"   Shape type: {obj.Shape.ShapeType}")
                        print(f"   Shape area: {obj.Shape.Area if hasattr(obj.Shape, 'Area') else 'N/A'}")
                        
                        if obj.Shape.ShapeType == 'Wire':
                            # Create face from wire
                            import Part
                            try:
                                face = Part.Face(obj.Shape)
                                print(f"   ✅ Created face with area: {face.Area}")
                                
                                # Extrude the face
                                solid = face.extrude(FreeCAD.Vector(0, 0, self.extrude_height))
                                print(f"   ✅ Extruded solid with volume: {solid.Volume}")
                                
                                # Add to extruded solids list
                                extruded_solids.append(solid)
                                extruded_count += 1
                                
                            except Exception as face_error:
                                print(f"   ❌ Face creation failed: {face_error}")
                                failed_count += 1
                                
                        elif obj.Shape.ShapeType == 'Edge':
                            # Try to create wire from edge, then face
                            import Part
                            try:
                                wire = Part.Wire(obj.Shape)
                                face = Part.Face(wire)
                                solid = face.extrude(FreeCAD.Vector(0, 0, self.extrude_height))
                                print(f"   ✅ Extruded edge to solid with volume: {solid.Volume}")
                                extruded_solids.append(solid)
                                extruded_count += 1
                                
                            except Exception as edge_error:
                                print(f"   ❌ Edge extrusion failed: {edge_error}")
                                failed_count += 1
                        else:
                            print(f"   ⚠️ Skipping {obj.Shape.ShapeType} - not a wire or edge")
                            failed_count += 1
                            
                    except Exception as e:
                        print(f"   ❌ Object {i + 1} failed: {e}")
                        failed_count += 1
                        continue
            
            print(f"📊 Extrusion Summary:")
            print(f"   ✅ Successfully extruded: {extruded_count}")
            print(f"   ❌ Failed: {failed_count}")
            print(f"   📦 Total solids created: {len(extruded_solids)}")
            
            self.progress_updated.emit(70, f"Extruded {extruded_count}/{total_objects} objects...")
            
            if extruded_solids:
                # Create a compound of all solids
                import Part
                compound = Part.Compound(extruded_solids)
                print(f"🔗 Created compound with {len(extruded_solids)} solids")
                
                # Export to STEP
                output_path = self.dxf_path.replace('.dxf', f'_extruded_{self.extrude_height}mm.step')
                compound.exportStl(output_path.replace('.step', '.stl'))  # Test export first
                compound.exportStep(output_path)
                
                # Check file size
                import os
                file_size = os.path.getsize(output_path)
                print(f"💾 STEP file saved: {output_path}")
                print(f"📏 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                
                self.progress_updated.emit(100, "STEP export complete!")
                self.finished.emit(True, f"Successfully exported {extruded_count} solids to STEP!\nSaved to: {output_path}\nFile size: {file_size:,} bytes")
            else:
                self.finished.emit(False, f"No solids were created. All {total_objects} objects failed to extrude.")
            
        except Exception as e:
            print(f"❌ FreeCAD STEP export failed: {e}")
            self.finished.emit(False, f"FreeCAD STEP export failed: {str(e)}")
    
    def export_step_fallback(self):
        """Fallback STEP export using existing system"""
        try:
            self.progress_updated.emit(10, "Using fallback STEP export...")
            
            from methods.enhanced_step_export import EnhancedStepExporter
            from methods.performance_processor import ProcessingConfig
            import multiprocessing as mp
            
            self.progress_updated.emit(30, "Creating enhanced exporter...")
            
            performance_config = ProcessingConfig(
                max_workers=mp.cpu_count(),
                chunk_size=10,
                use_numba=True,
                use_cadquery=True,
                parallel_extrusion=False,
                enable_profiling=False,
                log_performance=True
            )
            
            enhanced_exporter = EnhancedStepExporter(performance_config)
            
            self.progress_updated.emit(50, "Processing contours...")
            
            # Create output path
            output_path = self.dxf_path.replace('.dxf', f'_extruded_{self.extrude_height}mm.step')
            
            # Export using enhanced system
            success = enhanced_exporter.export_step_file(
                self.contours, self.img_size, self.mm_per_px, 
                self.extrude_height, output_path, self.progress_updated
            )
            
            if success:
                self.progress_updated.emit(100, "STEP export complete!")
                self.finished.emit(True, f"Successfully exported to STEP!\nSaved to: {output_path}")
            else:
                self.finished.emit(False, "STEP export failed")
                
        except Exception as e:
            self.finished.emit(False, f"Fallback STEP export failed: {str(e)}")
    
    def export_stl(self):
        """Export to STL using FreeCAD"""
        if not FREECAD_AVAILABLE:
            self.export_stl_fallback()
            return
        
        try:
            self.progress_updated.emit(10, "Loading DXF into FreeCAD...")
            
            # Create new FreeCAD document
            import FreeCAD
            doc = FreeCAD.newDocument("DXF_Export")
            
            # Import DXF using manual method (use current DXF path)
            self._import_dxf_manually(doc, self.dxf_path)
            
            self.progress_updated.emit(30, "Extruding contours...")
            
            # Get all objects and extrude them
            objects = doc.Objects
            extruded_count = 0
            
            for obj in objects:
                if hasattr(obj, 'Shape') and obj.Shape.ShapeType == 'Wire':
                    try:
                        # Extrude the wire
                        import Part
                        face = Part.Face(obj.Shape)
                        solid = face.extrude(FreeCAD.Vector(0, 0, self.extrude_height))
                        extruded_count += 1
                    except:
                        pass
            
            self.progress_updated.emit(70, f"Extruded {extruded_count} objects...")
            
            # Export to STL
            output_path = self.dxf_path.replace('.dxf', f'_extruded_{self.extrude_height}mm.stl')
            import Part
            Part.export(objects, output_path)
            
            self.progress_updated.emit(100, "STL export complete!")
            self.finished.emit(True, f"Successfully exported to STL!\nSaved to: {output_path}")
            
        except Exception as e:
            self.finished.emit(False, f"FreeCAD STL export failed: {str(e)}")
    
    def export_stl_fallback(self):
        """Fallback STL export using existing system"""
        try:
            self.progress_updated.emit(10, "Using fallback STL export...")
            
            from methods.enhanced_step_export import EnhancedStepExporter
            from methods.performance_processor import ProcessingConfig
            import multiprocessing as mp
            
            self.progress_updated.emit(30, "Creating enhanced exporter...")
            
            performance_config = ProcessingConfig(
                max_workers=mp.cpu_count(),
                chunk_size=10,
                use_numba=True,
                use_cadquery=True,
                parallel_extrusion=False,
                enable_profiling=False,
                log_performance=True
            )
            
            enhanced_exporter = EnhancedStepExporter(performance_config)
            
            self.progress_updated.emit(50, "Processing contours...")
            
            # Create output path
            output_path = self.dxf_path.replace('.dxf', f'_extruded_{self.extrude_height}mm.stl')
            
            # Export using enhanced system
            success = enhanced_exporter.export_stl_file(
                self.contours, self.img_size, self.mm_per_px, 
                self.extrude_height, output_path, self.progress_updated
            )
            
            if success:
                self.progress_updated.emit(100, "STL export complete!")
                self.finished.emit(True, f"Successfully exported to STL!\nSaved to: {output_path}")
            else:
                self.finished.emit(False, "STL export failed")
                
        except Exception as e:
            self.finished.emit(False, f"Fallback STL export failed: {str(e)}")
    
    def export_obj(self):
        """Export to OBJ using FreeCAD"""
        if not FREECAD_AVAILABLE:
            self.export_obj_fallback()
            return
        
        try:
            self.progress_updated.emit(10, "Loading DXF into FreeCAD...")
            
            # Create new FreeCAD document
            import FreeCAD
            doc = FreeCAD.newDocument("DXF_Export")
            
            # Import DXF using manual method (use current DXF path)
            self._import_dxf_manually(doc, self.dxf_path)
            
            self.progress_updated.emit(30, "Extruding contours...")
            
            # Get all objects and extrude them
            objects = doc.Objects
            extruded_count = 0
            
            for obj in objects:
                if hasattr(obj, 'Shape') and obj.Shape.ShapeType == 'Wire':
                    try:
                        # Extrude the wire
                        import Part
                        face = Part.Face(obj.Shape)
                        solid = face.extrude(FreeCAD.Vector(0, 0, self.extrude_height))
                        extruded_count += 1
                    except:
                        pass
            
            self.progress_updated.emit(70, f"Extruded {extruded_count} objects...")
            
            # Export to OBJ
            output_path = self.dxf_path.replace('.dxf', f'_extruded_{self.extrude_height}mm.obj')
            import Part
            Part.export(objects, output_path)
            
            self.progress_updated.emit(100, "OBJ export complete!")
            self.finished.emit(True, f"Successfully exported to OBJ!\nSaved to: {output_path}")
            
        except Exception as e:
            self.finished.emit(False, f"FreeCAD OBJ export failed: {str(e)}")
    
    def export_obj_fallback(self):
        """Fallback OBJ export - export as STL first, then copy"""
        try:
            self.progress_updated.emit(10, "Using fallback OBJ export...")
            
            # First export as STL
            stl_path = self.dxf_path.replace('.dxf', f'_extruded_{self.extrude_height}mm.stl')
            self.export_stl_fallback()
            
            # Then copy STL to OBJ (simple approach)
            import shutil
            obj_path = self.dxf_path.replace('.dxf', f'_extruded_{self.extrude_height}mm.obj')
            shutil.copy2(stl_path, obj_path)
            
            self.progress_updated.emit(100, "OBJ export complete!")
            self.finished.emit(True, f"Successfully exported to OBJ!\nSaved to: {obj_path}")
            
        except Exception as e:
            self.finished.emit(False, f"Fallback OBJ export failed: {str(e)}")


class DXFEditorDialog(QDialog):
    """Enhanced DXF editor dialog with FreeCAD integration"""
    
    def __init__(self, dxf_path: str, contours: List, mm_per_px: float, parent=None):
        super().__init__(parent)
        self.original_dxf_path = dxf_path  # Store original DXF path
        self.current_dxf_path = dxf_path   # Current DXF being displayed
        self.contours = contours
        self.mm_per_px = mm_per_px
        
        # Calculate image size from contours
        if contours:
            all_points = []
            for contour in contours:
                for point in contour:
                    all_points.append([point[0][0], point[0][1]])
            if all_points:
                self.img_size = (
                    int(max(p[1] for p in all_points)) + 1,
                    int(max(p[0] for p in all_points)) + 1
                )
            else:
                self.img_size = (1000, 1000)
        else:
            self.img_size = (1000, 1000)
        
        self.worker = None
        self.setup_ui()
        self.load_dxf_info()
    
    def setup_ui(self):
        """Setup the user interface with split layout"""
        # Main layout
        main_layout = QHBoxLayout(self)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - DXF Preview
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (40% left, 60% right)
        splitter.setSizes([400, 600])
        
    def create_left_panel(self):
        """Create the left control panel"""
        left_widget = QFrame()
        left_layout = QVBoxLayout(left_widget)
        
        # Title
        title_label = QLabel("DXF Editor")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_label)
        
        # File information
        file_info_group = QGroupBox("DXF File Information")
        file_info_layout = QVBoxLayout(file_info_group)
        
        self.file_path_label = QLabel(f"File: {os.path.basename(self.current_dxf_path)}")
        self.file_size_label = QLabel("Size: Calculating...")
        self.contour_count_label = QLabel(f"Contours: {len(self.contours)}")
        
        file_info_layout.addWidget(self.file_path_label)
        file_info_layout.addWidget(self.file_size_label)
        file_info_layout.addWidget(self.contour_count_label)
        
        left_layout.addWidget(file_info_group)
        
        # Spline conversion section
        spline_group = QGroupBox("Spline Conversion")
        spline_layout = QVBoxLayout(spline_group)
        
        spline_info = QLabel("Convert DXF entities to closed splines for better CAD compatibility")
        spline_info.setWordWrap(True)
        spline_layout.addWidget(spline_info)
        
        self.convert_splines_btn = QPushButton("Convert Contours To Splines")
        self.convert_splines_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.convert_splines_btn.clicked.connect(self.convert_to_splines)
        spline_layout.addWidget(self.convert_splines_btn)
        
        # Reset button
        self.reset_btn = QPushButton("Reset to Original DXF")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_to_original)
        spline_layout.addWidget(self.reset_btn)
        
        left_layout.addWidget(spline_group)
        
        # Export options section
        export_group = QGroupBox("3D Export Options")
        export_layout = QGridLayout(export_group)
        
        # Extrusion height
        export_layout.addWidget(QLabel("Extrusion Height (mm):"), 0, 0)
        self.extrude_height_spin = QDoubleSpinBox()
        self.extrude_height_spin.setRange(0.1, 100.0)
        self.extrude_height_spin.setValue(5.0)
        self.extrude_height_spin.setDecimals(1)
        export_layout.addWidget(self.extrude_height_spin, 0, 1)
        
        # Export buttons
        self.export_step_btn = QPushButton("Export to STEP")
        self.export_step_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.export_step_btn.clicked.connect(lambda: self.export_format("step"))
        export_layout.addWidget(self.export_step_btn, 1, 0)
        
        self.export_stl_btn = QPushButton("Export to STL")
        self.export_stl_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.export_stl_btn.clicked.connect(lambda: self.export_format("stl"))
        export_layout.addWidget(self.export_stl_btn, 1, 1)
        
        self.export_obj_btn = QPushButton("Export to OBJ")
        self.export_obj_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 10px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.export_obj_btn.clicked.connect(lambda: self.export_format("obj"))
        export_layout.addWidget(self.export_obj_btn, 1, 2)
        
        left_layout.addWidget(export_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        left_layout.addWidget(progress_group)
        
        # FreeCAD status
        freecad_status = QLabel(f"FreeCAD API: {'✅ Available' if FREECAD_AVAILABLE else '❌ Not Available'}")
        freecad_status.setStyleSheet(f"color: {'green' if FREECAD_AVAILABLE else 'red'}")
        left_layout.addWidget(freecad_status)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        left_layout.addWidget(close_btn)
        
        # Add stretch to push everything to the top
        left_layout.addStretch()
        
        return left_widget
    
    def create_right_panel(self):
        """Create the right preview panel"""
        right_widget = QFrame()
        right_layout = QVBoxLayout(right_widget)
        
        # Preview title
        preview_title = QLabel("DXF Preview")
        preview_title.setFont(QFont("Arial", 14, QFont.Bold))
        preview_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(preview_title)
        
        # Create navigation toolbar
        toolbar = self.create_navigation_toolbar()
        right_layout.addWidget(toolbar)
        
        # Create scroll area for the preview
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(400, 300)
        
        # Create custom preview widget with zoom/pan
        self.preview_widget = DXFPreviewWidget()
        
        scroll_area.setWidget(self.preview_widget)
        right_layout.addWidget(scroll_area)
        
        # Load and display DXF preview
        self.load_dxf_preview()
        
        return right_widget
    
    def create_navigation_toolbar(self):
        """Create navigation toolbar for zoom and pan controls"""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar.setMaximumHeight(50)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        layout.addWidget(zoom_label)
        
        # Zoom out button
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(30, 30)
        zoom_out_btn.setToolTip("Zoom Out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(zoom_out_btn)
        
        # Zoom slider
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 1000)  # 0.1x to 10x zoom
        self.zoom_slider.setValue(100)  # 1.0x zoom
        self.zoom_slider.setToolTip("Zoom Level")
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        layout.addWidget(self.zoom_slider)
        
        # Zoom in button
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(30, 30)
        zoom_in_btn.setToolTip("Zoom In")
        zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(zoom_in_btn)
        
        # Zoom percentage label
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.zoom_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        layout.addWidget(separator)
        
        # Navigation controls
        nav_label = QLabel("Navigation:")
        layout.addWidget(nav_label)
        
        # Fit to window button
        fit_btn = QPushButton("Fit")
        fit_btn.setFixedSize(40, 30)
        fit_btn.setToolTip("Fit to Window")
        fit_btn.clicked.connect(self.fit_to_window)
        layout.addWidget(fit_btn)
        
        # Reset view button
        reset_btn = QPushButton("Reset")
        reset_btn.setFixedSize(50, 30)
        reset_btn.setToolTip("Reset View")
        reset_btn.clicked.connect(self.reset_view)
        layout.addWidget(reset_btn)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        layout.addWidget(separator2)
        
        # Instructions
        instructions = QLabel("Mouse: Left/Middle drag to pan | Wheel to zoom")
        instructions.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(instructions)
        
        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.VLine)
        layout.addWidget(separator3)
        
        # Rendering quality toggle
        self.crisp_rendering = QCheckBox("Crisp Lines")
        self.crisp_rendering.setChecked(True)
        self.crisp_rendering.setToolTip("Toggle between crisp and smooth line rendering")
        self.crisp_rendering.toggled.connect(self.on_rendering_quality_changed)
        layout.addWidget(self.crisp_rendering)
        
        # Add stretch to push everything to the left
        layout.addStretch()
        
        return toolbar
    
    def on_zoom_slider_changed(self, value):
        """Handle zoom slider change"""
        if hasattr(self, 'preview_widget'):
            zoom_factor = value / 100.0  # Convert slider value to zoom factor
            self.preview_widget.zoom_factor = zoom_factor
            self.preview_widget.update_display()
        self.zoom_label.setText(f"{value}%")
    
    def zoom_changed(self, zoom_factor):
        """Handle zoom change from preview widget"""
        slider_value = int(zoom_factor * 100)
        self.zoom_slider.setValue(slider_value)
        self.zoom_label.setText(f"{slider_value}%")
    
    def zoom_in(self):
        """Zoom in wrapper"""
        if hasattr(self, 'preview_widget'):
            self.preview_widget.zoom_in()
    
    def zoom_out(self):
        """Zoom out wrapper"""
        if hasattr(self, 'preview_widget'):
            self.preview_widget.zoom_out()
    
    def fit_to_window(self):
        """Fit to window wrapper"""
        if hasattr(self, 'preview_widget'):
            self.preview_widget.fit_to_window()
    
    def reset_view(self):
        """Reset view wrapper"""
        if hasattr(self, 'preview_widget'):
            self.preview_widget.reset_view()
    
    def on_rendering_quality_changed(self, checked):
        """Handle rendering quality toggle"""
        if hasattr(self, 'preview_widget'):
            # Regenerate the preview with new rendering settings
            self.load_dxf_preview()
    
    def load_dxf_preview(self):
        """Load and display DXF preview"""
        try:
            # Create a simple preview of the DXF content
            self.create_dxf_preview_image()
        except Exception as e:
            self.preview_widget.setText(f"Preview Error: {str(e)}")
    
    def create_dxf_preview_image(self):
        """Create a preview image of the DXF content"""
        try:
            # Create a preview based on the contours
            if not self.contours:
                self.preview_widget.setText("No contours to preview")
                return
            
            # Calculate bounds
            all_points = []
            for contour in self.contours:
                for point in contour:
                    x = float(point[0][0]) * self.mm_per_px
                    y = float(point[0][1]) * self.mm_per_px
                    all_points.append((x, y))
            
            if not all_points:
                self.preview_widget.setText("No valid points to preview")
                return
            
            # Calculate preview dimensions
            min_x = min(p[0] for p in all_points)
            max_x = max(p[0] for p in all_points)
            min_y = min(p[1] for p in all_points)
            max_y = max(p[1] for p in all_points)
            
            width = max_x - min_x
            height = max_y - min_y
            
            if width == 0 or height == 0:
                self.preview_widget.setText("Invalid dimensions for preview")
                return
            
            # Create high-resolution preview image for better scaling
            # Use a larger base size for better quality when zooming
            preview_size = 800  # Increased from 400 for better quality
            scale = min(preview_size / width, preview_size / height) * 0.8
            
            pixmap = QPixmap(int(width * scale) + 100, int(height * scale) + 100)
            pixmap.fill(QColor(255, 255, 255))
            
            painter = QPainter(pixmap)
            
            # Get the crisp rendering setting from this dialog
            use_crisp = True
            if hasattr(self, 'crisp_rendering'):
                use_crisp = self.crisp_rendering.isChecked()
            
            if use_crisp:
                # Disable antialiasing for crisp lines
                painter.setRenderHint(QPainter.Antialiasing, False)
                # Use a slightly thicker pen for better visibility
                pen = QPen(QColor(0, 0, 0), 1.5)
            else:
                # Enable antialiasing for smooth lines
                painter.setRenderHint(QPainter.Antialiasing, True)
                pen = QPen(QColor(0, 0, 0), 1)
            
            painter.setPen(pen)
            
            for contour in self.contours:  # Show ALL contours for complete preview
                if len(contour) < 3:
                    continue
                
                path = QPainterPath()
                first_point = True
                
                for point in contour:
                    x = (float(point[0][0]) * self.mm_per_px - min_x) * scale + 25
                    y = (float(point[0][1]) * self.mm_per_px - min_y) * scale + 25
                    
                    if first_point:
                        path.moveTo(x, y)
                        first_point = False
                    else:
                        path.lineTo(x, y)
                
                # Close the path
                if len(contour) > 2:
                    first_x = (float(contour[0][0][0]) * self.mm_per_px - min_x) * scale + 25
                    first_y = (float(contour[0][0][1]) * self.mm_per_px - min_y) * scale + 25
                    path.lineTo(first_x, first_y)
                
                painter.drawPath(path)
            
            painter.end()
            
            # Set the preview using the new preview widget
            self.preview_widget.set_pixmap(pixmap)
            
        except Exception as e:
            self.preview_widget.setText(f"Preview Error: {str(e)}")
    
    def load_dxf_info(self):
        """Load DXF file information"""
        try:
            file_size = os.path.getsize(self.current_dxf_path)
            self.file_size_label.setText(f"Size: {file_size:,} bytes")
        except Exception as e:
            self.file_size_label.setText(f"Size: Error - {str(e)}")
    
    def convert_to_splines(self):
        """Start spline conversion"""
        self.start_operation("convert_splines")
    
    def reset_to_original(self):
        """Reset to original DXF and reload preview"""
        self.current_dxf_path = self.original_dxf_path
        self.load_dxf_preview()
        self.load_dxf_info()
        
        # Update file path label
        self.file_path_label.setText(f"File: {os.path.basename(self.current_dxf_path)}")
        
        QMessageBox.information(self, "Reset Complete", "Preview reset to original DXF file.")
    
    def export_format(self, format_type):
        """Start export operation"""
        self.start_operation(f"export_{format_type}")
    
    def start_operation(self, operation):
        """Start a FreeCAD operation"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Disable buttons
        self.convert_splines_btn.setEnabled(False)
        self.export_step_btn.setEnabled(False)
        self.export_stl_btn.setEnabled(False)
        self.export_obj_btn.setEnabled(False)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start worker (use current DXF path and pass dialog reference)
        self.worker = FreeCADWorker(
            self.current_dxf_path, operation, self.extrude_height_spin.value(),
            self.contours, self.img_size, self.mm_per_px, self
        )
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.finished.connect(self.operation_finished)
        self.worker.start()
    
    def update_progress(self, value, message):
        """Update progress bar and status"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def operation_finished(self, success, message):
        """Handle operation completion"""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Re-enable buttons
        self.convert_splines_btn.setEnabled(True)
        self.export_step_btn.setEnabled(True)
        self.export_stl_btn.setEnabled(True)
        self.export_obj_btn.setEnabled(True)
        
        # Show result
        if success:
            self.status_label.setText("Operation completed successfully!")
            QMessageBox.information(self, "Success", message)
        else:
            self.status_label.setText("Operation failed!")
            QMessageBox.critical(self, "Error", message)
        
        # Clean up worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
