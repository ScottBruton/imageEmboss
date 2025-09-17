"""
Parameter models for ImageEmboss
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ProcessingParameters:
    """Parameters for image processing pipeline"""
    
    # Image loading
    image_path: str = ""
    
    # Bilateral filtering
    bilateral_diameter: int = 9
    bilateral_sigma_color: int = 75
    bilateral_sigma_space: int = 75
    
    # Gaussian blur
    gaussian_kernel_size: int = 5
    
    # Canny edge detection
    canny_lower_threshold: int = 30
    canny_upper_threshold: int = 100
    
    # Edge processing
    edge_thickness: float = 3.0
    gap_threshold: float = 0.0
    
    # Contour processing
    largest_n: int = 10
    simplify_pct: float = 0.0
    
    # Export settings
    mm_per_px: float = 0.25
    invert: bool = True
    
    # Spline settings
    use_splines: bool = True
    spline_quality: str = "high"  # "high", "medium", "low"
    
    # 3D export settings
    extrude_height: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameters to dictionary"""
        return {
            'bilateral_diameter': self.bilateral_diameter,
            'bilateral_sigma_color': self.bilateral_sigma_color,
            'bilateral_sigma_space': self.bilateral_sigma_space,
            'gaussian_kernel_size': self.gaussian_kernel_size,
            'canny_lower_threshold': self.canny_lower_threshold,
            'canny_upper_threshold': self.canny_upper_threshold,
            'edge_thickness': self.edge_thickness,
            'gap_threshold': self.gap_threshold,
            'largest_n': self.largest_n,
            'simplify_pct': self.simplify_pct,
            'mm_per_px': self.mm_per_px,
            'invert': self.invert,
            'use_splines': self.use_splines,
            'spline_quality': self.spline_quality,
            'extrude_height': self.extrude_height
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingParameters':
        """Create parameters from dictionary"""
        return cls(**data)
    
    def copy(self) -> 'ProcessingParameters':
        """Create a copy of parameters"""
        return ProcessingParameters(**self.to_dict())


# Preset configurations
PRESET_CONFIGS = {
    "Default": {
        "bilateral_diameter": 9,
        "bilateral_sigma_color": 75,
        "bilateral_sigma_space": 75,
        "gaussian_kernel_size": 5,
        "canny_lower_threshold": 30,
        "canny_upper_threshold": 100,
        "edge_thickness": 3.0,
        "gap_threshold": 0.0,
        "largest_n": 10,
        "simplify_pct": 0.0,
        "mm_per_px": 0.25,
        "invert": True,
        "use_splines": True,
        "spline_quality": "high",
        "extrude_height": 1.0
    },
    "High Detail": {
        "bilateral_diameter": 5,
        "bilateral_sigma_color": 50,
        "bilateral_sigma_space": 50,
        "gaussian_kernel_size": 3,
        "canny_lower_threshold": 20,
        "canny_upper_threshold": 80,
        "edge_thickness": 2.0,
        "gap_threshold": 2.0,
        "largest_n": 20,
        "simplify_pct": 20.0,
        "mm_per_px": 0.25,
        "invert": True,
        "use_splines": True,
        "spline_quality": "high",
        "extrude_height": 1.0
    },
    "Low Noise": {
        "bilateral_diameter": 15,
        "bilateral_sigma_color": 100,
        "bilateral_sigma_space": 100,
        "gaussian_kernel_size": 7,
        "canny_lower_threshold": 50,
        "canny_upper_threshold": 150,
        "edge_thickness": 4.0,
        "gap_threshold": 5.0,
        "largest_n": 5,
        "simplify_pct": 40.0,
        "mm_per_px": 0.25,
        "invert": True,
        "use_splines": True,
        "spline_quality": "medium",
        "extrude_height": 1.0
    },
    "Architecture": {
        "bilateral_diameter": 7,
        "bilateral_sigma_color": 60,
        "bilateral_sigma_space": 60,
        "gaussian_kernel_size": 3,
        "canny_lower_threshold": 40,
        "canny_upper_threshold": 120,
        "edge_thickness": 2.0,
        "gap_threshold": 3.0,
        "largest_n": 15,
        "simplify_pct": 30.0,
        "mm_per_px": 0.25,
        "invert": True,
        "use_splines": True,
        "spline_quality": "high",
        "extrude_height": 1.0
    },
    "Nature": {
        "bilateral_diameter": 11,
        "bilateral_sigma_color": 80,
        "bilateral_sigma_space": 80,
        "gaussian_kernel_size": 5,
        "canny_lower_threshold": 25,
        "canny_upper_threshold": 90,
        "edge_thickness": 3.0,
        "gap_threshold": 4.0,
        "largest_n": 8,
        "simplify_pct": 35.0,
        "mm_per_px": 0.25,
        "invert": True,
        "use_splines": True,
        "spline_quality": "high",
        "extrude_height": 1.0
    }
}
