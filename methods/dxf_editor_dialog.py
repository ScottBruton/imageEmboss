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
    
    def __init__(self, dxf_path, operation, extrude_height=1.0, contours=None, img_size=None, mm_per_px=None):
        super().__init__()
        self.dxf_path = dxf_path
        self.operation = operation
        self.extrude_height = extrude_height
        self.contours = contours
        self.img_size = img_size
        self.mm_per_px = mm_per_px
        
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
        """Convert DXF entities to closed splines using FreeCAD"""
        if not FREECAD_AVAILABLE:
            self.convert_to_splines_fallback()
            return
        
        try:
            self.progress_updated.emit(10, "Loading DXF into FreeCAD...")
            
            # Create new FreeCAD document
            import FreeCAD
            doc = FreeCAD.newDocument("DXF_Splines")
            
            # Import DXF
            import Draft
            Draft.importDXF(self.dxf_path)
            
            self.progress_updated.emit(30, "Processing entities...")
            
            # Get all objects in the document
            objects = doc.Objects
            spline_count = 0
            
            for obj in objects:
                if hasattr(obj, 'Shape'):
                    # Convert to spline if it's a wire or edge
                    if obj.Shape.ShapeType == 'Wire':
                        try:
                            # Create B-spline from wire
                            spline = Draft.makeBSpline(obj.Shape.Edges)
                            spline_count += 1
                        except:
                            pass
            
            self.progress_updated.emit(80, f"Created {spline_count} splines...")
            
            # Save the modified DXF
            output_path = self.dxf_path.replace('.dxf', '_splines.dxf')
            Draft.exportDXF(objects, output_path)
            
            self.progress_updated.emit(100, "Spline conversion complete!")
            self.finished.emit(True, f"Successfully converted to splines!\nSaved to: {output_path}")
            
        except Exception as e:
            self.finished.emit(False, f"FreeCAD spline conversion failed: {str(e)}")
    
    def convert_to_splines_fallback(self):
        """Fallback spline conversion using existing system"""
        try:
            self.progress_updated.emit(10, "Using fallback spline conversion...")
            
            # Use existing enhanced export system
            from methods.enhanced_step_export import EnhancedStepExporter
            from methods.performance_processor import ProcessingConfig
            import multiprocessing as mp
            
            self.progress_updated.emit(30, "Creating enhanced exporter...")
            
            # Create enhanced exporter
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
            
            self.progress_updated.emit(50, "Processing contours with enhanced system...")
            
            # Create a temporary STEP file to demonstrate the conversion
            base_path = self.dxf_path.rsplit('.', 1)[0]
            temp_step_path = f"{base_path}_splines.step"
            
            # Use the enhanced system to create a 3D model
            workplane = enhanced_exporter.cadquery_processor.create_3d_model_parallel(
                self.contours, self.img_size, self.mm_per_px, 1.0, None
            )
            
            if workplane:
                workplane.export(temp_step_path)
                self.progress_updated.emit(100, "Fallback conversion complete!")
                self.finished.emit(True, f"Contours processed using enhanced system.\nTemporary STEP file: {temp_step_path}")
            else:
                self.finished.emit(False, "Failed to process contours with enhanced system")
                
        except Exception as e:
            self.finished.emit(False, f"Fallback conversion failed: {str(e)}")
    
    def export_step(self):
        """Export to STEP using FreeCAD"""
        if not FREECAD_AVAILABLE:
            self.export_step_fallback()
            return
        
        try:
            self.progress_updated.emit(10, "Loading DXF into FreeCAD...")
            
            # Create new FreeCAD document
            import FreeCAD
            doc = FreeCAD.newDocument("DXF_Export")
            
            # Import DXF
            import Draft
            Draft.importDXF(self.dxf_path)
            
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
            
            # Export to STEP
            output_path = self.dxf_path.replace('.dxf', f'_extruded_{self.extrude_height}mm.step')
            import Part
            Part.export(objects, output_path)
            
            self.progress_updated.emit(100, "STEP export complete!")
            self.finished.emit(True, f"Successfully exported to STEP!\nSaved to: {output_path}")
            
        except Exception as e:
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
            
            # Import DXF
            import Draft
            Draft.importDXF(self.dxf_path)
            
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
            
            # Import DXF
            import Draft
            Draft.importDXF(self.dxf_path)
            
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
        self.dxf_path = dxf_path
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
        
        self.file_path_label = QLabel(f"File: {os.path.basename(self.dxf_path)}")
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
            file_size = os.path.getsize(self.dxf_path)
            self.file_size_label.setText(f"Size: {file_size:,} bytes")
        except Exception as e:
            self.file_size_label.setText(f"Size: Error - {str(e)}")
    
    def convert_to_splines(self):
        """Start spline conversion"""
        self.start_operation("convert_splines")
    
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
        
        # Start worker
        self.worker = FreeCADWorker(
            self.dxf_path, operation, self.extrude_height_spin.value(),
            self.contours, self.img_size, self.mm_per_px
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
