"""
Parameter control panel
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QGroupBox, QCheckBox, QFrame, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ui.widgets.custom_controls import ParameterSlider, PresetComboBox, ProcessingButton
from core.models.parameters import ProcessingParameters, PRESET_CONFIGS
from typing import Dict, Any


class ParameterPanel(QWidget):
    """Panel for controlling processing parameters"""
    
    # Signals
    parameters_changed = Signal(object)  # ProcessingParameters
    preset_changed = Signal(str)
    export_requested = Signal()
    reset_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parameters = ProcessingParameters()
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Processing Parameters")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Preset selection
        preset_group = QGroupBox("Master Preset")
        preset_layout = QVBoxLayout(preset_group)
        
        self.preset_combo = PresetComboBox(PRESET_CONFIGS)
        preset_layout.addWidget(self.preset_combo)
        
        layout.addWidget(preset_group)
        
        # Scroll area for parameters
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Parameters widget
        self.parameters_widget = QWidget()
        self.parameters_layout = QVBoxLayout(self.parameters_widget)
        self.parameters_layout.setSpacing(10)
        
        # Create parameter groups
        self.create_filtering_group()
        self.create_edge_detection_group()
        self.create_contour_group()
        self.create_export_group()
        
        scroll_area.setWidget(self.parameters_widget)
        layout.addWidget(scroll_area)
        
        # Action buttons
        self.create_action_buttons(layout)
    
    def create_filtering_group(self):
        """Create filtering parameters group"""
        group = QGroupBox("Filtering")
        layout = QVBoxLayout(group)
        
        # Bilateral filter
        self.bilateral_diameter_slider = ParameterSlider(
            "Bilateral Diameter", 1, 25, 9, 2, 0
        )
        layout.addWidget(self.bilateral_diameter_slider)
        
        self.bilateral_sigma_color_slider = ParameterSlider(
            "Color Sigma", 10, 200, 75, 5, 0
        )
        layout.addWidget(self.bilateral_sigma_color_slider)
        
        self.bilateral_sigma_space_slider = ParameterSlider(
            "Space Sigma", 10, 200, 75, 5, 0
        )
        layout.addWidget(self.bilateral_sigma_space_slider)
        
        # Gaussian blur
        self.gaussian_kernel_size_slider = ParameterSlider(
            "Gaussian Kernel Size", 1, 15, 5, 2, 0
        )
        layout.addWidget(self.gaussian_kernel_size_slider)
        
        self.parameters_layout.addWidget(group)
    
    def create_edge_detection_group(self):
        """Create edge detection parameters group"""
        group = QGroupBox("Edge Detection")
        layout = QVBoxLayout(group)
        
        # Canny thresholds
        self.canny_lower_slider = ParameterSlider(
            "Canny Lower Threshold", 10, 200, 30, 5, 0
        )
        layout.addWidget(self.canny_lower_slider)
        
        self.canny_upper_slider = ParameterSlider(
            "Canny Upper Threshold", 50, 300, 100, 5, 0
        )
        layout.addWidget(self.canny_upper_slider)
        
        # Edge thickness
        self.edge_thickness_slider = ParameterSlider(
            "Edge Thickness", 1.0, 10.0, 3.0, 0.5, 1
        )
        layout.addWidget(self.edge_thickness_slider)
        
        self.parameters_layout.addWidget(group)
    
    def create_contour_group(self):
        """Create contour processing parameters group"""
        group = QGroupBox("Contour Processing")
        layout = QVBoxLayout(group)
        
        # Gap threshold
        self.gap_threshold_slider = ParameterSlider(
            "Gap Threshold", 0.0, 20.0, 0.0, 1.0, 1
        )
        layout.addWidget(self.gap_threshold_slider)
        
        # Largest N contours
        self.largest_n_slider = ParameterSlider(
            "Largest N Contours", 1, 50, 10, 1, 0
        )
        layout.addWidget(self.largest_n_slider)
        
        # Simplification
        self.simplify_pct_slider = ParameterSlider(
            "Simplification %", 0.0, 100.0, 0.0, 5.0, 1
        )
        layout.addWidget(self.simplify_pct_slider)
        
        self.parameters_layout.addWidget(group)
    
    def create_export_group(self):
        """Create export parameters group"""
        group = QGroupBox("Export Settings")
        layout = QVBoxLayout(group)
        
        # Scale
        self.mm_per_px_slider = ParameterSlider(
            "mm per pixel", 0.01, 2.0, 0.25, 0.01, 2
        )
        layout.addWidget(self.mm_per_px_slider)
        
        # Extrude height
        self.extrude_height_slider = ParameterSlider(
            "Extrude Height (mm)", 0.1, 10.0, 1.0, 0.1, 1
        )
        layout.addWidget(self.extrude_height_slider)
        
        # Options
        self.invert_checkbox = QCheckBox("Invert Image")
        self.invert_checkbox.setChecked(True)
        layout.addWidget(self.invert_checkbox)
        
        self.use_splines_checkbox = QCheckBox("Use Smooth Splines")
        self.use_splines_checkbox.setChecked(True)
        layout.addWidget(self.use_splines_checkbox)
        
        # Spline quality
        spline_layout = QHBoxLayout()
        spline_layout.addWidget(QLabel("Spline Quality:"))
        
        from PySide6.QtWidgets import QComboBox
        self.spline_quality_combo = QComboBox()
        self.spline_quality_combo.addItems(["high", "medium", "low"])
        self.spline_quality_combo.setCurrentText("high")
        spline_layout.addWidget(self.spline_quality_combo)
        spline_layout.addStretch()
        
        layout.addLayout(spline_layout)
        
        self.parameters_layout.addWidget(group)
    
    def create_action_buttons(self, layout):
        """Create action buttons"""
        button_layout = QHBoxLayout()
        
        # Export button
        self.export_button = ProcessingButton("Export DXF")
        button_layout.addWidget(self.export_button)
        
        # Reset button
        self.reset_button = ProcessingButton("Reset")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #A23B72;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #8B2A5A;
            }
        """)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
    
    def connect_signals(self):
        """Connect all signals"""
        # Preset changes
        self.preset_combo.preset_changed.connect(self.on_preset_changed)
        
        # Parameter changes
        self.bilateral_diameter_slider.value_changed.connect(self.on_parameter_changed)
        self.bilateral_sigma_color_slider.value_changed.connect(self.on_parameter_changed)
        self.bilateral_sigma_space_slider.value_changed.connect(self.on_parameter_changed)
        self.gaussian_kernel_size_slider.value_changed.connect(self.on_parameter_changed)
        self.canny_lower_slider.value_changed.connect(self.on_parameter_changed)
        self.canny_upper_slider.value_changed.connect(self.on_parameter_changed)
        self.edge_thickness_slider.value_changed.connect(self.on_parameter_changed)
        self.gap_threshold_slider.value_changed.connect(self.on_parameter_changed)
        self.largest_n_slider.value_changed.connect(self.on_parameter_changed)
        self.simplify_pct_slider.value_changed.connect(self.on_parameter_changed)
        self.mm_per_px_slider.value_changed.connect(self.on_parameter_changed)
        self.extrude_height_slider.value_changed.connect(self.on_parameter_changed)
        
        # Checkbox changes
        self.invert_checkbox.toggled.connect(self.on_parameter_changed)
        self.use_splines_checkbox.toggled.connect(self.on_parameter_changed)
        self.spline_quality_combo.currentTextChanged.connect(self.on_parameter_changed)
        
        # Button clicks
        self.export_button.clicked.connect(self.export_requested.emit)
        self.reset_button.clicked.connect(self.reset_requested.emit)
    
    def on_preset_changed(self, preset_name: str):
        """Handle preset change"""
        if preset_name in PRESET_CONFIGS:
            preset_config = PRESET_CONFIGS[preset_name]
            self.apply_preset(preset_config)
            self.preset_changed.emit(preset_name)
    
    def apply_preset(self, preset_config: Dict[str, Any]):
        """Apply preset configuration"""
        # Update sliders
        self.bilateral_diameter_slider.set_value(preset_config.get('bilateral_diameter', 9))
        self.bilateral_sigma_color_slider.set_value(preset_config.get('bilateral_sigma_color', 75))
        self.bilateral_sigma_space_slider.set_value(preset_config.get('bilateral_sigma_space', 75))
        self.gaussian_kernel_size_slider.set_value(preset_config.get('gaussian_kernel_size', 5))
        self.canny_lower_slider.set_value(preset_config.get('canny_lower_threshold', 30))
        self.canny_upper_slider.set_value(preset_config.get('canny_upper_threshold', 100))
        self.edge_thickness_slider.set_value(preset_config.get('edge_thickness', 3.0))
        self.gap_threshold_slider.set_value(preset_config.get('gap_threshold', 0.0))
        self.largest_n_slider.set_value(preset_config.get('largest_n', 10))
        self.simplify_pct_slider.set_value(preset_config.get('simplify_pct', 0.0))
        self.mm_per_px_slider.set_value(preset_config.get('mm_per_px', 0.25))
        self.extrude_height_slider.set_value(preset_config.get('extrude_height', 1.0))
        
        # Update checkboxes
        self.invert_checkbox.setChecked(preset_config.get('invert', True))
        self.use_splines_checkbox.setChecked(preset_config.get('use_splines', True))
        self.spline_quality_combo.setCurrentText(preset_config.get('spline_quality', 'high'))
    
    def on_parameter_changed(self):
        """Handle parameter change"""
        # Update parameters object
        self.parameters.bilateral_diameter = int(self.bilateral_diameter_slider.get_value())
        self.parameters.bilateral_sigma_color = int(self.bilateral_sigma_color_slider.get_value())
        self.parameters.bilateral_sigma_space = int(self.bilateral_sigma_space_slider.get_value())
        self.parameters.gaussian_kernel_size = int(self.gaussian_kernel_size_slider.get_value())
        self.parameters.canny_lower_threshold = int(self.canny_lower_slider.get_value())
        self.parameters.canny_upper_threshold = int(self.canny_upper_slider.get_value())
        self.parameters.edge_thickness = self.edge_thickness_slider.get_value()
        self.parameters.gap_threshold = self.gap_threshold_slider.get_value()
        self.parameters.largest_n = int(self.largest_n_slider.get_value())
        self.parameters.simplify_pct = self.simplify_pct_slider.get_value()
        self.parameters.mm_per_px = self.mm_per_px_slider.get_value()
        self.parameters.extrude_height = self.extrude_height_slider.get_value()
        self.parameters.invert = self.invert_checkbox.isChecked()
        self.parameters.use_splines = self.use_splines_checkbox.isChecked()
        self.parameters.spline_quality = self.spline_quality_combo.currentText()
        
        # Emit signal
        self.parameters_changed.emit(self.parameters)
    
    def get_parameters(self) -> ProcessingParameters:
        """Get current parameters"""
        return self.parameters
    
    def set_parameters(self, parameters: ProcessingParameters):
        """Set parameters"""
        self.parameters = parameters
        self.apply_preset(parameters.to_dict())
    
    def set_enabled(self, enabled: bool):
        """Enable/disable all controls"""
        for widget in self.findChildren(ParameterSlider):
            widget.set_enabled(enabled)
        
        self.preset_combo.setEnabled(enabled)
        self.invert_checkbox.setEnabled(enabled)
        self.use_splines_checkbox.setEnabled(enabled)
        self.spline_quality_combo.setEnabled(enabled)
        self.export_button.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)
