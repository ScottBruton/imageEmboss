"""
Main ViewModel
Handles the business logic for the main window
"""

from PySide6.QtCore import QObject, Signal, QTimer
from models.application_state import ApplicationState, StatusType, StatusLevel


class MainViewModel(QObject):
    """Main window viewmodel"""
    
    # Signals
    status_updated = Signal(StatusType, StatusLevel, str, str)  # type, level, message, details
    gpu_status_updated = Signal(bool, str)  # is_available, device_name
    model_status_updated = Signal(bool, str)  # is_loaded, model_name
    
    def __init__(self, app_state: ApplicationState):
        super().__init__()
        self.app_state = app_state
        
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
    
    def load_model(self, model_name: str):
        """Load a machine learning model"""
        # This would be implemented based on your specific model loading needs
        # For now, just update the status
        self.app_state.set_model_status(True, model_name)
    
    def unload_model(self):
        """Unload the current model"""
        self.app_state.set_model_status(False)
    
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
