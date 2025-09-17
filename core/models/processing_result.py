"""
Processing result models for ImageEmboss
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np


@dataclass
class ProcessingResult:
    """Result of image processing pipeline"""
    
    # Input data
    image_path: str = ""
    parameters: Optional[Any] = None
    
    # Processing results
    success: bool = True
    error_message: Optional[str] = None
    cancelled: bool = False
    progress: int = 0
    
    # Image data
    original_image: Optional[np.ndarray] = None
    image_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Processing steps
    edges: Optional[np.ndarray] = None
    contours: List[np.ndarray] = field(default_factory=list)
    splines: List[np.ndarray] = field(default_factory=list)
    
    # Export results
    dxf_path: Optional[str] = None
    step_path: Optional[str] = None
    stl_path: Optional[str] = None
    obj_path: Optional[str] = None
    
    # Statistics
    processing_time: float = 0.0
    contour_count: int = 0
    spline_count: int = 0
    
    # Step results for debugging
    step_results: Dict[str, Any] = field(default_factory=dict)
    
    def set_error(self, message: str):
        """Set error state"""
        self.success = False
        self.error_message = message
    
    def set_cancelled(self):
        """Set cancelled state"""
        self.cancelled = True
        self.success = False
    
    def update_progress(self, progress: int):
        """Update processing progress"""
        self.progress = max(0, min(100, progress))
    
    def add_step_result(self, step_name: str, result: Any):
        """Add result from a processing step"""
        self.step_results[step_name] = result
    
    def get_step_result(self, step_name: str) -> Any:
        """Get result from a processing step"""
        return self.step_results.get(step_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary (excluding numpy arrays)"""
        return {
            'image_path': self.image_path,
            'success': self.success,
            'error_message': self.error_message,
            'cancelled': self.cancelled,
            'progress': self.progress,
            'image_metadata': self.image_metadata,
            'dxf_path': self.dxf_path,
            'step_path': self.step_path,
            'stl_path': self.stl_path,
            'obj_path': self.obj_path,
            'processing_time': self.processing_time,
            'contour_count': self.contour_count,
            'spline_count': self.spline_count,
            'step_results': {k: v for k, v in self.step_results.items() 
                           if not isinstance(v, np.ndarray)}
        }
