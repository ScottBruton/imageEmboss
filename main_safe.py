"""
ImageEmboss - Safe Startup Version
This version has crash protection and simplified initialization
"""
import sys
import os
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


class SafeImageEmbossWindow(QMainWindow):
    """Safe version of ImageEmboss main window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageEmboss v2.0.0 - Safe Mode")
        self.setGeometry(100, 100, 1200, 800)
        
        self.setup_ui()
        self.check_dependencies()
    
    def setup_ui(self):
        """Setup basic UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("ImageEmboss v2.0.0")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86AB;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Status
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-size: 14px; color: #666;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(300)
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.log_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.load_image_btn = QPushButton("Load Image")
        self.load_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.load_image_btn.clicked.connect(self.load_image)
        self.load_image_btn.setEnabled(False)
        button_layout.addWidget(self.load_image_btn)
        
        self.export_btn = QPushButton("Export DXF")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.export_btn.clicked.connect(self.export_dxf)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        self.test_btn = QPushButton("Test Processing")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.test_btn.clicked.connect(self.test_processing)
        self.test_btn.setEnabled(False)
        button_layout.addWidget(self.test_btn)
        
        layout.addLayout(button_layout)
        
        # Info area
        info_label = QLabel("""
        <h3>Safe Mode Features:</h3>
        <ul>
        <li>✅ Crash protection and error handling</li>
        <li>✅ Dependency checking</li>
        <li>✅ Safe GPU initialization</li>
        <li>✅ Simplified UI to prevent crashes</li>
        <li>✅ Detailed error logging</li>
        </ul>
        
        <h3>Next Steps:</h3>
        <ol>
        <li>Check the log above for any errors</li>
        <li>Install missing dependencies if needed</li>
        <li>Try loading an image</li>
        <li>Test the processing pipeline</li>
        </ol>
        """)
        info_label.setStyleSheet("font-size: 12px; color: #333;")
        layout.addWidget(info_label)
    
    def log(self, message):
        """Add message to log"""
        self.log_area.append(message)
        self.log_area.ensureCursorVisible()
        QApplication.processEvents()
    
    def check_dependencies(self):
        """Check dependencies safely"""
        self.log("🔍 Checking dependencies...")
        
        dependencies = {
            'opencv-python': 'cv2',
            'numpy': 'numpy',
            'scipy': 'scipy',
            'ezdxf': 'ezdxf',
            'PySide6': 'PySide6',
            'Pillow': 'PIL'
        }
        
        missing_deps = []
        available_deps = []
        
        for package, module in dependencies.items():
            try:
                __import__(module)
                available_deps.append(package)
                self.log(f"✅ {package} - OK")
            except ImportError as e:
                missing_deps.append(package)
                self.log(f"❌ {package} - Missing ({e})")
        
        # Check optional dependencies
        optional_deps = {
            'numba': 'numba',
            'cupy': 'cupy',
            'trimesh': 'trimesh',
            'meshio': 'meshio'
        }
        
        for package, module in optional_deps.items():
            try:
                __import__(module)
                self.log(f"✅ {package} - Available (optional)")
            except ImportError:
                self.log(f"⚠️ {package} - Not available (optional)")
        
        if missing_deps:
            self.log(f"\n❌ Missing required dependencies: {', '.join(missing_deps)}")
            self.log("Please install missing dependencies:")
            self.log("pip install -r requirements.txt")
            self.status_label.setText("❌ Missing dependencies - Check log")
            self.status_label.setStyleSheet("color: #f44336;")
        else:
            self.log(f"\n✅ All required dependencies available!")
            self.status_label.setText("✅ Dependencies OK - Ready to use")
            self.status_label.setStyleSheet("color: #4CAF50;")
            self.load_image_btn.setEnabled(True)
            self.test_btn.setEnabled(True)
        
        # Test GPU safely
        self.test_gpu_safely()
    
    def test_gpu_safely(self):
        """Test GPU initialization safely"""
        self.log("\n🚀 Testing GPU acceleration...")
        
        try:
            import cupy as cp
            if cp.cuda.is_available():
                self.log("✅ CUDA available")
                try:
                    # Test basic GPU operation
                    test_array = cp.array([1, 2, 3, 4, 5])
                    result = cp.sum(test_array)
                    self.log(f"✅ GPU test successful: {result}")
                except Exception as e:
                    self.log(f"⚠️ GPU test failed: {e}")
            else:
                self.log("⚠️ CUDA not available")
        except ImportError:
            self.log("⚠️ CuPy not installed - GPU acceleration disabled")
        except Exception as e:
            self.log(f"⚠️ GPU initialization error: {e}")
    
    def load_image(self):
        """Load image safely"""
        self.log("\n📷 Loading image...")
        
        try:
            from PySide6.QtWidgets import QFileDialog
            from PySide6.QtCore import QStandardPaths
            
            # Get default image directory
            default_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
            if not os.path.exists(default_dir):
                default_dir = os.path.expanduser("~")
            
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Image",
                default_dir,
                "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
            )
            
            if file_path:
                self.log(f"Selected: {file_path}")
                
                # Test image loading
                import cv2
                image = cv2.imread(file_path)
                if image is not None:
                    h, w = image.shape[:2]
                    self.log(f"✅ Image loaded: {w}x{h} pixels")
                    self.export_btn.setEnabled(True)
                    self.current_image_path = file_path
                else:
                    self.log("❌ Failed to load image")
                    
        except Exception as e:
            self.log(f"❌ Error loading image: {e}")
            traceback.print_exc()
    
    def export_dxf(self):
        """Export DXF safely"""
        self.log("\n💾 Exporting DXF...")
        
        try:
            if not hasattr(self, 'current_image_path'):
                self.log("❌ No image loaded")
                return
            
            # Simple DXF export test
            import cv2
            import ezdxf
            
            # Load image
            image = cv2.imread(self.current_image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Simple edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                self.log(f"Found {len(contours)} contours")
                
                # Create DXF
                doc = ezdxf.new('R2010')
                msp = doc.modelspace()
                
                # Add first few contours as polylines
                for i, contour in enumerate(contours[:5]):  # Limit to first 5
                    points = []
                    for point in contour:
                        x, y = point[0]
                        points.append((x, y))
                    
                    if len(points) >= 3:
                        polyline = msp.add_lwpolyline(points)
                        polyline.closed = True
                
                # Save DXF
                output_path = self.current_image_path.replace('.', '_export.')
                if not output_path.endswith('.dxf'):
                    output_path += '.dxf'
                
                doc.saveas(output_path)
                self.log(f"✅ DXF exported: {output_path}")
                
                QMessageBox.information(self, "Export Complete", f"DXF file saved to:\n{output_path}")
            else:
                self.log("❌ No contours found")
                
        except Exception as e:
            self.log(f"❌ Export error: {e}")
            traceback.print_exc()
    
    def test_processing(self):
        """Test processing pipeline safely"""
        self.log("\n🧪 Testing processing pipeline...")
        
        try:
            # Test core modules
            from core.pipeline import ImageProcessingPipeline
            from core.models.parameters import ProcessingParameters
            
            self.log("✅ Core modules imported successfully")
            
            # Test pipeline creation
            pipeline = ImageProcessingPipeline()
            self.log("✅ Pipeline created successfully")
            
            # Test parameters
            params = ProcessingParameters()
            self.log("✅ Parameters created successfully")
            
            self.log("✅ Processing pipeline test passed!")
            
        except Exception as e:
            self.log(f"❌ Processing pipeline test failed: {e}")
            traceback.print_exc()


def setup_application():
    """Setup Qt application safely"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("ImageEmboss")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("ImageEmboss")
        
        # Set application font
        font = QFont("Arial", 9)
        app.setFont(font)
        
        # Set application style
        app.setStyle('Fusion')
        
        return app
    except Exception as e:
        print(f"❌ Application setup failed: {e}")
        return None


def main():
    """Main application entry point with crash protection"""
    try:
        print("🚀 Starting ImageEmboss Safe Mode...")
        
        # Setup application
        app = setup_application()
        if app is None:
            return 1
        
        # Create main window
        main_window = SafeImageEmbossWindow()
        main_window.show()
        
        # Show welcome message
        QMessageBox.information(
            main_window, 
            "ImageEmboss Safe Mode",
            "Welcome to ImageEmboss Safe Mode!\n\n"
            "This version includes crash protection and detailed error logging.\n"
            "Check the log area for any issues and try the test functions.\n\n"
            "If everything works, you can switch back to the full version."
        )
        
        # Run application
        return app.exec()
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        traceback.print_exc()
        
        # Try to show error dialog
        try:
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            QMessageBox.critical(
                None,
                "Application Error",
                f"ImageEmboss encountered an error:\n\n{e}\n\n"
                "Please check the console output for more details."
            )
        except:
            pass
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
