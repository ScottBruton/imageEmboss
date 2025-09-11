# ImageEmboss PySide6 - Usage Guide

## 🚀 **Quick Start**

### **Installation**
```bash
pip install -r requirements_pyside6.txt
```

### **Running the Application**
```bash
python imageEmboss_pyside6.py
```

## 🎨 **Drawing Tools**

### **Tool Selection**
Use the toolbar buttons in the DXF Preview panel:

- **👁️ View Tool**: Pan and zoom (default mode)
- **✏️ Paint Tool**: Draw freehand lines
- **🧽 Eraser Tool**: Erase parts of contours
- **📏 Line Tool**: Draw straight lines
- **📐 Shape Tool**: Draw rectangles, triangles, circles

### **Drawing Instructions**

#### **Paint Tool (✏️)**
1. Click the paint tool button
2. Click and drag to draw freehand lines
3. Release to finish the stroke

#### **Line Tool (📏)**
1. Click the line tool button
2. Click to start the line
3. Drag to see preview
4. Release to finish the line

#### **Shape Tools (📐)**
1. Select shape type from dropdown (rectangle, triangle, circle)
2. Click the shape tool button
3. Click and drag to create the shape
4. Release to finish

#### **Eraser Tool (🧽)**
1. Click the eraser tool button
2. Click on any drawing item to erase it
3. Drag to erase multiple items

## 🖼️ **Image Processing**

### **Loading Images**
- **File Menu**: File → Load Image (Ctrl+O)
- **Button**: Click "Select Image" button
- **Supported formats**: JPG, PNG, BMP, TIF, WEBP

### **Parameter Adjustment**
Use the sliders in the Parameters panel:

- **Bilateral Diameter**: Controls noise reduction
- **Bilateral Color σ**: Controls color similarity threshold
- **Gaussian Kernel**: Controls blur amount
- **Canny Lower/Upper**: Controls edge detection sensitivity
- **Edge Thickness**: Controls line thickness
- **Gap Threshold**: Connects nearby contour segments
- **Largest N**: Number of contours to keep
- **Simplify %**: Reduces contour complexity
- **Scale (mm/px)**: DXF output scale
- **Invert**: Inverts black/white values

### **Presets**
Select from the Master Preset dropdown:
- **Default**: Balanced settings
- **High Detail**: For fine textures
- **Low Noise**: Reduces grain
- **Custom**: Your manual adjustments

## 🔍 **Navigation**

### **Zoom Controls**
- **+ Button**: Zoom in
- **- Button**: Zoom out
- **1:1 Button**: Reset to fit
- **Mouse Wheel**: Zoom in/out at cursor position

### **Pan Controls**
- **Arrow Buttons**: Pan in directions
- **⌂ Button**: Reset pan position
- **Mouse Drag**: Pan when in view mode

## 💾 **Export**

### **DXF Export**
1. Adjust export scale if needed
2. Click "Export DXF" button (Ctrl+E)
3. Choose save location
4. All contours and drawings will be included

### **Export Scale**
- Controls the output size of the DXF
- 1.0 = original size
- 0.5 = half size
- 2.0 = double size

## ⌨️ **Keyboard Shortcuts**

- **Ctrl+O**: Load Image
- **Ctrl+E**: Export DXF
- **Ctrl+Q**: Quit Application

## 🎯 **Tips**

1. **Start with presets** - they're optimized for different image types
2. **Use zoom** - zoom in for detailed work, zoom out for overview
3. **Combine tools** - use drawing tools to add missing details
4. **Adjust parameters** - fine-tune settings for your specific image
5. **Save frequently** - export your work regularly

## 🔧 **Troubleshooting**

### **No contours detected**
- Try adjusting Canny thresholds
- Check if invert setting is correct
- Increase edge thickness

### **Too many small contours**
- Increase "Largest N" to keep fewer contours
- Increase "Simplify %" to reduce complexity
- Adjust gap threshold

### **Missing details**
- Decrease "Simplify %"
- Lower Canny thresholds
- Use drawing tools to add details

### **Application won't start**
- Check PySide6 installation: `pip install PySide6`
- Verify all dependencies are installed
- Check Python version (3.8+ recommended)

## 📁 **File Structure**
```
imageEmboss_pyside6.py     # Main application
requirements_pyside6.txt   # Dependencies
test_pyside6.py           # Test script
USAGE_GUIDE_PYSIDE6.md    # This guide
```

Enjoy creating beautiful DXF files from your images! 🎨✨
