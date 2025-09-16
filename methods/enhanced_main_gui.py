"""
Enhanced Main GUI with Performance Optimizations
Integrates parallel processing, Numba acceleration, and improved algorithms
"""

import os
import sys
import cv2
import numpy as np
import math
import multiprocessing as mp
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

# Import enhanced modules
from .enhanced_helpers import EnhancedImageProcessor
from .enhanced_gui_methods import EnhancedGUIMethods
from .performance_processor import ProcessingConfig
from .performance_settings_dialog import PerformanceSettingsDialog

# Import original modules for fallback
from .helpers import find_edges_and_contours, contours_from_mask, export_dxf
from .graphics_view import ImageGraphicsView
from .graphics_items import (DrawingPathItem, DrawingLineItem, DrawingRectItem, 
                           DrawingEllipseItem, DrawingPolygonItem)
from .gui_methods import GUIMethods


class EnhancedImageEmbossGUI(QMainWindow, EnhancedGUIMethods):
    """Enhanced main GUI with performance optimizations"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Emboss - Enhanced Image to DXF Converter")
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
        
        # Performance settings
        self.performance_config = ProcessingConfig(
            max_workers=mp.cpu_count(),
            use_numba=True,
            use_cadquery=True,
            parallel_extrusion=True,
            enable_profiling=False,
            log_performance=True
        )
        
        # Initialize enhanced processors
        self.enhanced_image_processor = EnhancedImageProcessor(self.performance_config)
        
        # Parameters
        self.params = {
            # Filtering parameters
            'bilateral_d': 9,
            'bilateral_c': 75,
            'bilateral_sigma': 75,
            'blur_kernel': 5,
            'blur_sigma': 1.0,
            
            # Edge detection parameters
            'canny_low': 50,
            'canny_high': 150,
            'thicken_kernel': 3,
            'invert': False,
            
            # Contour processing parameters
            'largest_n': 3,
            'simplify_pct': 0.6,
            'gap_threshold': 5.0,
            'gap_enabled': True,
            
            # Export parameters
            'mm_per_px': 0.25,
            'extrude_height': 1.0,
            
            # Performance parameters
            'use_parallel_processing': True,
            'use_numba_acceleration': True,
            'use_enhanced_cadquery': True,
            'enable_performance_profiling': False,
            'max_workers': mp.cpu_count(),
            'chunk_size': 10,
        }
        
        # Preset configurations
        self.preset_configs = {
            "Jaw Line": {
                'bilateral_d': 9, 'bilateral_c': 75, 'bilateral_sigma': 75,
                'blur_kernel': 3, 'blur_sigma': 0.5,
                'canny_low': 30, 'canny_high': 100,
                'thicken_kernel': 2, 'invert': False,
                'largest_n': 2, 'simplify_pct': 0.4, 'gap_threshold': 3.0
            },
            "Eyes": {
                'bilateral_d': 5, 'bilateral_c': 50, 'bilateral_sigma': 50,
                'blur_kernel': 3, 'blur_sigma': 0.3,
                'canny_low': 20, 'canny_high': 80,
                'thicken_kernel': 1, 'invert': False,
                'largest_n': 4, 'simplify_pct': 0.3, 'gap_threshold': 2.0
            },
            "Hair - Fine": {
                'bilateral_d': 3, 'bilateral_c': 30, 'bilateral_sigma': 30,
                'blur_kernel': 1, 'blur_sigma': 0.1,
                'canny_low': 10, 'canny_high': 50,
                'thicken_kernel': 1, 'invert': False,
                'largest_n': 10, 'simplify_pct': 0.2, 'gap_threshold': 1.0
            },
            "Architecture": {
                'bilateral_d': 15, 'bilateral_c': 100, 'bilateral_sigma': 100,
                'blur_kernel': 7, 'blur_sigma': 2.0,
                'canny_low': 80, 'canny_high': 200,
                'thicken_kernel': 5, 'invert': False,
                'largest_n': 5, 'simplify_pct': 0.8, 'gap_threshold': 8.0
            },
            "Custom": {}
        }
        
        # UI components
        self.original_view = None
        self.dxf_view = None
        self.tab_widget = None
        self.status_bar = None
        
        # Settings lock for area processing
        self.settings_locked = False
        
        # Initialize UI
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # Connect performance settings
        self.setup_performance_connections()
    
    def setup_performance_connections(self):
        """Setup connections for performance features"""
        # This will be called after the UI is set up
        pass
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left panel (parameters)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel (image views)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)
        
        central_widget.setLayout(main_layout)
    
    def create_left_panel(self):
        """Create the left parameter panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumWidth(400)
        panel.setMinimumWidth(350)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Performance status
        performance_group = QGroupBox("Performance Status")
        performance_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
        """)
        perf_layout = QVBoxLayout()
        
        # Performance mode indicator
        self.performance_mode_label = QLabel("Mode: Maximum Performance")
        self.performance_mode_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        perf_layout.addWidget(self.performance_mode_label)
        
        # CPU usage indicator
        self.cpu_usage_label = QLabel(f"CPU Cores: {mp.cpu_count()}")
        self.cpu_usage_label.setStyleSheet("color: #2196F3;")
        perf_layout.addWidget(self.cpu_usage_label)
        
        # Performance settings button
        perf_settings_button = QPushButton("Performance Settings")
        perf_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        perf_settings_button.clicked.connect(self.open_performance_settings)
        perf_layout.addWidget(perf_settings_button)
        
        # Performance stats button
        perf_stats_button = QPushButton("Show Performance Stats")
        perf_stats_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        perf_stats_button.clicked.connect(self.show_performance_stats)
        perf_layout.addWidget(perf_stats_button)
        
        # Benchmark button
        benchmark_button = QPushButton("Run Benchmark")
        benchmark_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        benchmark_button.clicked.connect(self.benchmark_performance)
        perf_layout.addWidget(benchmark_button)
        
        performance_group.setLayout(perf_layout)
        layout.addWidget(performance_group)
        
        # File selection
        file_group = self.create_file_selection_frame()
        layout.addWidget(file_group)
        
        # Parameter tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Create parameter tabs
        self.create_filtering_tab()
        self.create_edge_detection_tab()
        self.create_contour_processing_tab()
        self.create_export_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Export frame
        export_group = self.create_export_frame()
        layout.addWidget(export_group)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def create_right_panel(self):
        """Create the right panel with image views"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Tools toolbar
        tools_toolbar = self.create_tools_toolbar()
        layout.addWidget(tools_toolbar)
        
        # Image views
        views_layout = QHBoxLayout()
        views_layout.setSpacing(10)
        
        # Original image view
        original_group = QGroupBox("Original Image")
        original_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2196F3;
            }
        """)
        original_layout = QVBoxLayout()
        
        self.original_view = ImageGraphicsView()
        self.original_view.setMinimumSize(400, 300)
        self.original_view.setDragMode(QGraphicsView.RubberBandDrag)
        original_layout.addWidget(self.original_view)
        
        original_group.setLayout(original_layout)
        views_layout.addWidget(original_group)
        
        # DXF preview view
        dxf_group = QGroupBox("DXF Preview")
        dxf_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
        """)
        dxf_layout = QVBoxLayout()
        
        self.dxf_view = ImageGraphicsView()
        self.dxf_view.setMinimumSize(400, 300)
        self.dxf_view.setDragMode(QGraphicsView.RubberBandDrag)
        dxf_layout.addWidget(self.dxf_view)
        
        dxf_group.setLayout(dxf_layout)
        views_layout.addWidget(dxf_group)
        
        layout.addLayout(views_layout)
        panel.setLayout(layout)
        return panel
    
    def create_file_selection_frame(self):
        """Create file selection frame"""
        group = QGroupBox("File Selection")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #9C27B0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9C27B0;
            }
        """)
        layout = QVBoxLayout()
        
        # Load image button
        load_button = QPushButton("Load Image")
        load_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        load_button.clicked.connect(self.load_image)
        layout.addWidget(load_button)
        
        # File path display
        self.file_path_label = QLabel("No image loaded")
        self.file_path_label.setStyleSheet("color: #666; font-style: italic;")
        self.file_path_label.setWordWrap(True)
        layout.addWidget(self.file_path_label)
        
        group.setLayout(layout)
        return group
    
    def create_filtering_tab(self):
        """Create filtering parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Preset selection
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.preset_configs.keys()))
        self.preset_combo.currentTextChanged.connect(self.on_preset_change)
        preset_layout.addWidget(self.preset_combo)
        layout.addLayout(preset_layout)
        
        # Bilateral filter parameters
        bilateral_group = QGroupBox("Bilateral Filter")
        bilateral_layout = QFormLayout()
        
        # Bilateral d
        self.bilateral_d_slider = QSlider(Qt.Horizontal)
        self.bilateral_d_slider.setRange(1, 25)
        self.bilateral_d_slider.setValue(self.params['bilateral_d'])
        self.bilateral_d_slider.valueChanged.connect(self.on_param_change)
        bilateral_layout.addRow("Diameter:", self.bilateral_d_slider)
        
        # Bilateral c
        self.bilateral_c_slider = QSlider(Qt.Horizontal)
        self.bilateral_c_slider.setRange(10, 200)
        self.bilateral_c_slider.setValue(self.params['bilateral_c'])
        self.bilateral_c_slider.valueChanged.connect(self.on_param_change)
        bilateral_layout.addRow("Color Sigma:", self.bilateral_c_slider)
        
        # Bilateral sigma
        self.bilateral_sigma_slider = QSlider(Qt.Horizontal)
        self.bilateral_sigma_slider.setRange(10, 200)
        self.bilateral_sigma_slider.setValue(self.params['bilateral_sigma'])
        self.bilateral_sigma_slider.valueChanged.connect(self.on_param_change)
        bilateral_layout.addRow("Space Sigma:", self.bilateral_sigma_slider)
        
        bilateral_group.setLayout(bilateral_layout)
        layout.addWidget(bilateral_group)
        
        # Gaussian blur parameters
        blur_group = QGroupBox("Gaussian Blur")
        blur_layout = QFormLayout()
        
        # Blur kernel
        self.blur_kernel_slider = QSlider(Qt.Horizontal)
        self.blur_kernel_slider.setRange(1, 15)
        self.blur_kernel_slider.setValue(self.params['blur_kernel'])
        self.blur_kernel_slider.valueChanged.connect(self.on_param_change)
        blur_layout.addRow("Kernel Size:", self.blur_kernel_slider)
        
        # Blur sigma
        self.blur_sigma_slider = QSlider(Qt.Horizontal)
        self.blur_sigma_slider.setRange(1, 50)
        self.blur_sigma_slider.setValue(int(self.params['blur_sigma'] * 10))
        self.blur_sigma_slider.valueChanged.connect(self.on_param_change)
        blur_layout.addRow("Sigma:", self.blur_sigma_slider)
        
        blur_group.setLayout(blur_layout)
        layout.addWidget(blur_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Filtering")
    
    def create_edge_detection_tab(self):
        """Create edge detection parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Canny parameters
        canny_group = QGroupBox("Canny Edge Detection")
        canny_layout = QFormLayout()
        
        # Canny low threshold
        self.canny_low_slider = QSlider(Qt.Horizontal)
        self.canny_low_slider.setRange(10, 200)
        self.canny_low_slider.setValue(self.params['canny_low'])
        self.canny_low_slider.valueChanged.connect(self.on_param_change)
        canny_layout.addRow("Low Threshold:", self.canny_low_slider)
        
        # Canny high threshold
        self.canny_high_slider = QSlider(Qt.Horizontal)
        self.canny_high_slider.setRange(50, 300)
        self.canny_high_slider.setValue(self.params['canny_high'])
        self.canny_high_slider.valueChanged.connect(self.on_param_change)
        canny_layout.addRow("High Threshold:", self.canny_high_slider)
        
        canny_group.setLayout(canny_layout)
        layout.addWidget(canny_group)
        
        # Edge processing
        edge_group = QGroupBox("Edge Processing")
        edge_layout = QFormLayout()
        
        # Thicken kernel
        self.thicken_kernel_slider = QSlider(Qt.Horizontal)
        self.thicken_kernel_slider.setRange(1, 10)
        self.thicken_kernel_slider.setValue(self.params['thicken_kernel'])
        self.thicken_kernel_slider.valueChanged.connect(self.on_param_change)
        edge_layout.addRow("Thicken Kernel:", self.thicken_kernel_slider)
        
        # Invert checkbox
        self.invert_checkbox = QCheckBox("Invert Edges")
        self.invert_checkbox.setChecked(self.params['invert'])
        self.invert_checkbox.toggled.connect(self.on_param_change)
        edge_layout.addRow(self.invert_checkbox)
        
        edge_group.setLayout(edge_layout)
        layout.addWidget(edge_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Edge Detection")
    
    def create_contour_processing_tab(self):
        """Create contour processing parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Contour parameters
        contour_group = QGroupBox("Contour Processing")
        contour_layout = QFormLayout()
        
        # Largest n
        self.largest_n_slider = QSlider(Qt.Horizontal)
        self.largest_n_slider.setRange(1, 20)
        self.largest_n_slider.setValue(self.params['largest_n'])
        self.largest_n_slider.valueChanged.connect(self.on_param_change)
        contour_layout.addRow("Largest N:", self.largest_n_slider)
        
        # Simplify percentage
        self.simplify_pct_slider = QSlider(Qt.Horizontal)
        self.simplify_pct_slider.setRange(0, 100)
        self.simplify_pct_slider.setValue(int(self.params['simplify_pct'] * 100))
        self.simplify_pct_slider.valueChanged.connect(self.on_param_change)
        contour_layout.addRow("Simplify %:", self.simplify_pct_slider)
        
        # Gap threshold
        self.gap_threshold_slider = QSlider(Qt.Horizontal)
        self.gap_threshold_slider.setRange(0, 20)
        self.gap_threshold_slider.setValue(int(self.params['gap_threshold']))
        self.gap_threshold_slider.valueChanged.connect(self.on_param_change)
        contour_layout.addRow("Gap Threshold:", self.gap_threshold_slider)
        
        # Gap enabled checkbox
        self.gap_enabled_checkbox = QCheckBox("Enable Gap Closing")
        self.gap_enabled_checkbox.setChecked(self.params['gap_enabled'])
        self.gap_enabled_checkbox.toggled.connect(self.on_gap_enabled_toggled)
        contour_layout.addRow(self.gap_enabled_checkbox)
        
        contour_group.setLayout(contour_layout)
        layout.addWidget(contour_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Contour Processing")
    
    def create_export_tab(self):
        """Create export parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Export parameters
        export_group = QGroupBox("Export Settings")
        export_layout = QFormLayout()
        
        # MM per pixel
        self.mm_per_px_spin = QDoubleSpinBox()
        self.mm_per_px_spin.setRange(0.01, 10.0)
        self.mm_per_px_spin.setValue(self.params['mm_per_px'])
        self.mm_per_px_spin.setDecimals(3)
        self.mm_per_px_spin.valueChanged.connect(self.on_export_scale_change)
        export_layout.addRow("MM per Pixel:", self.mm_per_px_spin)
        
        # Extrude height
        self.extrude_height_spin = QDoubleSpinBox()
        self.extrude_height_spin.setRange(0.1, 100.0)
        self.extrude_height_spin.setValue(self.params['extrude_height'])
        self.extrude_height_spin.setDecimals(1)
        export_layout.addRow("Extrude Height (mm):", self.extrude_height_spin)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # Export buttons
        button_layout = QVBoxLayout()
        
        # Export DXF button
        export_dxf_button = QPushButton("Export DXF")
        export_dxf_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        export_dxf_button.clicked.connect(self.export_dxf_enhanced)
        button_layout.addWidget(export_dxf_button)
        
        # Export STEP button
        export_step_button = QPushButton("Export STEP (3D)")
        export_step_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        export_step_button.clicked.connect(self.export_dxf_enhanced)
        button_layout.addWidget(export_step_button)
        
        # Export STL button
        export_stl_button = QPushButton("Export STL (3D)")
        export_stl_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        export_stl_button.clicked.connect(self.export_dxf_enhanced)
        button_layout.addWidget(export_stl_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Export")
    
    def create_tools_toolbar(self):
        """Create tools toolbar"""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar.setMaximumHeight(60)
        
        layout = QHBoxLayout()
        layout.setSpacing(5)
        
        # Tool buttons
        tools = [
            ("View", "view", "👁️"),
            ("Paint", "paint", "🖌️"),
            ("Eraser", "eraser", "🧹"),
            ("Line", "line", "📏"),
            ("Rectangle", "rectangle", "⬜"),
            ("Circle", "circle", "⭕"),
            ("Area Process", "area_process", "🎯"),
            ("Merge Edges", "merge_edges", "🔗"),
        ]
        
        for tool_name, tool_mode, icon in tools:
            button = QPushButton(f"{icon} {tool_name}")
            button.setCheckable(True)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 2px solid #ddd;
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background-color: #4CAF50;
                    color: white;
                    border-color: #45a049;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:checked:hover {
                    background-color: #45a049;
                }
            """)
            button.clicked.connect(lambda checked, mode=tool_mode: self.set_edit_mode(mode))
            layout.addWidget(button)
        
        # Undo/Redo buttons
        undo_button = QPushButton("↶ Undo")
        undo_button.clicked.connect(self.undo_action)
        layout.addWidget(undo_button)
        
        redo_button = QPushButton("↷ Redo")
        redo_button.clicked.connect(self.redo_action)
        layout.addWidget(redo_button)
        
        # Settings lock button
        self.settings_lock_button = QPushButton("🔒 Lock Settings")
        self.settings_lock_button.setCheckable(True)
        self.settings_lock_button.clicked.connect(self.toggle_settings_lock)
        layout.addWidget(self.settings_lock_button)
        
        layout.addStretch()
        toolbar.setLayout(layout)
        return toolbar
    
    def create_export_frame(self):
        """Create export frame"""
        group = QGroupBox("Export")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FF9800;
            }
        """)
        layout = QVBoxLayout()
        
        # Output size display
        self.output_size_label = QLabel("Output size will be calculated")
        self.output_size_label.setStyleSheet("color: #666;")
        layout.addWidget(self.output_size_label)
        
        group.setLayout(layout)
        return group
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        load_action = QAction("Load Image", self)
        load_action.triggered.connect(self.load_image)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        save_project_action = QAction("Save Project", self)
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)
        
        load_project_action = QAction("Load Project", self)
        load_project_action.triggered.connect(self.load_project)
        file_menu.addAction(load_project_action)
        
        # Performance menu
        performance_menu = menubar.addMenu("Performance")
        
        perf_settings_action = QAction("Performance Settings", self)
        perf_settings_action.triggered.connect(self.open_performance_settings)
        performance_menu.addAction(perf_settings_action)
        
        perf_stats_action = QAction("Show Performance Stats", self)
        perf_stats_action.triggered.connect(self.show_performance_stats)
        performance_menu.addAction(perf_stats_action)
        
        benchmark_action = QAction("Run Benchmark", self)
        benchmark_action.triggered.connect(self.benchmark_performance)
        performance_menu.addAction(benchmark_action)
        
        performance_menu.addSeparator()
        
        toggle_perf_action = QAction("Toggle Performance Mode", self)
        toggle_perf_action.triggered.connect(self.toggle_performance_mode)
        performance_menu.addAction(toggle_perf_action)
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Enhanced ImageEmboss ready - Performance optimizations enabled")
    
    def open_performance_settings(self):
        """Open performance settings dialog"""
        dialog = PerformanceSettingsDialog(self, self.performance_config.__dict__)
        dialog.settings_changed.connect(self.on_performance_settings_changed)
        dialog.exec()
    
    def on_performance_settings_changed(self, settings):
        """Handle performance settings changes"""
        # Update performance configuration
        self.performance_config = ProcessingConfig(**settings)
        
        # Update parameters
        self.params.update(settings)
        
        # Update UI
        self.update_performance_status()
        
        # Reinitialize processors with new config
        self.enhanced_image_processor = EnhancedImageProcessor(self.performance_config)
        
        self.status_bar.showMessage("Performance settings updated")
    
    def update_performance_status(self):
        """Update performance status display"""
        if self.params.get('use_parallel_processing', True):
            mode = "Maximum Performance"
            color = "#4CAF50"
        else:
            mode = "Compatibility Mode"
            color = "#FF9800"
        
        self.performance_mode_label.setText(f"Mode: {mode}")
        self.performance_mode_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        self.cpu_usage_label.setText(f"CPU Cores: {self.params.get('max_workers', mp.cpu_count())}")
    
    def on_param_change(self):
        """Handle parameter changes"""
        # Update parameters from sliders
        self.update_parameters_from_sliders()
        
        # Set preset to Custom
        self.preset_combo.setCurrentText("Custom")
        
        # Update preview if settings are not locked
        if not self.settings_locked:
            self.update_preview_enhanced()
    
    def update_parameters_from_sliders(self):
        """Update parameters from slider values"""
        self.params['bilateral_d'] = self.bilateral_d_slider.value()
        self.params['bilateral_c'] = self.bilateral_c_slider.value()
        self.params['bilateral_sigma'] = self.bilateral_sigma_slider.value()
        self.params['blur_kernel'] = self.blur_kernel_slider.value()
        self.params['blur_sigma'] = self.blur_sigma_slider.value() / 10.0
        self.params['canny_low'] = self.canny_low_slider.value()
        self.params['canny_high'] = self.canny_high_slider.value()
        self.params['thicken_kernel'] = self.thicken_kernel_slider.value()
        self.params['invert'] = self.invert_checkbox.isChecked()
        self.params['largest_n'] = self.largest_n_slider.value()
        self.params['simplify_pct'] = self.simplify_pct_slider.value() / 100.0
        self.params['gap_threshold'] = self.gap_threshold_slider.value()
        self.params['gap_enabled'] = self.gap_enabled_checkbox.isChecked()
        self.params['mm_per_px'] = self.mm_per_px_spin.value()
        self.params['extrude_height'] = self.extrude_height_spin.value()
    
    def on_preset_change(self, preset_name):
        """Handle preset change"""
        if preset_name in self.preset_configs:
            preset = self.preset_configs[preset_name]
            
            # Update sliders
            self.bilateral_d_slider.setValue(preset.get('bilateral_d', 9))
            self.bilateral_c_slider.setValue(preset.get('bilateral_c', 75))
            self.bilateral_sigma_slider.setValue(preset.get('bilateral_sigma', 75))
            self.blur_kernel_slider.setValue(preset.get('blur_kernel', 5))
            self.blur_sigma_slider.setValue(int(preset.get('blur_sigma', 1.0) * 10))
            self.canny_low_slider.setValue(preset.get('canny_low', 50))
            self.canny_high_slider.setValue(preset.get('canny_high', 150))
            self.thicken_kernel_slider.setValue(preset.get('thicken_kernel', 3))
            self.invert_checkbox.setChecked(preset.get('invert', False))
            self.largest_n_slider.setValue(preset.get('largest_n', 3))
            self.simplify_pct_slider.setValue(int(preset.get('simplify_pct', 0.6) * 100))
            self.gap_threshold_slider.setValue(int(preset.get('gap_threshold', 5.0)))
            
            # Update parameters
            self.update_parameters_from_sliders()
            
            # Update preview
            if not self.settings_locked:
                self.update_preview_enhanced()
    
    def on_gap_enabled_toggled(self, enabled):
        """Handle gap enabled toggle"""
        self.gap_threshold_slider.setEnabled(enabled)
        self.params['gap_enabled'] = enabled
        if not self.settings_locked:
            self.update_preview_enhanced()
    
    def on_export_scale_change(self):
        """Handle export scale change"""
        self.params['mm_per_px'] = self.mm_per_px_spin.value()
        self.update_output_size_display()
    
    def update_output_size_display(self):
        """Update output size display"""
        if self.original_image is not None:
            h, w = self.original_image.shape[:2]
            mm_w = w * self.params['mm_per_px']
            mm_h = h * self.params['mm_per_px']
            self.output_size_label.setText(f"Output size: {mm_w:.1f} x {mm_h:.1f} mm")
    
    def toggle_settings_lock(self):
        """Toggle settings lock for area processing"""
        self.settings_locked = not self.settings_locked
        self.update_lock_button_state()
    
    def update_lock_button_state(self):
        """Update lock button state"""
        if self.settings_locked:
            self.settings_lock_button.setText("🔓 Unlock Settings")
            self.settings_lock_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
        else:
            self.settings_lock_button.setText("🔒 Lock Settings")
            self.settings_lock_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
    
    def set_edit_mode(self, mode):
        """Set edit mode"""
        self.edit_mode = mode
        # Update button states
        for button in self.findChildren(QPushButton):
            if button.isCheckable():
                button.setChecked(False)
        
        # Check the current button
        sender = self.sender()
        if sender:
            sender.setChecked(True)
        
        # Update cursor
        if hasattr(self, 'dxf_view'):
            self.dxf_view.set_edit_mode(mode)
    
    def showEvent(self, event):
        """Handle show event"""
        super().showEvent(event)
        self.force_maximize()
    
    def force_maximize(self):
        """Force window to maximize"""
        self.showMaximized()
        QTimer.singleShot(100, self.fit_images_to_view)
    
    def fit_images_to_view(self):
        """Fit images to view"""
        if hasattr(self, 'original_view') and self.original_view.scene():
            self.original_view.fitInView(self.original_view.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        if hasattr(self, 'dxf_view') and self.dxf_view.scene():
            self.dxf_view.fitInView(self.dxf_view.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
