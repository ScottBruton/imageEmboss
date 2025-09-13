"""
Custom graphics view for image display with zoom, pan, and drawing tools
"""
import math
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
                               QGraphicsPathItem, QGraphicsLineItem, QGraphicsRectItem,
                               QGraphicsEllipseItem, QGraphicsPolygonItem)
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QLineF, Signal, QMimeData, QDateTime
from PySide6.QtGui import (QPainter, QPen, QColor, QImage, QPixmap, QPainterPath, 
                          QDragEnterEvent, QDropEvent, QPolygonF, QTransform)

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
    
    # Signal for zoom events
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    
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
        
        # Set zoom behavior - allow unlimited zoom
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Remove zoom limits by overriding the default behavior
        self.setDragMode(QGraphicsView.NoDrag)  # Disable default drag mode
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
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
        
        # Undo/Redo system
        self.undo_stack = []  # List of actions that can be undone
        self.redo_stack = []  # List of actions that can be redone
        
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
            
            # Don't auto-fit to allow manual zoom control
            # self.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.zoom_factor = 1.0
    
    def resizeEvent(self, event):
        """Handle resize events to auto-fit image"""
        super().resizeEvent(event)
        # Disable auto-fit to prevent interference with zoom
        # if self.image_item is not None:
        #     # Auto-fit image when view is resized
        #     self.fitInView(self.image_item, Qt.KeepAspectRatio)
        #     self.zoom_factor = 1.0
    
    def scale(self, sx, sy):
        """Override scale to remove zoom limits"""
        # Get current transformation matrix
        matrix = self.transform()
        
        # Apply scaling to the matrix
        matrix.scale(sx, sy)
        
        # Set the new transformation matrix (this bypasses any built-in limits)
        self.setTransform(matrix)
        
        # Force update the zoom factor to match the actual matrix
        self.zoom_factor = matrix.m11()
    
    def wheelEvent(self, event):
        """Handle mouse wheel zoom with unlimited zoom"""
        # Get the position of the mouse before zooming
        old_pos = self.mapToScene(event.position().toPoint())
        
        # Zoom
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        # Apply zoom without limits
        self.scale(zoom_factor, zoom_factor)
        self.zoom_factor *= zoom_factor
        
        # Get the new position
        new_pos = self.mapToScene(event.position().toPoint())
        
        # Move scene to old position to keep cursor position stable
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
        """Reset zoom and pan to fit view (1:1 fit)"""
        # Fit the image to view (this is what 1:1 should mean - fit to container)
        if self.image_item:
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.zoom_factor = 1.0
    
    def set_edit_mode(self, mode):
        """Set the current edit mode"""
        self.edit_mode = mode
        self.drawing = False
        
        # Update cursor based on mode
        if mode == "view":
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.RubberBandDrag)
        elif mode == "paint":
            # Use a pencil-like cursor for paint mode
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        elif mode == "line":
            # Use cross cursor for line mode
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        elif mode == "eraser":
            # Use cross cursor for eraser mode
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        elif mode in ["rectangle", "triangle", "circle"]:
            # Use cross cursor for shape modes
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
            
            # Update temporary paint stroke
            self.update_temp_paint()
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
                # Remove temporary paint stroke
                if self.temp_drawing_item:
                    self.scene.removeItem(self.temp_drawing_item)
                
                # Create final path item for the paint stroke
                path_item = DrawingPathItem(self.drawing_path, self.drawing_pen)
                self.scene.addItem(path_item)
                # Add to undo stack
                self.add_to_undo_stack(path_item, "add")
        elif self.edit_mode == "line":
            self.finish_line(point)
        elif self.edit_mode in ["rectangle", "triangle", "circle"]:
            self.finish_shape(point)
        
        self.drawing = False
        self.drawing_points = []
        self.drawing_path = QPainterPath()
        self.temp_drawing_item = None
        
        self.drawing_finished.emit(point)
    
    def add_to_undo_stack(self, item, action_type="add"):
        """Add an action to the undo stack"""
        self.undo_stack.append({
            'item': item,
            'action': action_type,
            'timestamp': QDateTime.currentDateTime()
        })
        # Clear redo stack when new action is added
        self.redo_stack.clear()
        print(f"DEBUG: Added to undo stack - action: {action_type}, undo_stack size: {len(self.undo_stack)}, redo_stack size: {len(self.redo_stack)}")
    
    def undo_last_action(self):
        """Undo the last action"""
        if not self.undo_stack:
            print("DEBUG: undo_last_action - no actions to undo")
            return False
        
        action = self.undo_stack.pop()
        item = action['item']
        action_type = action['action']
        
        print(f"DEBUG: undo_last_action - action: {action_type}, undo_stack size: {len(self.undo_stack)}")
        
        if action_type == "add":
            # Remove the item from scene and add to redo stack as "add" (so redo will add it back)
            if item.scene() == self.scene:
                self.scene.removeItem(item)
                print("DEBUG: undo_last_action - removed item from scene")
            self.redo_stack.append({
                'item': item,
                'action': 'add',  # Keep as "add" so redo will add it back
                'timestamp': action['timestamp']
            })
            print(f"DEBUG: undo_last_action - added to redo stack, redo_stack size: {len(self.redo_stack)}")
        elif action_type == "remove":
            # Add the item back to scene and add to redo stack as "remove" (so redo will remove it again)
            if item.scene() is None:
                self.scene.addItem(item)
                print("DEBUG: undo_last_action - added item back to scene")
            self.redo_stack.append({
                'item': item,
                'action': 'remove',  # Keep as "remove" so redo will remove it again
                'timestamp': action['timestamp']
            })
            print(f"DEBUG: undo_last_action - added to redo stack, redo_stack size: {len(self.redo_stack)}")
        
        return True
    
    def can_undo(self):
        """Check if there are actions to undo"""
        return len(self.undo_stack) > 0
    
    def can_redo(self):
        """Check if there are actions to redo"""
        return len(self.redo_stack) > 0
    
    def is_at_clean_state(self):
        """Check if we're at the clean state (only preview image, no edits)"""
        # Count non-image items in the scene
        non_image_items = 0
        for item in self.scene.items():
            if not isinstance(item, QGraphicsPixmapItem):
                non_image_items += 1
        return non_image_items == 0
    
    def redo_last_action(self):
        """Redo the last undone action"""
        if not self.redo_stack:
            print("DEBUG: redo_last_action - no actions to redo")
            return False
        
        action = self.redo_stack.pop()
        item = action['item']
        action_type = action['action']
        
        print(f"DEBUG: redo_last_action - action: {action_type}, redo_stack size: {len(self.redo_stack)}")
        
        if action_type == "add":
            # Add the item back to scene and add to undo stack as "add" (so undo will remove it)
            if item.scene() is None:
                self.scene.addItem(item)
                print("DEBUG: redo_last_action - added item back to scene")
            self.undo_stack.append({
                'item': item,
                'action': 'add',  # Keep as "add" so undo will remove it
                'timestamp': action['timestamp']
            })
            print(f"DEBUG: redo_last_action - added to undo stack, undo_stack size: {len(self.undo_stack)}")
        elif action_type == "remove":
            # Remove the item from scene and add to undo stack as "remove" (so undo will add it back)
            if item.scene() == self.scene:
                self.scene.removeItem(item)
                print("DEBUG: redo_last_action - removed item from scene")
            self.undo_stack.append({
                'item': item,
                'action': 'remove',  # Keep as "remove" so undo will add it back
                'timestamp': action['timestamp']
            })
            print(f"DEBUG: redo_last_action - added to undo stack, undo_stack size: {len(self.undo_stack)}")
        
        return True
    
    def clear_undo_redo_stacks(self):
        """Clear both undo and redo stacks"""
        print(f"DEBUG: clear_undo_redo_stacks - clearing stacks, undo: {len(self.undo_stack)}, redo: {len(self.redo_stack)}")
        self.undo_stack.clear()
        self.redo_stack.clear()
    
    def update_temp_paint(self):
        """Update temporary paint stroke while drawing"""
        # Remove previous temporary paint stroke
        if self.temp_drawing_item:
            self.scene.removeItem(self.temp_drawing_item)
        
        # Create new temporary paint stroke
        if len(self.drawing_points) >= 2:
            self.temp_drawing_item = DrawingPathItem(self.drawing_path, self.drawing_pen)
            self.scene.addItem(self.temp_drawing_item)
    
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
        # Add to undo stack
        self.add_to_undo_stack(line_item, "add")
    
    def update_temp_shape(self, end_point):
        """Update temporary shape while drawing"""
        # Remove previous temporary shape
        if self.temp_drawing_item:
            self.scene.removeItem(self.temp_drawing_item)
        
        # Create new temporary shape based on type
        if self.edit_mode == "rectangle":
            rect = QRectF(self.shape_start_point, end_point).normalized()
            self.temp_drawing_item = DrawingRectItem(rect, self.drawing_pen)
        elif self.edit_mode == "circle":
            rect = QRectF(self.shape_start_point, end_point).normalized()
            self.temp_drawing_item = DrawingEllipseItem(rect, self.drawing_pen)
        elif self.edit_mode == "triangle":
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
        if self.edit_mode == "rectangle":
            rect = QRectF(self.shape_start_point, end_point).normalized()
            shape_item = DrawingRectItem(rect, self.drawing_pen)
        elif self.edit_mode == "circle":
            rect = QRectF(self.shape_start_point, end_point).normalized()
            shape_item = DrawingEllipseItem(rect, self.drawing_pen)
        elif self.edit_mode == "triangle":
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
        # Add to undo stack
        self.add_to_undo_stack(shape_item, "add")
    
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
