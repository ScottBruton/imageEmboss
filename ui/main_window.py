"""
Main application window
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QSplitter, QMenuBar, QStatusBar, QMessageBox,
                               QFileDialog, QProgressBar, QLabel, QTabWidget)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QAction, QKeySequence
from ui.panels.parameter_panel import ParameterPanel
from ui.panels.preview_panel import PreviewPanel
from ui.panels.model_viewer_panel import ModelViewerPanel
from ui.panels.original_image_panel import OriginalImagePanel
from ui.widgets.custom_controls import ProgressBar, StatusLabel
from core.pipeline import ImageProcessingPipeline
from core.models.parameters import ProcessingParameters
from core.models.processing_result import ProcessingResult
from utils.threading import ThreadedImageProcessor
from utils.gpu_accelerator import gpu_accelerator
from config.settings import app_settings
from config.constants import *
from typing import Optional
import os


class ImageEmbossMainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.pipeline = ImageProcessingPipeline()
        self.threaded_processor = None
        self.current_result = None
        self.processing_timer = QTimer()
        self.processing_timer.setSingleShot(True)
        self.processing_timer.timeout.connect(self.start_processing)
        
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_threading()
        self.connect_signals()
        self.load_settings()
        
        # Set window properties
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
    
    def setup_ui(self):
        """Setup main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (parameters and original image)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel (preview and 3D viewer)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions - make left panel bigger for original image
        splitter.setSizes([600, 1000])  # Left panel gets more space
        splitter.setStretchFactor(0, 1)  # Left panel can stretch
        splitter.setStretchFactor(1, 2)  # Right panel gets more stretch
    
    def create_left_panel(self) -> QWidget:
        """Create left panel with parameters and original image"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Original image panel
        self.original_image_panel = OriginalImagePanel()
        layout.addWidget(self.original_image_panel)
        
        # Parameter panel
        self.parameter_panel = ParameterPanel()
        layout.addWidget(self.parameter_panel)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with tabbed interface"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Preview panel tab
        self.preview_panel = PreviewPanel()
        self.tab_widget.addTab(self.preview_panel, "DXF Preview")
        
        # 3D model viewer panel tab
        self.model_viewer_panel = ModelViewerPanel()
        self.tab_widget.addTab(self.model_viewer_panel, "3D Model")
        
        layout.addWidget(self.tab_widget)
        
        return panel
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Image", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_dxf_action = QAction("Export DXF", self)
        export_dxf_action.setShortcut(QKeySequence.Save)
        export_dxf_action.triggered.connect(self.export_dxf)
        file_menu.addAction(export_dxf_action)
        
        export_step_action = QAction("Export STEP", self)
        export_step_action.setShortcut("Ctrl+E")
        export_step_action.triggered.connect(self.export_step)
        file_menu.addAction(export_step_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        zoom_fit_action = QAction("Zoom Fit", self)
        zoom_fit_action.setShortcut("Ctrl+0")
        zoom_fit_action.triggered.connect(self.zoom_fit)
        view_menu.addAction(zoom_fit_action)
        
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl+=")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        toggle_splines_action = QAction("Toggle Splines", self)
        toggle_splines_action.setShortcut("Ctrl+P")
        toggle_splines_action.triggered.connect(self.toggle_splines)
        tools_menu.addAction(toggle_splines_action)
        
        toggle_gpu_action = QAction("Toggle GPU", self)
        toggle_gpu_action.setShortcut("Ctrl+G")
        toggle_gpu_action.triggered.connect(self.toggle_gpu)
        tools_menu.addAction(toggle_gpu_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = self.statusBar()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # GPU status
        gpu_info = gpu_accelerator.get_gpu_info()
        if gpu_info['available']:
            gpu_status = f"GPU: {gpu_info['name']}"
        else:
            gpu_status = "GPU: Not available"
        
        self.gpu_status_label = QLabel(gpu_status)
        self.status_bar.addPermanentWidget(self.gpu_status_label)
    
    def setup_threading(self):
        """Setup threading"""
        self.threaded_processor = ThreadedImageProcessor(self)
    
    def connect_signals(self):
        """Connect all signals"""
        # Image panel
        self.original_image_panel.image_loaded.connect(self.on_image_loaded)
        
        # Parameter panel
        self.parameter_panel.parameters_changed.connect(self.on_parameters_changed)
        self.parameter_panel.export_requested.connect(self.export_dxf)
        self.parameter_panel.reset_requested.connect(self.reset_parameters)
        
        # Preview panel
        self.preview_panel.circle_tool_toggled.connect(self.on_circle_tool_toggled)
        self.preview_panel.merge_tool_toggled.connect(self.on_merge_tool_toggled)
        self.preview_panel.settings_lock_toggled.connect(self.on_settings_lock_toggled)
        
        # Model viewer panel
        self.model_viewer_panel.rotate_requested.connect(self.on_3d_rotate)
        self.model_viewer_panel.zoom_requested.connect(self.on_3d_zoom)
        self.model_viewer_panel.lighting_changed.connect(self.on_3d_lighting_changed)
    
    def load_settings(self):
        """Load application settings"""
        # Load window geometry
        geometry = app_settings.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        
        # Load window state
        state = app_settings.get_window_state()
        if state:
            self.restoreState(state)
        
        # Load last image
        last_image = app_settings.get_last_image_path()
        if last_image and os.path.exists(last_image):
            self.original_image_panel.load_image(last_image)
    
    def save_settings(self):
        """Save application settings"""
        # Save window geometry
        app_settings.set_window_geometry(self.saveGeometry())
        
        # Save window state
        app_settings.set_window_state(self.saveState())
        
        # Save last image path
        current_image = self.original_image_panel.get_current_image_path()
        if current_image:
            app_settings.set_last_image_path(current_image)
    
    def on_image_loaded(self, image_path: str):
        """Handle image loaded"""
        self.status_label.setText(f"Image loaded: {os.path.basename(image_path)}")
        
        # Start processing with current parameters
        if self.parameter_panel.get_parameters():
            self.start_processing()
    
    def on_parameters_changed(self, parameters: ProcessingParameters):
        """Handle parameter changes"""
        # Debounce processing
        self.processing_timer.stop()
        self.processing_timer.start(DEBOUNCE_DELAY_MS)
    
    def start_processing(self):
        """Start image processing"""
        if not self.original_image_panel.is_image_loaded():
            return
        
        image_path = self.original_image_panel.get_current_image_path()
        parameters = self.parameter_panel.get_parameters()
        
        if image_path and parameters:
            self.status_label.setText("Processing...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            self.threaded_processor.start_processing(image_path, parameters)
    
    def on_processing_completed(self, result: ProcessingResult):
        """Handle processing completion"""
        self.current_result = result
        
        try:
            # Update preview with error handling
            if hasattr(result, 'contours') and result.contours:
                self.preview_panel.set_contours(result.contours)
            if hasattr(result, 'splines') and result.splines:
                self.preview_panel.set_splines(result.splines)
            if hasattr(result, 'parameters') and result.parameters:
                self.preview_panel.set_use_splines(result.parameters.use_splines)
            
            # Update 3D viewer
            if hasattr(result, 'splines') and result.splines:
                self.model_viewer_panel.set_model(result.splines)
            
            # Update status
            self.status_label.setText("Processing completed")
            self.progress_bar.setVisible(False)
            
            print(f"✅ Processing completed in {result.processing_time:.2f}s")
            
        except Exception as e:
            print(f"Error updating UI after processing: {e}")
            self.status_label.setText("Processing completed with UI errors")
            self.progress_bar.setVisible(False)
    
    def on_processing_failed(self, error_message: str):
        """Handle processing failure"""
        self.status_label.setText(f"Error: {error_message}")
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Processing Error", error_message)
    
    def on_processing_cancelled(self):
        """Handle processing cancellation"""
        self.status_label.setText("Processing cancelled")
        self.progress_bar.setVisible(False)
    
    def on_progress_updated(self, progress: int):
        """Handle progress updates"""
        self.progress_bar.setValue(progress)
    
    def on_step_started(self, step_name: str):
        """Handle step start"""
        self.status_label.setText(f"Processing: {step_name}")
    
    def on_step_completed(self, step_name: str):
        """Handle step completion"""
        self.status_label.setText(f"Completed: {step_name}")
    
    def on_circle_tool_toggled(self, active: bool):
        """Handle circle tool toggle"""
        if active:
            self.status_label.setText("Circle tool active - click to select area")
        else:
            self.status_label.setText("Ready")
    
    def on_merge_tool_toggled(self, active: bool):
        """Handle merge tool toggle"""
        if active:
            self.status_label.setText("Merge tool active - select contours to merge")
        else:
            self.status_label.setText("Ready")
    
    def on_settings_lock_toggled(self, active: bool):
        """Handle settings lock toggle"""
        if active:
            self.status_label.setText("Settings locked for area processing")
        else:
            self.status_label.setText("Ready")
    
    def on_3d_rotate(self):
        """Handle 3D rotation"""
        self.status_label.setText("3D model rotated")
    
    def on_3d_zoom(self):
        """Handle 3D zoom"""
        self.status_label.setText("3D model zoomed")
    
    def on_3d_lighting_changed(self):
        """Handle 3D lighting change"""
        self.status_label.setText("3D lighting updated")
    
    def open_image(self):
        """Open image file"""
        self.original_image_panel.select_image_file()
    
    def export_dxf(self):
        """Export DXF file"""
        if not self.current_result or not self.current_result.dxf_path:
            QMessageBox.warning(self, "Export Error", "No DXF file to export")
            return
        
        # DXF file should already be created during processing
        QMessageBox.information(self, "Export Complete", 
                               f"DXF file exported: {self.current_result.dxf_path}")
    
    def export_step(self):
        """Export STEP file"""
        if not self.current_result or not self.current_result.step_path:
            QMessageBox.warning(self, "Export Error", "No STEP file to export")
            return
        
        # STEP file should already be created during processing
        QMessageBox.information(self, "Export Complete", 
                               f"STEP file exported: {self.current_result.step_path}")
    
    def reset_parameters(self):
        """Reset parameters to default"""
        self.parameter_panel.apply_preset(PRESET_CONFIGS["Default"])
        self.status_label.setText("Parameters reset to default")
    
    def zoom_fit(self):
        """Fit to view"""
        self.original_image_panel.fit_to_view()
        self.preview_panel.fit_to_view()
        self.status_label.setText("Zoomed to fit")
    
    def zoom_in(self):
        """Zoom in"""
        self.original_image_panel.zoom_in()
        self.preview_panel.zoom_in()
        self.status_label.setText("Zoomed in")
    
    def zoom_out(self):
        """Zoom out"""
        self.original_image_panel.zoom_out()
        self.preview_panel.zoom_out()
        self.status_label.setText("Zoomed out")
    
    def toggle_splines(self):
        """Toggle spline display"""
        current_use_splines = self.parameter_panel.get_parameters().use_splines
        new_use_splines = not current_use_splines
        
        # Update parameter panel
        self.parameter_panel.use_splines_checkbox.setChecked(new_use_splines)
        
        # Update preview
        self.preview_panel.set_use_splines(new_use_splines)
        
        self.status_label.setText(f"Splines {'enabled' if new_use_splines else 'disabled'}")
    
    def toggle_gpu(self):
        """Toggle GPU acceleration"""
        current_gpu = app_settings.is_gpu_acceleration_enabled()
        new_gpu = not current_gpu
        
        app_settings.set_gpu_acceleration(new_gpu)
        
        # Update GPU status
        if new_gpu and gpu_accelerator.is_available():
            self.gpu_status_label.setText("GPU: Enabled")
        else:
            self.gpu_status_label.setText("GPU: Disabled")
        
        self.status_label.setText(f"GPU acceleration {'enabled' if new_gpu else 'disabled'}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, f"About {APP_NAME}", 
                         f"{APP_NAME} v{APP_VERSION}\n\n"
                         f"{APP_DESCRIPTION}\n\n"
                         f"Convert images to smooth spline DXF files and 3D models.")
    
    def closeEvent(self, event):
        """Handle window close"""
        # Save settings
        self.save_settings()
        
        # Cancel any ongoing processing
        if self.threaded_processor:
            self.threaded_processor.cancel_processing()
        
        event.accept()
