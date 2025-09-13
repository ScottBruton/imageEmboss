"""
Custom graphics view for image display with zoom, pan, and drawing tools
"""
import math
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
                               QGraphicsPathItem, QGraphicsLineItem, QGraphicsRectItem,
                               QGraphicsEllipseItem, QGraphicsPolygonItem)
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QLineF, Signal, QMimeData
from PySide6.QtGui import (QPainter, QPen, QColor, QImage, QPixmap, QPainterPath, 
                          QDragEnterEvent, QDropEvent, QPolygonF)

from .graphics_items import (DrawingPathItem, DrawingLineItem, DrawingRectItem, 
                           DrawingEllipseItem, DrawingPolygonItem)


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
