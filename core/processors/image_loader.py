"""
Image loading processor
"""
import cv2
import numpy as np
from typing import Dict, Any
from .base_processor import PipelineStep
from ..models.processing_result import ProcessingResult


class ImageLoader(PipelineStep):
    """Loads and validates images"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        self.max_size = 10000  # Maximum image dimension
    
    def execute(self, result: ProcessingResult) -> ProcessingResult:
        """Load and validate image"""
        try:
            # Load image
            image = cv2.imread(result.image_path)
            if image is None:
                result.set_error(f"Could not load image: {result.image_path}")
                return result
            
            # Validate image size
            height, width = image.shape[:2]
            if max(height, width) > self.max_size:
                result.set_error(f"Image too large: {width}x{height}. Maximum: {self.max_size}")
                return result
            
            # Store image and metadata
            result.original_image = image
            result.image_metadata = {
                'width': width,
                'height': height,
                'channels': image.shape[2] if len(image.shape) > 2 else 1,
                'format': self._get_image_format(result.image_path),
                'size_mb': (image.nbytes / (1024 * 1024))
            }
            
            print(f"📷 Image loaded: {width}x{height}, {result.image_metadata['size_mb']:.1f}MB")
            
        except Exception as e:
            result.set_error(f"Image loading failed: {str(e)}")
        
        return result
    
    def validate_input(self, result: ProcessingResult) -> bool:
        """Validate input for image loading"""
        if not result.image_path:
            result.set_error("No image path provided")
            return False
        
        # Check file extension
        import os
        ext = os.path.splitext(result.image_path)[1].lower()
        if ext not in self.supported_formats:
            result.set_error(f"Unsupported image format: {ext}")
            return False
        
        # Check if file exists
        if not os.path.exists(result.image_path):
            result.set_error(f"Image file not found: {result.image_path}")
            return False
        
        return True
    
    def _get_image_format(self, image_path: str) -> str:
        """Get image format from file extension"""
        import os
        return os.path.splitext(image_path)[1].lower()
    
    def get_progress_weight(self) -> float:
        """Image loading is quick"""
        return 0.1
