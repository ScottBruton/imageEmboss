"""
ImageEmboss - Image to DXF Converter
Main application entry point
"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from ui.main_window import ImageEmbossMainWindow
from config.constants import APP_NAME, APP_VERSION
from utils.gpu_accelerator import gpu_accelerator


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import scipy
    except ImportError:
        missing_deps.append("scipy")
    
    try:
        import ezdxf
    except ImportError:
        missing_deps.append("ezdxf")
    
    try:
        from PySide6 import QtWidgets
    except ImportError:
        missing_deps.append("PySide6")
    
    if missing_deps:
        print("❌ Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\nPlease install missing dependencies:")
        print("pip install -r requirements.txt")
        return False
    
    return True


def setup_application():
    """Setup Qt application"""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("ImageEmboss")
    
    # Set application font
    font = QFont("Arial", 9)
    app.setFont(font)
    
    # Set application style
    app.setStyle('Fusion')
    
    return app


def show_startup_info():
    """Show startup information"""
    print(f"🚀 Starting {APP_NAME} v{APP_VERSION}")
    print("=" * 50)
    
    # Check GPU availability
    gpu_info = gpu_accelerator.get_gpu_info()
    if gpu_info['available']:
        print(f"✅ GPU acceleration available: {gpu_info['name']}")
        print(f"   Memory: {gpu_info['memory_gb']:.1f}GB")
    else:
        print("⚠️ GPU acceleration not available")
        print("   Install CUDA and CuPy for GPU acceleration")
    
    # Check FreeCAD
    try:
        from utils.file_utils import get_freecad_path
        freecad_path = get_freecad_path()
        if freecad_path:
            print(f"✅ FreeCAD found: {freecad_path}")
        else:
            print("⚠️ FreeCAD not found - 3D export will be disabled")
            print("   Download from: https://www.freecadweb.org/downloads.php")
    except Exception as e:
        print(f"⚠️ Error checking FreeCAD: {e}")
    
    print("=" * 50)


def main():
    """Main application entry point"""
    try:
        # Check dependencies
        if not check_dependencies():
            return 1
        
        # Show startup info
        show_startup_info()
        
        # Setup application
        app = setup_application()
        
        # Create main window
        main_window = ImageEmbossMainWindow()
        main_window.show()
        
        # Show welcome message
        QMessageBox.information(
            main_window, 
            f"Welcome to {APP_NAME}",
            f"Welcome to {APP_NAME} v{APP_VERSION}!\n\n"
            "To get started:\n"
            "1. Click 'Select Image' to load an image\n"
            "2. Adjust parameters as needed\n"
            "3. Click 'Export DXF' to create smooth spline DXF files\n"
            "4. Use 'Export STEP' for 3D models\n\n"
            "For best results, use high-contrast images with clear edges."
        )
        
        # Run application
        return app.exec()
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
