import sys
import os

# Add the virtual environment to the path
venv_path = os.path.join(os.path.dirname(__file__), 'venv_freecad', 'Lib', 'site-packages')
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

try:
    import PySide6
    from PySide6 import QtCore, QtGui, QtWidgets
    
    # Create PySide2 as an alias to PySide6
    sys.modules['PySide2'] = PySide6
    sys.modules['PySide2.QtCore'] = QtCore
    sys.modules['PySide2.QtGui'] = QtGui
    sys.modules['PySide2.QtWidgets'] = QtWidgets
    print("✅ PySide2 compatibility layer created")
except ImportError as e:
    print(f"❌ Failed to create PySide2 compatibility: {e}")
