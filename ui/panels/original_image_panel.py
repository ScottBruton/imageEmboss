"""
Original image display panel
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QGroupBox, QPushButton, QFrame, QFileDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from ui.widgets.simple_graphics_view import SimpleGraphicsView
from ui.widgets.custom_controls import ToolButton, StatusLabel
from utils.file_utils import is_supported_image, get_file_size_mb, validate_image_file
from typing import Optional
import numpy as np
import cv2


class OriginalImagePanel(QWidget):
    """Panel for displaying original image"""
    
    # Signals
    image_loaded = Signal(str)  # image_path
    image_selected = Signal(str)  # image_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = ""
        self.original_image = None
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Original Image")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # File selection
        self.create_file_selection(layout)
        
        # Image display
        self.create_image_display(layout)
        
        # Image info
        self.create_image_info(layout)
    
    def create_file_selection(self, layout):
        """Create file selection controls"""
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # Select button
        self.select_button = ToolButton("📁 Select Image", "Select image file")
        file_layout.addWidget(self.select_button)
        
        # File path display
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setStyleSheet("""
            QLabel {
                color: #666666;
                background-color: #F5F5F5;
                border: 1px solid #DDDDDD;
                border-radius: 3px;
                padding: 4px 8px;
                font-family: monospace;
            }
        """)
        file_layout.addWidget(self.file_path_label)
        
        layout.addWidget(file_group)
    
    def create_image_display(self, layout):
        """Create image display widget"""
        self.image_view = SimpleGraphicsView()
        self.image_view.setMinimumHeight(400)  # Increased from 200
        self.image_view.setMaximumHeight(600)  # Increased from 300
        layout.addWidget(self.image_view)
    
    def create_image_info(self, layout):
        """Create image information display"""
        info_group = QGroupBox("Image Information")
        info_layout = QVBoxLayout(info_group)
        
        # Info labels
        self.image_size_label = StatusLabel("Size: Not loaded")
        info_layout.addWidget(self.image_size_label)
        
        self.file_size_label = StatusLabel("File Size: Not loaded")
        info_layout.addWidget(self.file_size_label)
        
        self.format_label = StatusLabel("Format: Not loaded")
        info_layout.addWidget(self.format_label)
        
        self.scale_label = StatusLabel("Scale: 1.00")
        info_layout.addWidget(self.scale_label)
        
        layout.addWidget(info_group)
    
    def connect_signals(self):
        """Connect all signals"""
        self.select_button.clicked.connect(self.select_image_file)
        self.image_view.wheel_zoomed.connect(self.on_zoom_changed)
    
    def select_image_file(self):
        """Select image file"""
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Image Files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            self.load_image(file_path)
    
    def load_image(self, image_path: str):
        """Load image from file"""
        # Validate file
        is_valid, error_message = validate_image_file(image_path)
        if not is_valid:
            self.show_error(f"Invalid image file: {error_message}")
            return
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                self.show_error("Could not load image file")
                return
            
            # Convert BGR to RGB for proper color display
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Store image data
            self.current_image_path = image_path
            self.original_image = image
            
            # Update display
            self.image_view.set_image(image)
            
            # Update file path display
            self.file_path_label.setText(image_path)
            
            # Update image info
            self.update_image_info(image, image_path)
            
            # Emit signals
            self.image_loaded.emit(image_path)
            self.image_selected.emit(image_path)
            
            print(f"✅ Image loaded: {image_path}")
            
        except Exception as e:
            self.show_error(f"Error loading image: {str(e)}")
    
    def update_image_info(self, image: np.ndarray, image_path: str):
        """Update image information display"""
        # Image size
        h, w = image.shape[:2]
        self.image_size_label.setText(f"Size: {w}x{h}")
        
        # File size
        file_size = get_file_size_mb(image_path)
        self.file_size_label.setText(f"File Size: {file_size:.1f} MB")
        
        # Format
        import os
        ext = os.path.splitext(image_path)[1].upper()
        self.format_label.setText(f"Format: {ext}")
        
        # Scale (will be updated by main application)
        self.scale_label.setText("Scale: 1.00")
    
    def on_zoom_changed(self, zoom_factor: float):
        """Handle zoom change"""
        # Update scale display
        scale = zoom_factor
        self.scale_label.setText(f"Scale: {scale:.2f}")
    
    def show_error(self, message: str):
        """Show error message"""
        print(f"❌ {message}")
        # In a full implementation, this would show a proper error dialog
    
    def get_current_image(self) -> Optional[np.ndarray]:
        """Get current image"""
        return self.original_image
    
    def get_current_image_path(self) -> str:
        """Get current image path"""
        return self.current_image_path
    
    def set_scale(self, scale: float):
        """Set scale factor"""
        self.scale_label.setText(f"Scale: {scale:.2f}")
    
    def fit_to_view(self):
        """Fit image to view"""
        self.image_view.fit_in_view()
    
    def zoom_in(self):
        """Zoom in"""
        self.image_view.zoom_in()
    
    def zoom_out(self):
        """Zoom out"""
        self.image_view.zoom_out()
    
    def reset_zoom(self):
        """Reset zoom"""
        self.image_view.reset_zoom()
    
    def clear_image(self):
        """Clear image"""
        self.current_image_path = ""
        self.original_image = None
        self.file_path_label.setText("No file selected")
        self.image_size_label.setText("Size: Not loaded")
        self.file_size_label.setText("File Size: Not loaded")
        self.format_label.setText("Format: Not loaded")
        self.scale_label.setText("Scale: 1.00")
        
        # Clear image view
        self.image_view.set_image(np.zeros((100, 100, 3), dtype=np.uint8))
    
    def is_image_loaded(self) -> bool:
        """Check if image is loaded"""
        return self.original_image is not None
    
    def get_image_metadata(self) -> dict:
        """Get image metadata"""
        if self.original_image is None:
            return {}
        
        h, w = self.original_image.shape[:2]
        return {
            'width': w,
            'height': h,
            'channels': self.original_image.shape[2] if len(self.original_image.shape) > 2 else 1,
            'file_path': self.current_image_path,
            'file_size_mb': get_file_size_mb(self.current_image_path) if self.current_image_path else 0.0
        }
