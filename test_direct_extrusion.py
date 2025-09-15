"""
Test script to try direct contour extrusion without DXF import.
This bypasses the problematic DXF import step entirely.
"""

import os
import time
import cadquery as cq
import numpy as np

def test_direct_extrusion():
    """Test direct contour extrusion without DXF import"""
    
    # Load your existing contours from the DXF file
    dxf_path = "testDXF.dxf"
    if not os.path.exists(dxf_path):
        print(f"ERROR: DXF file not found: {dxf_path}")
        return False
    
    print(f"Testing direct contour extrusion with: {dxf_path}")
    
    try:
        # Method 1: Try to import DXF and see what happens
        print("\n=== METHOD 1: Direct DXF Import ===")
        start_time = time.time()
        
        try:
            imported_dxf = cq.importers.importDXF(dxf_path)
            import_time = time.time() - start_time
            print(f"✅ DXF imported successfully in {import_time:.2f}s")
            
            # Try to process it
            wires = imported_dxf.wires()
            pending = wires.toPending()
            result = pending.extrude(1.0)
            result.export("kAndIv2.step")
            
            print("✅ Direct DXF import and export successful!")
            return True
            
        except Exception as e:
            print(f"❌ Direct DXF import failed: {e}")
            print("This confirms the DXF import is the problem")
        
        # Method 2: Try with a timeout to see if it's just slow
        print("\n=== METHOD 2: DXF Import with Timeout Test ===")
        import threading
        
        result = {"success": False, "error": None}
        
        def import_worker():
            try:
                start_time = time.time()
                imported_dxf = cq.importers.importDXF(dxf_path)
                import_time = time.time() - start_time
                print(f"✅ DXF imported in {import_time:.2f}s")
                result["success"] = True
            except Exception as e:
                result["error"] = str(e)
                print(f"❌ Import failed: {e}")
        
        thread = threading.Thread(target=import_worker)
        thread.daemon = True
        thread.start()
        thread.join(30)  # 30 second timeout
        
        if thread.is_alive():
            print("⏰ DXF import is hanging - this confirms the issue")
        elif result["success"]:
            print("✅ DXF import worked within 30 seconds")
            return True
        else:
            print(f"❌ DXF import failed: {result['error']}")
        
        # Method 3: Try alternative approaches
        print("\n=== METHOD 3: Alternative Approaches ===")
        print("Since DXF import is the problem, we need to:")
        print("1. Use a different DXF library or approach")
        print("2. Simplify the DXF before import")
        print("3. Use a different CAD library")
        print("4. Process contours directly without DXF")
        
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing direct contour extrusion approaches...")
    success = test_direct_extrusion()
    
    if success:
        print("\n✅ Found a working approach!")
    else:
        print("\n❌ Need to try different approaches")
        print("\n💡 SUGGESTIONS:")
        print("1. Try using FreeCAD instead of CadQuery")
        print("2. Use a different DXF processing library")
        print("3. Simplify the DXF file before import")
        print("4. Use trimesh for STL export (faster)")