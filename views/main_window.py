"""
Main Window View
The main application window with grid layout
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QGridLayout, QSplitter, QFrame, QLabel, QTextEdit,
                            QPushButton, QFileDialog, QMessageBox, QDialog, QScrollArea)
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
        
        # Parameters will be added here
        params_label = QLabel("Processing parameters will appear here")
        params_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                padding: 20px;
                text-align: center;
            }
        """)
        params_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(params_label)
        
        layout.addStretch()
        return panel
    
    def _create_bottom_panel(self) -> QFrame:
        """Create the bottom panel for logs"""
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
        title = QLabel("Output Log")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1d23;
                color: #adb5bd;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.append("ImageEmboss started successfully!")
        self.log_text.append("GPU and CUDA status will be displayed in the header.")
        layout.addWidget(self.log_text)
        
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
            
            # For now, simulate processing time
            # TODO: Implement actual model inference here using viewmodel.predict_image()
            QTimer.singleShot(2000, self._on_processing_complete)
            
        except Exception as e:
            self._log_message(f"Error during processing: {str(e)}")
            self.header.set_status_message("Processing failed")
            self.process_btn.setEnabled(True)
    
    def _on_processing_complete(self):
        """Handle completion of image processing"""
        self._log_message("Image processing completed!")
        self.header.set_status_message("Processing completed")
        self.process_btn.setEnabled(True)
