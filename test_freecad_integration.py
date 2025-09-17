"""
Test FreeCAD Integration
"""
import sys
import os

# Add the virtual environment to the path
venv_path = os.path.join(os.path.dirname(__file__), 'venv_freecad', 'Lib', 'site-packages')
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

def test_pyside2_compat():
    """Test PySide2 compatibility layer"""
    print("🔧 Testing PySide2 compatibility layer...")
    try:
        import pyside2_compat
        print("✅ PySide2 compatibility layer loaded successfully")
        return True
    except Exception as e:
        print(f"❌ PySide2 compatibility layer failed: {e}")
        return False

def test_freecad_import():
    """Test FreeCAD import"""
    print("🔧 Testing FreeCAD import...")
    try:
        # Try to create PySide2 compatibility layer
        import pyside2_compat
        
        # Try to add FreeCAD to Python path
        FREECAD_PATHS = [
            r"C:\Program Files\FreeCAD 1.0\bin",
            r"C:\Program Files\FreeCAD 0.21\bin",
            r"C:\Program Files\FreeCAD 0.20\bin",
        ]

        for path in FREECAD_PATHS:
            if os.path.exists(path) and path not in sys.path:
                sys.path.append(path)
            
            try:
                import FreeCAD
                import Part
                import Draft
                print(f"✅ FreeCAD API loaded successfully from {path}")
                return True
            except ImportError as e:
                print(f"❌ FreeCAD API not available from {path}: {e}")
                continue
        
        print("❌ FreeCAD API not available from any standard location")
        return False
        
    except Exception as e:
        print(f"❌ FreeCAD import test failed: {e}")
        return False

def test_dxf_editor_import():
    """Test DXF editor dialog import"""
    print("🔧 Testing DXF editor dialog import...")
    try:
        from methods.dxf_editor_dialog import DXFEditorDialog, FreeCADWorker
        print("✅ DXF editor dialog imported successfully")
        return True
    except Exception as e:
        print(f"❌ DXF editor dialog import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting FreeCAD Integration Tests...")
    print("=" * 50)
    
    tests = [
        test_pyside2_compat,
        test_freecad_import,
        test_dxf_editor_import,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=" * 50)
    print("📊 Test Results:")
    print(f"   PySide2 Compatibility: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"   FreeCAD Import: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"   DXF Editor Import: {'✅ PASS' if results[2] else '❌ FAIL'}")
    
    if all(results):
        print("\n🎉 All tests passed! FreeCAD integration is working.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
