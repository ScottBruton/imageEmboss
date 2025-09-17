"""
GPU acceleration utilities
"""
import numpy as np
from typing import Optional, Tuple


class GPUAccelerator:
    """Manages GPU acceleration capabilities"""
    
    def __init__(self):
        self.cupy_available = False
        self.gpu_memory = 0
        self.gpu_name = "Unknown"
        self._init_gpu()
    
    def _init_gpu(self):
        """Initialize GPU acceleration"""
        try:
            import cupy as cp
            
            # Check if CUDA is available
            if cp.cuda.is_available():
                self.cupy_available = True
                
                # Get GPU info
                mempool = cp.get_default_memory_pool()
                self.gpu_memory = mempool.total_bytes() / (1024**3)  # GB
                
                # Get GPU name
                try:
                    import subprocess
                    result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader,nounits'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.gpu_name = result.stdout.strip()
                    else:
                        self.gpu_name = "NVIDIA GPU"
                except:
                    self.gpu_name = "NVIDIA GPU"
                
                print(f"🚀 GPU acceleration available: {self.gpu_name} ({self.gpu_memory:.1f}GB)")
            else:
                print("⚠️ CUDA not available")
                
        except ImportError:
            print("⚠️ CuPy not installed - GPU acceleration disabled")
        except Exception as e:
            print(f"⚠️ GPU initialization failed: {e}")
    
    def is_available(self) -> bool:
        """Check if GPU acceleration is available"""
        return self.cupy_available
    
    def get_gpu_info(self) -> dict:
        """Get GPU information"""
        return {
            'available': self.cupy_available,
            'name': self.gpu_name,
            'memory_gb': self.gpu_memory
        }
    
    def bilateral_filter_gpu(self, image: np.ndarray, diameter: int, sigma_color: float, sigma_space: float) -> np.ndarray:
        """GPU-accelerated bilateral filtering"""
        if not self.cupy_available:
            return image
        
        try:
            import cupy as cp
            
            # Upload to GPU
            image_gpu = cp.asarray(image)
            
            # Apply bilateral filter (simplified version)
            # Note: CuPy doesn't have bilateral filter, so we'll use a combination of filters
            # This is a simplified approximation
            
            # Gaussian blur for spatial smoothing
            kernel_size = max(3, diameter)
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            # Create Gaussian kernel
            sigma = sigma_space / 3.0
            kernel = self._create_gaussian_kernel(kernel_size, sigma)
            
            # Apply convolution
            filtered_gpu = self._convolve2d(image_gpu, kernel)
            
            # Download result
            return cp.asnumpy(filtered_gpu)
            
        except Exception as e:
            print(f"⚠️ GPU bilateral filter failed: {e}")
            return image
    
    def gaussian_blur_gpu(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """GPU-accelerated Gaussian blur"""
        if not self.cupy_available:
            return image
        
        try:
            import cupy as cp
            
            # Upload to GPU
            image_gpu = cp.asarray(image)
            
            # Create Gaussian kernel
            sigma = kernel_size / 6.0
            kernel = self._create_gaussian_kernel(kernel_size, sigma)
            
            # Apply convolution
            blurred_gpu = self._convolve2d(image_gpu, kernel)
            
            # Download result
            return cp.asnumpy(blurred_gpu)
            
        except Exception as e:
            print(f"⚠️ GPU Gaussian blur failed: {e}")
            return image
    
    def dilate_gpu(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """GPU-accelerated dilation"""
        if not self.cupy_available:
            return image
        
        try:
            import cupy as cp
            
            # Upload to GPU
            image_gpu = cp.asarray(image)
            
            # Create kernel
            kernel = cp.ones((kernel_size, kernel_size), dtype=cp.uint8)
            
            # Apply dilation
            dilated_gpu = self._dilate(image_gpu, kernel)
            
            # Download result
            return cp.asnumpy(dilated_gpu)
            
        except Exception as e:
            print(f"⚠️ GPU dilation failed: {e}")
            return image
    
    def _create_gaussian_kernel(self, size: int, sigma: float) -> 'cp.ndarray':
        """Create Gaussian kernel on GPU"""
        import cupy as cp
        
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
    
    def _convolve2d(self, image: 'cp.ndarray', kernel: 'cp.ndarray') -> 'cp.ndarray':
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
    
    def _dilate(self, image: 'cp.ndarray', kernel: 'cp.ndarray') -> 'cp.ndarray':
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


# Global GPU accelerator instance
gpu_accelerator = GPUAccelerator()
