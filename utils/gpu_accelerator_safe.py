"""
Safe GPU acceleration utilities with crash protection
"""
import numpy as np
from typing import Optional, Tuple


class SafeGPUAccelerator:
    """Safe GPU accelerator with crash protection"""
    
    def __init__(self):
        self.cupy_available = False
        self.gpu_memory = 0
        self.gpu_name = "Unknown"
        self.initialization_error = None
        self._init_gpu_safely()
    
    def _init_gpu_safely(self):
        """Initialize GPU acceleration with crash protection"""
        try:
            print("🔍 Checking GPU availability...")
            
            # Try to import CuPy
            try:
                import cupy as cp
                print("✅ CuPy imported successfully")
            except ImportError as e:
                print(f"⚠️ CuPy not available: {e}")
                self.initialization_error = f"CuPy not installed: {e}"
                return
            
            # Check CUDA availability
            try:
                if cp.cuda.is_available():
                    print("✅ CUDA is available")
                    self.cupy_available = True
                else:
                    print("⚠️ CUDA not available")
                    self.initialization_error = "CUDA not available"
                    return
            except Exception as e:
                print(f"⚠️ CUDA check failed: {e}")
                self.initialization_error = f"CUDA check failed: {e}"
                return
            
            # Get GPU info safely
            try:
                # Test basic GPU operation
                test_array = cp.array([1, 2, 3])
                result = cp.sum(test_array)
                print(f"✅ GPU test successful: {result}")
                
                # Get memory info
                try:
                    mempool = cp.get_default_memory_pool()
                    self.gpu_memory = mempool.total_bytes() / (1024**3)  # GB
                    print(f"✅ GPU memory: {self.gpu_memory:.1f}GB")
                except Exception as e:
                    print(f"⚠️ Could not get GPU memory info: {e}")
                    self.gpu_memory = 0
                
                # Get GPU name
                try:
                    import subprocess
                    result = subprocess.run(
                        ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader,nounits'], 
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        self.gpu_name = result.stdout.strip()
                        print(f"✅ GPU name: {self.gpu_name}")
                    else:
                        self.gpu_name = "NVIDIA GPU"
                        print("⚠️ Could not get GPU name")
                except Exception as e:
                    print(f"⚠️ Could not get GPU name: {e}")
                    self.gpu_name = "NVIDIA GPU"
                
                print(f"🚀 GPU acceleration initialized successfully")
                
            except Exception as e:
                print(f"❌ GPU test failed: {e}")
                self.initialization_error = f"GPU test failed: {e}"
                self.cupy_available = False
                
        except Exception as e:
            print(f"❌ GPU initialization failed: {e}")
            self.initialization_error = f"GPU initialization failed: {e}"
            self.cupy_available = False
    
    def is_available(self) -> bool:
        """Check if GPU acceleration is available"""
        return self.cupy_available
    
    def get_gpu_info(self) -> dict:
        """Get GPU information"""
        return {
            'available': self.cupy_available,
            'name': self.gpu_name,
            'memory_gb': self.gpu_memory,
            'error': self.initialization_error
        }
    
    def bilateral_filter_gpu(self, image: np.ndarray, diameter: int, sigma_color: float, sigma_space: float) -> np.ndarray:
        """GPU-accelerated bilateral filtering with fallback"""
        if not self.cupy_available:
            print("⚠️ GPU not available, using CPU bilateral filter")
            return self._bilateral_filter_cpu(image, diameter, sigma_color, sigma_space)
        
        try:
            import cupy as cp
            
            # Upload to GPU
            image_gpu = cp.asarray(image)
            
            # Apply simplified bilateral filter (Gaussian blur approximation)
            kernel_size = max(3, diameter)
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            # Create Gaussian kernel
            sigma = sigma_space / 3.0
            kernel = self._create_gaussian_kernel_gpu(kernel_size, sigma)
            
            # Apply convolution
            filtered_gpu = self._convolve2d_gpu(image_gpu, kernel)
            
            # Download result
            return cp.asnumpy(filtered_gpu)
            
        except Exception as e:
            print(f"⚠️ GPU bilateral filter failed, using CPU: {e}")
            return self._bilateral_filter_cpu(image, diameter, sigma_color, sigma_space)
    
    def _bilateral_filter_cpu(self, image: np.ndarray, diameter: int, sigma_color: float, sigma_space: float) -> np.ndarray:
        """CPU bilateral filter fallback"""
        try:
            import cv2
            return cv2.bilateralFilter(image, diameter, sigma_color, sigma_space)
        except Exception as e:
            print(f"⚠️ CPU bilateral filter failed: {e}")
            return image
    
    def gaussian_blur_gpu(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """GPU-accelerated Gaussian blur with fallback"""
        if not self.cupy_available:
            print("⚠️ GPU not available, using CPU Gaussian blur")
            return self._gaussian_blur_cpu(image, kernel_size)
        
        try:
            import cupy as cp
            
            # Upload to GPU
            image_gpu = cp.asarray(image)
            
            # Create Gaussian kernel
            kernel = self._create_gaussian_kernel_gpu(kernel_size, kernel_size / 6.0)
            
            # Apply convolution
            blurred_gpu = self._convolve2d_gpu(image_gpu, kernel)
            
            # Download result
            return cp.asnumpy(blurred_gpu)
            
        except Exception as e:
            print(f"⚠️ GPU Gaussian blur failed, using CPU: {e}")
            return self._gaussian_blur_cpu(image, kernel_size)
    
    def _gaussian_blur_cpu(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """CPU Gaussian blur fallback"""
        try:
            import cv2
            return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        except Exception as e:
            print(f"⚠️ CPU Gaussian blur failed: {e}")
            return image
    
    def dilate_gpu(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """GPU-accelerated dilation with fallback"""
        if not self.cupy_available:
            print("⚠️ GPU not available, using CPU dilation")
            return self._dilate_cpu(image, kernel_size)
        
        try:
            import cupy as cp
            
            # Upload to GPU
            image_gpu = cp.asarray(image)
            
            # Create kernel
            kernel = cp.ones((kernel_size, kernel_size), dtype=cp.uint8)
            
            # Apply dilation
            dilated_gpu = self._dilate_gpu_internal(image_gpu, kernel)
            
            # Download result
            return cp.asnumpy(dilated_gpu)
            
        except Exception as e:
            print(f"⚠️ GPU dilation failed, using CPU: {e}")
            return self._dilate_cpu(image, kernel_size)
    
    def _dilate_cpu(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """CPU dilation fallback"""
        try:
            import cv2
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            return cv2.dilate(image, kernel, iterations=1)
        except Exception as e:
            print(f"⚠️ CPU dilation failed: {e}")
            return image
    
    def _create_gaussian_kernel_gpu(self, size: int, sigma: float) -> 'cp.ndarray':
        """Create Gaussian kernel on GPU"""
        try:
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
        except Exception as e:
            print(f"⚠️ Failed to create Gaussian kernel: {e}")
            return None
    
    def _convolve2d_gpu(self, image: 'cp.ndarray', kernel: 'cp.ndarray') -> 'cp.ndarray':
        """2D convolution on GPU"""
        try:
            import cupy as cp
            
            if kernel is None:
                return image
            
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
        except Exception as e:
            print(f"⚠️ GPU convolution failed: {e}")
            return image
    
    def _dilate_gpu_internal(self, image: 'cp.ndarray', kernel: 'cp.ndarray') -> 'cp.ndarray':
        """Dilation on GPU"""
        try:
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
        except Exception as e:
            print(f"⚠️ GPU dilation failed: {e}")
            return image


# Global safe GPU accelerator instance
safe_gpu_accelerator = SafeGPUAccelerator()
