"""
Main Window View
The main application window with grid layout
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QGridLayout, QSplitter, QFrame, QLabel, QTextEdit,
                            QPushButton, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor
from viewmodels.main_viewmodel import MainViewModel
from components.header_component import HeaderComponent
from models.application_state import StatusType, StatusLevel


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
        
        # Left panel - Image input/processing
        self.left_panel = self._create_left_panel()
        grid_layout.addWidget(self.left_panel, 0, 0, 2, 1)
        
        # Center panel - Main workspace
        self.center_panel = self._create_center_panel()
        grid_layout.addWidget(self.center_panel, 0, 1, 2, 2)
        
        # Right panel - Parameters and controls
        self.right_panel = self._create_right_panel()
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
        
        # Image preview area
        self.image_preview = QLabel("No image loaded")
        self.image_preview.setStyleSheet("""
            QLabel {
                background-color: #343a40;
                border: 2px dashed #495057;
                border-radius: 4px;
                color: #adb5bd;
                padding: 20px;
                text-align: center;
            }
        """)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumHeight(200)
        layout.addWidget(self.image_preview)
        
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
            self.process_btn.setEnabled(True)
        else:
            self._log_message("No model loaded")
            self.process_btn.setEnabled(False)
    
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
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_path:
            self._log_message(f"Image loaded: {file_path}")
            self.image_preview.setText(f"Image: {file_path.split('/')[-1]}")
    
    def _save_project(self):
        self._log_message("Project saved")
    
    def _save_project_as(self):
        self._log_message("Save project as...")
    
    def _load_model(self):
        self.viewmodel.load_model("Segmentation Model")
        self._log_message("Loading model...")
    
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
        self._log_message("Processing image...")
        self.process_btn.setEnabled(False)
        # Simulate processing
        QTimer.singleShot(2000, lambda: self.process_btn.setEnabled(True))
