"""
DXF preview panel with editing tools
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QGroupBox, QCheckBox, QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QFont, QPainter, QPen, QBrush, QColor
from ui.widgets.simple_graphics_view import SimpleGraphicsView
from ui.widgets.custom_controls import ToolButton, StatusLabel
from typing import List, Optional
import numpy as np


class PreviewPanel(QWidget):
    """Panel for DXF preview and editing tools"""
    
    # Signals
    circle_tool_toggled = Signal(bool)
    merge_tool_toggled = Signal(bool)
    settings_lock_toggled = Signal(bool)
    zoom_changed = Signal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_image = None
        self.contours = []
        self.splines = []
        self.use_splines = True
        self.circle_tool_active = False
        self.merge_tool_active = False
        self.settings_locked = False
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("DXF Preview")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Graphics view
        self.graphics_view = SimpleGraphicsView()
        self.graphics_view.setMinimumHeight(400)
        layout.addWidget(self.graphics_view)
        
        # Tool controls
        self.create_tool_controls(layout)
        
        # Status info
        self.create_status_info(layout)
    
    def create_tool_controls(self, layout):
        """Create tool control buttons"""
        tool_group = QGroupBox("Editing Tools")
        tool_layout = QVBoxLayout(tool_group)
        
        # Tool buttons
        button_layout = QHBoxLayout()
        
        self.circle_tool_button = ToolButton("🎯 Circle Tool", "Select area for processing")
        self.circle_tool_button.setCheckable(True)
        button_layout.addWidget(self.circle_tool_button)
        
        self.merge_tool_button = ToolButton("🔗 Merge", "Merge overlapping contours")
        self.merge_tool_button.setCheckable(True)
        button_layout.addWidget(self.merge_tool_button)
        
        self.settings_lock_button = ToolButton("🔒 Lock", "Lock settings for area processing")
        self.settings_lock_button.setCheckable(True)
        button_layout.addWidget(self.settings_lock_button)
        
        tool_layout.addLayout(button_layout)
        
        # Tool options
        options_layout = QHBoxLayout()
        
        self.show_original_checkbox = QCheckBox("Show Original")
        self.show_original_checkbox.setChecked(True)
        options_layout.addWidget(self.show_original_checkbox)
        
        self.show_contours_checkbox = QCheckBox("Show Contours")
        self.show_contours_checkbox.setChecked(True)
        options_layout.addWidget(self.show_contours_checkbox)
        
        self.show_splines_checkbox = QCheckBox("Show Splines")
        self.show_splines_checkbox.setChecked(True)
        options_layout.addWidget(self.show_splines_checkbox)
        
        options_layout.addStretch()
        tool_layout.addLayout(options_layout)
        
        layout.addWidget(tool_group)
    
    def create_status_info(self, layout):
        """Create status information display"""
        status_group = QGroupBox("Preview Info")
        status_layout = QVBoxLayout(status_group)
        
        # Status labels
        self.zoom_label = StatusLabel("Zoom: 100%")
        status_layout.addWidget(self.zoom_label)
        
        self.contour_count_label = StatusLabel("Contours: 0")
        status_layout.addWidget(self.contour_count_label)
        
        self.spline_count_label = StatusLabel("Splines: 0")
        status_layout.addWidget(self.spline_count_label)
        
        self.image_size_label = StatusLabel("Image: Not loaded")
        status_layout.addWidget(self.image_size_label)
        
        layout.addWidget(status_group)
    
    def connect_signals(self):
        """Connect all signals"""
        # Tool buttons
        self.circle_tool_button.toggled.connect(self.on_circle_tool_toggled)
        self.merge_tool_button.toggled.connect(self.on_merge_tool_toggled)
        self.settings_lock_button.toggled.connect(self.on_settings_lock_toggled)
        
        # Graphics view
        self.graphics_view.wheel_zoomed.connect(self.on_zoom_changed)
        self.graphics_view.mouse_pressed.connect(self.on_mouse_pressed)
        self.graphics_view.mouse_moved.connect(self.on_mouse_moved)
        
        # Checkboxes
        self.show_original_checkbox.toggled.connect(self.update_display)
        self.show_contours_checkbox.toggled.connect(self.update_display)
        self.show_splines_checkbox.toggled.connect(self.update_display)
    
    def set_original_image(self, image: np.ndarray):
        """Set original image for display"""
        self.original_image = image
        if self.show_original_checkbox.isChecked():
            self.graphics_view.set_image(image)
        
        # Update status
        if image is not None:
            h, w = image.shape[:2]
            self.image_size_label.setText(f"Image: {w}x{h}")
        else:
            self.image_size_label.setText("Image: Not loaded")
    
    def set_contours(self, contours: List[np.ndarray]):
        """Set contours for display"""
        self.contours = contours
        self.contour_count_label.setText(f"Contours: {len(contours)}")
        self.update_display()
    
    def set_splines(self, splines: List[np.ndarray]):
        """Set splines for display"""
        self.splines = splines
        self.spline_count_label.setText(f"Splines: {len(splines)}")
        self.update_display()
    
    def set_use_splines(self, use_splines: bool):
        """Set whether to use splines"""
        self.use_splines = use_splines
        self.update_display()
    
    def update_display(self):
        """Update the display based on current settings"""
        if not self.original_image is None and self.show_original_checkbox.isChecked():
            self.graphics_view.set_image(self.original_image)
        else:
            # Clear image
            self.graphics_view.set_image(np.zeros((100, 100, 3), dtype=np.uint8))
        
        # Update DXF preview
        if self.show_contours_checkbox.isChecked() or self.show_splines_checkbox.isChecked():
            contours_to_show = self.contours if self.show_contours_checkbox.isChecked() else []
            splines_to_show = self.splines if self.show_splines_checkbox.isChecked() else []
            
            self.graphics_view.set_dxf_preview(
                contours_to_show, 
                splines_to_show, 
                self.use_splines
            )
    
    def on_circle_tool_toggled(self, active: bool):
        """Handle circle tool toggle"""
        self.circle_tool_active = active
        self.circle_tool_toggled.emit(active)
        
        if active:
            self.merge_tool_button.setChecked(False)
            self.merge_tool_active = False
    
    def on_merge_tool_toggled(self, active: bool):
        """Handle merge tool toggle"""
        self.merge_tool_active = active
        self.merge_tool_toggled.emit(active)
        
        if active:
            self.circle_tool_button.setChecked(False)
            self.circle_tool_active = False
    
    def on_settings_lock_toggled(self, active: bool):
        """Handle settings lock toggle"""
        self.settings_locked = active
        self.settings_lock_toggled.emit(active)
    
    def on_zoom_changed(self, zoom_factor: float):
        """Handle zoom change"""
        zoom_percent = int(zoom_factor * 100)
        self.zoom_label.setText(f"Zoom: {zoom_percent}%")
        self.zoom_changed.emit(zoom_factor)
    
    def on_mouse_pressed(self, pos: QPointF):
        """Handle mouse press"""
        if self.circle_tool_active:
            # Handle circle tool selection
            print(f"Circle tool: Mouse pressed at {pos.x():.1f}, {pos.y():.1f}")
        elif self.merge_tool_active:
            # Handle merge tool selection
            print(f"Merge tool: Mouse pressed at {pos.x():.1f}, {pos.y():.1f}")
    
    def on_mouse_moved(self, pos: QPointF):
        """Handle mouse move"""
        # Update cursor or selection as needed
        pass
    
    def fit_to_view(self):
        """Fit image to view"""
        self.graphics_view.fit_in_view()
    
    def zoom_in(self):
        """Zoom in"""
        self.graphics_view.zoom_in()
    
    def zoom_out(self):
        """Zoom out"""
        self.graphics_view.zoom_out()
    
    def reset_zoom(self):
        """Reset zoom"""
        self.graphics_view.reset_zoom()
    
    def clear_preview(self):
        """Clear preview"""
        self.contours = []
        self.splines = []
        self.contour_count_label.setText("Contours: 0")
        self.spline_count_label.setText("Splines: 0")
        self.update_display()
    
    def get_tool_states(self) -> dict:
        """Get current tool states"""
        return {
            'circle_tool_active': self.circle_tool_active,
            'merge_tool_active': self.merge_tool_active,
            'settings_locked': self.settings_locked
        }
    
    def set_tool_states(self, states: dict):
        """Set tool states"""
        self.circle_tool_button.setChecked(states.get('circle_tool_active', False))
        self.merge_tool_button.setChecked(states.get('merge_tool_active', False))
        self.settings_lock_button.setChecked(states.get('settings_locked', False))
