"""
Simple graphics view without complex operations to prevent crashes
"""
import numpy as np
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLabel
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QImage
from typing import List, Optional


class SimpleGraphicsView(QGraphicsView):
    """Simplified graphics view to prevent crashes"""
    
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
        
        # View settings
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Zoom settings
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = QPointF()
    
    def set_image(self, image: np.ndarray):
        """Set image to display"""
        if image is None:
            return
        
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
            print(f"Error setting image: {e}")
    
    def set_dxf_preview(self, contours: List[np.ndarray], splines: List[np.ndarray] = None, use_splines: bool = True):
        """Set DXF preview - simplified version"""
        # For now, just print the info instead of drawing
        print(f"DXF Preview: {len(contours)} contours, {len(splines) if splines else 0} splines")
    
    def fit_in_view(self):
        """Fit image in view"""
        if self.image_item.pixmap().isNull():
            return
        
        try:
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.zoom_factor = self.transform().m11()
        except Exception as e:
            print(f"Error fitting in view: {e}")
    
    def zoom_in(self):
        """Zoom in"""
        self.zoom(1.2)
    
    def zoom_out(self):
        """Zoom out"""
        self.zoom(0.8)
    
    def zoom(self, factor: float):
        """Zoom by factor"""
        new_zoom = self.zoom_factor * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.zoom_factor = new_zoom
            self.scale(factor, factor)
            self.wheel_zoomed.emit(self.zoom_factor)
    
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
