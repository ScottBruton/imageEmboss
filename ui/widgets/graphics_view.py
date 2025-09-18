"""
Custom graphics view for image and DXF display
"""
import numpy as np
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor
from typing import List, Optional, Tuple


class ImageGraphicsView(QGraphicsView):
    """Custom graphics view for displaying images and DXF previews"""
    
    # Signals
    mouse_moved = Signal(QPointF)
    mouse_pressed = Signal(QPointF)
    mouse_released = Signal(QPointF)
    wheel_zoomed = Signal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Image item
        self.image_item = QGraphicsPixmapItem()
        self.scene.addItem(self.image_item)
        
        # DXF preview items
        self.dxf_items: List[QGraphicsItem] = []
        
        # View settings
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Zoom settings
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = QPointF()
        
        # Prevent recursive repaints
        self._is_updating = False
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._delayed_update)
        self._pending_image = None
        self._pending_dxf_data = None
    
    def set_image(self, image: np.ndarray):
        """Set image to display"""
        if image is None:
            return
        
        # Store pending image and start delayed update
        self._pending_image = image.copy() if hasattr(image, 'copy') else image
        self._update_timer.start(50)  # 50ms delay
    
    def _delayed_update(self):
        """Perform delayed update to prevent recursive repaints"""
        if self._is_updating:
            return
            
        try:
            self._is_updating = True
            
            # Update image if pending
            if self._pending_image is not None:
                self._update_image_internal(self._pending_image)
                self._pending_image = None
            
            # Update DXF preview if pending
            if self._pending_dxf_data is not None:
                contours, splines, use_splines = self._pending_dxf_data
                self._update_dxf_internal(contours, splines, use_splines)
                self._pending_dxf_data = None
                
        except Exception as e:
            print(f"Error in delayed update: {e}")
        finally:
            self._is_updating = False
    
    def _update_image_internal(self, image: np.ndarray):
        """Internal method to update image"""
        try:
            # Convert numpy array to QPixmap
            height, width = image.shape[:2]
            if len(image.shape) == 3:
                # Color image (already converted to RGB)
                bytes_per_line = 3 * width
                q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            else:
                # Grayscale image
                bytes_per_line = width
                q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            
            pixmap = QPixmap.fromImage(q_image)
            self.image_item.setPixmap(pixmap)
            
            # Fit image in view
            self.fit_in_view()
            
        except Exception as e:
            print(f"Error updating image: {e}")
    
    def set_dxf_preview(self, contours: List[np.ndarray], splines: List[np.ndarray] = None, use_splines: bool = True):
        """Set DXF preview contours and splines"""
        # Store pending DXF data and start delayed update
        self._pending_dxf_data = (contours, splines, use_splines)
        self._update_timer.start(50)  # 50ms delay
    
    def _update_dxf_internal(self, contours: List[np.ndarray], splines: List[np.ndarray] = None, use_splines: bool = True):
        """Internal method to update DXF preview"""
        try:
            # Clear existing DXF items
            for item in self.dxf_items:
                self.scene.removeItem(item)
            self.dxf_items.clear()
            
            # Add contour items
            for i, contour in enumerate(contours):
                if len(contour) < 3:
                    continue
                
                # Create contour item
                contour_item = ContourGraphicsItem(contour, is_spline=False)
                self.scene.addItem(contour_item)
                self.dxf_items.append(contour_item)
            
            # Add spline items if available and enabled
            if splines and use_splines:
                for i, spline in enumerate(splines):
                    if len(spline) < 3:
                        continue
                    
                    # Create spline item
                    spline_item = ContourGraphicsItem(spline, is_spline=True)
                    self.scene.addItem(spline_item)
                    self.dxf_items.append(spline_item)
                    
        except Exception as e:
            print(f"Error updating DXF preview: {e}")
    
    def fit_in_view(self):
        """Fit image in view"""
        if self.image_item.pixmap().isNull() or self._is_updating:
            return
        
        try:
            self._is_updating = True
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.zoom_factor = self.transform().m11()
        except Exception as e:
            print(f"Error fitting in view: {e}")
        finally:
            self._is_updating = False
    
    def zoom_in(self):
        """Zoom in"""
        self.zoom(1.2)
    
    def zoom_out(self):
        """Zoom out"""
        self.zoom(0.8)
    
    def zoom(self, factor: float):
        """Zoom by factor"""
        if self._is_updating:
            return
            
        new_zoom = self.zoom_factor * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            try:
                self._is_updating = True
                self.zoom_factor = new_zoom
                self.scale(factor, factor)
                self.wheel_zoomed.emit(self.zoom_factor)
            except Exception as e:
                print(f"Error zooming: {e}")
            finally:
                self._is_updating = False
    
    def reset_zoom(self):
        """Reset zoom to fit"""
        self.fit_in_view()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move"""
        scene_pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(scene_pos)
        self.last_mouse_pos = scene_pos
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        scene_pos = self.mapToScene(event.pos())
        self.mouse_pressed.emit(scene_pos)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        scene_pos = self.mapToScene(event.pos())
        self.mouse_released.emit(scene_pos)
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        """Handle wheel zoom"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()


class ContourGraphicsItem(QGraphicsItem):
    """Graphics item for displaying contours and splines"""
    
    def __init__(self, contour: np.ndarray, is_spline: bool = False):
        super().__init__()
        self.contour = contour
        self.is_spline = is_spline
        
        # Calculate bounding rect
        if len(contour) > 0:
            points = contour.reshape(-1, 2)
            self.bounding_rect = QRectF(
                points[:, 0].min(), points[:, 1].min(),
                points[:, 0].max() - points[:, 0].min(),
                points[:, 1].max() - points[:, 1].min()
            )
        else:
            self.bounding_rect = QRectF()
    
    def boundingRect(self) -> QRectF:
        """Return bounding rectangle"""
        return self.bounding_rect
    
    def paint(self, painter: QPainter, option, widget=None):
        """Paint the contour"""
        if len(self.contour) < 3:
            return
        
        try:
            # Set pen based on type
            if self.is_spline:
                pen = QPen(QColor(255, 0, 0), 2)  # Red for splines
            else:
                pen = QPen(QColor(0, 255, 0), 1)  # Green for contours
            
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            # Draw contour
            points = self.contour.reshape(-1, 2)
            q_points = [QPointF(x, y) for x, y in points]
            
            if len(q_points) > 1:
                # Draw lines between points
                for i in range(len(q_points) - 1):
                    painter.drawLine(q_points[i], q_points[i + 1])
                
                # Close contour if needed
                if not np.allclose(points[0], points[-1]):
                    painter.drawLine(q_points[-1], q_points[0])
                    
        except Exception as e:
            print(f"Error painting contour: {e}")
            # Don't re-raise the exception to prevent crashes


# Import QImage for image conversion
try:
    from PySide6.QtGui import QImage
except ImportError:
    print("⚠️ QImage not available - image display will be limited")
    QImage = None
