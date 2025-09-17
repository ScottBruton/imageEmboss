"""
3D model viewer panel
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QGroupBox, QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ui.widgets.custom_controls import ToolButton, StatusLabel
from typing import Optional
import numpy as np


class ModelViewerPanel(QWidget):
    """Panel for 3D model viewing"""
    
    # Signals
    rotate_requested = Signal()
    zoom_requested = Signal()
    lighting_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_loaded = False
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.zoom_level = 1.0
        self.lighting_enabled = True
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("3D Model Viewer")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 3D view widget
        self.create_3d_view(layout)
        
        # Control buttons
        self.create_control_buttons(layout)
        
        # Status info
        self.create_status_info(layout)
    
    def create_3d_view(self, layout):
        """Create 3D view widget"""
        # For now, create a placeholder widget
        # In a full implementation, this would be an OpenGL widget
        self.view_placeholder = QFrame()
        self.view_placeholder.setFrameStyle(QFrame.Box)
        self.view_placeholder.setStyleSheet("""
            QFrame {
                background-color: #F0F0F0;
                border: 2px solid #CCCCCC;
                border-radius: 5px;
            }
        """)
        self.view_placeholder.setMinimumHeight(300)
        
        # Add placeholder text
        placeholder_layout = QVBoxLayout(self.view_placeholder)
        placeholder_text = QLabel("3D Model Display\n\nOpenGL 3D viewer will be implemented here")
        placeholder_text.setAlignment(Qt.AlignCenter)
        placeholder_text.setFont(QFont("Arial", 10))
        placeholder_text.setStyleSheet("color: #666666;")
        placeholder_layout.addWidget(placeholder_text)
        
        layout.addWidget(self.view_placeholder)
    
    def create_control_buttons(self, layout):
        """Create control buttons"""
        control_group = QGroupBox("3D Controls")
        control_layout = QVBoxLayout(control_group)
        
        # Rotation controls
        rotation_layout = QHBoxLayout()
        
        self.rotate_x_button = ToolButton("🔄 Rotate X", "Rotate around X axis")
        rotation_layout.addWidget(self.rotate_x_button)
        
        self.rotate_y_button = ToolButton("🔄 Rotate Y", "Rotate around Y axis")
        rotation_layout.addWidget(self.rotate_y_button)
        
        self.reset_rotation_button = ToolButton("↺ Reset", "Reset rotation")
        rotation_layout.addWidget(self.reset_rotation_button)
        
        control_layout.addLayout(rotation_layout)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        self.zoom_in_button = ToolButton("🔍+ Zoom In", "Zoom in")
        zoom_layout.addWidget(self.zoom_in_button)
        
        self.zoom_out_button = ToolButton("🔍- Zoom Out", "Zoom out")
        zoom_layout.addWidget(self.zoom_out_button)
        
        self.fit_view_button = ToolButton("📐 Fit View", "Fit model to view")
        zoom_layout.addWidget(self.fit_view_button)
        
        control_layout.addLayout(zoom_layout)
        
        # Lighting controls
        lighting_layout = QHBoxLayout()
        
        self.lighting_button = ToolButton("💡 Lighting", "Toggle lighting")
        self.lighting_button.setCheckable(True)
        self.lighting_button.setChecked(True)
        lighting_layout.addWidget(self.lighting_button)
        
        self.wireframe_button = ToolButton("🔲 Wireframe", "Toggle wireframe mode")
        self.wireframe_button.setCheckable(True)
        lighting_layout.addWidget(self.wireframe_button)
        
        control_layout.addLayout(lighting_layout)
        
        layout.addWidget(control_group)
    
    def create_status_info(self, layout):
        """Create status information display"""
        status_group = QGroupBox("Model Info")
        status_layout = QVBoxLayout(status_group)
        
        # Status labels
        self.model_status_label = StatusLabel("Model: Not loaded")
        status_layout.addWidget(self.model_status_label)
        
        self.rotation_label = StatusLabel("Rotation: X=0°, Y=0°")
        status_layout.addWidget(self.rotation_label)
        
        self.zoom_label = StatusLabel("Zoom: 100%")
        status_layout.addWidget(self.zoom_label)
        
        self.lighting_label = StatusLabel("Lighting: On")
        status_layout.addWidget(self.lighting_label)
        
        layout.addWidget(status_group)
    
    def connect_signals(self):
        """Connect all signals"""
        # Rotation buttons
        self.rotate_x_button.clicked.connect(self.rotate_x)
        self.rotate_y_button.clicked.connect(self.rotate_y)
        self.reset_rotation_button.clicked.connect(self.reset_rotation)
        
        # Zoom buttons
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.fit_view_button.clicked.connect(self.fit_view)
        
        # Lighting buttons
        self.lighting_button.toggled.connect(self.toggle_lighting)
        self.wireframe_button.toggled.connect(self.toggle_wireframe)
    
    def set_model(self, model_data: Optional[np.ndarray]):
        """Set 3D model data"""
        if model_data is not None:
            self.model_loaded = True
            self.model_status_label.setText("Model: Loaded")
            self.update_display()
        else:
            self.model_loaded = False
            self.model_status_label.setText("Model: Not loaded")
    
    def update_display(self):
        """Update 3D display"""
        if self.model_loaded:
            # In a full implementation, this would update the OpenGL view
            print("Updating 3D display...")
    
    def rotate_x(self):
        """Rotate around X axis"""
        self.rotation_x += 15.0
        self.update_rotation_display()
        self.rotate_requested.emit()
    
    def rotate_y(self):
        """Rotate around Y axis"""
        self.rotation_y += 15.0
        self.update_rotation_display()
        self.rotate_requested.emit()
    
    def reset_rotation(self):
        """Reset rotation"""
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.update_rotation_display()
        self.rotate_requested.emit()
    
    def zoom_in(self):
        """Zoom in"""
        self.zoom_level *= 1.2
        self.update_zoom_display()
        self.zoom_requested.emit()
    
    def zoom_out(self):
        """Zoom out"""
        self.zoom_level /= 1.2
        self.update_zoom_display()
        self.zoom_requested.emit()
    
    def fit_view(self):
        """Fit model to view"""
        self.zoom_level = 1.0
        self.update_zoom_display()
        self.zoom_requested.emit()
    
    def toggle_lighting(self, enabled: bool):
        """Toggle lighting"""
        self.lighting_enabled = enabled
        self.lighting_label.setText(f"Lighting: {'On' if enabled else 'Off'}")
        self.lighting_changed.emit()
    
    def toggle_wireframe(self, enabled: bool):
        """Toggle wireframe mode"""
        # In a full implementation, this would change the rendering mode
        print(f"Wireframe mode: {'On' if enabled else 'Off'}")
    
    def update_rotation_display(self):
        """Update rotation display"""
        self.rotation_label.setText(f"Rotation: X={self.rotation_x:.0f}°, Y={self.rotation_y:.0f}°")
    
    def update_zoom_display(self):
        """Update zoom display"""
        zoom_percent = int(self.zoom_level * 100)
        self.zoom_label.setText(f"Zoom: {zoom_percent}%")
    
    def get_view_state(self) -> dict:
        """Get current view state"""
        return {
            'rotation_x': self.rotation_x,
            'rotation_y': self.rotation_y,
            'zoom_level': self.zoom_level,
            'lighting_enabled': self.lighting_enabled
        }
    
    def set_view_state(self, state: dict):
        """Set view state"""
        self.rotation_x = state.get('rotation_x', 0.0)
        self.rotation_y = state.get('rotation_y', 0.0)
        self.zoom_level = state.get('zoom_level', 1.0)
        self.lighting_enabled = state.get('lighting_enabled', True)
        
        self.update_rotation_display()
        self.update_zoom_display()
        self.lighting_button.setChecked(self.lighting_enabled)
    
    def clear_model(self):
        """Clear 3D model"""
        self.model_loaded = False
        self.model_status_label.setText("Model: Not loaded")
        self.update_display()
