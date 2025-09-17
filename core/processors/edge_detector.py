"""
Edge detection processor with GPU acceleration support
"""
import cv2
import numpy as np
from typing import Optional
from .base_processor import PipelineStep
from ..models.processing_result import ProcessingResult


class EdgeDetector(PipelineStep):
    """Detects edges using Canny algorithm with bilateral filtering"""
    
    def __init__(self):
        super().__init__()
        self.supports_gpu = True
        self.gpu_available = False
        self._init_gpu()
    
    def _init_gpu(self):
        """Initialize GPU acceleration if available"""
        try:
            import cupy as cp
            self.gpu_available = True
            print("🚀 GPU acceleration available for edge detection")
        except ImportError:
            self.gpu_available = False
            print("⚠️ GPU acceleration not available, using CPU")
    
    def execute(self, result: ProcessingResult) -> ProcessingResult:
        """Detect edges in the image"""
        if result.original_image is None:
            result.set_error("No image loaded for edge detection")
            return result
        
        params = result.parameters
        
        if self.gpu_available and self.supports_gpu_acceleration():
            return self.execute_gpu(result)
        else:
            return self.execute_cpu(result)
    
    def execute_cpu(self, result: ProcessingResult) -> ProcessingResult:
        """CPU-based edge detection"""
        try:
            image = result.original_image
            params = result.parameters
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply bilateral filter
            bilateral = cv2.bilateralFilter(
                gray,
                params.bilateral_diameter,
                params.bilateral_sigma_color,
                params.bilateral_sigma_space
            )
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(
                bilateral,
                (params.gaussian_kernel_size, params.gaussian_kernel_size),
                0
            )
            
            # Apply Canny edge detection
            edges = cv2.Canny(
                blurred,
                params.canny_lower_threshold,
                params.canny_upper_threshold
            )
            
            # Thicken edges
            kernel_size = max(1, int(params.edge_thickness))
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            thickened_edges = cv2.dilate(edges, kernel, iterations=1)
            
            # Invert if needed
            if params.invert:
                thickened_edges = 255 - thickened_edges
            
            result.edges = thickened_edges
            print(f"🔍 Edges detected: {np.sum(thickened_edges > 0)} edge pixels")
            
        except Exception as e:
            result.set_error(f"Edge detection failed: {str(e)}")
        
        return result
    
    def execute_gpu(self, result: ProcessingResult) -> ProcessingResult:
        """GPU-accelerated edge detection"""
        try:
            import cupy as cp
            
            image = result.original_image
            params = result.parameters
            
            # Convert to grayscale (CPU - OpenCV doesn't support GPU bilateral)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply bilateral filter (CPU)
            bilateral = cv2.bilateralFilter(
                gray,
                params.bilateral_diameter,
                params.bilateral_sigma_color,
                params.bilateral_sigma_space
            )
            
            # Upload to GPU
            bilateral_gpu = cp.asarray(bilateral)
            
            # Apply Gaussian blur on GPU
            gaussian_k = params.gaussian_kernel_size
            if gaussian_k % 2 == 0:
                gaussian_k += 1
            
            # Create Gaussian kernel
            kernel = self._create_gaussian_kernel_gpu(gaussian_k)
            
            # Apply convolution
            blurred_gpu = self._convolve2d_gpu(bilateral_gpu, kernel)
            
            # Download for Canny (OpenCV Canny is faster on CPU for small images)
            blurred = cp.asnumpy(blurred_gpu)
            
            # Apply Canny edge detection (CPU)
            edges = cv2.Canny(
                blurred,
                params.canny_lower_threshold,
                params.canny_upper_threshold
            )
            
            # Upload edges to GPU for dilation
            edges_gpu = cp.asarray(edges)
            
            # Apply dilation on GPU
            kernel_size = max(1, int(params.edge_thickness))
            kernel = cp.ones((kernel_size, kernel_size), dtype=cp.uint8)
            thickened_edges_gpu = self._dilate_gpu(edges_gpu, kernel)
            
            # Download result
            thickened_edges = cp.asnumpy(thickened_edges_gpu)
            
            # Invert if needed
            if params.invert:
                thickened_edges = 255 - thickened_edges
            
            result.edges = thickened_edges
            print(f"🚀 GPU edges detected: {np.sum(thickened_edges > 0)} edge pixels")
            
        except Exception as e:
            print(f"⚠️ GPU edge detection failed, falling back to CPU: {e}")
            return self.execute_cpu(result)
        
        return result
    
    def _create_gaussian_kernel_gpu(self, size: int) -> 'cp.ndarray':
        """Create Gaussian kernel on GPU"""
        import cupy as cp
        
        sigma = size / 6.0
        x = cp.arange(size, dtype=cp.float32)
        y = cp.arange(size, dtype=cp.float32)
        X, Y = cp.meshgrid(x, y)
        
        # Center the kernel
        center = size // 2
        X = X - center
        Y = Y - center
        
        # Calculate Gaussian
        kernel = cp.exp(-(X**2 + Y**2) / (2 * sigma**2))
        kernel = kernel / cp.sum(kernel)  # Normalize
        
        return kernel
    
    def _convolve2d_gpu(self, image: 'cp.ndarray', kernel: 'cp.ndarray') -> 'cp.ndarray':
        """2D convolution on GPU"""
        import cupy as cp
        
        img_h, img_w = image.shape
        kernel_h, kernel_w = kernel.shape
        
        # Calculate padding
        pad_h = kernel_h // 2
        pad_w = kernel_w // 2
        
        # Pad image
        padded = cp.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), mode='constant')
        
        # Perform convolution
        result = cp.zeros_like(image)
        
        for i in range(img_h):
            for j in range(img_w):
                result[i, j] = cp.sum(padded[i:i+kernel_h, j:j+kernel_w] * kernel)
        
        return result
    
    def _dilate_gpu(self, image: 'cp.ndarray', kernel: 'cp.ndarray') -> 'cp.ndarray':
        """Dilation on GPU"""
        import cupy as cp
        
        img_h, img_w = image.shape
        kernel_h, kernel_w = kernel.shape
        
        # Calculate padding
        pad_h = kernel_h // 2
        pad_w = kernel_w // 2
        
        # Pad image
        padded = cp.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), mode='constant')
        
        # Perform dilation
        result = cp.zeros_like(image)
        
        for i in range(img_h):
            for j in range(img_w):
                region = padded[i:i+kernel_h, j:j+kernel_w]
                result[i, j] = cp.max(region * kernel)
        
        return result
    
    def validate_input(self, result: ProcessingResult) -> bool:
        """Validate input for edge detection"""
        if result.original_image is None:
            result.set_error("No image loaded")
            return False
        
        if result.parameters is None:
            result.set_error("No parameters provided")
            return False
        
        return True
    
    def get_progress_weight(self) -> float:
        """Edge detection is a significant step"""
        return 0.2
