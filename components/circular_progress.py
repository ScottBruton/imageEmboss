"""
Circular Progress Widget
A circular progress indicator with percentage display
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QFont


class CircularProgress(QWidget):
    """Circular progress indicator with percentage display"""
    
    def __init__(self, parent=None, size=40, line_width=4):
        super().__init__(parent)
        self.size = size
        self.line_width = line_width
        self.progress = 0.0
        
        # Colors
        self.background_color = QColor(60, 60, 60)  # Dark gray
        self.progress_color = QColor(52, 144, 220)  # Blue
        self.text_color = QColor(255, 255, 255)     # White
        
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    
    def set_progress(self, progress: float):
        """Set progress value (0.0 to 100.0)"""
        self.progress = max(0.0, min(100.0, progress))
        self.update()
    
    def paintEvent(self, event):
        """Paint the circular progress"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate dimensions
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - self.line_width
        
        # Draw background circle
        painter.setPen(QPen(self.background_color, self.line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawEllipse(center, radius, radius)
        
        # Draw progress arc
        if self.progress > 0:
            painter.setPen(QPen(self.progress_color, self.line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            
            # Calculate arc span (0 to 360 degrees)
            span_angle = int(16 * self.progress * 3.6)  # Qt uses 1/16th degrees
            
            # Draw arc starting from top (-90 degrees)
            painter.drawArc(
                center.x() - radius, center.y() - radius,
                radius * 2, radius * 2,
                -90 * 16, -span_angle  # Negative for clockwise
            )
        
        # Draw percentage text
        painter.setPen(QPen(self.text_color))
        font = QFont("Arial", max(8, self.size // 6), QFont.Weight.Bold)
        painter.setFont(font)
        
        text = f"{int(self.progress)}%"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    
    def set_colors(self, background: QColor = None, progress: QColor = None, text: QColor = None):
        """Set custom colors"""
        if background:
            self.background_color = background
        if progress:
            self.progress_color = progress
        if text:
            self.text_color = text
        self.update()


class DownloadButton(QWidget):
    """Button with integrated circular progress for downloads"""
    
    def __init__(self, parent=None, size=40):
        super().__init__(parent)
        self.size = size
        self.is_downloading = False
        self.progress = 0.0
        
        # Create circular progress
        self.circular_progress = CircularProgress(self, size, 3)
        self.circular_progress.hide()
        
        # Button styling
        self.setFixedSize(size, size)
        self.setStyleSheet("""
            QWidget {
                background-color: #28a745;
                border: none;
                border-radius: 20px;
            }
            QWidget:hover {
                background-color: #218838;
            }
            QWidget:pressed {
                background-color: #1e7e34;
            }
        """)
        
        # Timer for download simulation
        self.download_timer = QTimer()
        self.download_timer.timeout.connect(self._update_download_progress)
    
    def start_download(self):
        """Start download animation"""
        self.is_downloading = True
        self.progress = 0.0
        self.circular_progress.show()
        self.circular_progress.set_progress(0.0)
        
        # Start timer to simulate download progress
        self.download_timer.start(100)  # Update every 100ms
    
    def update_progress(self, progress: float):
        """Update download progress"""
        self.progress = progress
        self.circular_progress.set_progress(progress)
    
    def complete_download(self):
        """Complete download animation"""
        self.is_downloading = False
        self.download_timer.stop()
        self.circular_progress.set_progress(100.0)
        
        # Hide progress after a short delay
        QTimer.singleShot(1000, self._hide_progress)
    
    def fail_download(self):
        """Handle download failure"""
        self.is_downloading = False
        self.download_timer.stop()
        self.circular_progress.hide()
    
    def _update_download_progress(self):
        """Update download progress (simulation)"""
        if self.is_downloading and self.progress < 100:
            # Simulate progress
            self.progress += 2.0
            self.circular_progress.set_progress(self.progress)
        elif self.progress >= 100:
            self.complete_download()
    
    def _hide_progress(self):
        """Hide progress indicator"""
        self.circular_progress.hide()
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.is_downloading:
                self.start_download()
        super().mousePressEvent(event)
