import os
import sys
import cv2
import numpy as np
import ezdxf
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                               QSlider, QComboBox, QCheckBox, QFileDialog, 
                               QMessageBox, QSplitter, QFrame, QGraphicsView, 
                               QGraphicsScene, QGraphicsPixmapItem, QSizePolicy,
                               QGroupBox, QSpinBox, QDoubleSpinBox, QLineEdit,
                               QProgressBar, QStatusBar, QMenuBar, QToolBar,
                               QGraphicsItem, QGraphicsEllipseItem, QGraphicsRectItem,
                               QGraphicsPolygonItem, QGraphicsLineItem, QGraphicsPathItem,
                               QTabWidget, QButtonGroup)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPoint, QRect, QSize, QPointF, QMimeData, QLineF
from PySide6.QtGui import (QPixmap, QImage, QPainter, QPen, QBrush, QColor, 
                           QFont, QAction, QDragEnterEvent, QDropEvent,
                           QPainterPath, QPolygonF, QTransform, QCursor)

# -------------------------
# Helpers (unchanged from original)
# -------------------------
def find_edges_and_contours(img_bgr, params):
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
    # Find external contours only
    contours, _ = cv2.findContours(255 - mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # invert so dark = fill

    if not contours:
        return []

    # Keep N largest by area
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:max(1, int(largest_n))]

    # Apply gap threshold to connect nearby contour segments
    if gap_threshold > 0:
        # Apply gap closing to the entire mask first
        kernel_size = max(1, int(gap_threshold))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        # Create a mask from all contours
        combined_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(combined_mask, contours, -1, 255, -1)
        
        # Apply morphological closing to close gaps
        closed_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find new contours from the gap-closed mask
        new_contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if new_contours:
            # Keep the largest contours
            new_contours = sorted(new_contours, key=cv2.contourArea, reverse=True)[:max(1, int(largest_n))]
            contours = new_contours

    if simplify_pct and simplify_pct > 0:
        h, w = mask.shape[:2]
        diag = np.sqrt(w*w + h*h)
        eps = float(simplify_pct) * 0.01 * diag  # percent of diagonal
        simplified = []
        for c in contours:
            approx = cv2.approxPolyDP(c, eps, True)
            simplified.append(approx if len(approx) >= 3 else c)
        contours = simplified

    return contours

def export_dxf(contours, out_path, img_size, mm_per_px=0.25):
    h, w = img_size
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Image coords have origin top-left, y down.
    # DXF uses origin bottom-left, y up.
    # Flip Y and scale to mm.
    for cnt in contours:
        pts = []
        for p in cnt:
            x = float(p[0][0])
            y = float(p[0][1])
            x_mm = x * mm_per_px
            y_mm = (h - y) * mm_per_px
            pts.append((x_mm, y_mm))
        if len(pts) >= 3:
            msp.add_lwpolyline(pts, close=True)

    doc.saveas(out_path)

# -------------------------
# Custom Graphics Items for Drawing Tools
# -------------------------
class DrawingPathItem(QGraphicsPathItem):
    """Custom graphics item for drawing paths (paint strokes)"""
    def __init__(self, path=None, pen=None, parent=None):
        super().__init__(path, parent)
        if pen:
            self.setPen(pen)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

class DrawingLineItem(QGraphicsLineItem):
    """Custom graphics item for drawing lines"""
    def __init__(self, line=None, pen=None, parent=None):
        super().__init__(line, parent)
        if pen:
            self.setPen(pen)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

class DrawingRectItem(QGraphicsRectItem):
    """Custom graphics item for drawing rectangles"""
    def __init__(self, rect=None, pen=None, parent=None):
        super().__init__(rect, parent)
        if pen:
            self.setPen(pen)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

class DrawingEllipseItem(QGraphicsEllipseItem):
    """Custom graphics item for drawing circles/ellipses"""
    def __init__(self, rect=None, pen=None, parent=None):
        super().__init__(rect, parent)
        if pen:
            self.setPen(pen)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

class DrawingPolygonItem(QGraphicsPolygonItem):
    """Custom graphics item for drawing polygons (triangles)"""
    def __init__(self, polygon=None, pen=None, parent=None):
        super().__init__(polygon, parent)
        if pen:
            self.setPen(pen)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

# -------------------------
# Custom Graphics View for Image Display
# -------------------------
class ImageGraphicsView(QGraphicsView):
    """Custom graphics view for displaying images with zoom, pan, and drawing tools"""
    
    # Signals for drawing events
    drawing_started = Signal(QPointF)
    drawing_updated = Signal(QPointF)
    drawing_finished = Signal(QPointF)
    
    # Signal for image drop
    image_dropped = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Enable mouse tracking for better interaction
        self.setMouseTracking(True)
        
        # Set up view properties
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Zoom and pan variables
        self.zoom_factor = 1.0
        self.pan_start = QPoint()
        self.panning = False
        
        # Image item
        self.image_item = None
        
        # Drawing tool variables
        self.edit_mode = "view"  # view, paint, eraser, line, rectangle, triangle, circle
        self.drawing = False
        self.drawing_path = QPainterPath()
        self.drawing_points = []
        self.current_drawing_item = None
        self.temp_drawing_item = None
        
        # Drawing pen settings
        self.drawing_pen = QPen(QColor(0, 0, 255), 2, Qt.SolidLine)  # Blue pen
        self.eraser_radius = 15
        
        # Shape drawing variables
        self.shape_start_point = QPointF()
        self.shape_type = "rectangle"  # rectangle, triangle, circle
        
    def set_image(self, image):
        """Set the image to display"""
        self.scene.clear()
        if image is not None:
            # Convert OpenCV image to QPixmap
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            # Remove .rgbSwapped() to fix the blue tint issue
            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            
            self.image_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.image_item)
            
            # Fit image in view
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.zoom_factor = 1.0
    
    def resizeEvent(self, event):
        """Handle resize events to auto-fit image"""
        super().resizeEvent(event)
        if self.image_item is not None:
            # Auto-fit image when view is resized
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.zoom_factor = 1.0
    
    def wheelEvent(self, event):
        """Handle mouse wheel zoom"""
        # Get the position of the mouse before zooming
        old_pos = self.mapToScene(event.position().toPoint())
        
        # Zoom
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)
        self.zoom_factor *= zoom_factor
        
        # Get the new position
        new_pos = self.mapToScene(event.position().toPoint())
        
        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        
        event.accept()
    
    def mousePressEvent(self, event):
        """Handle mouse press for panning and drawing"""
        scene_point = self.mapToScene(event.position().toPoint())
        
        if event.button() == Qt.LeftButton:
            if self.edit_mode == "view":
                self.pan_start = event.position().toPoint()
                self.panning = True
                self.setCursor(Qt.ClosedHandCursor)
            elif self.edit_mode == "eraser":
                self.erase_at_point(scene_point)
            else:
                # Start drawing
                self.start_drawing(scene_point)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for panning and drawing"""
        scene_point = self.mapToScene(event.position().toPoint())
        
        if self.panning and self.edit_mode == "view":
            delta = event.position().toPoint() - self.pan_start
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            self.pan_start = event.position().toPoint()
        elif self.drawing:
            # Update drawing
            self.update_drawing(scene_point)
        elif self.edit_mode == "eraser":
            # Erase while dragging
            self.erase_at_point(scene_point)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        scene_point = self.mapToScene(event.position().toPoint())
        
        if event.button() == Qt.LeftButton:
            if self.panning and self.edit_mode == "view":
                self.panning = False
                self.setCursor(Qt.ArrowCursor)
            elif self.drawing:
                # Finish drawing
                self.finish_drawing(scene_point)
        
        super().mouseReleaseEvent(event)
    
    def reset_view(self):
        """Reset zoom and pan"""
        self.zoom_factor = 1.0
        if self.image_item:
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
    
    def set_edit_mode(self, mode):
        """Set the current edit mode"""
        self.edit_mode = mode
        self.drawing = False
        
        # Update cursor based on mode
        if mode == "view":
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.RubberBandDrag)
        elif mode == "paint":
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        elif mode == "line":
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        elif mode == "eraser":
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        elif mode in ["rectangle", "triangle", "circle"]:
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
    
    def set_shape_type(self, shape_type):
        """Set the shape type for shape drawing"""
        self.shape_type = shape_type
    
    def start_drawing(self, point):
        """Start drawing operation"""
        self.drawing = True
        self.drawing_points = [point]
        
        if self.edit_mode == "paint":
            self.drawing_path = QPainterPath()
            self.drawing_path.moveTo(point)
        elif self.edit_mode == "line":
            self.shape_start_point = point
        elif self.edit_mode in ["rectangle", "triangle", "circle"]:
            self.shape_start_point = point
        
        self.drawing_started.emit(point)
    
    def update_drawing(self, point):
        """Update drawing operation"""
        if not self.drawing:
            return
        
        if self.edit_mode == "paint":
            self.drawing_path.lineTo(point)
            self.drawing_points.append(point)
        elif self.edit_mode == "line":
            self.update_temp_line(point)
        elif self.edit_mode in ["rectangle", "triangle", "circle"]:
            self.update_temp_shape(point)
        
        self.drawing_updated.emit(point)
    
    def finish_drawing(self, point):
        """Finish drawing operation"""
        if not self.drawing:
            return
        
        if self.edit_mode == "paint":
            if len(self.drawing_points) >= 2:
                # Create a path item for the paint stroke
                path_item = DrawingPathItem(self.drawing_path, self.drawing_pen)
                self.scene.addItem(path_item)
        elif self.edit_mode == "line":
            self.finish_line(point)
        elif self.edit_mode in ["rectangle", "triangle", "circle"]:
            self.finish_shape(point)
        
        self.drawing = False
        self.drawing_points = []
        self.drawing_path = QPainterPath()
        self.temp_drawing_item = None
        
        self.drawing_finished.emit(point)
    
    def update_temp_line(self, end_point):
        """Update temporary line while drawing"""
        # Remove previous temporary line
        if self.temp_drawing_item:
            self.scene.removeItem(self.temp_drawing_item)
        
        # Create new temporary line
        line = QLineF(self.shape_start_point, end_point)
        self.temp_drawing_item = DrawingLineItem(line, self.drawing_pen)
        self.scene.addItem(self.temp_drawing_item)
    
    def finish_line(self, end_point):
        """Finish drawing a line"""
        if self.temp_drawing_item:
            self.scene.removeItem(self.temp_drawing_item)
        
        line = QLineF(self.shape_start_point, end_point)
        line_item = DrawingLineItem(line, self.drawing_pen)
        self.scene.addItem(line_item)
    
    def update_temp_shape(self, end_point):
        """Update temporary shape while drawing"""
        # Remove previous temporary shape
        if self.temp_drawing_item:
            self.scene.removeItem(self.temp_drawing_item)
        
        # Create new temporary shape based on type
        if self.shape_type == "rectangle":
            rect = QRectF(self.shape_start_point, end_point).normalized()
            self.temp_drawing_item = DrawingRectItem(rect, self.drawing_pen)
        elif self.shape_type == "circle":
            rect = QRectF(self.shape_start_point, end_point).normalized()
            self.temp_drawing_item = DrawingEllipseItem(rect, self.drawing_pen)
        elif self.shape_type == "triangle":
            # Create triangle points
            if end_point.y() < self.shape_start_point.y():  # Triangle pointing up
                points = [
                    QPointF(self.shape_start_point.x(), end_point.y()),
                    QPointF(end_point.x(), end_point.y()),
                    QPointF((self.shape_start_point.x() + end_point.x()) / 2, self.shape_start_point.y())
                ]
            else:  # Triangle pointing down
                points = [
                    QPointF(self.shape_start_point.x(), self.shape_start_point.y()),
                    QPointF(end_point.x(), self.shape_start_point.y()),
                    QPointF((self.shape_start_point.x() + end_point.x()) / 2, end_point.y())
                ]
            polygon = QPolygonF(points)
            self.temp_drawing_item = DrawingPolygonItem(polygon, self.drawing_pen)
        
        if self.temp_drawing_item:
            self.scene.addItem(self.temp_drawing_item)
    
    def finish_shape(self, end_point):
        """Finish drawing a shape"""
        if self.temp_drawing_item:
            self.scene.removeItem(self.temp_drawing_item)
        
        # Create final shape item
        if self.shape_type == "rectangle":
            rect = QRectF(self.shape_start_point, end_point).normalized()
            shape_item = DrawingRectItem(rect, self.drawing_pen)
        elif self.shape_type == "circle":
            rect = QRectF(self.shape_start_point, end_point).normalized()
            shape_item = DrawingEllipseItem(rect, self.drawing_pen)
        elif self.shape_type == "triangle":
            # Create triangle points
            if end_point.y() < self.shape_start_point.y():  # Triangle pointing up
                points = [
                    QPointF(self.shape_start_point.x(), end_point.y()),
                    QPointF(end_point.x(), end_point.y()),
                    QPointF((self.shape_start_point.x() + end_point.x()) / 2, self.shape_start_point.y())
                ]
            else:  # Triangle pointing down
                points = [
                    QPointF(self.shape_start_point.x(), self.shape_start_point.y()),
                    QPointF(end_point.x(), self.shape_start_point.y()),
                    QPointF((self.shape_start_point.x() + end_point.x()) / 2, end_point.y())
                ]
            polygon = QPolygonF(points)
            shape_item = DrawingPolygonItem(polygon, self.drawing_pen)
        
        self.scene.addItem(shape_item)
    
    def erase_at_point(self, point):
        """Erase items at the given point"""
        # Find items at the point
        items = self.scene.items(point)
        for item in items:
            if isinstance(item, (DrawingPathItem, DrawingLineItem, DrawingRectItem, 
                               DrawingEllipseItem, DrawingPolygonItem)):
                self.scene.removeItem(item)
    
    def get_drawing_items(self):
        """Get all drawing items from the scene"""
        drawing_items = []
        for item in self.scene.items():
            if isinstance(item, (DrawingPathItem, DrawingLineItem, DrawingRectItem, 
                               DrawingEllipseItem, DrawingPolygonItem)):
                drawing_items.append(item)
        return drawing_items
    
    def clear_drawing_items(self):
        """Clear all drawing items from the scene"""
        items_to_remove = []
        for item in self.scene.items():
            if isinstance(item, (DrawingPathItem, DrawingLineItem, DrawingRectItem, 
                               DrawingEllipseItem, DrawingPolygonItem)):
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.scene.removeItem(item)
    
    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            # Check if any of the URLs is an image file
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp')):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event):
        """Handle drop event"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp')):
                    # Emit signal to load the image
                    self.image_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

# -------------------------
# Main Application Class
# -------------------------
class ImageEmbossGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Emboss - Image to DXF Converter")
        # Set initial window size to be large
        self.setGeometry(100, 100, 1600, 1000)
        
        # Data
        self.original_image = None
        self.current_mask = None
        self.current_contours = []
        self.image_path = None
        
        # Edit mode variables
        self.edit_mode = "view"  # view, paint, eraser, shapes
        self.drawing = False
        self.drawing_points = []
        self.edited_contours = []
        self.erased_contours = set()
        self.erased_points = set()
        
        # Default parameters
        self.params = {
            "bilateral_diameter": 9,
            "bilateral_sigma_color": 75,
            "bilateral_sigma_space": 75,
            "gaussian_kernel_size": 5,
            "canny_lower_threshold": 30,
            "canny_upper_threshold": 100,
            "edge_thickness": 3,  # Changed from 2 to 3
            "gap_threshold": 0.0,  # Changed from 5.0 to 0.0
            "largest_n": 10,
            "simplify_pct": 0.0,  # Changed from 0.5 to 0.0
            "mm_per_px": 0.25,
            "invert": True
        }
        
        # Preset configurations
        self.preset_configs = {
            "Default": {
                "bilateral_diameter": 9,
                "bilateral_sigma_color": 75,
                "gaussian_kernel_size": 5,
                "canny_lower_threshold": 30,
                "canny_upper_threshold": 100,
                "edge_thickness": 3.0,  # Updated to 3.0
                "gap_threshold": 0.0,  # Updated to 0.0
                "largest_n": 10,
                "simplify_pct": 0.0,  # Updated to 0.0
                "mm_per_px": 0.25,
                "invert": True
            },
            "High Detail": {
                "bilateral_diameter": 6,
                "bilateral_sigma_color": 60,
                "gaussian_kernel_size": 3,
                "canny_lower_threshold": 20,
                "canny_upper_threshold": 60,
                "edge_thickness": 1.5,
                "gap_threshold": 3.0,
                "largest_n": 15,
                "simplify_pct": 0.3,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Low Noise": {
                "bilateral_diameter": 12,
                "bilateral_sigma_color": 120,
                "gaussian_kernel_size": 7,
                "canny_lower_threshold": 50,
                "canny_upper_threshold": 150,
                "edge_thickness": 3.0,
                "gap_threshold": 6.0,
                "largest_n": 10,
                "simplify_pct": 0.6,
                "mm_per_px": 0.25,
                "invert": True
            }
        }
        
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # Show window first, then maximize
        self.show()
        
        # Maximize after window is shown
        QTimer.singleShot(100, self.force_maximize)
        
        # Fit images to view after window is maximized
        QTimer.singleShot(200, self.fit_images_to_view)
        
    def setup_ui(self):
        """Setup the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - horizontal split (left and right panels)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)  # Small margins
        
        # Left panel - original image and parameters
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)  # Equal space
        
        # Right panel - DXF preview and tools
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)  # Equal space
    
    def create_left_panel(self):
        """Create the left panel with original image and parameters"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        # Top section - file selection
        top_frame = self.create_file_selection_frame()
        layout.addWidget(top_frame)
        
        # Middle section - original image
        original_group = QGroupBox("Original Image")
        original_layout = QVBoxLayout(original_group)
        original_layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        self.original_view = ImageGraphicsView()
        self.original_view.setMinimumSize(100, 100)  # Much smaller minimum
        self.original_view.image_dropped.connect(self.load_image_from_path)
        original_layout.addWidget(self.original_view)
        
        layout.addWidget(original_group, 4)  # Even more space for image
        
        # Bottom section - parameters
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_group)
        params_layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        # Master preset
        preset_frame = QFrame()
        preset_layout = QHBoxLayout(preset_frame)
        preset_layout.addWidget(QLabel("Master Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.preset_configs.keys()))
        self.preset_combo.setCurrentText("Default")
        self.preset_combo.currentTextChanged.connect(self.on_preset_change)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        params_layout.addWidget(preset_frame)
        
        # Create tab widget for parameters
        self.tab_widget = QTabWidget()
        self.create_filtering_tab()
        self.create_edge_detection_tab()
        self.create_contour_processing_tab()
        self.create_export_tab()
        params_layout.addWidget(self.tab_widget)
        
        layout.addWidget(params_group, 1)  # Less space for parameters
        
        return frame
    
    def create_right_panel(self):
        """Create the right panel with DXF preview and tools"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        # Top section - export controls
        export_frame = self.create_export_frame()
        layout.addWidget(export_frame)
        
        # Thin tools toolbar
        tools_toolbar = self.create_tools_toolbar()
        layout.addWidget(tools_toolbar)
        
        # DXF preview - takes remaining space
        dxf_group = QGroupBox("DXF Preview")
        dxf_layout = QVBoxLayout(dxf_group)
        dxf_layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        self.dxf_view = ImageGraphicsView()
        self.dxf_view.setMinimumSize(100, 100)  # Much smaller minimum
        self.dxf_view.image_dropped.connect(self.load_image_from_path)
        dxf_layout.addWidget(self.dxf_view)
        
        layout.addWidget(dxf_group, 1)  # Takes all remaining space
        
        return frame
        
    def create_filtering_tab(self):
        """Create the filtering parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Bilateral Diameter
        bilateral_d_layout = QHBoxLayout()
        bilateral_d_label = QLabel("Bilateral Diameter:")
        bilateral_d_label.setToolTip("Controls how much the image is smoothed while preserving edges. Higher values smooth more but may blur important details.")
        bilateral_d_layout.addWidget(bilateral_d_label)
        
        self.bilateral_d_slider = QSlider(Qt.Horizontal)
        self.bilateral_d_slider.setRange(5, 15)
        self.bilateral_d_slider.setValue(9)
        self.bilateral_d_slider.setToolTip("Controls how much the image is smoothed while preserving edges. Higher values smooth more but may blur important details.")
        self.bilateral_d_slider.valueChanged.connect(self.on_param_change)
        bilateral_d_layout.addWidget(self.bilateral_d_slider)
        
        self.bilateral_d_label = QLabel("9")
        self.bilateral_d_label.setMinimumWidth(30)
        bilateral_d_layout.addWidget(self.bilateral_d_label)
        
        layout.addLayout(bilateral_d_layout)
        
        # Bilateral Sigma Color
        bilateral_c_layout = QHBoxLayout()
        bilateral_c_label = QLabel("Bilateral Color σ:")
        bilateral_c_label.setToolTip("Controls how similar colors need to be to be smoothed together. Higher values allow more different colors to be smoothed.")
        bilateral_c_layout.addWidget(bilateral_c_label)
        
        self.bilateral_c_slider = QSlider(Qt.Horizontal)
        self.bilateral_c_slider.setRange(25, 150)
        self.bilateral_c_slider.setValue(75)
        self.bilateral_c_slider.setToolTip("Controls how similar colors need to be to be smoothed together. Higher values allow more different colors to be smoothed.")
        self.bilateral_c_slider.valueChanged.connect(self.on_param_change)
        bilateral_c_layout.addWidget(self.bilateral_c_slider)
        
        self.bilateral_c_label = QLabel("75")
        self.bilateral_c_label.setMinimumWidth(30)
        bilateral_c_layout.addWidget(self.bilateral_c_label)
        
        layout.addLayout(bilateral_c_layout)
        
        # Gaussian Kernel Size
        gaussian_layout = QHBoxLayout()
        gaussian_label = QLabel("Gaussian Kernel:")
        gaussian_label.setToolTip("Controls the amount of blur applied to the image. Higher values create more blur, which can help reduce noise but may soften important edges.")
        gaussian_layout.addWidget(gaussian_label)
        
        self.gaussian_slider = QSlider(Qt.Horizontal)
        self.gaussian_slider.setRange(3, 9)
        self.gaussian_slider.setValue(5)
        self.gaussian_slider.setToolTip("Controls the amount of blur applied to the image. Higher values create more blur, which can help reduce noise but may soften important edges.")
        self.gaussian_slider.valueChanged.connect(self.on_param_change)
        gaussian_layout.addWidget(self.gaussian_slider)
        
        self.gaussian_label = QLabel("5")
        self.gaussian_label.setMinimumWidth(30)
        gaussian_layout.addWidget(self.gaussian_label)
        
        layout.addLayout(gaussian_layout)
        
        self.tab_widget.addTab(tab, "Filtering")
    
    def create_edge_detection_tab(self):
        """Create the edge detection parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Canny Lower Threshold
        canny_l_layout = QHBoxLayout()
        canny_l_label = QLabel("Canny Lower:")
        canny_l_label.setToolTip("Lower threshold for edge detection. Lower values detect more edges (including weak ones), higher values only detect strong edges.")
        canny_l_layout.addWidget(canny_l_label)
        
        self.canny_l_slider = QSlider(Qt.Horizontal)
        self.canny_l_slider.setRange(10, 100)
        self.canny_l_slider.setValue(30)
        self.canny_l_slider.setToolTip("Lower threshold for edge detection. Lower values detect more edges (including weak ones), higher values only detect strong edges.")
        self.canny_l_slider.valueChanged.connect(self.on_param_change)
        canny_l_layout.addWidget(self.canny_l_slider)
        
        self.canny_l_label = QLabel("30")
        self.canny_l_label.setMinimumWidth(30)
        canny_l_layout.addWidget(self.canny_l_label)
        
        layout.addLayout(canny_l_layout)
        
        # Canny Upper Threshold
        canny_u_layout = QHBoxLayout()
        canny_u_label = QLabel("Canny Upper:")
        canny_u_label.setToolTip("Upper threshold for edge detection. Higher values only detect very strong edges, lower values include more edges.")
        canny_u_layout.addWidget(canny_u_label)
        
        self.canny_u_slider = QSlider(Qt.Horizontal)
        self.canny_u_slider.setRange(30, 200)
        self.canny_u_slider.setValue(100)
        self.canny_u_slider.setToolTip("Upper threshold for edge detection. Higher values only detect very strong edges, lower values include more edges.")
        self.canny_u_slider.valueChanged.connect(self.on_param_change)
        canny_u_layout.addWidget(self.canny_u_slider)
        
        self.canny_u_label = QLabel("100")
        self.canny_u_label.setMinimumWidth(30)
        canny_u_layout.addWidget(self.canny_u_label)
        
        layout.addLayout(canny_u_layout)
        
        # Edge Thickness
        thickness_layout = QHBoxLayout()
        thickness_label = QLabel("Edge Thickness:")
        thickness_label.setToolTip("Controls how thick the lines will be in your final DXF file. Higher values create thicker lines, lower values create thinner lines.")
        thickness_layout.addWidget(thickness_label)
        
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 50)
        self.thickness_slider.setValue(3)  # Updated default to 3
        self.thickness_slider.setToolTip("Controls how thick the lines will be in your final DXF file. Higher values create thicker lines, lower values create thinner lines.")
        self.thickness_slider.valueChanged.connect(self.on_param_change)
        thickness_layout.addWidget(self.thickness_slider)
        
        self.thickness_label = QLabel("3.0")  # Updated default to 3.0
        self.thickness_label.setMinimumWidth(30)
        thickness_layout.addWidget(self.thickness_label)
        
        layout.addLayout(thickness_layout)
        
        self.tab_widget.addTab(tab, "Edge Detection")
    
    def create_contour_processing_tab(self):
        """Create the contour processing parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Gap Threshold
        gap_layout = QHBoxLayout()
        gap_label = QLabel("Gap Threshold:")
        gap_label.setToolTip("Controls how close edges need to be to be connected together. Higher values connect edges that are farther apart.")
        gap_layout.addWidget(gap_label)
        
        self.gap_enabled_checkbox = QCheckBox("Enable")
        self.gap_enabled_checkbox.setChecked(False)  # Default disabled
        self.gap_enabled_checkbox.setToolTip("Enable gap threshold processing")
        self.gap_enabled_checkbox.toggled.connect(self.on_gap_enabled_toggled)
        gap_layout.addWidget(self.gap_enabled_checkbox)
        
        self.gap_slider = QSlider(Qt.Horizontal)
        self.gap_slider.setRange(0, 20)
        self.gap_slider.setValue(0)  # Updated default to 0
        self.gap_slider.setEnabled(False)  # Initially disabled
        self.gap_slider.setToolTip("Controls how close edges need to be to be connected together. Higher values connect edges that are farther apart.")
        self.gap_slider.valueChanged.connect(self.on_param_change)
        gap_layout.addWidget(self.gap_slider)
        
        self.gap_label = QLabel("0.0")  # Updated default to 0.0
        self.gap_label.setMinimumWidth(30)
        gap_layout.addWidget(self.gap_label)
        
        layout.addLayout(gap_layout)
        
        # Largest N
        largest_layout = QHBoxLayout()
        largest_label = QLabel("Largest N:")
        largest_label.setToolTip("Controls how many of the largest shapes to keep. Higher values keep more shapes, lower values keep only the biggest ones.")
        largest_layout.addWidget(largest_label)
        
        self.largest_slider = QSlider(Qt.Horizontal)
        self.largest_slider.setRange(1, 50)
        self.largest_slider.setValue(10)
        self.largest_slider.setToolTip("Controls how many of the largest shapes to keep. Higher values keep more shapes, lower values keep only the biggest ones.")
        self.largest_slider.valueChanged.connect(self.on_param_change)
        largest_layout.addWidget(self.largest_slider)
        
        self.largest_label = QLabel("10")
        self.largest_label.setMinimumWidth(30)
        largest_layout.addWidget(self.largest_label)
        
        layout.addLayout(largest_layout)
        
        # Simplify
        simplify_layout = QHBoxLayout()
        simplify_label = QLabel("Simplify %:")
        simplify_label.setToolTip("Controls how much detail to remove from the shapes. Higher values create simpler shapes with fewer points, lower values keep more detail.")
        simplify_layout.addWidget(simplify_label)
        
        self.simplify_slider = QSlider(Qt.Horizontal)
        self.simplify_slider.setRange(0, 200)
        self.simplify_slider.setValue(0)  # Updated default to 0
        self.simplify_slider.setToolTip("Controls how much detail to remove from the shapes. Higher values create simpler shapes with fewer points, lower values keep more detail.")
        self.simplify_slider.valueChanged.connect(self.on_param_change)
        simplify_layout.addWidget(self.simplify_slider)
        
        self.simplify_label = QLabel("0.0")  # Updated default to 0.0
        self.simplify_label.setMinimumWidth(30)
        simplify_layout.addWidget(self.simplify_label)
        
        layout.addLayout(simplify_layout)
        
        self.tab_widget.addTab(tab, "Contour Processing")
    
    def create_export_tab(self):
        """Create the export parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Scale
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scale (mm/px):"))
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(1, 200)
        self.scale_slider.setValue(25)
        self.scale_slider.valueChanged.connect(self.on_param_change)
        scale_layout.addWidget(self.scale_slider)
        
        self.scale_label = QLabel("0.25")
        self.scale_label.setMinimumWidth(30)
        scale_layout.addWidget(self.scale_label)
        
        layout.addLayout(scale_layout)
        
        # Invert checkbox
        self.invert_checkbox = QCheckBox("Invert Black/White")
        self.invert_checkbox.setChecked(True)
        self.invert_checkbox.toggled.connect(self.on_param_change)
        layout.addWidget(self.invert_checkbox)
        
        layout.addStretch()  # Push everything to the top
        
        self.tab_widget.addTab(tab, "Export")
        
    def create_file_selection_frame(self):
        """Create the file selection frame for left panel"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        # File selection
        self.load_button = QPushButton("Select Image")
        self.load_button.setToolTip("Load an image file to process")
        self.load_button.clicked.connect(self.load_image)
        layout.addWidget(self.load_button)
        
        self.status_label = QLabel("No image loaded")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Image dimensions display
        self.dimensions_label = QLabel("")
        layout.addWidget(self.dimensions_label)
        
        return frame
    
    def create_export_frame(self):
        """Create the export frame for right panel"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        # Scale input
        layout.addWidget(QLabel("Scale:"))
        self.export_scale_input = QDoubleSpinBox()
        self.export_scale_input.setRange(0.1, 10.0)
        self.export_scale_input.setValue(1.0)
        self.export_scale_input.setDecimals(2)
        self.export_scale_input.setToolTip("Scale factor for DXF export (1.0 = original size)")
        self.export_scale_input.valueChanged.connect(self.on_export_scale_change)
        layout.addWidget(self.export_scale_input)
        
        # Output size display
        self.output_size_label = QLabel("")
        layout.addWidget(self.output_size_label)
        
        # Export button
        self.export_button = QPushButton("Export DXF")
        self.export_button.setToolTip("Export the processed image as a DXF file")
        self.export_button.clicked.connect(self.export_dxf)
        layout.addWidget(self.export_button)
        
        return frame
    
    def create_tools_toolbar(self):
        """Create a thin tools toolbar above the DXF preview"""
        toolbar = QFrame()
        toolbar.setMaximumHeight(50)  # Keep it thin
        toolbar.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)  # Minimal margins
        
        # Zoom controls
        layout.addWidget(QLabel("Zoom:"))
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setMaximumSize(25, 25)
        zoom_in_btn.setToolTip("Zoom in")
        zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setMaximumSize(25, 25)
        zoom_out_btn.setToolTip("Zoom out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(zoom_out_btn)
        
        zoom_1_1_btn = QPushButton("1:1")
        zoom_1_1_btn.setMaximumSize(35, 25)
        zoom_1_1_btn.setToolTip("Reset to 1:1 zoom")
        zoom_1_1_btn.clicked.connect(self.zoom_reset)
        layout.addWidget(zoom_1_1_btn)
        
        layout.addSpacing(10)
        
        # Pan controls
        layout.addWidget(QLabel("Pan:"))
        pan_up_btn = QPushButton("↑")
        pan_up_btn.setMaximumSize(25, 25)
        pan_up_btn.setToolTip("Pan up")
        pan_up_btn.clicked.connect(lambda: self.pan_preview(0, -50))
        layout.addWidget(pan_up_btn)
        
        pan_down_btn = QPushButton("↓")
        pan_down_btn.setMaximumSize(25, 25)
        pan_down_btn.setToolTip("Pan down")
        pan_down_btn.clicked.connect(lambda: self.pan_preview(0, 50))
        layout.addWidget(pan_down_btn)
        
        pan_left_btn = QPushButton("←")
        pan_left_btn.setMaximumSize(25, 25)
        pan_left_btn.setToolTip("Pan left")
        pan_left_btn.clicked.connect(lambda: self.pan_preview(-50, 0))
        layout.addWidget(pan_left_btn)
        
        pan_right_btn = QPushButton("→")
        pan_right_btn.setMaximumSize(25, 25)
        pan_right_btn.setToolTip("Pan right")
        pan_right_btn.clicked.connect(lambda: self.pan_preview(50, 0))
        layout.addWidget(pan_right_btn)
        
        layout.addSpacing(10)
        
        # Edit controls
        layout.addWidget(QLabel("Edit:"))
        
        # Create button group for mutually exclusive selection
        self.edit_button_group = QButtonGroup()
        
        # View mode button
        self.view_btn = QPushButton("👁")
        self.view_btn.setMaximumSize(25, 25)
        self.view_btn.setCheckable(True)
        self.view_btn.setChecked(True)
        self.view_btn.setToolTip("View mode - navigate and zoom")
        self.view_btn.clicked.connect(lambda: self.set_edit_mode("view"))
        self.edit_button_group.addButton(self.view_btn, 0)
        layout.addWidget(self.view_btn)
        
        # Paint mode button
        self.paint_btn = QPushButton("✏️")
        self.paint_btn.setMaximumSize(25, 25)
        self.paint_btn.setCheckable(True)
        self.paint_btn.setToolTip("Paint mode - draw freehand")
        self.paint_btn.clicked.connect(lambda: self.set_edit_mode("paint"))
        self.edit_button_group.addButton(self.paint_btn, 1)
        layout.addWidget(self.paint_btn)
        
        # Eraser mode button
        self.eraser_btn = QPushButton("🧽")
        self.eraser_btn.setMaximumSize(25, 25)
        self.eraser_btn.setCheckable(True)
        self.eraser_btn.setToolTip("Eraser mode - erase drawings")
        self.eraser_btn.clicked.connect(lambda: self.set_edit_mode("eraser"))
        self.edit_button_group.addButton(self.eraser_btn, 2)
        layout.addWidget(self.eraser_btn)
        
        # Line mode button
        self.line_btn = QPushButton("📏")
        self.line_btn.setMaximumSize(25, 25)
        self.line_btn.setCheckable(True)
        self.line_btn.setToolTip("Line mode - draw straight lines")
        self.line_btn.clicked.connect(lambda: self.set_edit_mode("line"))
        self.edit_button_group.addButton(self.line_btn, 3)
        layout.addWidget(self.line_btn)
        
        layout.addSpacing(10)
        
        # Undo/Redo controls
        layout.addWidget(QLabel("History:"))
        self.undo_btn = QPushButton("↶")
        self.undo_btn.setMaximumSize(25, 25)
        self.undo_btn.setToolTip("Undo last action")
        self.undo_btn.clicked.connect(self.undo_action)
        layout.addWidget(self.undo_btn)
        
        self.redo_btn = QPushButton("↷")
        self.redo_btn.setMaximumSize(25, 25)
        self.redo_btn.setToolTip("Redo last undone action")
        self.redo_btn.clicked.connect(self.redo_action)
        layout.addWidget(self.redo_btn)
        
        layout.addSpacing(10)
        
        # Shape controls
        layout.addWidget(QLabel("Shape:"))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Rectangle", "Triangle", "Circle"])
        self.shape_combo.setMaximumWidth(80)
        self.shape_combo.setToolTip("Select shape type for drawing")
        self.shape_combo.currentTextChanged.connect(self.set_shape_mode)
        layout.addWidget(self.shape_combo)
        
        # Shape mode button
        self.shape_btn = QPushButton("🔺")
        self.shape_btn.setMaximumSize(25, 25)
        self.shape_btn.setCheckable(True)
        self.shape_btn.setToolTip("Draw shapes")
        self.shape_btn.clicked.connect(lambda: self.set_edit_mode("shape"))
        self.edit_button_group.addButton(self.shape_btn, 4)
        layout.addWidget(self.shape_btn)
        
        layout.addStretch()  # Push everything to the left
        
        return toolbar
    
    def create_navigation_controls(self):
        """Create navigation controls for the DXF preview"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        # Zoom controls
        layout.addWidget(QLabel("Zoom:"))
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(zoom_out_btn)
        
        reset_btn = QPushButton("1:1")
        reset_btn.clicked.connect(self.zoom_reset)
        layout.addWidget(reset_btn)
        
        layout.addWidget(QFrame())  # Separator
        
        # Pan controls
        layout.addWidget(QLabel("Pan:"))
        pan_up_btn = QPushButton("↑")
        pan_up_btn.clicked.connect(lambda: self.pan_preview(0, -1))
        layout.addWidget(pan_up_btn)
        
        pan_down_btn = QPushButton("↓")
        pan_down_btn.clicked.connect(lambda: self.pan_preview(0, 1))
        layout.addWidget(pan_down_btn)
        
        pan_left_btn = QPushButton("←")
        pan_left_btn.clicked.connect(lambda: self.pan_preview(-1, 0))
        layout.addWidget(pan_left_btn)
        
        pan_right_btn = QPushButton("→")
        pan_right_btn.clicked.connect(lambda: self.pan_preview(1, 0))
        layout.addWidget(pan_right_btn)
        
        pan_reset_btn = QPushButton("⌂")
        pan_reset_btn.clicked.connect(self.pan_reset)
        layout.addWidget(pan_reset_btn)
        
        layout.addWidget(QFrame())  # Separator
        
        # Edit controls
        layout.addWidget(QLabel("Edit:"))
        
        # View tool
        view_btn = QPushButton("👁️")
        view_btn.setToolTip("View tool - Pan and zoom (default mode)")
        view_btn.clicked.connect(lambda: self.set_edit_mode("view"))
        layout.addWidget(view_btn)
        
        # Paint tool
        paint_btn = QPushButton("✏️")
        paint_btn.setToolTip("Paint tool - Draw freehand lines")
        paint_btn.clicked.connect(lambda: self.set_edit_mode("paint"))
        layout.addWidget(paint_btn)
        
        # Eraser tool
        eraser_btn = QPushButton("🧽")
        eraser_btn.setToolTip("Eraser tool - Erase parts of contours")
        eraser_btn.clicked.connect(lambda: self.set_edit_mode("eraser"))
        layout.addWidget(eraser_btn)
        
        # Line tool
        line_btn = QPushButton("📏")
        line_btn.setToolTip("Line tool - Draw straight lines")
        line_btn.clicked.connect(lambda: self.set_edit_mode("line"))
        layout.addWidget(line_btn)
        
        # Shape selection
        self.shape_type_combo = QComboBox()
        self.shape_type_combo.addItems(["rectangle", "triangle", "circle"])
        self.shape_type_combo.setToolTip("Select shape type for the shape tool")
        self.shape_type_combo.currentTextChanged.connect(self.on_shape_type_change)
        layout.addWidget(self.shape_type_combo)
        
        # Shape tool
        shape_btn = QPushButton("📐")
        shape_btn.setToolTip("Shape tool - Draw rectangles, triangles, circles")
        shape_btn.clicked.connect(self.set_shape_mode)
        layout.addWidget(shape_btn)
        
        layout.addStretch()
        return frame
    
    
    def setup_menu(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        load_action = QAction('Load Image', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_image)
        file_menu.addAction(load_action)
        
        export_action = QAction('Export DXF', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_dxf)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    # Event handlers
    def load_image(self):
        """Load an image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select an image to convert",
            "", "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp);;All files (*.*)"
        )
        
        if file_path:
            self.load_image_from_path(file_path)
    
    def load_image_from_path(self, path):
        """Load image from a given path"""
        self.image_path = path
        self.original_image = cv2.imread(path, cv2.IMREAD_COLOR)
        
        if self.original_image is not None:
            # Reset edit state for new image
            self.edited_contours = []
            self.erased_contours = set()
            self.erased_points = set()
            self.edit_mode = "view"
            
            # Clear drawing items
            self.dxf_view.clear_drawing_items()
            
            # Update status and dimensions
            h, w = self.original_image.shape[:2]
            self.status_label.setText(f"Loaded: {os.path.basename(path)}")
            self.dimensions_label.setText(f"Size: {w}×{h}px")
            
            # Update output size display
            self.on_export_scale_change()
            
            # Display original image
            self.display_original_image()
            
            # Update preview
            self.update_preview()
            
            # Fit images to view after loading
            QTimer.singleShot(50, self.fit_images_to_view)
            
            self.status_bar.showMessage(f"Loaded: {os.path.basename(path)}")
        else:
            QMessageBox.critical(self, "Error", "Could not read image.")
    
    def display_original_image(self):
        """Display the original image in the left panel"""
        if self.original_image is None:
            return
        
        # Convert BGR to RGB for display
        img_rgb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        self.original_view.set_image(img_rgb)
    
    def update_preview(self):
        """Update the DXF preview"""
        if self.original_image is None:
            return
        
        # Update parameters from sliders
        self.params["bilateral_diameter"] = self.bilateral_d_slider.value()
        self.params["bilateral_sigma_color"] = self.bilateral_c_slider.value()
        self.params["bilateral_sigma_space"] = self.bilateral_c_slider.value()
        self.params["gaussian_kernel_size"] = self.gaussian_slider.value()
        if self.params["gaussian_kernel_size"] % 2 == 0:
            self.params["gaussian_kernel_size"] += 1  # Ensure odd
        self.params["canny_lower_threshold"] = self.canny_l_slider.value()
        self.params["canny_upper_threshold"] = self.canny_u_slider.value()
        self.params["edge_thickness"] = self.thickness_slider.value()
        self.params["gap_threshold"] = self.gap_slider.value()
        self.params["largest_n"] = self.largest_slider.value()
        self.params["simplify_pct"] = self.simplify_slider.value() / 100.0
        self.params["mm_per_px"] = self.scale_slider.value() / 100.0
        self.params["invert"] = self.invert_checkbox.isChecked()
        
        # Update labels
        self.bilateral_d_label.setText(str(self.params["bilateral_diameter"]))
        self.bilateral_c_label.setText(str(self.params["bilateral_sigma_color"]))
        self.gaussian_label.setText(str(self.params["gaussian_kernel_size"]))
        self.canny_l_label.setText(str(self.params["canny_lower_threshold"]))
        self.canny_u_label.setText(str(self.params["canny_upper_threshold"]))
        self.thickness_label.setText(f"{self.params['edge_thickness']:.1f}")
        self.gap_label.setText(f"{self.params['gap_threshold']:.1f}")
        self.largest_label.setText(str(self.params["largest_n"]))
        self.simplify_label.setText(f"{self.params['simplify_pct']:.1f}")
        self.scale_label.setText(f"{self.params['mm_per_px']:.3f}")
        
        # Process image
        self.current_mask = find_edges_and_contours(self.original_image, self.params)
        self.current_contours = contours_from_mask(
            self.current_mask, 
            self.params["largest_n"], 
            self.params["simplify_pct"],
            self.params["gap_threshold"]
        )
        
        # Display DXF preview
        self.display_dxf_preview()
    
    def display_dxf_preview(self):
        """Display the DXF preview"""
        if not self.current_contours or self.original_image is None:
            self.dxf_view.scene.clear()
            return
        
        # Clear the scene but keep the image
        items_to_remove = []
        for item in self.dxf_view.scene.items():
            if not isinstance(item, QGraphicsPixmapItem):
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.dxf_view.scene.removeItem(item)
        
        # Create a white background if no image is set
        if not self.dxf_view.image_item:
            h, w = self.original_image.shape[:2]
            white_image = np.ones((h, w, 3), dtype=np.uint8) * 255
            self.dxf_view.set_image(white_image)
        
        # Draw contours as graphics items
        for i, contour in enumerate(self.current_contours):
            if i in self.erased_contours:
                continue
            
            # Create a list of points for the contour
            points = []
            for j, point in enumerate(contour):
                if (i, j) not in self.erased_points:
                    points.append([point[0][0], point[0][1]])
            
            if len(points) >= 3:
                # Create a path for the contour
                path = QPainterPath()
                path.moveTo(points[0][0], points[0][1])
                for point in points[1:]:
                    path.lineTo(point[0], point[1])
                path.closeSubpath()
                
                # Create graphics item with solid line
                area = cv2.contourArea(contour)
                color = QColor(0, 100, 0) if area > 100 else QColor(255, 0, 0)
                pen = QPen(color, 2, Qt.SolidLine)
                
                path_item = QGraphicsPathItem(path)
                path_item.setPen(pen)
                self.dxf_view.scene.addItem(path_item)
        
        # Draw edited contours (manually added)
        for contour in self.edited_contours:
            points = []
            for point in contour:
                points.append([point[0][0], point[0][1]])
            
            if len(points) >= 3:
                # Create a path for the contour
                path = QPainterPath()
                path.moveTo(points[0][0], points[0][1])
                for point in points[1:]:
                    path.lineTo(point[0], point[1])
                path.closeSubpath()
                
                # Create graphics item with blue color
                pen = QPen(QColor(0, 0, 255), 2, Qt.SolidLine)
                
                path_item = QGraphicsPathItem(path)
                path_item.setPen(pen)
                self.dxf_view.scene.addItem(path_item)
    
    def on_param_change(self):
        """Handle parameter changes"""
        # Set preset to Custom when user manually changes parameters
        if self.preset_combo.currentText() != "Custom":
            self.preset_combo.setCurrentText("Custom")
        
        self.update_preview()
    
    def on_preset_change(self, preset_name):
        """Handle preset changes"""
        if preset_name == "Custom":
            return
        
        config = self.preset_configs.get(preset_name)
        if not config:
            return
        
        # Apply preset values
        self.bilateral_d_slider.setValue(config["bilateral_diameter"])
        self.bilateral_c_slider.setValue(config["bilateral_sigma_color"])
        self.gaussian_slider.setValue(config["gaussian_kernel_size"])
        self.canny_l_slider.setValue(config["canny_lower_threshold"])
        self.canny_u_slider.setValue(config["canny_upper_threshold"])
        self.thickness_slider.setValue(int(config["edge_thickness"]))
        self.gap_slider.setValue(int(config["gap_threshold"]))
        self.largest_slider.setValue(config["largest_n"])
        self.simplify_slider.setValue(int(config["simplify_pct"] * 100))
        self.scale_slider.setValue(int(config["mm_per_px"] * 100))
        self.invert_checkbox.setChecked(config["invert"])
        
        # Update preview
        self.update_preview()
    
    def on_export_scale_change(self):
        """Update output size display when export scale changes"""
        if self.original_image is not None:
            scale = self.export_scale_input.value()
            h, w = self.original_image.shape[:2]
            new_h = int(h * scale)
            new_w = int(w * scale)
            self.output_size_label.setText(f"Output: {new_w}×{new_h}px")
    
    def zoom_in(self):
        """Zoom in on the preview"""
        self.dxf_view.scale(1.2, 1.2)
    
    def zoom_out(self):
        """Zoom out on the preview"""
        self.dxf_view.scale(0.8, 0.8)
    
    def zoom_reset(self):
        """Reset zoom to fit"""
        self.dxf_view.reset_view()
    
    def pan_preview(self, dx, dy):
        """Pan the preview"""
        # This would need custom implementation in the graphics view
        pass
    
    def pan_reset(self):
        """Reset pan position"""
        self.dxf_view.reset_view()
    
    def set_edit_mode(self, mode):
        """Set the edit mode for the DXF view"""
        self.dxf_view.set_edit_mode(mode)
        self.edit_mode = mode
        
        # Set cursor based on mode
        if mode == "view":
            cursor = QCursor(Qt.ArrowCursor)
        elif mode == "paint":
            cursor = QCursor(Qt.CrossCursor)
        elif mode == "eraser":
            cursor = QCursor(Qt.CrossCursor)  # Could create custom eraser cursor
        elif mode == "line":
            cursor = QCursor(Qt.CrossCursor)
        elif mode == "shape":
            cursor = QCursor(Qt.CrossCursor)
        else:
            cursor = QCursor(Qt.ArrowCursor)
        
        # Apply cursor to both views
        self.original_view.setCursor(cursor)
        self.dxf_view.setCursor(cursor)
    
    def set_shape_mode(self):
        """Set shape drawing mode"""
        shape_type = self.shape_combo.currentText()
        self.dxf_view.set_shape_type(shape_type)
        self.dxf_view.set_edit_mode(shape_type)
        self.edit_mode = shape_type
    
    def undo_action(self):
        """Undo the last drawing action"""
        self.dxf_view.undo_last_action()
    
    def redo_action(self):
        """Redo the last undone action"""
        self.dxf_view.redo_last_action()
    
    def on_gap_enabled_toggled(self, enabled):
        """Handle gap threshold enable/disable toggle"""
        self.gap_slider.setEnabled(enabled)
        if not enabled:
            self.gap_slider.setValue(0)
            self.gap_label.setText("0.0")
        self.on_param_change()  # Update preview
    
    def force_maximize(self):
        """Force the window to maximize"""
        # Try multiple methods to ensure maximization
        self.setWindowState(Qt.WindowMaximized)
        self.showMaximized()
        
        # Try setting geometry to screen size as backup
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            self.setGeometry(screen_geometry)
        
        # Force update
        self.update()
        self.repaint()
    
    def showEvent(self, event):
        """Handle show event to ensure maximization"""
        super().showEvent(event)
        if not self.isMaximized():
            self.showMaximized()
    
    def fit_images_to_view(self):
        """Fit both images to their respective views"""
        if hasattr(self, 'original_view') and self.original_view.image_item is not None:
            self.original_view.fitInView(self.original_view.image_item, Qt.KeepAspectRatio)
            self.original_view.zoom_factor = 1.0
        
        if hasattr(self, 'dxf_view') and self.dxf_view.image_item is not None:
            self.dxf_view.fitInView(self.dxf_view.image_item, Qt.KeepAspectRatio)
            self.dxf_view.zoom_factor = 1.0
    
    def on_shape_type_change(self, shape_type):
        """Handle shape type change"""
        if self.edit_mode in ["rectangle", "triangle", "circle"]:
            self.dxf_view.set_shape_type(shape_type)
    
    def convert_drawing_items_to_contours(self):
        """Convert drawing items to contours for DXF export"""
        contours = []
        drawing_items = self.dxf_view.get_drawing_items()
        
        for item in drawing_items:
            if isinstance(item, DrawingPathItem):
                # Convert path to contour points
                path = item.path()
                points = []
                for i in range(path.elementCount()):
                    element = path.elementAt(i)
                    points.append([[int(element.x), int(element.y)]])
                if len(points) >= 3:
                    contours.append(np.array(points, dtype=np.int32))
            
            elif isinstance(item, DrawingLineItem):
                # Convert line to contour points
                line = item.line()
                points = [
                    [[int(line.p1().x()), int(line.p1().y())]],
                    [[int(line.p2().x()), int(line.p2().y())]]
                ]
                contours.append(np.array(points, dtype=np.int32))
            
            elif isinstance(item, DrawingRectItem):
                # Convert rectangle to contour points
                rect = item.rect()
                points = [
                    [[int(rect.left()), int(rect.top())]],
                    [[int(rect.right()), int(rect.top())]],
                    [[int(rect.right()), int(rect.bottom())]],
                    [[int(rect.left()), int(rect.bottom())]],
                    [[int(rect.left()), int(rect.top())]]  # Close the rectangle
                ]
                contours.append(np.array(points, dtype=np.int32))
            
            elif isinstance(item, DrawingEllipseItem):
                # Convert ellipse to contour points
                rect = item.rect()
                center_x = rect.center().x()
                center_y = rect.center().y()
                radius_x = rect.width() / 2
                radius_y = rect.height() / 2
                
                # Generate circle points
                num_points = 16
                points = []
                for i in range(num_points):
                    angle = 2 * math.pi * i / num_points
                    x = center_x + radius_x * math.cos(angle)
                    y = center_y + radius_y * math.sin(angle)
                    points.append([[int(x), int(y)]])
                # Close the circle
                points.append([[int(center_x + radius_x), int(center_y)]])
                contours.append(np.array(points, dtype=np.int32))
            
            elif isinstance(item, DrawingPolygonItem):
                # Convert polygon to contour points
                polygon = item.polygon()
                points = []
                for i in range(polygon.size()):
                    point = polygon.point(i)
                    points.append([[int(point.x()), int(point.y())]])
                if len(points) >= 3:
                    contours.append(np.array(points, dtype=np.int32))
        
        return contours
    
    def export_dxf(self):
        """Export the DXF file"""
        if self.image_path is None:
            QMessageBox.warning(self, "Warning", "No image loaded.")
            return
        
        # Get export scale
        export_scale = self.export_scale_input.value()
        
        # Get file path
        h, w = self.original_image.shape[:2]
        new_h, new_w = int(h * export_scale), int(w * export_scale)
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        default_name = f"{base_name}_{new_w}x{new_h}.dxf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DXF as",
            default_name, "AutoCAD DXF (*.dxf)"
        )
        
        if file_path:
            try:
                # Process contours for export
                export_contours = contours_from_mask(
                    self.current_mask, 
                    self.params["largest_n"], 
                    self.params["simplify_pct"],
                    self.params["gap_threshold"]
                )
                
                # Filter out erased contours and add edited contours
                filtered_contours = []
                for i, contour in enumerate(export_contours):
                    if i not in self.erased_contours:
                        # Filter out individual erased points
                        filtered_contour = []
                        for j, point in enumerate(contour):
                            if (i, j) not in self.erased_points:
                                filtered_contour.append(point)
                        if len(filtered_contour) >= 3:
                            filtered_contours.append(np.array(filtered_contour, dtype=np.int32))
                
                # Add manually edited contours
                filtered_contours.extend(self.edited_contours)
                
                # Convert drawing items to contours
                drawing_contours = self.convert_drawing_items_to_contours()
                filtered_contours.extend(drawing_contours)
                
                if not filtered_contours:
                    QMessageBox.warning(self, "Warning", "No contours found for export.")
                    return
                
                # Calculate effective mm_per_px
                effective_mm_per_px = self.params["mm_per_px"] / export_scale
                
                # Export DXF
                export_dxf(filtered_contours, file_path, self.current_mask.shape[:2], 
                          effective_mm_per_px)
                
                QMessageBox.information(self, "Success", 
                                      f"DXF saved to:\n{file_path}\nSize: {new_w}×{new_h}px")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

# -------------------------
# Main
# -------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Image Emboss")
    app.setApplicationVersion("2.0")
    
    window = ImageEmbossGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
