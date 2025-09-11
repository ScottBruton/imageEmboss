#!/usr/bin/env python3
"""
Test script for the PySide6 version of ImageEmboss
"""

import sys
import os

# Add the current directory to the path so we can import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from imageEmboss_pyside6 import main
    
    print("✅ PySide6 version loaded successfully!")
    print("🚀 Starting ImageEmboss PySide6 application...")
    
    # Run the application
    main()
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure PySide6 is installed: pip install PySide6")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error running application: {e}")
    sys.exit(1)
