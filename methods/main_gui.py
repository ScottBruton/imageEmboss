"""
Main GUI application class for ImageEmboss
"""
import os
import sys
import cv2
import numpy as np
import math
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QSlider, QComboBox, QCheckBox, 
                               QFileDialog, QMessageBox, QFrame, QGraphicsView, 
                               QGraphicsScene, QGraphicsPixmapItem, QSizePolicy,
                               QGroupBox, QSpinBox, QDoubleSpinBox, QLineEdit,
                               QProgressBar, QStatusBar, QMenuBar, QToolBar,
                               QGraphicsItem, QGraphicsEllipseItem, QGraphicsRectItem,
                               QGraphicsPolygonItem, QGraphicsLineItem, QGraphicsPathItem,
                               QTabWidget, QButtonGroup)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPoint, QRect, QSize, QPointF, QMimeData, QLineF
from PySide6.QtGui import (QPixmap, QImage, QPainter, QPen, QBrush, QColor, 
                           QFont, QAction, QDragEnterEvent, QDropEvent,
                           QPainterPath, QPolygonF, QTransform, QCursor)

from .helpers import find_edges_and_contours, contours_from_mask, export_dxf
from .graphics_view import ImageGraphicsView
from .graphics_items import (DrawingPathItem, DrawingLineItem, DrawingRectItem, 
                           DrawingEllipseItem, DrawingPolygonItem)
from .gui_methods import GUIMethods


class ImageEmbossGUI(QMainWindow, GUIMethods):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Emboss - Image to DXF Converter")
        # Set initial window size to be large
        self.setGeometry(100, 100, 1600, 1000)
        
        # Data
        self.original_image = None
        self.current_mask = None
        self.current_contours = []
        self.image_path = None
        
        # Edit mode variables
        self.edit_mode = "view"  # view, paint, eraser, shapes
        self.drawing = False
        self.drawing_points = []
        self.edited_contours = []
        self.erased_contours = set()
        self.erased_points = set()
        
        # Default parameters
        self.params = {
            "bilateral_diameter": 9,
            "bilateral_sigma_color": 75,
            "bilateral_sigma_space": 75,
            "gaussian_kernel_size": 5,
            "canny_lower_threshold": 30,
            "canny_upper_threshold": 100,
            "edge_thickness": 3,  # Changed from 2 to 3
            "gap_threshold": 0.0,  # Changed from 5.0 to 0.0
            "largest_n": 10,
            "simplify_pct": 0.0,  # Changed from 0.5 to 0.0
            "mm_per_px": 0.25,
            "invert": True
        }
        
        # Preset configurations
        self.preset_configs = {
            "Default": {
                "bilateral_diameter": 9,
                "bilateral_sigma_color": 75,
                "gaussian_kernel_size": 5,
                "canny_lower_threshold": 30,
                "canny_upper_threshold": 100,
                "edge_thickness": 3.0,  # Updated to 3.0
                "gap_threshold": 0.0,  # Updated to 0.0
                "largest_n": 10,
                "simplify_pct": 0.0,  # Updated to 0.0
                "mm_per_px": 0.25,
                "invert": True
            },
            "High Detail": {
                "bilateral_diameter": 6,
                "bilateral_sigma_color": 60,
                "gaussian_kernel_size": 3,
                "canny_lower_threshold": 20,
                "canny_upper_threshold": 60,
                "edge_thickness": 1.5,
                "gap_threshold": 3.0,
                "largest_n": 15,
                "simplify_pct": 0.3,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Low Noise": {
                "bilateral_diameter": 12,
                "bilateral_sigma_color": 120,
                "gaussian_kernel_size": 7,
                "canny_lower_threshold": 50,
                "canny_upper_threshold": 150,
                "edge_thickness": 3.0,
                "gap_threshold": 6.0,
                "largest_n": 10,
                "simplify_pct": 0.6,
                "mm_per_px": 0.25,
                "invert": True
            }
        }
        
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # Show window first, then maximize
        self.show()
        
        # Maximize after window is shown
        QTimer.singleShot(100, self.force_maximize)
        
        # Fit images to view after window is maximized
        QTimer.singleShot(200, self.fit_images_to_view)
    
    def setup_ui(self):
        """Setup the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - horizontal split (left and right panels)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)  # Small margins
        
        # Left panel - original image and parameters
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)  # Equal space
        
        # Right panel - DXF preview and tools
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)  # Equal space
    
    def create_left_panel(self):
        """Create the left panel with original image and parameters"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        # Top section - file selection
        top_frame = self.create_file_selection_frame()
        layout.addWidget(top_frame)
        
        # Middle section - original image
        original_group = QGroupBox("Original Image")
        original_layout = QVBoxLayout(original_group)
        original_layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        self.original_view = ImageGraphicsView()
        self.original_view.setMinimumSize(100, 100)  # Much smaller minimum
        self.original_view.image_dropped.connect(self.load_image_from_path)
        original_layout.addWidget(self.original_view)
        
        layout.addWidget(original_group, 4)  # Even more space for image
        
        # Bottom section - parameters
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_group)
        params_layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        # Master preset
        preset_frame = QFrame()
        preset_layout = QHBoxLayout(preset_frame)
        preset_layout.addWidget(QLabel("Master Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.preset_configs.keys()))
        self.preset_combo.setCurrentText("Default")
        self.preset_combo.currentTextChanged.connect(self.on_preset_change)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        params_layout.addWidget(preset_frame)
        
        # Create tab widget for parameters
        self.tab_widget = QTabWidget()
        self.create_filtering_tab()
        self.create_edge_detection_tab()
        self.create_contour_processing_tab()
        self.create_export_tab()
        params_layout.addWidget(self.tab_widget)
        
        layout.addWidget(params_group, 1)  # Less space for parameters
        
        return frame
    
    def create_right_panel(self):
        """Create the right panel with DXF preview and tools"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        # Top section - export controls
        export_frame = self.create_export_frame()
        layout.addWidget(export_frame)
        
        # Thin tools toolbar
        tools_toolbar = self.create_tools_toolbar()
        layout.addWidget(tools_toolbar)
        
        # DXF preview - takes remaining space
        dxf_group = QGroupBox("DXF Preview")
        dxf_layout = QVBoxLayout(dxf_group)
        dxf_layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        
        self.dxf_view = ImageGraphicsView()
        self.dxf_view.setMinimumSize(100, 100)  # Much smaller minimum
        self.dxf_view.image_dropped.connect(self.load_image_from_path)
        dxf_layout.addWidget(self.dxf_view)
        
        layout.addWidget(dxf_group, 1)  # Takes all remaining space
        
        return frame
        
    def create_filtering_tab(self):
        """Create the filtering parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Bilateral Diameter
        bilateral_d_layout = QHBoxLayout()
        
        # Bilateral diameter preset
        bilateral_d_preset_combo = QComboBox()
        bilateral_d_preset_combo.addItems(["Small", "Medium", "Large"])
        bilateral_d_preset_combo.setCurrentText("Medium")
        bilateral_d_preset_combo.currentTextChanged.connect(self.on_bilateral_d_preset_change)
        bilateral_d_preset_combo.setToolTip("Bilateral diameter presets: Small(6), Medium(9), Large(12)")
        bilateral_d_layout.addWidget(bilateral_d_preset_combo)
        
        bilateral_d_label = QLabel("Bilateral Diameter:")
        bilateral_d_label.setToolTip("Controls how much the image is smoothed while preserving edges. Higher values smooth more but may blur important details.")
        bilateral_d_layout.addWidget(bilateral_d_label)
        
        self.bilateral_d_slider = QSlider(Qt.Horizontal)
        self.bilateral_d_slider.setRange(5, 15)
        self.bilateral_d_slider.setValue(9)
        self.bilateral_d_slider.setToolTip("Controls how much the image is smoothed while preserving edges. Higher values smooth more but may blur important details.")
        self.bilateral_d_slider.valueChanged.connect(self.on_param_change)
        bilateral_d_layout.addWidget(self.bilateral_d_slider)
        
        self.bilateral_d_label = QLabel("9")
        self.bilateral_d_label.setMinimumWidth(30)
        bilateral_d_layout.addWidget(self.bilateral_d_label)
        
        layout.addLayout(bilateral_d_layout)
        
        # Bilateral Sigma Color
        bilateral_c_layout = QHBoxLayout()
        
        # Bilateral color preset
        bilateral_c_preset_combo = QComboBox()
        bilateral_c_preset_combo.addItems(["Low", "Medium", "High"])
        bilateral_c_preset_combo.setCurrentText("Medium")
        bilateral_c_preset_combo.currentTextChanged.connect(self.on_bilateral_c_preset_change)
        bilateral_c_preset_combo.setToolTip("Bilateral color presets: Low(40), Medium(75), High(120)")
        bilateral_c_layout.addWidget(bilateral_c_preset_combo)
        
        bilateral_c_label = QLabel("Bilateral Color σ:")
        bilateral_c_label.setToolTip("Controls how similar colors need to be to be smoothed together. Higher values allow more different colors to be smoothed.")
        bilateral_c_layout.addWidget(bilateral_c_label)
        
        self.bilateral_c_slider = QSlider(Qt.Horizontal)
        self.bilateral_c_slider.setRange(25, 150)
        self.bilateral_c_slider.setValue(75)
        self.bilateral_c_slider.setToolTip("Controls how similar colors need to be to be smoothed together. Higher values allow more different colors to be smoothed.")
        self.bilateral_c_slider.valueChanged.connect(self.on_param_change)
        bilateral_c_layout.addWidget(self.bilateral_c_slider)
        
        self.bilateral_c_label = QLabel("75")
        self.bilateral_c_label.setMinimumWidth(30)
        bilateral_c_layout.addWidget(self.bilateral_c_label)
        
        layout.addLayout(bilateral_c_layout)
        
        # Gaussian Kernel Size
        gaussian_layout = QHBoxLayout()
        
        # Gaussian preset
        gaussian_preset_combo = QComboBox()
        gaussian_preset_combo.addItems(["Light", "Medium", "Heavy"])
        gaussian_preset_combo.setCurrentText("Medium")
        gaussian_preset_combo.currentTextChanged.connect(self.on_gaussian_preset_change)
        gaussian_preset_combo.setToolTip("Gaussian blur presets: Light(3), Medium(5), Heavy(7)")
        gaussian_layout.addWidget(gaussian_preset_combo)
        
        gaussian_label = QLabel("Gaussian Kernel:")
        gaussian_label.setToolTip("Controls the amount of blur applied to the image. Higher values create more blur, which can help reduce noise but may soften important edges.")
        gaussian_layout.addWidget(gaussian_label)
        
        self.gaussian_slider = QSlider(Qt.Horizontal)
        self.gaussian_slider.setRange(3, 9)
        self.gaussian_slider.setValue(5)
        self.gaussian_slider.setToolTip("Controls the amount of blur applied to the image. Higher values create more blur, which can help reduce noise but may soften important edges.")
        self.gaussian_slider.valueChanged.connect(self.on_param_change)
        gaussian_layout.addWidget(self.gaussian_slider)
        
        self.gaussian_label = QLabel("5")
        self.gaussian_label.setMinimumWidth(30)
        gaussian_layout.addWidget(self.gaussian_label)
        
        layout.addLayout(gaussian_layout)
        
        self.tab_widget.addTab(tab, "Filtering")
    
    def create_edge_detection_tab(self):
        """Create the edge detection parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Canny preset
        canny_preset_layout = QHBoxLayout()
        canny_preset_combo = QComboBox()
        canny_preset_combo.addItems(["Sensitive", "Medium", "Conservative"])
        canny_preset_combo.setCurrentText("Medium")
        canny_preset_combo.currentTextChanged.connect(self.on_canny_preset_change)
        canny_preset_combo.setToolTip("Canny edge presets: Sensitive(20/60), Medium(30/100), Conservative(50/150)")
        canny_preset_layout.addWidget(canny_preset_combo)
        
        canny_label = QLabel("Canny Edge Detection")
        canny_preset_layout.addWidget(canny_label)
        layout.addLayout(canny_preset_layout)
        
        # Canny Lower Threshold
        canny_l_layout = QHBoxLayout()
        canny_l_label = QLabel("Canny Lower:")
        canny_l_label.setToolTip("Lower threshold for edge detection. Lower values detect more edges (including weak ones), higher values only detect strong edges.")
        canny_l_layout.addWidget(canny_l_label)
        
        self.canny_l_slider = QSlider(Qt.Horizontal)
        self.canny_l_slider.setRange(10, 100)
        self.canny_l_slider.setValue(30)
        self.canny_l_slider.setToolTip("Lower threshold for edge detection. Lower values detect more edges (including weak ones), higher values only detect strong edges.")
        self.canny_l_slider.valueChanged.connect(self.on_param_change)
        canny_l_layout.addWidget(self.canny_l_slider)
        
        self.canny_l_label = QLabel("30")
        self.canny_l_label.setMinimumWidth(30)
        canny_l_layout.addWidget(self.canny_l_label)
        
        layout.addLayout(canny_l_layout)
        
        # Canny Upper Threshold
        canny_u_layout = QHBoxLayout()
        canny_u_label = QLabel("Canny Upper:")
        canny_u_label.setToolTip("Upper threshold for edge detection. Higher values only detect very strong edges, lower values include more edges.")
        canny_u_layout.addWidget(canny_u_label)
        
        self.canny_u_slider = QSlider(Qt.Horizontal)
        self.canny_u_slider.setRange(30, 200)
        self.canny_u_slider.setValue(100)
        self.canny_u_slider.setToolTip("Upper threshold for edge detection. Higher values only detect very strong edges, lower values include more edges.")
        self.canny_u_slider.valueChanged.connect(self.on_param_change)
        canny_u_layout.addWidget(self.canny_u_slider)
        
        self.canny_u_label = QLabel("100")
        self.canny_u_label.setMinimumWidth(30)
        canny_u_layout.addWidget(self.canny_u_label)
        
        layout.addLayout(canny_u_layout)
        
        # Edge Thickness
        thickness_layout = QHBoxLayout()
        
        # Thickness preset
        thickness_preset_combo = QComboBox()
        thickness_preset_combo.addItems(["Thin", "Medium", "Thick"])
        thickness_preset_combo.setCurrentText("Medium")
        thickness_preset_combo.currentTextChanged.connect(self.on_thickness_preset_change)
        thickness_preset_combo.setToolTip("Edge thickness presets: Thin(1.0), Medium(2.5), Thick(6.0)")
        thickness_layout.addWidget(thickness_preset_combo)
        
        thickness_label = QLabel("Edge Thickness:")
        thickness_label.setToolTip("Controls how thick the lines will be in your final DXF file. Higher values create thicker lines, lower values create thinner lines.")
        thickness_layout.addWidget(thickness_label)
        
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 50)
        self.thickness_slider.setValue(3)  # Updated default to 3
        self.thickness_slider.setToolTip("Controls how thick the lines will be in your final DXF file. Higher values create thicker lines, lower values create thinner lines.")
        self.thickness_slider.valueChanged.connect(self.on_param_change)
        thickness_layout.addWidget(self.thickness_slider)
        
        self.thickness_label = QLabel("3.0")  # Updated default to 3.0
        self.thickness_label.setMinimumWidth(30)
        thickness_layout.addWidget(self.thickness_label)
        
        layout.addLayout(thickness_layout)
        
        self.tab_widget.addTab(tab, "Edge Detection")
    
    def create_contour_processing_tab(self):
        """Create the contour processing parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Gap Threshold
        gap_layout = QHBoxLayout()
        
        # Gap preset
        gap_preset_combo = QComboBox()
        gap_preset_combo.addItems(["None", "Light", "Medium", "Heavy"])
        gap_preset_combo.setCurrentText("Medium")
        gap_preset_combo.currentTextChanged.connect(self.on_gap_preset_change)
        gap_preset_combo.setToolTip("Gap closing presets: None(0), Light(2.5), Medium(5.0), Heavy(10.0)")
        gap_layout.addWidget(gap_preset_combo)
        
        gap_label = QLabel("Gap Threshold:")
        gap_label.setToolTip("Controls how close edges need to be to be connected together. Higher values connect edges that are farther apart.")
        gap_layout.addWidget(gap_label)
        
        self.gap_enabled_checkbox = QCheckBox("Enable")
        self.gap_enabled_checkbox.setChecked(False)  # Default disabled
        self.gap_enabled_checkbox.setToolTip("Enable gap threshold processing")
        self.gap_enabled_checkbox.toggled.connect(self.on_gap_enabled_toggled)
        gap_layout.addWidget(self.gap_enabled_checkbox)
        
        self.gap_slider = QSlider(Qt.Horizontal)
        self.gap_slider.setRange(0, 20)
        self.gap_slider.setValue(0)  # Updated default to 0
        self.gap_slider.setEnabled(False)  # Initially disabled
        self.gap_slider.setToolTip("Controls how close edges need to be to be connected together. Higher values connect edges that are farther apart.")
        self.gap_slider.valueChanged.connect(self.on_param_change)
        gap_layout.addWidget(self.gap_slider)
        
        self.gap_label = QLabel("0.0")  # Updated default to 0.0
        self.gap_label.setMinimumWidth(30)
        gap_layout.addWidget(self.gap_label)
        
        layout.addLayout(gap_layout)
        
        # Largest N
        largest_layout = QHBoxLayout()
        
        # Largest preset
        largest_preset_combo = QComboBox()
        largest_preset_combo.addItems(["Few", "Medium", "Many"])
        largest_preset_combo.setCurrentText("Medium")
        largest_preset_combo.currentTextChanged.connect(self.on_largest_preset_change)
        largest_preset_combo.setToolTip("Contour count presets: Few(3), Medium(10), Many(30)")
        largest_layout.addWidget(largest_preset_combo)
        
        largest_label = QLabel("Largest N:")
        largest_label.setToolTip("Controls how many of the largest shapes to keep. Higher values keep more shapes, lower values keep only the biggest ones.")
        largest_layout.addWidget(largest_label)
        
        self.largest_slider = QSlider(Qt.Horizontal)
        self.largest_slider.setRange(1, 50)
        self.largest_slider.setValue(10)
        self.largest_slider.setToolTip("Controls how many of the largest shapes to keep. Higher values keep more shapes, lower values keep only the biggest ones.")
        self.largest_slider.valueChanged.connect(self.on_param_change)
        largest_layout.addWidget(self.largest_slider)
        
        self.largest_label = QLabel("10")
        self.largest_label.setMinimumWidth(30)
        largest_layout.addWidget(self.largest_label)
        
        layout.addLayout(largest_layout)
        
        # Simplify
        simplify_layout = QHBoxLayout()
        
        # Simplify preset
        simplify_preset_combo = QComboBox()
        simplify_preset_combo.addItems(["Detailed", "Medium", "Simple"])
        simplify_preset_combo.setCurrentText("Medium")
        simplify_preset_combo.currentTextChanged.connect(self.on_simplify_preset_change)
        simplify_preset_combo.setToolTip("Simplification presets: Detailed(0.2), Medium(0.5), Simple(1.0)")
        simplify_layout.addWidget(simplify_preset_combo)
        
        simplify_label = QLabel("Simplify %:")
        simplify_label.setToolTip("Controls how much detail to remove from the shapes. Higher values create simpler shapes with fewer points, lower values keep more detail.")
        simplify_layout.addWidget(simplify_label)
        
        self.simplify_slider = QSlider(Qt.Horizontal)
        self.simplify_slider.setRange(0, 200)
        self.simplify_slider.setValue(0)  # Updated default to 0
        self.simplify_slider.setToolTip("Controls how much detail to remove from the shapes. Higher values create simpler shapes with fewer points, lower values keep more detail.")
        self.simplify_slider.valueChanged.connect(self.on_param_change)
        simplify_layout.addWidget(self.simplify_slider)
        
        self.simplify_label = QLabel("0.0")  # Updated default to 0.0
        self.simplify_label.setMinimumWidth(30)
        simplify_layout.addWidget(self.simplify_label)
        
        layout.addLayout(simplify_layout)
        
        self.tab_widget.addTab(tab, "Contour Processing")
    
    def create_export_tab(self):
        """Create the export parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Scale
        scale_layout = QHBoxLayout()
        
        # Scale preset
        scale_preset_combo = QComboBox()
        scale_preset_combo.addItems(["Small", "Medium", "Large"])
        scale_preset_combo.setCurrentText("Medium")
        scale_preset_combo.currentTextChanged.connect(self.on_scale_preset_change)
        scale_preset_combo.setToolTip("Scale presets: Small(0.15), Medium(0.25), Large(1.0)")
        scale_layout.addWidget(scale_preset_combo)
        
        scale_layout.addWidget(QLabel("Scale (mm/px):"))
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(1, 200)
        self.scale_slider.setValue(25)
        self.scale_slider.valueChanged.connect(self.on_param_change)
        scale_layout.addWidget(self.scale_slider)
        
        self.scale_label = QLabel("0.25")
        self.scale_label.setMinimumWidth(30)
        scale_layout.addWidget(self.scale_label)
        
        layout.addLayout(scale_layout)
        
        # Invert checkbox
        self.invert_checkbox = QCheckBox("Invert Black/White")
        self.invert_checkbox.setChecked(True)
        self.invert_checkbox.toggled.connect(self.on_param_change)
        layout.addWidget(self.invert_checkbox)
        
        layout.addStretch()  # Push everything to the top
        
        self.tab_widget.addTab(tab, "Export")
        
    def create_file_selection_frame(self):
        """Create the file selection frame for left panel"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        # File selection
        self.load_button = QPushButton("Select Image")
        self.load_button.setToolTip("Load an image file to process")
        self.load_button.clicked.connect(self.load_image)
        layout.addWidget(self.load_button)
        
        self.status_label = QLabel("No image loaded")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Image dimensions display
        self.dimensions_label = QLabel("")
        layout.addWidget(self.dimensions_label)
        
        return frame
    
    def create_export_frame(self):
        """Create the export frame for right panel"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        # Scale input
        layout.addWidget(QLabel("Scale:"))
        self.export_scale_input = QDoubleSpinBox()
        self.export_scale_input.setRange(0.1, 10.0)
        self.export_scale_input.setValue(1.0)
        self.export_scale_input.setDecimals(2)
        self.export_scale_input.setToolTip("Scale factor for DXF export (1.0 = original size)")
        self.export_scale_input.valueChanged.connect(self.on_export_scale_change)
        layout.addWidget(self.export_scale_input)
        
        # Output size display
        self.output_size_label = QLabel("")
        layout.addWidget(self.output_size_label)
        
        # Export button
        self.export_button = QPushButton("Export DXF")
        self.export_button.setToolTip("Export the processed image as a DXF file")
        self.export_button.clicked.connect(self.export_dxf)
        layout.addWidget(self.export_button)
        
        return frame
    
    def create_tools_toolbar(self):
        """Create a thin tools toolbar above the DXF preview"""
        toolbar = QFrame()
        toolbar.setMaximumHeight(50)  # Keep it thin
        toolbar.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)  # Minimal margins
        
        # Zoom controls
        layout.addWidget(QLabel("Zoom:"))
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setMaximumSize(25, 25)
        zoom_in_btn.setToolTip("Zoom in")
        zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setMaximumSize(25, 25)
        zoom_out_btn.setToolTip("Zoom out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(zoom_out_btn)
        
        zoom_1_1_btn = QPushButton("1:1")
        zoom_1_1_btn.setMaximumSize(35, 25)
        zoom_1_1_btn.setToolTip("Reset to 1:1 zoom")
        zoom_1_1_btn.clicked.connect(self.zoom_reset)
        layout.addWidget(zoom_1_1_btn)
        
        layout.addSpacing(10)
        
        # Pan controls
        layout.addWidget(QLabel("Pan:"))
        pan_up_btn = QPushButton("↑")
        pan_up_btn.setMaximumSize(25, 25)
        pan_up_btn.setToolTip("Pan up")
        pan_up_btn.clicked.connect(lambda: self.pan_preview(0, -50))
        layout.addWidget(pan_up_btn)
        
        pan_down_btn = QPushButton("↓")
        pan_down_btn.setMaximumSize(25, 25)
        pan_down_btn.setToolTip("Pan down")
        pan_down_btn.clicked.connect(lambda: self.pan_preview(0, 50))
        layout.addWidget(pan_down_btn)
        
        pan_left_btn = QPushButton("←")
        pan_left_btn.setMaximumSize(25, 25)
        pan_left_btn.setToolTip("Pan left")
        pan_left_btn.clicked.connect(lambda: self.pan_preview(-50, 0))
        layout.addWidget(pan_left_btn)
        
        pan_right_btn = QPushButton("→")
        pan_right_btn.setMaximumSize(25, 25)
        pan_right_btn.setToolTip("Pan right")
        pan_right_btn.clicked.connect(lambda: self.pan_preview(50, 0))
        layout.addWidget(pan_right_btn)
        
        layout.addSpacing(10)
        
        # Edit controls
        layout.addWidget(QLabel("Edit:"))
        
        # Create button group for mutually exclusive selection
        self.edit_button_group = QButtonGroup()
        
        # View mode button
        self.view_btn = QPushButton("👁")
        self.view_btn.setMaximumSize(25, 25)
        self.view_btn.setCheckable(True)
        self.view_btn.setChecked(True)
        self.view_btn.setToolTip("View mode - navigate and zoom")
        self.view_btn.clicked.connect(lambda: self.set_edit_mode("view"))
        self.edit_button_group.addButton(self.view_btn, 0)
        layout.addWidget(self.view_btn)
        
        # Paint mode button
        self.paint_btn = QPushButton("✏️")
        self.paint_btn.setMaximumSize(25, 25)
        self.paint_btn.setCheckable(True)
        self.paint_btn.setToolTip("Paint mode - draw freehand")
        self.paint_btn.clicked.connect(lambda: self.set_edit_mode("paint"))
        self.edit_button_group.addButton(self.paint_btn, 1)
        layout.addWidget(self.paint_btn)
        
        # Eraser mode button
        self.eraser_btn = QPushButton("🧽")
        self.eraser_btn.setMaximumSize(25, 25)
        self.eraser_btn.setCheckable(True)
        self.eraser_btn.setToolTip("Eraser mode - erase drawings")
        self.eraser_btn.clicked.connect(lambda: self.set_edit_mode("eraser"))
        self.edit_button_group.addButton(self.eraser_btn, 2)
        layout.addWidget(self.eraser_btn)
        
        # Line mode button
        self.line_btn = QPushButton("📏")
        self.line_btn.setMaximumSize(25, 25)
        self.line_btn.setCheckable(True)
        self.line_btn.setToolTip("Line mode - draw straight lines")
        self.line_btn.clicked.connect(lambda: self.set_edit_mode("line"))
        self.edit_button_group.addButton(self.line_btn, 3)
        layout.addWidget(self.line_btn)
        
        layout.addSpacing(10)
        
        # Undo/Redo controls
        layout.addWidget(QLabel("History:"))
        self.undo_btn = QPushButton("↶")
        self.undo_btn.setMaximumSize(25, 25)
        self.undo_btn.setToolTip("Undo last action")
        self.undo_btn.clicked.connect(self.undo_action)
        layout.addWidget(self.undo_btn)
        
        self.redo_btn = QPushButton("↷")
        self.redo_btn.setMaximumSize(25, 25)
        self.redo_btn.setToolTip("Redo last undone action")
        self.redo_btn.clicked.connect(self.redo_action)
        layout.addWidget(self.redo_btn)
        
        layout.addSpacing(10)
        
        # Shape controls
        layout.addWidget(QLabel("Shape:"))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Rectangle", "Triangle", "Circle"])
        self.shape_combo.setMaximumWidth(80)
        self.shape_combo.setToolTip("Select shape type for drawing")
        self.shape_combo.currentTextChanged.connect(self.set_shape_mode)
        layout.addWidget(self.shape_combo)
        
        # Shape mode button
        self.shape_btn = QPushButton("🔺")
        self.shape_btn.setMaximumSize(25, 25)
        self.shape_btn.setCheckable(True)
        self.shape_btn.setToolTip("Draw shapes")
        self.shape_btn.clicked.connect(lambda: self.set_edit_mode("shapes"))
        self.edit_button_group.addButton(self.shape_btn, 4)
        layout.addWidget(self.shape_btn)
        
        layout.addStretch()  # Push everything to the left
        
        return toolbar
