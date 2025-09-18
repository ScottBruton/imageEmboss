# ImageEmboss Troubleshooting Guide

## Application Crashes on Startup

If your ImageEmboss application crashes with "Python has stopped working", follow these steps:

### Step 1: Run Crash Diagnosis

1. **Run the diagnosis tool**:
   ```bash
   python diagnose_crash.py
   ```
   Or double-click `diagnose.bat`

2. **Check the output** for any failed dependencies or modules

### Step 2: Try Safe Mode

1. **Run the safe mode version**:
   ```bash
   python main_safe.py
   ```
   Or double-click `run_safe.bat`

2. **Check the log area** for any error messages

3. **Test basic functionality**:
   - Try loading an image
   - Test the processing pipeline
   - Check if DXF export works

### Step 3: Try Simplified Version

1. **Run the simplified version**:
   ```bash
   python main_simple.py
   ```
   Or double-click `run_simple.bat`

2. **This version removes complex features** that might cause crashes

### Step 4: Check Dependencies

#### Required Dependencies
```bash
pip install opencv-python numpy scipy ezdxf Pillow PySide6
```

#### Optional Dependencies
```bash
pip install numba  # For performance
pip install cupy-cuda12x  # For GPU acceleration (requires CUDA)
pip install trimesh meshio  # For 3D processing
```

### Step 5: Common Issues and Solutions

#### Issue: "PySide6 not found"
**Solution**: Reinstall PySide6
```bash
pip uninstall PySide6
pip install PySide6
```

#### Issue: "OpenCV not found"
**Solution**: Install OpenCV
```bash
pip install opencv-python
```

#### Issue: "SciPy not found"
**Solution**: Install SciPy
```bash
pip install scipy
```

#### Issue: GPU-related crashes
**Solution**: Disable GPU acceleration
1. Use the safe mode version
2. Or modify the code to skip GPU initialization

#### Issue: Graphics view crashes
**Solution**: Use simplified graphics view
1. The simplified version uses basic QGraphicsView
2. Avoid complex graphics operations

#### Issue: Memory issues
**Solution**: Reduce image size or processing complexity
1. Use smaller images
2. Reduce the number of contours
3. Lower processing quality settings

### Step 6: System Requirements

#### Minimum Requirements
- Windows 10/11
- Python 3.11.9 or higher
- 4GB RAM
- 1GB free disk space

#### Recommended Requirements
- Windows 11
- Python 3.11.9 or higher
- 8GB RAM
- NVIDIA GPU with CUDA support
- 2GB free disk space

### Step 7: Virtual Environment

If you're having dependency conflicts:

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

2. **Activate it**:
   ```bash
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Step 8: Debug Mode

To get more detailed error information:

1. **Run with debug output**:
   ```bash
   python -u main.py 2>&1 | tee debug.log
   ```

2. **Check the debug.log file** for detailed error messages

### Step 9: Alternative Versions

If the main application still crashes:

1. **Use the safe mode** (`main_safe.py`) - Has crash protection
2. **Use the simplified version** (`main_simple.py`) - Removes complex features
3. **Use the original version** (`imageEmboss.py`) - Tkinter-based version

### Step 10: Getting Help

If none of the above solutions work:

1. **Run the diagnosis tool** and save the output
2. **Check the console output** for error messages
3. **Try the safe mode** and note any errors in the log
4. **Create an issue** with:
   - Diagnosis output
   - Error messages
   - System information
   - Steps to reproduce

## Performance Issues

### Slow Processing
1. **Enable GPU acceleration** (if available)
2. **Reduce image size**
3. **Lower processing quality**
4. **Use fewer contours**

### Memory Issues
1. **Close other applications**
2. **Use smaller images**
3. **Reduce processing complexity**
4. **Restart the application**

## Export Issues

### DXF Export Fails
1. **Check if ezdxf is installed**
2. **Verify image has contours**
3. **Try different export settings**
4. **Check file permissions**

### 3D Export Fails
1. **Install FreeCAD** from official website
2. **Check FreeCAD path** in settings
3. **Try different 3D formats**
4. **Use simplified 3D export**

## UI Issues

### Interface Not Responsive
1. **Check if processing is running**
2. **Wait for processing to complete**
3. **Try canceling and restarting**
4. **Use the simplified version**

### Graphics View Issues
1. **Try the simplified graphics view**
2. **Update graphics drivers**
3. **Use software rendering**
4. **Disable hardware acceleration**

## File Issues

### Cannot Load Images
1. **Check file format** (PNG, JPG, BMP, TIFF supported)
2. **Check file size** (not too large)
3. **Check file permissions**
4. **Try different image files**

### Cannot Save Files
1. **Check write permissions**
2. **Check disk space**
3. **Try different save location**
4. **Check file path length**

## Network Issues

### Cannot Download Dependencies
1. **Check internet connection**
2. **Use different package index**
3. **Try offline installation**
4. **Check firewall settings**

## Still Having Issues?

1. **Run the diagnosis tool** and save the output
2. **Try all the alternative versions**
3. **Check system requirements**
4. **Create a detailed issue report** with:
   - Operating system version
   - Python version
   - Diagnosis output
   - Error messages
   - Steps to reproduce
   - What you've already tried

Remember: The safe mode and simplified versions are designed to work even when the main application crashes. Use them to identify the specific issue causing the crash.
