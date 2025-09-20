"""
Application State Model
Manages the global state of the application including system status
"""

from PySide6.QtCore import QObject, Signal
from enum import Enum
from typing import Dict, Any
import torch


class StatusType(Enum):
    """Types of status indicators"""
    GPU = "gpu"
    ML_MODEL = "ml_model"
    CUDA = "cuda"
    SYSTEM = "system"


class StatusLevel(Enum):
    """Status levels for indicators"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class StatusIndicator:
    """Represents a status indicator"""
    
    def __init__(self, status_type: StatusType, level: StatusLevel, message: str, details: str = ""):
        self.status_type = status_type
        self.level = level
        self.message = message
        self.details = details
        self.timestamp = None


class ApplicationState(QObject):
    """Global application state management"""
    
    # Signals
    status_changed = Signal(StatusType, StatusLevel, str, str)  # type, level, message, details
    gpu_status_changed = Signal(bool, str)  # is_available, device_name
    model_status_changed = Signal(bool, str)  # is_loaded, model_name
    
    def __init__(self):
        super().__init__()
        self._status_indicators: Dict[StatusType, StatusIndicator] = {}
        self._gpu_available = False
        self._gpu_device = ""
        self._model_loaded = False
        self._model_name = ""
        
        # Initialize status indicators
        self._initialize_status_indicators()
        
        # Check system status
        self._check_system_status()
    
    def _initialize_status_indicators(self):
        """Initialize all status indicators"""
        # GPU Status
        self._status_indicators[StatusType.GPU] = StatusIndicator(
            StatusType.GPU, StatusLevel.UNKNOWN, "Checking GPU...", ""
        )
        
        # CUDA Status
        self._status_indicators[StatusType.CUDA] = StatusIndicator(
            StatusType.CUDA, StatusLevel.UNKNOWN, "Checking CUDA...", ""
        )
        
        # ML Model Status
        self._status_indicators[StatusType.ML_MODEL] = StatusIndicator(
            StatusType.ML_MODEL, StatusLevel.UNKNOWN, "No model loaded", ""
        )
        
        # System Status
        self._status_indicators[StatusType.SYSTEM] = StatusIndicator(
            StatusType.SYSTEM, StatusLevel.SUCCESS, "System ready", ""
        )
    
    def _check_system_status(self):
        """Check and update system status"""
        # Check GPU availability
        self._check_gpu_status()
        
        # Check CUDA availability
        self._check_cuda_status()
    
    def _check_gpu_status(self):
        """Check GPU availability"""
        try:
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
                
                self._gpu_available = True
                self._gpu_device = device_name
                
                self._update_status(
                    StatusType.GPU, 
                    StatusLevel.SUCCESS, 
                    f"GPU Available ({device_count} device{'s' if device_count > 1 else ''})",
                    f"Device: {device_name}"
                )
                
                self.gpu_status_changed.emit(True, device_name)
            else:
                self._gpu_available = False
                self._gpu_device = ""
                
                self._update_status(
                    StatusType.GPU, 
                    StatusLevel.WARNING, 
                    "GPU Not Available",
                    "Running on CPU"
                )
                
                self.gpu_status_changed.emit(False, "")
                
        except Exception as e:
            self._update_status(
                StatusType.GPU, 
                StatusLevel.ERROR, 
                "GPU Check Failed",
                str(e)
            )
            self.gpu_status_changed.emit(False, "")
    
    def _check_cuda_status(self):
        """Check CUDA availability"""
        try:
            if torch.cuda.is_available():
                cuda_version = torch.version.cuda
                self._update_status(
                    StatusType.CUDA, 
                    StatusLevel.SUCCESS, 
                    f"CUDA {cuda_version}",
                    f"PyTorch CUDA support enabled"
                )
            else:
                self._update_status(
                    StatusType.CUDA, 
                    StatusLevel.WARNING, 
                    "CUDA Not Available",
                    "CPU-only mode"
                )
        except Exception as e:
            self._update_status(
                StatusType.CUDA, 
                StatusLevel.ERROR, 
                "CUDA Check Failed",
                str(e)
            )
    
    def _update_status(self, status_type: StatusType, level: StatusLevel, message: str, details: str = ""):
        """Update a status indicator"""
        self._status_indicators[status_type] = StatusIndicator(status_type, level, message, details)
        self.status_changed.emit(status_type, level, message, details)
    
    def get_status(self, status_type: StatusType) -> StatusIndicator:
        """Get status indicator by type"""
        return self._status_indicators.get(status_type)
    
    def get_all_status(self) -> Dict[StatusType, StatusIndicator]:
        """Get all status indicators"""
        return self._status_indicators.copy()
    
    def set_model_status(self, is_loaded: bool, model_name: str = ""):
        """Set ML model status"""
        self._model_loaded = is_loaded
        self._model_name = model_name
        
        if is_loaded and model_name:
            self._update_status(
                StatusType.ML_MODEL, 
                StatusLevel.SUCCESS, 
                f"Model Loaded: {model_name}",
                "Ready for inference"
            )
        else:
            self._update_status(
                StatusType.ML_MODEL, 
                StatusLevel.WARNING, 
                "No Model Loaded",
                "Load a model to begin"
            )
        
        self.model_status_changed.emit(is_loaded, model_name)
    
    @property
    def gpu_available(self) -> bool:
        """Check if GPU is available"""
        return self._gpu_available
    
    @property
    def gpu_device(self) -> str:
        """Get GPU device name"""
        return self._gpu_device
    
    @property
    def model_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model_loaded
    
    @property
    def model_name(self) -> str:
        """Get loaded model name"""
        return self._model_name
