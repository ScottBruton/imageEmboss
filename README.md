# ImageEmboss - Image to DXF Converter

A professional Python application that converts images to smooth spline-based DXF files and 3D models with real-time preview and GPU acceleration.

## Features

### 🎨 **Smooth Spline Generation**
- Converts all contours to smooth B-splines using SciPy
- No jagged segments - everything is smooth curves
- Closed contours only for professional DXF output
- Adjustable spline quality (high, medium, low)

### 🚀 **Performance Optimized**
- **GPU Acceleration** with CuPy for 3-5x faster processing
- **Multithreading** for responsive UI (no freezing)
- **Real-time preview** with 60 FPS updates
- **Debounced processing** to prevent excessive operations

### 🎯 **Professional Output**
- **DXF Export** with smooth splines (AutoCAD compatible)
- **3D Export** via FreeCAD integration (STEP, STL, OBJ)
- **Scale control** (mm per pixel)
- **Multiple export formats**

### 🖥️ **Modern UI**
- **Intuitive interface** with parameter presets
- **Real-time preview** of DXF and 3D models
- **Editing tools** (Circle tool, Merge tool, Settings lock)
- **Professional appearance** with modern design

## Installation

### Prerequisites
- Python 3.11.9 or higher
- Windows 10/11 (tested on Windows)
- NVIDIA GPU (optional, for GPU acceleration)

### Quick Start
1. **Clone or download** the project
2. **Run the installer**:
   ```bash
   python install_packages.py
   ```
3. **Start the application**:
   ```bash
   python main.py
   ```

### Manual Installation
```bash
# Core dependencies
pip install opencv-python numpy scipy ezdxf Pillow PySide6

# Performance optimization
pip install numba

# GPU acceleration (optional)
pip install cupy-cuda12x

# 3D visualization (optional)
pip install PyOpenGL PyOpenGL-accelerate trimesh meshio
```

### FreeCAD Integration
1. Download FreeCAD 1.0 from: https://www.freecadweb.org/downloads.php
2. Install FreeCAD
3. The application will automatically detect FreeCAD for 3D export

## Usage

### Basic Workflow
1. **Load Image**: Click "Select Image" to load your image
2. **Adjust Parameters**: Use the parameter panel to fine-tune processing
3. **Preview Results**: See real-time preview of DXF and 3D models
4. **Export Files**: Click "Export DXF" or "Export STEP" to save files

### Parameter Presets
- **Default**: Balanced settings for most images
- **High Detail**: Maximum detail preservation
- **Low Noise**: Noise reduction for clean images
- **Architecture**: Optimized for architectural drawings
- **Nature**: Optimized for natural images

### Key Parameters
- **Bilateral Filter**: Noise reduction while preserving edges
- **Canny Thresholds**: Edge detection sensitivity
- **Edge Thickness**: Thickness of detected edges
- **Gap Threshold**: Gap closing for continuous contours
- **Largest N**: Number of contours to keep
- **Simplification %**: Contour simplification level
- **mm per pixel**: Scale for export (mm per pixel)
- **Use Splines**: Enable smooth spline generation

### Editing Tools
- **🎯 Circle Tool**: Select area for processing
- **🔗 Merge Tool**: Merge overlapping contours
- **🔒 Settings Lock**: Lock settings for area processing

## Architecture

### Design Patterns
- **Pipeline Pattern**: Sequential processing steps
- **Observer Pattern**: Real-time UI updates
- **Strategy Pattern**: Algorithm selection
- **Command Pattern**: Undo/redo functionality
- **Factory Pattern**: Exporter creation
- **MVC Pattern**: Overall structure

### Module Structure
```
ImageEmboss/
├── core/                    # Core processing logic
│   ├── pipeline.py         # Main processing pipeline
│   ├── processors/         # Processing steps
│   └── models/            # Data models
├── ui/                     # User interface
│   ├── main_window.py     # Main application window
│   ├── panels/            # UI panels
│   ├── widgets/           # Custom widgets
│   └── dialogs/           # Dialog boxes
├── utils/                  # Utilities
│   ├── threading.py       # Threading utilities
│   ├── gpu_accelerator.py # GPU acceleration
│   └── file_utils.py      # File operations
├── config/                 # Configuration
│   ├── settings.py        # Application settings
│   └── constants.py       # Constants
└── main.py                # Application entry point
```

### Processing Pipeline
```
Image → Edge Detection → Contour Extraction → Spline Generation → DXF Export → STEP Export
```

## Performance

### GPU Acceleration
- **CuPy integration** for GPU computing
- **Automatic fallback** to CPU if GPU not available
- **3-5x performance improvement** when GPU available
- **Memory efficient** GPU operations

### Multithreading
- **UI thread**: Only UI updates, no blocking operations
- **Processing thread**: All image processing in background
- **Debounced updates**: 300ms delay to prevent excessive processing
- **Progress feedback**: Real-time status updates

### Optimization
- **Lazy loading** of heavy components
- **Memory efficient** image processing
- **Optimized algorithms** for each step
- **Caching** of expensive operations

## File Formats

### Input Formats
- **Images**: JPEG, PNG, BMP, TIFF
- **Drag and drop** support
- **Large image** support (4K+)

### Output Formats
- **DXF**: AutoCAD format with smooth splines
- **STEP**: 3D CAD format via FreeCAD
- **STL**: 3D printing format
- **OBJ**: 3D model format

## Troubleshooting

### Common Issues

**"SciPy not available"**
- Install SciPy: `pip install scipy`
- Required for smooth spline generation

**"FreeCAD not found"**
- Download and install FreeCAD from official website
- Required for 3D export (STEP, STL, OBJ)

**"GPU acceleration not available"**
- Install CUDA toolkit from NVIDIA
- Install CuPy: `pip install cupy-cuda12x`
- GPU acceleration is optional

**"Application freezes during processing"**
- This should not happen with the new multithreading
- If it does, check if you're using the latest version

### Performance Tips
1. **Use GPU acceleration** if available
2. **Adjust parameters** based on image type
3. **Use appropriate presets** for your image type
4. **Close other applications** for maximum performance

## Development

### Building from Source
```bash
git clone <repository>
cd ImageEmboss
python install_packages.py
python main.py
```

### Testing
```bash
# Run with test images
python main.py

# Test specific components
python -c "from core.pipeline import ImageProcessingPipeline; print('Pipeline OK')"
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **OpenCV** for image processing
- **SciPy** for spline generation
- **ezdxf** for DXF export
- **FreeCAD** for 3D export
- **PySide6** for the modern UI
- **CuPy** for GPU acceleration

## Support

For support, please:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed information

---

**ImageEmboss v2.0.0** - Professional Image to DXF Converter with Smooth Splines
