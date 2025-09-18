"""
ImageEmboss Crash Diagnosis Tool
This script helps identify what's causing the application to crash
"""
import sys
import os
import traceback

def test_import(module_name, description=""):
    """Test importing a module safely"""
    try:
        __import__(module_name)
        print(f"✅ {module_name} - OK {description}")
        return True
    except ImportError as e:
        print(f"❌ {module_name} - FAILED {description}: {e}")
        return False
    except Exception as e:
        print(f"⚠️ {module_name} - ERROR {description}: {e}")
        return False

def test_qt_initialization():
    """Test Qt initialization"""
    print("\n🔍 Testing Qt initialization...")
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        
        print("✅ Qt modules imported successfully")
        
        # Test application creation
        app = QApplication(sys.argv)
        print("✅ QApplication created successfully")
        
        # Test basic widget creation
        from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
        window = QMainWindow()
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("Test")
        
        print("✅ Basic Qt widgets created successfully")
        
        app.quit()
        return True
        
    except Exception as e:
        print(f"❌ Qt initialization failed: {e}")
        traceback.print_exc()
        return False

def test_opencv():
    """Test OpenCV functionality"""
    print("\n🔍 Testing OpenCV...")
    try:
        import cv2
        import numpy as np
        
        # Test basic image operations
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        print("✅ OpenCV basic operations successful")
        return True
        
    except Exception as e:
        print(f"❌ OpenCV test failed: {e}")
        traceback.print_exc()
        return False

def test_gpu():
    """Test GPU functionality"""
    print("\n🔍 Testing GPU acceleration...")
    try:
        import cupy as cp
        print("✅ CuPy imported successfully")
        
        if cp.cuda.is_available():
            print("✅ CUDA is available")
            
            # Test basic GPU operation
            test_array = cp.array([1, 2, 3, 4, 5])
            result = cp.sum(test_array)
            print(f"✅ GPU test successful: {result}")
            return True
        else:
            print("⚠️ CUDA not available")
            return False
            
    except ImportError:
        print("⚠️ CuPy not installed")
        return False
    except Exception as e:
        print(f"❌ GPU test failed: {e}")
        traceback.print_exc()
        return False

def test_core_modules():
    """Test core application modules"""
    print("\n🔍 Testing core modules...")
    
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    modules_to_test = [
        ("config.constants", "Configuration constants"),
        ("config.settings", "Application settings"),
        ("core.models.parameters", "Processing parameters"),
        ("core.models.processing_result", "Processing results"),
        ("core.pipeline", "Processing pipeline"),
        ("core.processors.base_processor", "Base processor"),
        ("core.processors.image_loader", "Image loader"),
        ("core.processors.edge_detector", "Edge detector"),
        ("core.processors.contour_extractor", "Contour extractor"),
        ("core.processors.spline_generator", "Spline generator"),
        ("utils.file_utils", "File utilities"),
        ("utils.math_utils", "Math utilities"),
        ("utils.threading", "Threading utilities"),
    ]
    
    success_count = 0
    for module_name, description in modules_to_test:
        if test_import(module_name, description):
            success_count += 1
    
    print(f"\n📊 Core modules: {success_count}/{len(modules_to_test)} successful")
    return success_count == len(modules_to_test)

def test_ui_modules():
    """Test UI modules"""
    print("\n🔍 Testing UI modules...")
    
    modules_to_test = [
        ("ui.main_window", "Main window"),
        ("ui.panels.original_image_panel", "Original image panel"),
        ("ui.panels.parameter_panel", "Parameter panel"),
        ("ui.panels.preview_panel", "Preview panel"),
        ("ui.panels.model_viewer_panel", "Model viewer panel"),
        ("ui.widgets.custom_controls", "Custom controls"),
        ("ui.widgets.graphics_view", "Graphics view"),
    ]
    
    success_count = 0
    for module_name, description in modules_to_test:
        if test_import(module_name, description):
            success_count += 1
    
    print(f"\n📊 UI modules: {success_count}/{len(modules_to_test)} successful")
    return success_count == len(modules_to_test)

def test_graphics_view():
    """Test graphics view specifically"""
    print("\n🔍 Testing graphics view...")
    try:
        from ui.widgets.graphics_view import ImageGraphicsView
        from PySide6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Test graphics view creation
        view = ImageGraphicsView()
        print("✅ Graphics view created successfully")
        
        # Test with simple image
        import numpy as np
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        view.set_image(test_image)
        print("✅ Graphics view image set successfully")
        
        app.quit()
        return True
        
    except Exception as e:
        print(f"❌ Graphics view test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main diagnosis function"""
    print("🔧 ImageEmboss Crash Diagnosis Tool")
    print("=" * 50)
    
    # Test basic dependencies
    print("\n📦 Testing basic dependencies...")
    basic_deps = [
        ("numpy", "Numerical computing"),
        ("cv2", "OpenCV"),
        ("scipy", "Scientific computing"),
        ("ezdxf", "DXF export"),
        ("PIL", "Pillow image processing"),
        ("PySide6", "Qt GUI framework"),
    ]
    
    basic_success = 0
    for module, desc in basic_deps:
        if test_import(module, desc):
            basic_success += 1
    
    print(f"\n📊 Basic dependencies: {basic_success}/{len(basic_deps)} successful")
    
    # Test optional dependencies
    print("\n📦 Testing optional dependencies...")
    optional_deps = [
        ("numba", "JIT compilation"),
        ("cupy", "GPU acceleration"),
        ("trimesh", "3D mesh processing"),
        ("meshio", "Mesh I/O"),
    ]
    
    optional_success = 0
    for module, desc in optional_deps:
        if test_import(module, desc):
            optional_success += 1
    
    print(f"\n📊 Optional dependencies: {optional_success}/{len(optional_deps)} successful")
    
    # Test Qt
    qt_ok = test_qt_initialization()
    
    # Test OpenCV
    opencv_ok = test_opencv()
    
    # Test GPU
    gpu_ok = test_gpu()
    
    # Test core modules
    core_ok = test_core_modules()
    
    # Test UI modules
    ui_ok = test_ui_modules()
    
    # Test graphics view specifically
    graphics_ok = test_graphics_view()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 DIAGNOSIS SUMMARY")
    print("=" * 50)
    
    print(f"Basic Dependencies: {'✅' if basic_success == len(basic_deps) else '❌'} ({basic_success}/{len(basic_deps)})")
    print(f"Optional Dependencies: {'✅' if optional_success > 0 else '⚠️'} ({optional_success}/{len(optional_deps)})")
    print(f"Qt Initialization: {'✅' if qt_ok else '❌'}")
    print(f"OpenCV: {'✅' if opencv_ok else '❌'}")
    print(f"GPU Acceleration: {'✅' if gpu_ok else '⚠️'}")
    print(f"Core Modules: {'✅' if core_ok else '❌'}")
    print(f"UI Modules: {'✅' if ui_ok else '❌'}")
    print(f"Graphics View: {'✅' if graphics_ok else '❌'}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    if basic_success < len(basic_deps):
        print("❌ Install missing basic dependencies:")
        print("   pip install -r requirements.txt")
    
    if not qt_ok:
        print("❌ Qt initialization failed - this is likely the main issue")
        print("   Try reinstalling PySide6: pip install --upgrade PySide6")
    
    if not graphics_ok:
        print("❌ Graphics view failed - this could cause crashes")
        print("   Try using the safe mode: python main_safe.py")
    
    if not core_ok or not ui_ok:
        print("❌ Core/UI modules failed - check for import errors")
        print("   Make sure all files are in the correct locations")
    
    if not gpu_ok:
        print("⚠️ GPU acceleration not available (optional)")
        print("   Install CUDA and CuPy for GPU acceleration")
    
    print("\n🚀 NEXT STEPS:")
    if qt_ok and basic_success == len(basic_deps):
        print("1. Try running the safe mode: python main_safe.py")
        print("2. If safe mode works, the issue is in the main application")
        print("3. Check the graphics view implementation")
    else:
        print("1. Fix the failing dependencies first")
        print("2. Reinstall PySide6 if Qt is failing")
        print("3. Run this diagnosis again")

if __name__ == "__main__":
    main()
