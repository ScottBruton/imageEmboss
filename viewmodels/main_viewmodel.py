"""
Main ViewModel
Handles the business logic for the main window
"""

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QPixmap
from models.application_state import ApplicationState, StatusType, StatusLevel
from models.model_manager import ModelManager, ModelConfig
import os


class MainViewModel(QObject):
    """Main window viewmodel"""
    
    # Signals
    status_updated = Signal(StatusType, StatusLevel, str, str)  # type, level, message, details
    gpu_status_updated = Signal(bool, str)  # is_available, device_name
    model_status_updated = Signal(bool, str)  # is_loaded, model_name
    image_loaded = Signal(str, QPixmap)  # file_path, pixmap
    image_load_failed = Signal(str)  # error_message
    
    def __init__(self, app_state: ApplicationState):
        super().__init__()
        self.app_state = app_state
        
        # Initialize model manager
        self.model_manager = ModelManager(device="auto")
        
        # Current image state
        self.current_image_path = None
        self.current_image_pixmap = None
        
        # Connect to application state signals
        self.app_state.status_changed.connect(self._on_status_changed)
        self.app_state.gpu_status_changed.connect(self._on_gpu_status_changed)
        self.app_state.model_status_changed.connect(self._on_model_status_changed)
        
        # Setup periodic status updates
        self._setup_status_timer()
    
    def _setup_status_timer(self):
        """Setup timer for periodic status updates"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_system_status)
        self.status_timer.start(5000)  # Update every 5 seconds
    
    def _on_status_changed(self, status_type: StatusType, level: StatusLevel, message: str, details: str):
        """Handle status changes from application state"""
        self.status_updated.emit(status_type, level, message, details)
    
    def _on_gpu_status_changed(self, is_available: bool, device_name: str):
        """Handle GPU status changes"""
        self.gpu_status_updated.emit(is_available, device_name)
    
    def _on_model_status_changed(self, is_loaded: bool, model_name: str):
        """Handle model status changes"""
        self.model_status_updated.emit(is_loaded, model_name)
    
    def _update_system_status(self):
        """Periodically update system status"""
        # This could include checking for new GPU devices, model status, etc.
        pass
    
    def get_status(self, status_type: StatusType):
        """Get status indicator by type"""
        return self.app_state.get_status(status_type)
    
    def get_all_status(self):
        """Get all status indicators"""
        return self.app_state.get_all_status()
    
    def load_model(self, config: ModelConfig):
        """Load a machine learning model with the given configuration"""
        try:
            # Unload any existing model first
            if self.model_manager.is_model_loaded:
                self.model_manager.unload_model()
            
            # Load the new model
            success = self.model_manager.load_model(config)
            
            if success:
                model_info = self.model_manager.get_model_info()
                device_info = f" on {model_info['device']}"
                if model_info.get('gpu_memory'):
                    device_info += f" ({model_info['gpu_memory']:.1f}GB)"
                
                self.app_state.set_model_status(True, f"{config.model_name}{device_info}")
                return True
            else:
                self.app_state.set_model_status(False, "Failed to load model")
                return False
                
        except Exception as e:
            self.app_state.set_model_status(False, f"Error: {str(e)}")
            return False
    
    def unload_model(self):
        """Unload the current model"""
        if self.model_manager.is_model_loaded:
            self.model_manager.unload_model()
        self.app_state.set_model_status(False)
    
    def get_model_manager(self) -> ModelManager:
        """Get the model manager instance"""
        return self.model_manager
    
    def predict_image(self, image):
        """Run inference on an image using the loaded model"""
        if not self.model_manager.is_model_loaded:
            raise ValueError("No model loaded")
        
        return self.model_manager.predict(image)
    
    @property
    def gpu_available(self) -> bool:
        """Check if GPU is available"""
        return self.app_state.gpu_available
    
    @property
    def gpu_device(self) -> str:
        """Get GPU device name"""
        return self.app_state.gpu_device
    
    @property
    def model_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.app_state.model_loaded
    
    @property
    def model_name(self) -> str:
        """Get loaded model name"""
        return self.app_state.model_name
    
    def load_image(self, file_path: str):
        """Load an image from file path"""
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                self.image_load_failed.emit(f"File not found: {file_path}")
                return False
            
            # Load the image
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                self.image_load_failed.emit(f"Failed to load image: {file_path}")
                return False
            
            # Store the image data
            self.current_image_path = file_path
            self.current_image_pixmap = pixmap
            
            # Emit success signal
            self.image_loaded.emit(file_path, pixmap)
            return True
            
        except Exception as e:
            self.image_load_failed.emit(f"Error loading image: {str(e)}")
            return False
    
    def get_current_image_path(self) -> str:
        """Get the current image file path"""
        return self.current_image_path
    
    def get_current_image_pixmap(self) -> QPixmap:
        """Get the current image pixmap"""
        return self.current_image_pixmap
    
    def has_image_loaded(self) -> bool:
        """Check if an image is currently loaded"""
        return self.current_image_path is not None and self.current_image_pixmap is not None
    
    def can_process_image(self) -> bool:
        """Check if image processing is possible (both image and model loaded)"""
        return self.has_image_loaded() and self.model_manager.is_model_loaded
