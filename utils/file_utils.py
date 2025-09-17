"""
File utility functions
"""
import os
import shutil
from typing import List, Optional


def get_supported_image_formats() -> List[str]:
    """Get list of supported image formats"""
    return ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']


def is_supported_image(file_path: str) -> bool:
    """Check if file is a supported image format"""
    if not os.path.exists(file_path):
        return False
    
    ext = os.path.splitext(file_path)[1].lower()
    return ext in get_supported_image_formats()


def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    if not os.path.exists(file_path):
        return 0.0
    
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


def create_output_path(input_path: str, suffix: str, extension: str) -> str:
    """Create output path with suffix and extension"""
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_dir = os.path.dirname(input_path)
    return os.path.join(output_dir, f"{base_name}_{suffix}.{extension}")


def ensure_directory_exists(directory: str):
    """Ensure directory exists, create if not"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def clean_temp_files(directory: str, pattern: str = "*.tmp"):
    """Clean temporary files from directory"""
    try:
        import glob
        temp_files = glob.glob(os.path.join(directory, pattern))
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
    except:
        pass


def get_freecad_path() -> Optional[str]:
    """Find FreeCAD executable path"""
    try:
        # Try which command first
        import shutil
        freecad_path = shutil.which('freecad')
        if freecad_path:
            return freecad_path
        
        # Try common Windows paths
        common_paths = [
            r"C:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe",
            r"C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe",
            r"C:\Program Files\FreeCAD 0.20\bin\FreeCAD.exe",
            r"C:\Program Files\FreeCAD\bin\FreeCAD.exe"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
        
    except Exception:
        return None


def validate_image_file(file_path: str) -> tuple[bool, str]:
    """Validate image file and return (is_valid, error_message)"""
    if not file_path:
        return False, "No file path provided"
    
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    if not is_supported_image(file_path):
        return False, f"Unsupported image format: {os.path.splitext(file_path)[1]}"
    
    file_size = get_file_size_mb(file_path)
    if file_size > 100:  # 100MB limit
        return False, f"File too large: {file_size:.1f}MB (max 100MB)"
    
    return True, ""
