"""Scrollable image view with mouse-wheel zoom."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QResizeEvent, QShowEvent, QWheelEvent
from PySide6.QtWidgets import QScrollArea, QLabel, QSizePolicy


class ZoomableImageView(QScrollArea):
    """Displays a pixmap scaled to fit the viewport, with optional wheel zoom."""

    MIN_ZOOM = 0.05
    MAX_ZOOM = 10.0
    ZOOM_STEP = 1.15

    def __init__(self, placeholder_text: str = ""):
        super().__init__()
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #343a40;
                border: 2px dashed #495057;
                border-radius: 4px;
            }
        """)

        self._label = QLabel(placeholder_text)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._label.setStyleSheet("background-color: #343a40; color: #adb5bd; padding: 0; margin: 0;")
        self.setWidget(self._label)

        self._source_pixmap = None
        self._auto_fit = True
        self._zoom = 1.0

    def set_placeholder(self, text: str):
        self._source_pixmap = None
        self._label.clear()
        self._label.setText(text)
        self._label.setStyleSheet("background-color: #343a40; color: #adb5bd; padding: 20px;")

    def set_pixmap(self, pixmap, fit: bool = True):
        if pixmap is None or pixmap.isNull():
            return

        self._source_pixmap = pixmap
        self._label.setText("")
        self._label.setStyleSheet("background-color: #343a40; padding: 0; margin: 0;")
        self._auto_fit = fit
        self._schedule_refresh()

    def update_pixmap(self, pixmap):
        """Replace the source pixmap without resetting zoom mode."""
        if pixmap is None or pixmap.isNull():
            return

        self._source_pixmap = pixmap
        self._label.setText("")
        self._refresh_display()

    def fit_to_viewport(self):
        self._auto_fit = True
        self._refresh_display()

    def _schedule_refresh(self):
        QTimer.singleShot(0, self._refresh_display)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self._source_pixmap is not None and self._auto_fit:
            self._refresh_display()

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        if self._source_pixmap is not None and self._auto_fit:
            self._schedule_refresh()

    def wheelEvent(self, event: QWheelEvent):
        if self._source_pixmap is None:
            event.ignore()
            return

        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return

        if self._auto_fit:
            viewport = self.viewport().size()
            if viewport.width() > 0 and viewport.height() > 0:
                self._zoom = min(
                    viewport.width() / self._source_pixmap.width(),
                    viewport.height() / self._source_pixmap.height(),
                )
            self._auto_fit = False

        factor = self.ZOOM_STEP if delta > 0 else 1.0 / self.ZOOM_STEP
        self._zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom * factor))
        self._refresh_display()
        event.accept()

    def _refresh_display(self):
        if self._source_pixmap is None:
            return

        viewport = self.viewport().size()
        if viewport.width() < 10 or viewport.height() < 10:
            QTimer.singleShot(50, self._refresh_display)
            return

        if self._auto_fit:
            scale = min(
                viewport.width() / self._source_pixmap.width(),
                viewport.height() / self._source_pixmap.height(),
            )
        else:
            scale = self._zoom

        new_width = max(1, int(self._source_pixmap.width() * scale))
        new_height = max(1, int(self._source_pixmap.height() * scale))
        scaled = self._source_pixmap.scaled(
            new_width,
            new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._label.setPixmap(scaled)
        self._label.setFixedSize(scaled.size())
