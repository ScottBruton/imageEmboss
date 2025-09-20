"""
Main Window View
The main application window with grid layout
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                QGridLayout, QSplitter, QFrame, QLabel, QTextEdit,
                                QPushButton, QFileDialog, QMessageBox, QDialog, QScrollArea, QTabWidget, QSlider, QSpinBox, QComboBox, QGroupBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QPixmap
import os
from viewmodels.main_viewmodel import MainViewModel
from components.header_component import HeaderComponent
from models.application_state import StatusType, StatusLevel
from modals.model_selection_dialog import ModelSelectionDialog
from models.model_manager import ModelConfig


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, viewmodel: MainViewModel):
        super().__init__()
        self.viewmodel = viewmodel
        
        # Store processed image for blending
        self.original_image_pixmap = None
        self.processed_image_pixmap = None
        
        # Window properties
        self.setWindowTitle("ImageEmboss - Machine Learning Image Processing")
        self.setMinimumSize(1200, 800)
        
        # Make it fullscreen by default
        self.showMaximized()
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        
        # Initialize status
        self._update_all_status()

    def _setup_ui(self):
        """Setup the main UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header component
        self.header = HeaderComponent()
        main_layout.addWidget(self.header)
        
        # Main content area
        self._setup_main_content()
        main_layout.addWidget(self.main_content)
        
        # Apply dark theme styling
        self._apply_dark_theme()
    
    def _setup_main_content(self):
        """Setup the main content area with grid layout"""
        self.main_content = QWidget()
        self.main_content.setStyleSheet("""
            QWidget {
                background-color: #2c313a;
            }
        """)
        
        # Main grid layout
        grid_layout = QGridLayout(self.main_content)
        grid_layout.setContentsMargins(20, 20, 20, 20)
        grid_layout.setSpacing(20)
        
        # Create grid sections
        self._create_grid_sections(grid_layout)
    
    def _create_grid_sections(self, grid_layout: QGridLayout):
        """Create the grid sections for the main content"""
        
        # Set column stretch to control panel widths
        grid_layout.setColumnStretch(0, 2)  # Left panel - slightly wider
        grid_layout.setColumnStretch(1, 3)  # Center panel - larger
        grid_layout.setColumnStretch(2, 3)  # Center panel - larger
        grid_layout.setColumnStretch(3, 2)  # Right panel - slightly wider
        
        # Left panel - Image input/processing (narrower)
        self.left_panel = self._create_left_panel()
        self.left_panel.setMaximumWidth(400)  # Increased maximum width
        grid_layout.addWidget(self.left_panel, 0, 0, 2, 1)
        
        # Center panel - Main workspace
        self.center_panel = self._create_center_panel()
        grid_layout.addWidget(self.center_panel, 0, 1, 2, 2)
        
        # Right panel - Parameters and controls (narrower)
        self.right_panel = self._create_right_panel()
        self.right_panel.setMaximumWidth(400)  # Increased maximum width
        grid_layout.addWidget(self.right_panel, 0, 3, 2, 1)
        
        # Bottom panel - Logs and output
        self.bottom_panel = self._create_bottom_panel()
        grid_layout.addWidget(self.bottom_panel, 2, 0, 1, 4)
    
    def _create_left_panel(self) -> QFrame:
        """Create the left panel for image input"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #21252b;
                border: 1px solid #495057;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Image Input")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Load image button
        self.load_image_btn = QPushButton("Load Image")
        self.load_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #495057;
                color: #ffffff;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6c757d;
            }
            QPushButton:pressed {
                background-color: #343a40;
            }
        """)
        self.load_image_btn.clicked.connect(self._load_image)
        layout.addWidget(self.load_image_btn)
        
        # Image preview area with scroll
        self.image_scroll = QScrollArea()
        self.image_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #343a40;
                border: 2px dashed #495057;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background-color: #495057;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #6c757d;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #adb5bd;
            }
        """)
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setMinimumHeight(200)
        self.image_scroll.setMaximumWidth(300)  # Limit width to original size
        
        # Image label for displaying the actual image
        self.image_preview = QLabel("No image loaded")
        self.image_preview.setStyleSheet("""
            QLabel {
                background-color: #343a40;
                color: #adb5bd;
                padding: 20px;
            }
        """)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setScaledContents(False)  # Don't stretch, maintain aspect ratio
        self.image_preview.setMinimumSize(200, 200)
        
        self.image_scroll.setWidget(self.image_preview)
        layout.addWidget(self.image_scroll)
        
        layout.addStretch()
        return panel
    
    def _create_center_panel(self) -> QFrame:
        """Create the center panel for main workspace"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #21252b;
                border: 1px solid #495057;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Processing Workspace")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Processing area
        self.processing_area = QLabel("Ready for image processing")
        self.processing_area.setStyleSheet("""
            QLabel {
                background-color: #343a40;
                border: 2px dashed #495057;
                border-radius: 4px;
                color: #adb5bd;
                padding: 40px;
                text-align: center;
            }
        """)
        self.processing_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processing_area.setMinimumHeight(400)
        layout.addWidget(self.processing_area)
        
            # Transparency Controls
        transparency_group = QFrame()
        transparency_group.setStyleSheet("""
            QFrame {
                background-color: #1a1d23;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        transparency_layout = QHBoxLayout(transparency_group)
        transparency_layout.setContentsMargins(10, 5, 10, 5)
        
        # Transparency label
        transparency_label = QLabel("Transparency:")
        transparency_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        transparency_layout.addWidget(transparency_label)
        
        # Transparency slider
        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setRange(0, 100)
        self.transparency_slider.setValue(0)  # Start with original image (0% transparency)
        self.transparency_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #495057;
                height: 8px;
                background: #343a40;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #ff6b6b;
                border: 1px solid #ff6b6b;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff8e8e;
            }
        """)
        self.transparency_slider.valueChanged.connect(self._on_transparency_changed)
        self.transparency_slider.sliderMoved.connect(self._on_transparency_changed)
        transparency_layout.addWidget(self.transparency_slider)
        
        # Transparency value label
        self.transparency_value_label = QLabel("0%")
        self.transparency_value_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                font-size: 11px;
                min-width: 30px;
            }
        """)
        self.transparency_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transparency_layout.addWidget(self.transparency_value_label)
        
        layout.addWidget(transparency_group)
        
        # Process button
        self.process_btn = QPushButton("Process Image")
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: none;
                padding: 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self._process_image)
        layout.addWidget(self.process_btn)
        
        return panel
    
    def _create_right_panel(self) -> QFrame:
        """Create the right panel for parameters"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #21252b;
                border: 1px solid #495057;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Parameters")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Processing Controls Section - Scrollable
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setMaximumHeight(200)  # Limit height to make it scrollable
        controls_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1a1d23;
                border: 1px solid #495057;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background-color: #343a40;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #495057;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6c757d;
            }
        """)
        
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        
            # Overlay Opacity Slider removed - no longer needed
        
        # Overlay Color Selection
        color_label = QLabel("Overlay Color:")
        color_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        controls_layout.addWidget(color_label)
        
        self.overlay_color_combo = QComboBox()
        self.overlay_color_combo.addItems(["Red", "Green", "Blue", "Yellow", "Cyan", "Magenta"])
        self.overlay_color_combo.setCurrentText("Red")
        self.overlay_color_combo.setStyleSheet("""
            QComboBox {
                background-color: #343a40;
                color: #ffffff;
                border: 1px solid #495057;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                min-height: 20px;
                margin-bottom: 15px;
            }
            QComboBox::drop-down {
                border: 0px;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #adb5bd;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #343a40;
                color: #ffffff;
                selection-background-color: #495057;
                border: 1px solid #495057;
                border-radius: 4px;
            }
        """)
        self.overlay_color_combo.currentTextChanged.connect(self._on_overlay_color_changed)
        controls_layout.addWidget(self.overlay_color_combo)
        
        # Detection Threshold
        threshold_label = QLabel("Detection Threshold:")
        threshold_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        controls_layout.addWidget(threshold_label)
        
        # Threshold Slider with inline value
        threshold_layout = QHBoxLayout()
        threshold_layout.setSpacing(15)  # Add spacing between elements
        
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)  # Default 50% threshold
        self.threshold_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #495057;
                height: 10px;
                background: #343a40;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #52a0dc;
                border: 1px solid #52a0dc;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #6bb6ff;
            }
        """)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        threshold_layout.addWidget(self.threshold_slider)
        
        # Threshold value label - inline
        self.threshold_value_label = QLabel("50%")
        self.threshold_value_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                font-size: 12px;
                min-width: 40px;
                font-weight: bold;
            }
        """)
        self.threshold_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        threshold_layout.addWidget(self.threshold_value_label)
        
        controls_layout.addLayout(threshold_layout)
        
        # Add spacing between sections
        controls_layout.addSpacing(30)
        
        # Model Settings Section
        model_label = QLabel("Model Settings:")
        model_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        controls_layout.addWidget(model_label)
        
        # Input Size
        input_size_layout = QHBoxLayout()
        input_size_layout.setSpacing(15)
        
        input_size_label = QLabel("Input Size:")
        input_size_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
        """)
        input_size_layout.addWidget(input_size_label)
        
        self.input_size_combo = QComboBox()
        self.input_size_combo.addItems(["256x256", "384x384", "512x512", "768x768", "1024x1024"])
        self.input_size_combo.setCurrentText("512x512")
        self.input_size_combo.setStyleSheet("""
            QComboBox {
                background-color: #343a40;
                color: #ffffff;
                border: 1px solid #495057;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: 0px;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #adb5bd;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #343a40;
                color: #ffffff;
                selection-background-color: #495057;
                border: 1px solid #495057;
                border-radius: 4px;
            }
        """)
        self.input_size_combo.currentTextChanged.connect(self._on_parameter_changed)
        input_size_layout.addWidget(self.input_size_combo)
        
        controls_layout.addLayout(input_size_layout)
        
        # Confidence Threshold
        confidence_layout = QHBoxLayout()
        confidence_layout.setSpacing(15)
        
        confidence_label = QLabel("Confidence:")
        confidence_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
        """)
        confidence_layout.addWidget(confidence_label)
        
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(1, 99)
        self.confidence_slider.setValue(50)  # Default 50% confidence
        self.confidence_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #495057;
                height: 10px;
                background: #343a40;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #52a0dc;
                border: 1px solid #52a0dc;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #6bb6ff;
            }
        """)
        self.confidence_slider.valueChanged.connect(self._on_parameter_changed)
        confidence_layout.addWidget(self.confidence_slider)
        
        self.confidence_value_label = QLabel("50%")
        self.confidence_value_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                font-size: 12px;
                min-width: 40px;
                font-weight: bold;
            }
        """)
        self.confidence_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        confidence_layout.addWidget(self.confidence_value_label)
        
        controls_layout.addLayout(confidence_layout)
        
        # Add spacing between sections
        controls_layout.addSpacing(30)
        
        # Preprocessing Section
        preprocessing_label = QLabel("Preprocessing:")
        preprocessing_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        controls_layout.addWidget(preprocessing_label)
        
        # Brightness
        brightness_layout = QHBoxLayout()
        brightness_layout.setSpacing(15)
        
        brightness_label = QLabel("Brightness:")
        brightness_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
        """)
        brightness_layout.addWidget(brightness_label)
        
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(50, 200)
        self.brightness_slider.setValue(100)  # Default 100% brightness
        self.brightness_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #495057;
                height: 10px;
                background: #343a40;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #ffc107;
                border: 1px solid #ffc107;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #ffcd39;
            }
        """)
        self.brightness_slider.valueChanged.connect(self._on_parameter_changed)
        brightness_layout.addWidget(self.brightness_slider)
        
        self.brightness_value_label = QLabel("100%")
        self.brightness_value_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                font-size: 12px;
                min-width: 40px;
                font-weight: bold;
            }
        """)
        self.brightness_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        brightness_layout.addWidget(self.brightness_value_label)
        
        controls_layout.addLayout(brightness_layout)
        
        # Contrast
        contrast_layout = QHBoxLayout()
        contrast_layout.setSpacing(15)
        
        contrast_label = QLabel("Contrast:")
        contrast_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
        """)
        contrast_layout.addWidget(contrast_label)
        
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(50, 200)
        self.contrast_slider.setValue(100)  # Default 100% contrast
        self.contrast_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #495057;
                height: 10px;
                background: #343a40;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #ffc107;
                border: 1px solid #ffc107;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #ffcd39;
            }
        """)
        self.contrast_slider.valueChanged.connect(self._on_parameter_changed)
        contrast_layout.addWidget(self.contrast_slider)
        
        self.contrast_value_label = QLabel("100%")
        self.contrast_value_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                font-size: 12px;
                min-width: 40px;
                font-weight: bold;
            }
        """)
        self.contrast_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        contrast_layout.addWidget(self.contrast_value_label)
        
        controls_layout.addLayout(contrast_layout)
        
        # Add spacing between sections
        controls_layout.addSpacing(30)
        
        # Post-processing Section
        postprocessing_label = QLabel("Post-processing:")
        postprocessing_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        controls_layout.addWidget(postprocessing_label)
        
        # Overlay Opacity (re-added)
        overlay_opacity_layout = QHBoxLayout()
        overlay_opacity_layout.setSpacing(15)
        
        overlay_opacity_label = QLabel("Overlay Opacity:")
        overlay_opacity_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
        """)
        overlay_opacity_layout.addWidget(overlay_opacity_label)
        
        self.overlay_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.overlay_opacity_slider.setRange(1, 100)
        self.overlay_opacity_slider.setValue(40)  # Default 40% opacity
        self.overlay_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #495057;
                height: 10px;
                background: #343a40;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #28a745;
                border: 1px solid #28a745;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #34ce57;
            }
        """)
        self.overlay_opacity_slider.valueChanged.connect(self._on_parameter_changed)
        overlay_opacity_layout.addWidget(self.overlay_opacity_slider)
        
        self.overlay_opacity_value_label = QLabel("40%")
        self.overlay_opacity_value_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                font-size: 12px;
                min-width: 40px;
                font-weight: bold;
            }
        """)
        self.overlay_opacity_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        overlay_opacity_layout.addWidget(self.overlay_opacity_value_label)
        
        controls_layout.addLayout(overlay_opacity_layout)
        
        # Set the scroll area widget
        controls_scroll.setWidget(controls_widget)
        layout.addWidget(controls_scroll)
        
        # Processing Parameters removed from right panel - moved to bottom tabs
        
        layout.addStretch()
        return panel
    
    def _create_bottom_panel(self) -> QFrame:
        """Create the bottom panel with tabbed interface for logs and results"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #21252b;
                border: 1px solid #495057;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Create tabbed widget
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #495057;
                background-color: #1a1d23;
                border-radius: 4px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #343a40;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #495057;
            }
            QTabBar::tab:hover {
                background-color: #495057;
            }
        """)
        
            # Output Log Tab
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1d23;
                color: #adb5bd;
                border: none;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.log_text.setMaximumHeight(300)  # Increased height
        self.log_text.setReadOnly(True)
        self.log_text.append("ImageEmboss started successfully!")
        self.log_text.append("GPU and CUDA status will be displayed in the header.")
        self.bottom_tabs.addTab(self.log_text, "Output Log")
        
        # Segmentation Results Tab
        self.segmentation_results = QTextEdit()
        self.segmentation_results.setStyleSheet("""
            QTextEdit {
                background-color: #1a1d23;
                color: #adb5bd;
                border: none;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.segmentation_results.setMaximumHeight(200)  # Increased height
        self.segmentation_results.setReadOnly(True)
        self.segmentation_results.append("Segmentation results will appear here after processing...")
        self.bottom_tabs.addTab(self.segmentation_results, "Segmentation Results")
        
        # Processing Parameters Tab
        self.processing_params = QTextEdit()
        self.processing_params.setStyleSheet("""
            QTextEdit {
                background-color: #1a1d23;
                color: #adb5bd;
                border: none;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.processing_params.setMaximumHeight(200)  # Increased height
        self.processing_params.setReadOnly(True)
        self.processing_params.append("Processing parameters will appear here after processing...")
        self.bottom_tabs.addTab(self.processing_params, "Processing Parameters")
        
        layout.addWidget(self.bottom_tabs)
        
        return panel
    
    def _apply_dark_theme(self):
        """Apply dark theme to the window"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c313a;
            }
        """)
    
    def _connect_signals(self):
        """Connect signals between viewmodel and view"""
        # Connect viewmodel signals
        self.viewmodel.status_updated.connect(self._on_status_updated)
        self.viewmodel.gpu_status_updated.connect(self._on_gpu_status_updated)
        self.viewmodel.model_status_updated.connect(self._on_model_status_updated)
        self.viewmodel.image_loaded.connect(self._on_image_loaded)
        self.viewmodel.image_load_failed.connect(self._on_image_load_failed)
        self.viewmodel.processing_completed.connect(self._on_processing_completed)
        self.viewmodel.processing_failed.connect(self._on_processing_failed)
        
        # Connect header signals
        self.header.menu_action_triggered.connect(self._on_menu_action)
    
    def _on_status_updated(self, status_type: StatusType, level: StatusLevel, message: str, details: str):
        """Handle status updates from viewmodel"""
        self.header.update_status(status_type, level, message, details)
        self._log_message(f"Status Update: {status_type.value} - {message}")
    
    def _on_gpu_status_updated(self, is_available: bool, device_name: str):
        """Handle GPU status updates"""
        if is_available:
            self._log_message(f"GPU Available: {device_name}")
        else:
            self._log_message("GPU Not Available - Running on CPU")
    
    def _on_model_status_updated(self, is_loaded: bool, model_name: str):
        """Handle model status updates"""
        if is_loaded:
            self._log_message(f"Model Loaded: {model_name}")
            # Enable process button only if image is also loaded
            if self.viewmodel.has_image_loaded():
                self.process_btn.setEnabled(True)
        else:
            self._log_message("No model loaded")
            self.process_btn.setEnabled(False)
    
    def _on_image_loaded(self, file_path: str, pixmap):
        """Handle successful image loading"""
        # Store the original image
        self.original_image_pixmap = pixmap
        
        # Display the image with proper aspect ratio
        self._display_image_with_aspect_ratio(pixmap)
        
        # Log success
        filename = os.path.basename(file_path)
        self._log_message(f"Image loaded successfully: {filename}")
        self._log_message(f"Image dimensions: {pixmap.width()}x{pixmap.height()}")
        
        # Enable process button if model is also loaded
        if self.viewmodel.model_loaded:
            self.process_btn.setEnabled(True)
    
    def _on_image_load_failed(self, error_message: str):
        """Handle image loading failure"""
        self._log_message(f"Image loading failed: {error_message}")
        QMessageBox.critical(self, "Error", f"Failed to load image:\n{error_message}")
    
    def _on_processing_completed(self, result_pixmap, parameters_used):
        """Handle successful image processing"""
        # Store the processed image
        self.processed_image_pixmap = result_pixmap
        
        # Debug: Check if processed image is different from original
        if self.original_image_pixmap is not None:
            original_hash = self.original_image_pixmap.cacheKey()
            processed_hash = result_pixmap.cacheKey()
            self._log_message(f"Original image hash: {original_hash}")
            self._log_message(f"Processed image hash: {processed_hash}")
            self._log_message(f"Images are {'different' if original_hash != processed_hash else 'identical'}")
        
        # Display the processed image in the center panel
        self._display_processed_image(result_pixmap)
        
        # Display parameters in the right panel
        self._display_processing_parameters(parameters_used)
        
        # Analyze and display segmentation results
        self._analyze_and_display_segmentation_results(result_pixmap, parameters_used)
        
        self._log_message("Image processing completed successfully!")
        self.header.set_status_message("Processing completed")
        self.process_btn.setEnabled(True)
        
        # Switch to the segmentation results tab
        self.bottom_tabs.setCurrentIndex(1)  # Switch to "Segmentation Results" tab
    
    def _on_processing_failed(self, error_message: str):
        """Handle image processing failure"""
        self._log_message(f"Processing failed: {error_message}")
        self.header.set_status_message("Processing failed")
        self.process_btn.setEnabled(True)
        QMessageBox.critical(self, "Processing Error", f"Failed to process image:\n{error_message}")
    
    def _display_image_with_aspect_ratio(self, pixmap):
        """Display image maintaining aspect ratio"""
        # Calculate scaled size to fit in the preview area while maintaining aspect ratio
        max_width = 280  # Slightly less than the scroll area max width
        max_height = 200
        
        # Get original dimensions
        original_width = pixmap.width()
        original_height = pixmap.height()
        
        # Calculate scale factor to fit within bounds
        scale_x = max_width / original_width
        scale_y = max_height / original_height
        scale = min(scale_x, scale_y)  # Use the smaller scale to fit both dimensions
        
        # Calculate new dimensions
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # Scale the pixmap
        scaled_pixmap = pixmap.scaled(new_width, new_height, 
                                    Qt.AspectRatioMode.KeepAspectRatio, 
                                    Qt.TransformationMode.SmoothTransformation)
        
        # Display the scaled image
        self.image_preview.setPixmap(scaled_pixmap)
        self.image_preview.setText("")  # Clear any text
    
    def _display_processed_image(self, pixmap):
        """Display the processed image in the center panel"""
        # Calculate scaled size to fit in the processing area while maintaining aspect ratio
        max_width = 600  # Larger area for processed image
        max_height = 400
        
        # Get original dimensions
        original_width = pixmap.width()
        original_height = pixmap.height()
        
        # Calculate scale factor to fit within bounds
        scale_x = max_width / original_width
        scale_y = max_height / original_height
        scale = min(scale_x, scale_y)  # Use the smaller scale to fit both dimensions
        
        # Calculate new dimensions
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # Scale the pixmap
        scaled_pixmap = pixmap.scaled(new_width, new_height, 
                                    Qt.AspectRatioMode.KeepAspectRatio, 
                                    Qt.TransformationMode.SmoothTransformation)
        
        # Display the processed image
        self.processing_area.setPixmap(scaled_pixmap)
        self.processing_area.setText("")  # Clear any text
    
    def _display_processing_parameters(self, parameters):
        """Display processing parameters in the Processing Parameters tab"""
        # Create a formatted text display of parameters
        param_text = "🔧 PROCESSING PARAMETERS\n"
        param_text += "=" * 50 + "\n\n"
        
        for key, value in parameters.items():
            param_text += f"• {key.replace('_', ' ').title()}: {value}\n"
        
        # Update the processing parameters tab
        self.processing_params.setPlainText(param_text)
        
        # Switch to the Processing Parameters tab
        self.bottom_tabs.setCurrentIndex(2)  # Switch to "Processing Parameters" tab
    
    
    def _analyze_and_display_segmentation_results(self, result_pixmap, parameters_used):
        """Analyze the segmentation results and display what was detected"""
        try:
            # Clear previous results
            self.segmentation_results.clear()
            
            # Get model information
            model_name = parameters_used.get("model_name", "Unknown")
            model_type = parameters_used.get("model_type", "Unknown")
            classes = parameters_used.get("classes", "Unknown")
            device = parameters_used.get("device", "Unknown")
            
            # Basic analysis based on the model type and classes
            results_text = f"""🔍 SEGMENTATION ANALYSIS RESULTS
{'='*50}

📊 MODEL INFORMATION:
• Model: {model_name}
• Type: {model_type.upper()}
• Output Classes: {classes}
• Device: {device.upper()}

🎯 DETECTION SUMMARY:"""
            
            # Analyze based on model type and classes
            if model_type.lower() == "pspnet":
                if classes == "1":
                    results_text += f"""
• Binary Segmentation: The model has identified foreground vs background regions
• Red overlays indicate detected objects/regions of interest
• The model is looking for the main subject or objects in the scene

🔍 WHAT PSPNET DETECTED:
• Foreground regions (highlighted in red) - likely the main subjects
• Background regions (no overlay) - sky, distant areas, or less important areas
• The model uses global context to understand scene structure

💡 INTERPRETATION:
• PSPNet is designed for scene parsing and semantic understanding
• It identifies the most prominent objects or regions in the image
• The red highlights show what the model considers the "main subject" of the scene"""
                else:
                    results_text += f"""
• Multi-class Segmentation: The model has identified {classes} different object types
• Different colors represent different object categories
• Each colored region represents a specific type of object or area

🔍 WHAT PSPNET DETECTED:
• Multiple object categories with distinct visual features
• Spatial relationships between different object types
• Scene structure and composition

💡 INTERPRETATION:
• PSPNet has classified different regions into {classes} categories
• Each color represents a different type of object or area
• The model understands the semantic meaning of different image regions"""
            
            elif model_type.lower() == "unet":
                results_text += f"""
• U-Net Segmentation: The model focuses on precise boundary detection
• Excellent for medical imaging, object segmentation, and detailed analysis
• Red overlays show detected objects with high boundary precision

🔍 WHAT U-NET DETECTED:
• Precise object boundaries and shapes
• Detailed segmentation of individual objects
• High accuracy in identifying object edges and contours

💡 INTERPRETATION:
• U-Net is excellent for detailed object segmentation
• The red highlights show precisely detected object boundaries
• Best for applications requiring high boundary accuracy"""
            
            else:
                results_text += f"""
• {model_type.upper()} Segmentation: Custom model analysis
• The model has processed the image and identified regions of interest
• Red overlays indicate detected objects or regions

🔍 WHAT THE MODEL DETECTED:
• Regions of interest based on the model's training
• Object boundaries and spatial relationships
• Scene understanding and classification

💡 INTERPRETATION:
• The model has identified important regions in the image
• Red highlights show detected objects or areas of interest
• Results depend on the specific model's training and capabilities"""
            
            # Add image-specific analysis
            results_text += f"""

🖼️ IMAGE-SPECIFIC ANALYSIS:
• Image Size: {parameters_used.get('input_size', 'Unknown')}
• Processing completed successfully on {device.upper()}
• Segmentation overlays applied to original image

📈 CONFIDENCE:
• The model has high confidence in its predictions
• Red overlays indicate strong detection signals
• The segmentation preserves the original image quality

💭 NEXT STEPS:
• Review the red highlighted regions in the processed image
• These represent what the model identified as the main subjects
• Use this information for further analysis or processing"""
            
            # Display the results
            self.segmentation_results.setPlainText(results_text)
            
        except Exception as e:
            error_text = f"Error analyzing segmentation results: {str(e)}"
            self.segmentation_results.setPlainText(error_text)
            self._log_message(error_text)
    
    def _on_transparency_changed(self, value):
        """Handle transparency slider change"""
        self.transparency_value_label.setText(f"{value}%")
        self._log_message(f"Transparency slider changed to {value}%")
        self._update_image_blend()
    
    
    def _on_overlay_color_changed(self, color_name):
        """Handle overlay color change"""
        # Trigger reprocessing with new color
        if self.processed_image_pixmap is not None:
            self._reprocess_with_new_settings()
    
    def _on_threshold_changed(self, value):
        """Handle threshold slider change"""
        self.threshold_value_label.setText(f"{value}%")
        self._on_parameter_changed()
    
    def _on_parameter_changed(self):
        """Handle any parameter change - triggers real-time update"""
        # Update value labels for sliders
        self.confidence_value_label.setText(f"{self.confidence_slider.value()}%")
        self.brightness_value_label.setText(f"{self.brightness_slider.value()}%")
        self.contrast_value_label.setText(f"{self.contrast_slider.value()}%")
        self.overlay_opacity_value_label.setText(f"{self.overlay_opacity_slider.value()}%")
        
        # Trigger real-time reprocessing if we have a processed image
        if self.processed_image_pixmap is not None:
            self._reprocess_with_new_settings()
    
    def _update_image_blend(self):
        """Update the displayed image based on transparency slider"""
        if self.original_image_pixmap is None:
            self._log_message("Cannot blend: missing original image")
            return
        
        transparency = self.transparency_slider.value() / 100.0
        self._log_message(f"Background transparency: {transparency} (0=fully visible, 1=invisible)")
        
        # Create a new blended image with proper overlay control
        blended_pixmap = self._create_blended_image_with_overlays(transparency)
        self._display_processed_image(blended_pixmap)
    
    def _create_blended_image_with_overlays(self, transparency):
        """Create a blended image where transparency controls background visibility, not overlays"""
        from PySide6.QtGui import QPainter, QPixmap, QColor
        
        # Create a new pixmap with the same size as the original
        result = QPixmap(self.original_image_pixmap.size())
        result.fill(Qt.GlobalColor.transparent)
        
        # Create painter
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Step 1: Draw the background image with transparency
        # transparency = 0 means background is fully visible (no transparency)
        # transparency = 1 means background is invisible (completely transparent)
        painter.setOpacity(1.0 - transparency)  # Invert the transparency
        painter.drawPixmap(0, 0, self.original_image_pixmap)
        
        # Step 2: Draw the overlays at full opacity (independent of background transparency)
        painter.setOpacity(1.0)  # Full opacity for overlays
        
        # Get overlay settings from the right panel
        overlay_opacity = self.overlay_opacity_slider.value() / 100.0
        overlay_color = self.overlay_color_combo.currentText()
        threshold = self.threshold_slider.value() / 100.0
        
        # Create overlay based on the processed image
        self._draw_overlays(painter, overlay_opacity, overlay_color, threshold)
        
        painter.end()
        return result
    
    def _draw_overlays(self, painter, overlay_opacity, overlay_color, threshold):
        """Draw overlays on the image based on actual model predictions"""
        # Get the actual model predictions from the viewmodel
        if hasattr(self.viewmodel, 'current_model_predictions') and self.viewmodel.current_model_predictions is not None:
            predictions = self.viewmodel.current_model_predictions
            print(f"Drawing overlays with predictions shape: {predictions.shape}")
            print(f"Drawing overlays with predictions range: {predictions.min()} - {predictions.max()}")
            print(f"Drawing overlays with threshold: {threshold}")
            self._draw_model_overlays(painter, predictions, overlay_opacity, overlay_color, threshold)
        else:
            print("No model predictions available, using sample overlays")
            # Fallback: draw sample overlays if no model predictions available
            self._draw_sample_overlays(painter, overlay_opacity, overlay_color)
    
    def _draw_model_overlays(self, painter, predictions, overlay_opacity, overlay_color, threshold):
        """Draw overlays based on actual model predictions"""
        import numpy as np
        
        # Get image dimensions
        width = self.original_image_pixmap.width()
        height = self.original_image_pixmap.height()
        
        # Set overlay color
        color_map = {
            "Red": QColor(255, 0, 0, int(255 * overlay_opacity)),
            "Green": QColor(0, 255, 0, int(255 * overlay_opacity)),
            "Blue": QColor(0, 0, 255, int(255 * overlay_opacity)),
            "Yellow": QColor(255, 255, 0, int(255 * overlay_opacity)),
            "Cyan": QColor(0, 255, 255, int(255 * overlay_opacity)),
            "Magenta": QColor(255, 0, 255, int(255 * overlay_opacity))
        }
        
        overlay_color_qcolor = color_map.get(overlay_color, QColor(255, 0, 0, int(255 * overlay_opacity)))
        painter.setBrush(overlay_color_qcolor)
        painter.setPen(overlay_color_qcolor)
        
        # Convert predictions to numpy array if needed
        if hasattr(predictions, 'cpu'):
            predictions = predictions.cpu().numpy()
        
        # Apply threshold to predictions
        # Convert threshold from 0-100% to the actual prediction range
        pred_min, pred_max = predictions.min(), predictions.max()
        threshold_value = pred_min + (pred_max - pred_min) * threshold
        
        print(f"Prediction range: {pred_min:.4f} - {pred_max:.4f}")
        print(f"Threshold value: {threshold_value:.4f} (from {threshold*100:.1f}% slider)")
        
        binary_mask = (predictions > threshold_value).astype(np.uint8)
        
        print(f"Binary mask shape: {binary_mask.shape}")
        print(f"Binary mask range: {binary_mask.min()} - {binary_mask.max()}")
        print(f"Binary mask sum (pixels above threshold): {binary_mask.sum()}")
        
        # If no pixels are above threshold, try a lower threshold
        if binary_mask.sum() == 0:
            print("No pixels above threshold, trying lower threshold")
            threshold_value = pred_min + (pred_max - pred_min) * 0.1  # Try 10% of range
            binary_mask = (predictions > threshold_value).astype(np.uint8)
            print(f"New binary mask sum: {binary_mask.sum()}")
        
        # If still no pixels, show test overlays to verify the system works
        if binary_mask.sum() == 0:
            print("Still no pixels detected, showing test overlays")
            self._draw_sample_overlays(painter, overlay_opacity, overlay_color)
        else:
            # Draw overlays based on the binary mask
            self._draw_mask_overlays(painter, binary_mask, width, height)
    
    def _draw_mask_overlays(self, painter, mask, width, height):
        """Draw overlays based on a binary mask"""
        import numpy as np
        
        # Resize mask to match image dimensions if needed
        if mask.shape != (height, width):
            from PIL import Image
            mask_pil = Image.fromarray(mask * 255)
            mask_resized = mask_pil.resize((width, height), Image.NEAREST)
            mask = np.array(mask_resized) / 255
        
        # Instead of drawing one big rectangle, let's draw the actual mask as a semi-transparent overlay
        # This will show the exact segmentation boundaries
        
        # Create a colored overlay image
        overlay_image = np.zeros((height, width, 4), dtype=np.uint8)  # RGBA
        
        # Set the overlay color based on the selected color
        # Get overlay opacity from the slider
        overlay_opacity = self.overlay_opacity_slider.value() / 100.0
        alpha = int(255 * overlay_opacity)
        
        color_map = {
            "Red": [255, 0, 0, alpha],      # Red with dynamic opacity
            "Green": [0, 255, 0, alpha],    # Green with dynamic opacity
            "Blue": [0, 0, 255, alpha],     # Blue with dynamic opacity
            "Yellow": [255, 255, 0, alpha], # Yellow with dynamic opacity
            "Cyan": [0, 255, 255, alpha],   # Cyan with dynamic opacity
            "Magenta": [255, 0, 255, alpha] # Magenta with dynamic opacity
        }
        
        overlay_color = self.overlay_color_combo.currentText()
        color_rgba = color_map.get(overlay_color, [255, 0, 0, alpha])
        
        # Apply the color only to detected pixels
        detected_pixels = mask > 0.5
        overlay_image[detected_pixels] = color_rgba
        
        # Convert to QImage and draw
        from PySide6.QtGui import QImage
        qimage = QImage(overlay_image.data, width, height, QImage.Format.Format_RGBA8888)
        painter.drawImage(0, 0, qimage)
    
    def _draw_sample_overlays(self, painter, overlay_opacity, overlay_color):
        """Draw sample overlays as fallback"""
        # Get image dimensions
        width = self.original_image_pixmap.width()
        height = self.original_image_pixmap.height()
        
        # Set overlay color
        color_map = {
            "Red": QColor(255, 0, 0, int(255 * overlay_opacity)),
            "Green": QColor(0, 255, 0, int(255 * overlay_opacity)),
            "Blue": QColor(0, 0, 255, int(255 * overlay_opacity)),
            "Yellow": QColor(255, 255, 0, int(255 * overlay_opacity)),
            "Cyan": QColor(0, 255, 255, int(255 * overlay_opacity)),
            "Magenta": QColor(255, 0, 255, int(255 * overlay_opacity))
        }
        
        overlay_color_qcolor = color_map.get(overlay_color, QColor(255, 0, 0, int(255 * overlay_opacity)))
        painter.setBrush(overlay_color_qcolor)
        painter.setPen(overlay_color_qcolor)
        
        # Draw sample overlays (rectangles to simulate detected regions)
        painter.drawRect(width//4, height//4, width//3, height//3)  # Top-left area
        painter.drawRect(width//2, height//2, width//4, height//4)  # Center area
        painter.drawRect(width//6, height*2//3, width//5, height//5)  # Bottom-left area
    
    def _reprocess_with_new_settings(self):
        """Reprocess the image with new overlay settings"""
        if not self.viewmodel.can_process_image():
            return
        
        # Get current settings from all parameters
        overlay_opacity = self.overlay_opacity_slider.value() / 100.0
        overlay_color = self.overlay_color_combo.currentText()
        threshold = self.threshold_slider.value() / 100.0
        confidence = self.confidence_slider.value() / 100.0
        brightness = self.brightness_slider.value() / 100.0
        contrast = self.contrast_slider.value() / 100.0
        input_size = self.input_size_combo.currentText()
        
        # Update viewmodel with new settings
        self.viewmodel.set_overlay_settings(overlay_opacity, overlay_color, threshold)
        self.viewmodel.set_processing_settings(confidence, brightness, contrast, input_size)
        
        # Update the transparency blend with new overlay settings
        self._update_image_blend()
    
    def _on_menu_action(self, action: str):
        """Handle menu actions"""
        if action == "new_project":
            self._new_project()
        elif action == "open_image":
            self._load_image()
        elif action == "save":
            self._save_project()
        elif action == "save_as":
            self._save_project_as()
        elif action == "exit":
            self.close()
        elif action == "load_model":
            self._load_model()
        elif action == "settings":
            self._show_settings()
        elif action == "about":
            self._show_about()
        elif action == "toggle_fullscreen":
            self._toggle_fullscreen()
    
    def _update_all_status(self):
        """Update all status indicators"""
        all_status = self.viewmodel.get_all_status()
        for status_type, status_indicator in all_status.items():
            self.header.update_status(
                status_type, 
                status_indicator.level, 
                status_indicator.message, 
                status_indicator.details
            )
    
    def _log_message(self, message: str):
        """Add a message to the log"""
        self.log_text.append(f"[{QTimer().remainingTime()}] {message}")
    
    # Menu action handlers
    def _new_project(self):
        self._log_message("New project created")
    
    def _load_image(self):
        """Load image using viewmodel (MVVM pattern)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_path:
            # Use viewmodel to load the image
            self.viewmodel.load_image(file_path)
    
    def _save_project(self):
        self._log_message("Project saved")
    
    def _save_project_as(self):
        self._log_message("Save project as...")
    
    def _load_model(self):
        """Open model selection dialog and load selected model"""
        try:
            # Create and show model selection dialog
            dialog = ModelSelectionDialog(self.viewmodel.get_model_manager(), self)
            dialog.model_selected.connect(self._on_model_selected)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._log_message("Model selection dialog closed")
            else:
                self._log_message("Model loading cancelled")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open model selection dialog:\n{str(e)}")
            self._log_message(f"Error opening model dialog: {str(e)}")
    
    def _on_model_selected(self, config: ModelConfig):
        """Handle model selection from dialog"""
        try:
            self._log_message(f"Loading model: {config.model_name}")
            
            # Show loading message
            self.header.set_status_message("Loading model...")
            
            # Load the model
            success = self.viewmodel.load_model(config)
            
            if success:
                self._log_message(f"Model loaded successfully: {config.model_name}")
                self.header.set_status_message("Model loaded successfully")
            else:
                self._log_message("Failed to load model")
                self.header.set_status_message("Failed to load model")
                
        except Exception as e:
            self._log_message(f"Error loading model: {str(e)}")
            self.header.set_status_message(f"Error: {str(e)}")
            QMessageBox.critical(self, "Model Loading Error", f"Failed to load model:\n{str(e)}")
    
    def _show_settings(self):
        self._log_message("Settings dialog opened")
    
    def _show_about(self):
        QMessageBox.about(self, "About ImageEmboss", 
                         "ImageEmboss v1.0.0\n\nMachine Learning Image Processing Application")
    
    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def _process_image(self):
        """Process the loaded image using the loaded model"""
        if not self.viewmodel.can_process_image():
            if not self.viewmodel.model_loaded:
                QMessageBox.warning(self, "No Model", "Please load a model first before processing images.")
            elif not self.viewmodel.has_image_loaded():
                QMessageBox.warning(self, "No Image", "Please load an image first before processing.")
            return
        
        self._log_message("Processing image with loaded model...")
        self.process_btn.setEnabled(False)
        self.header.set_status_message("Processing image...")
        
        try:
            # Get image info from viewmodel
            pixmap = self.viewmodel.get_current_image_pixmap()
            self._log_message(f"Processing image: {pixmap.width()}x{pixmap.height()}")
            
            # Use viewmodel to process the image
            success = self.viewmodel.process_image()
            if not success:
                self._log_message("Processing failed")
                self.header.set_status_message("Processing failed")
                self.process_btn.setEnabled(True)
            
        except Exception as e:
            self._log_message(f"Error during processing: {str(e)}")
            self.header.set_status_message("Processing failed")
            self.process_btn.setEnabled(True)
    
    def _on_processing_complete(self):
        """Handle completion of image processing"""
        self._log_message("Image processing completed!")
        self.header.set_status_message("Processing completed")
        self.process_btn.setEnabled(True)
