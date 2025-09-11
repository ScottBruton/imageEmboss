# Windowed Fullscreen and Error Fixes

## ✅ **Issues Fixed:**

### **1. Windowed Fullscreen Mode**
**Problem:** App was starting in exclusive fullscreen mode (no title bar, no window controls).

**Solution:** Changed from `showFullScreen()` to `showMaximized()`:
```python
# Before (exclusive fullscreen):
self.showFullScreen()

# After (windowed fullscreen):
self.showMaximized()
```

### **2. Missing QLineF Import**
**Problem:** `NameError: name 'QLineF' is not defined` when using drawing tools.

**Solution:** Added `QLineF` to imports:
```python
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPoint, QRect, QSize, QPointF, QMimeData, QLineF
```

### **3. Wrong Attribute Name**
**Problem:** `AttributeError: 'ImageEmbossGUI' object has no attribute 'shape_type_combo'`.

**Solution:** Fixed attribute name from `shape_type_combo` to `shape_combo`:
```python
# Before (error):
shape_type = self.shape_type_combo.currentText()

# After (fixed):
shape_type = self.shape_combo.currentText()
```

## 🎯 **Result:**

### **✅ Now Working:**
- **Windowed fullscreen mode** - App starts maximized with title bar and window controls
- **Drawing tools work** - No more QLineF errors when using line/shape tools
- **Shape selection works** - No more attribute errors when changing shape types
- **Auto-fit images** - Images still automatically fit to available space
- **Resizable window** - Can minimize, maximize, and resize normally

### **📐 Window Behavior:**
- **Starts maximized** with title bar visible
- **Has window controls** (minimize, maximize, close buttons)
- **Can be resized** by dragging edges or using window controls
- **Images auto-fit** when window is resized
- **True windowed mode** - not exclusive fullscreen

The application now starts in proper windowed fullscreen mode with all drawing tools working correctly! 🎯✨
