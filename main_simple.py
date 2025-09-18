"""
ImageEmboss - Simplified Version
This version removes complex features that might cause crashes
"""
import sys
import os
import traceback
import cv2
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                               QMessageBox, QSlider, QSpinBox, QCheckBox, QGroupBox,
                               QGraphicsView, QGraphicsScene, QGraphicsPixmapItem)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QImage

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


class SimpleImageEmbossWindow(QMainWindow):
    """Simplified ImageEmboss main window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageEmboss v2.0.0 - Simplified")
        self.setGeometry(100, 100, 1400, 900)
        
        # Data
        self.original_image = None
        self.current_contours = []
        self.image_path = None
        
        # Parameters
        self.params = {
            'bilateral_d': 9,
            'bilateral_c': 75,
            'bilateral_sigma': 75,
            'blur_kernel': 5,
            'canny_low': 50,
            'canny_high': 150,
            'thicken_kernel': 3,
            'largest_n': 3,
            'simplify_pct': 0.6,
            'gap_threshold': 5.0,
            'mm_per_px': 0.25
        }
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """Setup simplified UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left panel (parameters)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel (image views)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)
    
    def create_left_panel(self):
        """Create left parameter panel"""
        panel = QWidget()
        panel.setMaximumWidth(400)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        self.load_btn = QPushButton("Load Image")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.load_btn.clicked.connect(self.load_image)
        file_layout.addWidget(self.load_btn)
        
        self.file_label = QLabel("No image loaded")
        self.file_label.setStyleSheet("color: #666; font-style: italic;")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)
        
        layout.addWidget(file_group)
        
        # Parameters
        params_group = QGroupBox("Processing Parameters")
        params_layout = QVBoxLayout(params_group)
        
        # Bilateral filter
        bilateral_group = QGroupBox("Bilateral Filter")
        bilateral_layout = QVBoxLayout(bilateral_group)
        
        self.bilateral_d_slider = self.create_slider("Diameter:", 1, 25, self.params['bilateral_d'])
        bilateral_layout.addWidget(self.bilateral_d_slider)
        
        self.bilateral_c_slider = self.create_slider("Color Sigma:", 10, 200, self.params['bilateral_c'])
        bilateral_layout.addWidget(self.bilateral_c_slider)
        
        params_layout.addWidget(bilateral_group)
        
        # Edge detection
        edge_group = QGroupBox("Edge Detection")
        edge_layout = QVBoxLayout(edge_group)
        
        self.canny_low_slider = self.create_slider("Canny Low:", 10, 200, self.params['canny_low'])
        edge_layout.addWidget(self.canny_low_slider)
        
        self.canny_high_slider = self.create_slider("Canny High:", 50, 300, self.params['canny_high'])
        edge_layout.addWidget(self.canny_high_slider)
        
        params_layout.addWidget(edge_group)
        
        # Contour processing
        contour_group = QGroupBox("Contour Processing")
        contour_layout = QVBoxLayout(contour_group)
        
        self.largest_n_slider = self.create_slider("Largest N:", 1, 20, self.params['largest_n'])
        contour_layout.addWidget(self.largest_n_slider)
        
        self.simplify_slider = self.create_slider("Simplify %:", 0, 100, int(self.params['simplify_pct'] * 100))
        contour_layout.addWidget(self.simplify_slider)
        
        params_layout.addWidget(contour_group)
        
        layout.addWidget(params_group)
        
        # Export
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        self.mm_per_px_spin = QSpinBox()
        self.mm_per_px_spin.setRange(1, 1000)
        self.mm_per_px_spin.setValue(int(self.params['mm_per_px'] * 1000))
        self.mm_per_px_spin.setSuffix(" mm/1000px")
        export_layout.addWidget(QLabel("Scale:"))
        export_layout.addWidget(self.mm_per_px_spin)
        
        self.export_btn = QPushButton("Export DXF")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.export_btn.clicked.connect(self.export_dxf)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        
        layout.addWidget(export_group)
        
        layout.addStretch()
        return panel
    
    def create_right_panel(self):
        """Create right panel with image views"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Original image
        original_group = QGroupBox("Original Image")
        original_layout = QVBoxLayout(original_group)
        
        self.original_view = QGraphicsView()
        self.original_view.setMinimumSize(400, 300)
        self.original_scene = QGraphicsScene()
        self.original_view.setScene(self.original_scene)
        original_layout.addWidget(self.original_view)
        
        layout.addWidget(original_group)
        
        # DXF preview
        dxf_group = QGroupBox("DXF Preview")
        dxf_layout = QVBoxLayout(dxf_group)
        
        self.dxf_view = QGraphicsView()
        self.dxf_view.setMinimumSize(400, 300)
        self.dxf_scene = QGraphicsScene()
        self.dxf_view.setScene(self.dxf_scene)
        dxf_layout.addWidget(self.dxf_view)
        
        layout.addWidget(dxf_group)
        
        return panel
    
    def create_slider(self, label_text, min_val, max_val, default_val):
        """Create a parameter slider"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(label_text)
        label.setMinimumWidth(100)
        layout.addWidget(label)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(self.on_param_change)
        layout.addWidget(slider)
        
        value_label = QLabel(str(default_val))
        value_label.setMinimumWidth(30)
        value_label.setAlignment(Qt.AlignRight)
        layout.addWidget(value_label)
        
        # Connect slider to value label
        def update_label(value):
            value_label.setText(str(value))
        slider.valueChanged.connect(update_label)
        
        return widget
    
    def setup_timer(self):
        """Setup processing timer"""
        self.processing_timer = QTimer()
        self.processing_timer.setSingleShot(True)
        self.processing_timer.timeout.connect(self.process_image)
    
    def on_param_change(self):
        """Handle parameter changes"""
        # Update parameters
        self.params['bilateral_d'] = self.bilateral_d_slider.findChild(QSlider).value()
        self.params['bilateral_c'] = self.bilateral_c_slider.findChild(QSlider).value()
        self.params['canny_low'] = self.canny_low_slider.findChild(QSlider).value()
        self.params['canny_high'] = self.canny_high_slider.findChild(QSlider).value()
        self.params['largest_n'] = self.largest_n_slider.findChild(QSlider).value()
        self.params['simplify_pct'] = self.simplify_slider.findChild(QSlider).value() / 100.0
        self.params['mm_per_px'] = self.mm_per_px_spin.value() / 1000.0
        
        # Start processing timer (debounced)
        if self.original_image is not None:
            self.processing_timer.start(500)  # 500ms delay
    
    def load_image(self):
        """Load image file"""
        try:
            from PySide6.QtCore import QStandardPaths
            
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
                self.image_path = file_path
                self.file_label.setText(f"Loaded: {os.path.basename(file_path)}")
                
                # Load image
                self.original_image = cv2.imread(file_path)
                
                if self.original_image is not None:
                    # Display original image
                    self.display_original_image()
                    
                    # Process image
                    self.process_image()
                    
                    self.export_btn.setEnabled(True)
                else:
                    QMessageBox.warning(self, "Error", "Failed to load image")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading image: {e}")
            traceback.print_exc()
    
    def display_original_image(self):
        """Display original image"""
        try:
            if self.original_image is None:
                return
            
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # Create QImage
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Create pixmap and display
            pixmap = QPixmap.fromImage(qt_image)
            
            # Clear scene and add pixmap
            self.original_scene.clear()
            self.original_scene.addPixmap(pixmap)
            self.original_view.fitInView(self.original_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            
        except Exception as e:
            print(f"Error displaying original image: {e}")
    
    def process_image(self):
        """Process image to find contours"""
        try:
            if self.original_image is None:
                return
            
            # Convert to grayscale
            gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            
            # Apply bilateral filter
            filtered = cv2.bilateralFilter(
                gray,
                self.params['bilateral_d'],
                self.params['bilateral_c'],
                self.params['bilateral_sigma']
            )
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(filtered, (5, 5), 0)
            
            # Apply Canny edge detection
            edges = cv2.Canny(
                blurred,
                self.params['canny_low'],
                self.params['canny_high']
            )
            
            # Thicken edges
            kernel = np.ones((3, 3), np.uint8)
            thickened = cv2.dilate(edges, kernel, iterations=1)
            
            # Find contours
            contours, _ = cv2.findContours(255 - thickened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Sort by area and keep largest N
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            self.current_contours = contours[:self.params['largest_n']]
            
            # Display DXF preview
            self.display_dxf_preview()
            
        except Exception as e:
            print(f"Error processing image: {e}")
            traceback.print_exc()
    
    def display_dxf_preview(self):
        """Display DXF preview"""
        try:
            if not self.current_contours:
                return
            
            # Create preview image
            h, w = self.original_image.shape[:2]
            preview = np.zeros((h, w, 3), dtype=np.uint8)
            
            # Draw contours
            cv2.drawContours(preview, self.current_contours, -1, (255, 255, 255), 2)
            
            # Convert to RGB
            rgb_preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_preview.shape
            bytes_per_line = ch * w
            
            # Create QImage
            qt_image = QImage(rgb_preview.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Create pixmap and display
            pixmap = QPixmap.fromImage(qt_image)
            
            # Clear scene and add pixmap
            self.dxf_scene.clear()
            self.dxf_scene.addPixmap(pixmap)
            self.dxf_view.fitInView(self.dxf_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            
        except Exception as e:
            print(f"Error displaying DXF preview: {e}")
    
    def export_dxf(self):
        """Export DXF file"""
        try:
            if not self.current_contours:
                QMessageBox.warning(self, "Warning", "No contours to export")
                return
            
            # Get output path
            if self.image_path:
                base_name = os.path.splitext(os.path.basename(self.image_path))[0]
                output_dir = os.path.dirname(self.image_path)
                output_path = os.path.join(output_dir, f"{base_name}_export.dxf")
            else:
                output_path, _ = QFileDialog.getSaveFileName(
                    self, "Save DXF", "", "DXF Files (*.dxf)"
                )
                if not output_path:
                    return
            
            # Export DXF
            import ezdxf
            
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            
            h, w = self.original_image.shape[:2]
            
            for contour in self.current_contours:
                points = []
                for point in contour:
                    x, y = point[0]
                    # Convert to DXF coordinates
                    dxf_x = x * self.params['mm_per_px']
                    dxf_y = (h - y) * self.params['mm_per_px']
                    points.append((dxf_x, dxf_y))
                
                if len(points) >= 3:
                    polyline = msp.add_lwpolyline(points)
                    polyline.closed = True
            
            doc.saveas(output_path)
            
            QMessageBox.information(
                self, "Export Complete", 
                f"DXF file exported successfully:\n{output_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting DXF: {e}")
            traceback.print_exc()


def setup_application():
    """Setup Qt application"""
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


def main():
    """Main application entry point"""
    try:
        print("🚀 Starting ImageEmboss Simplified...")
        
        # Setup application
        app = setup_application()
        
        # Create main window
        main_window = SimpleImageEmbossWindow()
        main_window.show()
        
        # Show welcome message
        QMessageBox.information(
            main_window, 
            "ImageEmboss Simplified",
            "Welcome to ImageEmboss Simplified!\n\n"
            "This version has simplified features to prevent crashes.\n"
            "Try loading an image and adjusting the parameters.\n\n"
            "If this works, the issue is in the complex features of the main app."
        )
        
        # Run application
        return app.exec()
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
