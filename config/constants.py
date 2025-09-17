"""
Application constants
"""
from typing import Dict, Any

# Application info
APP_NAME = "ImageEmboss"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Image to DXF Converter with Smooth Splines"

# File formats
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
SUPPORTED_EXPORT_FORMATS = ['.dxf', '.step', '.stl', '.obj']

# Processing limits
MAX_IMAGE_SIZE = 10000  # Maximum image dimension in pixels
MAX_FILE_SIZE_MB = 100  # Maximum file size in MB
MIN_CONTOUR_AREA = 100  # Minimum contour area in pixels
MAX_CONTOURS = 100  # Maximum number of contours to process

# UI constants
DEFAULT_WINDOW_WIDTH = 1600
DEFAULT_WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 800

# Panel sizes
LEFT_PANEL_WIDTH = 400
RIGHT_PANEL_WIDTH = 1200
PREVIEW_PANEL_HEIGHT = 600
MODEL_VIEWER_HEIGHT = 400
EXPORT_CONTROLS_HEIGHT = 200

# Processing parameters
DEFAULT_MM_PER_PX = 0.25
DEFAULT_EXTRUDE_HEIGHT = 1.0
DEFAULT_SPLINE_QUALITY = "high"

# Threading
DEBOUNCE_DELAY_MS = 300
PROCESSING_TIMEOUT_SEC = 300

# GPU settings
GPU_MEMORY_LIMIT_GB = 8.0
GPU_FALLBACK_ENABLED = True

# Export settings
DXF_VERSION = "R2010"
STEP_VERSION = "AP214"

# Color schemes
COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'accent': '#F18F01',
    'success': '#C73E1D',
    'warning': '#F18F01',
    'error': '#C73E1D',
    'background': '#F5F5F5',
    'surface': '#FFFFFF',
    'text': '#333333',
    'text_secondary': '#666666'
}

# Status messages
STATUS_MESSAGES = {
    'ready': 'Ready',
    'loading': 'Loading image...',
    'processing': 'Processing...',
    'exporting': 'Exporting...',
    'completed': 'Processing completed',
    'error': 'Error occurred',
    'cancelled': 'Processing cancelled'
}

# Tooltips
TOOLTIPS = {
    'bilateral_diameter': 'Diameter of bilateral filter (odd number)',
    'bilateral_sigma_color': 'Color sigma for bilateral filter',
    'bilateral_sigma_space': 'Space sigma for bilateral filter',
    'gaussian_kernel_size': 'Size of Gaussian blur kernel (odd number)',
    'canny_lower_threshold': 'Lower threshold for Canny edge detection',
    'canny_upper_threshold': 'Upper threshold for Canny edge detection',
    'edge_thickness': 'Thickness of detected edges',
    'gap_threshold': 'Threshold for closing gaps in contours',
    'largest_n': 'Number of largest contours to keep',
    'simplify_pct': 'Percentage of contour simplification',
    'mm_per_px': 'Millimeters per pixel for export scaling',
    'extrude_height': 'Height for 3D extrusion in mm',
    'use_splines': 'Export smooth splines instead of polylines',
    'spline_quality': 'Quality of spline generation'
}

# Error messages
ERROR_MESSAGES = {
    'no_image': 'No image loaded',
    'invalid_image': 'Invalid image format',
    'file_not_found': 'File not found',
    'processing_failed': 'Processing failed',
    'export_failed': 'Export failed',
    'gpu_not_available': 'GPU acceleration not available',
    'freecad_not_found': 'FreeCAD not found',
    'scipy_not_available': 'SciPy not available for spline generation'
}

# Success messages
SUCCESS_MESSAGES = {
    'image_loaded': 'Image loaded successfully',
    'processing_completed': 'Processing completed successfully',
    'dxf_exported': 'DXF file exported successfully',
    'step_exported': 'STEP file exported successfully',
    'stl_exported': 'STL file exported successfully',
    'obj_exported': 'OBJ file exported successfully'
}

# Progress messages
PROGRESS_MESSAGES = {
    'loading_image': 'Loading image...',
    'detecting_edges': 'Detecting edges...',
    'extracting_contours': 'Extracting contours...',
    'generating_splines': 'Generating smooth splines...',
    'exporting_dxf': 'Exporting DXF...',
    'exporting_step': 'Exporting STEP...',
    'exporting_stl': 'Exporting STL...',
    'exporting_obj': 'Exporting OBJ...'
}

# Keyboard shortcuts
KEYBOARD_SHORTCUTS = {
    'open_file': 'Ctrl+O',
    'save_dxf': 'Ctrl+S',
    'export_step': 'Ctrl+E',
    'export_stl': 'Ctrl+T',
    'export_obj': 'Ctrl+J',
    'undo': 'Ctrl+Z',
    'redo': 'Ctrl+Y',
    'reset_parameters': 'Ctrl+R',
    'toggle_splines': 'Ctrl+P',
    'toggle_gpu': 'Ctrl+G',
    'zoom_fit': 'Ctrl+0',
    'zoom_in': 'Ctrl+=',
    'zoom_out': 'Ctrl+-',
    'quit': 'Ctrl+Q'
}

# Menu structure
MENU_STRUCTURE = {
    'File': [
        ('Open Image', 'open_file', 'Ctrl+O'),
        ('Recent Files', 'recent_files', None),
        ('---', None, None),
        ('Export DXF', 'export_dxf', 'Ctrl+S'),
        ('Export STEP', 'export_step', 'Ctrl+E'),
        ('Export STL', 'export_stl', 'Ctrl+T'),
        ('Export OBJ', 'export_obj', 'Ctrl+J'),
        ('---', None, None),
        ('Exit', 'quit', 'Ctrl+Q')
    ],
    'Edit': [
        ('Undo', 'undo', 'Ctrl+Z'),
        ('Redo', 'redo', 'Ctrl+Y'),
        ('---', None, None),
        ('Reset Parameters', 'reset_parameters', 'Ctrl+R')
    ],
    'View': [
        ('Zoom Fit', 'zoom_fit', 'Ctrl+0'),
        ('Zoom In', 'zoom_in', 'Ctrl+='),
        ('Zoom Out', 'zoom_out', 'Ctrl+-'),
        ('---', None, None),
        ('Toggle Splines', 'toggle_splines', 'Ctrl+P'),
        ('Toggle GPU', 'toggle_gpu', 'Ctrl+G')
    ],
    'Tools': [
        ('Circle Tool', 'circle_tool', None),
        ('Merge Tool', 'merge_tool', None),
        ('Settings Lock', 'settings_lock', None)
    ],
    'Help': [
        ('About', 'about', None),
        ('Documentation', 'documentation', None),
        ('Check for Updates', 'check_updates', None)
    ]
}
