"""
Custom graphics items for drawing tools
"""
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsLineItem, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPolygonItem


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
