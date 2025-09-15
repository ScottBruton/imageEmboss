"""
3D Preview Dialog for STEP and STL files
Provides a simple 3D viewer with rotation and zoom capabilities
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QSlider, QGroupBox, QMessageBox, QApplication, QProgressBar)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QOpenGLContext, QSurfaceFormat
import numpy as np
import os


class ModelLoaderThread(QThread):
    """Worker thread for loading 3D models without blocking the UI"""
    model_loaded = Signal(object, str)  # model, file_type
    error_occurred = Signal(str)  # error message
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        try:
            print(f"DEBUG: ModelLoaderThread starting for file: {self.file_path}")
            file_ext = os.path.splitext(self.file_path)[1].lower()
            print(f"DEBUG: File extension: {file_ext}")
            
            if file_ext == '.stl':
                print("DEBUG: Loading STL file...")
                # Load STL directly
                import trimesh
                print("DEBUG: trimesh imported successfully")
                mesh = trimesh.load(self.file_path)
                print(f"DEBUG: STL loaded successfully, vertices: {len(mesh.vertices)}, faces: {len(mesh.faces)}")
                self.model_loaded.emit(mesh, 'stl')
                print("DEBUG: STL model_loaded signal emitted")
                
            elif file_ext == '.step':
                print("DEBUG: STEP file detected - looking for STL preview file")
                # Look for the corresponding STL preview file
                stl_path = self.file_path.replace('.step', '_preview.stl')
                print(f"DEBUG: Looking for STL preview file: {stl_path}")
                
                if os.path.exists(stl_path):
                    print("DEBUG: STL preview file found, loading it directly")
                    # Load the STL preview file directly
                    import trimesh
                    mesh = trimesh.load(stl_path)
                    print(f"DEBUG: STL preview loaded successfully, vertices: {len(mesh.vertices)}, faces: {len(mesh.faces)}")
                    self.model_loaded.emit(mesh, 'step')
                    print("DEBUG: STEP model_loaded signal emitted")
                else:
                    print("DEBUG: STL preview file not found")
                    self.error_occurred.emit("STL preview file not found.\n\nThis STEP file was exported before the preview feature was added.\nPlease re-export the STEP file to generate the STL preview.")
            else:
                error_msg = f"Unsupported file format: {file_ext}"
                print(f"DEBUG: {error_msg}")
                self.error_occurred.emit(error_msg)
                
        except ImportError as e:
            error_msg = f"Missing dependency: {e}"
            if 'cadquery' in str(e):
                error_msg = "CadQuery not available. Please install with: pip install cadquery"
            print(f"DEBUG: ImportError - {error_msg}")
            self.error_occurred.emit(error_msg)
        except Exception as e:
            error_msg = f"Error loading model: {e}"
            print(f"DEBUG: Exception in ModelLoaderThread: {error_msg}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            self.error_occurred.emit(error_msg)


class Simple3DViewer(QOpenGLWidget):
    """Simple 3D viewer widget using OpenGL"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set up OpenGL format - use compatibility profile for legacy functions
        fmt = QSurfaceFormat()
        fmt.setVersion(2, 1)  # Use older version for compatibility
        fmt.setProfile(QSurfaceFormat.CompatibilityProfile)  # Enable legacy functions
        fmt.setSamples(4)  # Anti-aliasing
        self.setFormat(fmt)
        
        # 3D data
        self.vertices = []
        self.faces = []
        self.rotation_x = 0
        self.rotation_y = 0
        self.zoom = 1.0
        
        # Mouse interaction
        self.last_pos = None
    
    def draw_test_cube(self):
        """Draw a simple test cube to verify OpenGL is working"""
        from OpenGL import GL
        
        # Set up projection matrix
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        
        # Simple perspective projection
        aspect = self.width() / self.height() if self.height() > 0 else 1
        from OpenGL.GLU import gluPerspective
        gluPerspective(45, aspect, 0.1, 100.0)
        
        # Set up modelview matrix
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        
        # Apply transformations
        GL.glTranslatef(0, 0, -3 * self.zoom)
        GL.glRotatef(self.rotation_x, 1, 0, 0)
        GL.glRotatef(self.rotation_y, 0, 1, 0)
        
        # Draw a simple cube
        GL.glBegin(GL.GL_QUADS)
        
        # Front face
        GL.glColor3f(1.0, 0.0, 0.0)  # Red
        GL.glVertex3f(-0.5, -0.5, 0.5)
        GL.glVertex3f(0.5, -0.5, 0.5)
        GL.glVertex3f(0.5, 0.5, 0.5)
        GL.glVertex3f(-0.5, 0.5, 0.5)
        
        # Back face
        GL.glColor3f(0.0, 1.0, 0.0)  # Green
        GL.glVertex3f(-0.5, -0.5, -0.5)
        GL.glVertex3f(-0.5, 0.5, -0.5)
        GL.glVertex3f(0.5, 0.5, -0.5)
        GL.glVertex3f(0.5, -0.5, -0.5)
        
        # Top face
        GL.glColor3f(0.0, 0.0, 1.0)  # Blue
        GL.glVertex3f(-0.5, 0.5, -0.5)
        GL.glVertex3f(-0.5, 0.5, 0.5)
        GL.glVertex3f(0.5, 0.5, 0.5)
        GL.glVertex3f(0.5, 0.5, -0.5)
        
        # Bottom face
        GL.glColor3f(1.0, 1.0, 0.0)  # Yellow
        GL.glVertex3f(-0.5, -0.5, -0.5)
        GL.glVertex3f(0.5, -0.5, -0.5)
        GL.glVertex3f(0.5, -0.5, 0.5)
        GL.glVertex3f(-0.5, -0.5, 0.5)
        
        # Right face
        GL.glColor3f(1.0, 0.0, 1.0)  # Magenta
        GL.glVertex3f(0.5, -0.5, -0.5)
        GL.glVertex3f(0.5, 0.5, -0.5)
        GL.glVertex3f(0.5, 0.5, 0.5)
        GL.glVertex3f(0.5, -0.5, 0.5)
        
        # Left face
        GL.glColor3f(0.0, 1.0, 1.0)  # Cyan
        GL.glVertex3f(-0.5, -0.5, -0.5)
        GL.glVertex3f(-0.5, -0.5, 0.5)
        GL.glVertex3f(-0.5, 0.5, 0.5)
        GL.glVertex3f(-0.5, 0.5, -0.5)
        
        GL.glEnd()
        
    def load_mesh(self, mesh):
        """Load mesh data and extract vertices and faces"""
        try:
            print(f"DEBUG: Simple3DViewer.load_mesh called")
            print(f"DEBUG: Input mesh type: {type(mesh)}")
            print(f"DEBUG: Input mesh vertices shape: {mesh.vertices.shape}")
            print(f"DEBUG: Input mesh faces shape: {mesh.faces.shape}")
            
            # Extract vertices and faces
            self.vertices = mesh.vertices.astype(np.float32)
            self.faces = mesh.faces.astype(np.uint32)
            print(f"DEBUG: Converted vertices shape: {self.vertices.shape}")
            print(f"DEBUG: Converted faces shape: {self.faces.shape}")
            print(f"DEBUG: First few vertices: {self.vertices[:3]}")
            print(f"DEBUG: First few faces: {self.faces[:3]}")
            
            # Center the mesh
            center = np.mean(self.vertices, axis=0)
            print(f"DEBUG: Mesh center: {center}")
            self.vertices -= center
            
            # Scale to fit in view
            max_dim = np.max(np.abs(self.vertices))
            print(f"DEBUG: Max dimension: {max_dim}")
            if max_dim > 0:
                self.vertices /= max_dim * 2
                print(f"DEBUG: Scaled vertices, new max: {np.max(np.abs(self.vertices))}")
            
            print("DEBUG: Calling update()...")
            self.update()
            print("DEBUG: load_mesh completed successfully")
            print(f"DEBUG: Final vertices count: {len(self.vertices)}")
            print(f"DEBUG: Final faces count: {len(self.faces)}")
            return True
            
        except Exception as e:
            print(f"DEBUG: Error loading mesh: {e}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return False
    
    
    def initializeGL(self):
        """Initialize OpenGL"""
        from OpenGL import GL
        
        # Enable depth testing
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        
        # Set up lighting
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [1, 1, 1, 0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.2, 0.2, 0.2, 1])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.8, 0.8, 0.8, 1])
        
        # Set background color
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
    
    def paintGL(self):
        """Paint the 3D scene"""
        from OpenGL import GL
        from OpenGL.GLU import gluPerspective
        import math
        
        # Clear the screen
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        
        if len(self.vertices) == 0:
            # Draw a simple test cube when no model is loaded
            GL.glColor3f(1.0, 0.0, 0.0)  # Red color
            self.draw_test_cube()
            return
        
        # Set up projection matrix
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        
        # Simple perspective projection
        aspect = self.width() / self.height() if self.height() > 0 else 1
        gluPerspective(45, aspect, 0.1, 100.0)
        
        # Set up modelview matrix
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        
        # Apply transformations
        GL.glTranslatef(0, 0, -3 * self.zoom)
        GL.glRotatef(self.rotation_x, 1, 0, 0)
        GL.glRotatef(self.rotation_y, 0, 1, 0)
        
        # Draw the mesh
        GL.glColor3f(0.7, 0.7, 0.9)  # Light blue color
        
        GL.glBegin(GL.GL_TRIANGLES)
        for face in self.faces:
            for vertex_idx in face:
                if vertex_idx < len(self.vertices):
                    vertex = self.vertices[vertex_idx]
                    GL.glVertex3f(vertex[0], vertex[1], vertex[2])
        GL.glEnd()
    
    def resizeGL(self, width, height):
        """Handle resize events"""
        from OpenGL import GL
        GL.glViewport(0, 0, width, height)
    
    def mousePressEvent(self, event):
        """Handle mouse press for rotation"""
        self.last_pos = event.position().toPoint()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for rotation"""
        if self.last_pos is not None:
            dx = event.position().x() - self.last_pos.x()
            dy = event.position().y() - self.last_pos.y()
            
            self.rotation_y += dx * 0.5
            self.rotation_x += dy * 0.5
            
            self.last_pos = event.position().toPoint()
            self.update()
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zoom"""
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        self.zoom *= zoom_factor
        self.zoom = max(0.1, min(10.0, self.zoom))  # Limit zoom range
        self.update()


class StepViewerDialog(QDialog):
    """Dialog for previewing 3D STEP and STL files"""
    
    def __init__(self, parent=None, file_path=None):
        print(f"DEBUG: StepViewerDialog.__init__ called with file_path: {file_path}")
        super().__init__(parent)
        self.setWindowTitle("3D Preview")
        self.setModal(True)
        self.resize(900, 700)
        print("DEBUG: Dialog basic setup completed")
        
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # File info section
        if file_path:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].upper()
            info_label = QLabel(f"Previewing: {file_name} ({file_ext} format)")
            info_label.setStyleSheet("font-weight: bold; padding: 8px; background-color: #2b2b2b; color: white; border-radius: 4px;")
            info_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(info_label)
            print(f"DEBUG: Added file info label for: {file_name}")
        
        # Loading status section
        loading_section = QVBoxLayout()
        self.loading_label = QLabel("Loading 3D model...")
        self.loading_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px;")
        self.loading_label.setAlignment(Qt.AlignCenter)
        loading_section.addWidget(self.loading_label)
        
        # Progress bar for loading
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)  # Initially hidden
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4CAF50;
                border-radius: 5px;
                text-align: center;
                background-color: #2b2b2b;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        loading_section.addWidget(self.progress_bar)
        main_layout.addLayout(loading_section)
        print("DEBUG: Added loading section")
        
        # 3D viewer section
        print("DEBUG: Creating Simple3DViewer...")
        self.viewer = Simple3DViewer(self)
        self.viewer.setMinimumSize(600, 400)
        main_layout.addWidget(self.viewer, 1)  # Give it stretch factor
        print("DEBUG: Added 3D viewer to layout")
        
        # Initially hide the viewer until model is loaded
        self.viewer.setVisible(False)
        print("DEBUG: 3D viewer initially hidden")
        
        # Controls section
        controls_section = QHBoxLayout()
        controls_section.setSpacing(15)
        
        # Rotation controls
        rotation_group = QGroupBox("Rotation")
        rotation_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
        """)
        rotation_layout = QVBoxLayout()
        rotation_layout.setSpacing(5)
        
        # X rotation
        x_layout = QHBoxLayout()
        x_label = QLabel("X:")
        x_label.setMinimumWidth(20)
        x_layout.addWidget(x_label)
        self.x_slider = QSlider(Qt.Horizontal)
        self.x_slider.setRange(-180, 180)
        self.x_slider.setValue(0)
        self.x_slider.valueChanged.connect(self.on_rotation_changed)
        x_layout.addWidget(self.x_slider)
        rotation_layout.addLayout(x_layout)
        
        # Y rotation
        y_layout = QHBoxLayout()
        y_label = QLabel("Y:")
        y_label.setMinimumWidth(20)
        y_layout.addWidget(y_label)
        self.y_slider = QSlider(Qt.Horizontal)
        self.y_slider.setRange(-180, 180)
        self.y_slider.setValue(0)
        self.y_slider.valueChanged.connect(self.on_rotation_changed)
        y_layout.addWidget(self.y_slider)
        rotation_layout.addLayout(y_layout)
        
        rotation_group.setLayout(rotation_layout)
        controls_section.addWidget(rotation_group)
        
        # Zoom control
        zoom_group = QGroupBox("Zoom")
        zoom_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2196F3;
            }
        """)
        zoom_layout = QVBoxLayout()
        zoom_layout.setSpacing(5)
        zoom_label = QLabel("Zoom:")
        zoom_label.setMinimumWidth(40)
        zoom_layout.addWidget(zoom_label)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 1000)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_group.setLayout(zoom_layout)
        controls_section.addWidget(zoom_group)
        
        # Reset button
        reset_button = QPushButton("Reset View")
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        reset_button.clicked.connect(self.reset_view)
        controls_section.addWidget(reset_button)
        
        main_layout.addLayout(controls_section)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button)
        
        self.setLayout(main_layout)
        
        # Load the file if provided
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load and display the 3D file using threaded loading"""
        print(f"DEBUG: StepViewerDialog.load_file called with: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"DEBUG: File not found: {file_path}")
            QMessageBox.warning(self, "File Not Found", f"File not found: {file_path}")
            return
        
        file_ext = os.path.splitext(file_path)[1].lower()
        print(f"DEBUG: File extension: {file_ext}")
        
        if file_ext not in ['.stl', '.step']:
            print(f"DEBUG: Unsupported file format: {file_ext}")
            QMessageBox.warning(self, "Unsupported Format", 
                               f"Unsupported file format: {file_ext}\n"
                               "Only STL and STEP files are supported for 3D preview.")
            return
        
        # Show progress bar for loading
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.loading_label.setText("Loading 3D model...")
        
        # Create and start the loader thread
        print("DEBUG: Creating ModelLoaderThread...")
        self.loader_thread = ModelLoaderThread(file_path)
        print("DEBUG: Connecting signals...")
        self.loader_thread.model_loaded.connect(self.on_model_loaded)
        self.loader_thread.error_occurred.connect(self.on_load_error)
        print("DEBUG: Starting loader thread...")
        self.loader_thread.start()
        print("DEBUG: Loader thread started")
        
        # Simulate progress updates
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(100)  # Update every 100ms
        self.progress_value = 0
    
    def update_progress(self):
        """Update progress bar with animation"""
        if hasattr(self, 'progress_timer') and self.progress_timer.isActive():
            self.progress_value += 2
            if self.progress_value < 90:  # Don't go to 100% until actually loaded
                self.progress_bar.setValue(self.progress_value)
            else:
                self.progress_timer.stop()
    
    def on_model_loaded(self, mesh, file_type):
        """Handle successful model loading"""
        print(f"DEBUG: on_model_loaded called with file_type: {file_type}")
        print(f"DEBUG: Mesh vertices: {len(mesh.vertices)}, faces: {len(mesh.faces)}")
        
        # Stop progress timer and update progress bar
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        
        if file_type == 'step':
            self.loading_label.setText("STEP file loaded successfully!")
        else:
            self.loading_label.setText(f"Model loaded successfully! ({file_type.upper()} format)")
        self.loading_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
        
        # Load the mesh into the viewer
        print("DEBUG: Loading mesh into viewer...")
        success = self.viewer.load_mesh(mesh)
        print(f"DEBUG: Viewer load_mesh result: {success}")
        
        # Show the viewer and hide loading label
        print("DEBUG: Making viewer visible...")
        self.viewer.setVisible(True)
        print("DEBUG: Setting timer to hide loading label...")
        QTimer.singleShot(2000, lambda: self.loading_label.setVisible(False))
        print("DEBUG: on_model_loaded completed")
    
    def on_load_error(self, error_message):
        """Handle model loading error"""
        print(f"DEBUG: on_load_error called with: {error_message}")
        self.loading_label.setText(f"Error: {error_message}")
        self.loading_label.setStyleSheet("color: red; font-weight: bold; padding: 5px;")
        QMessageBox.critical(self, "Load Error", error_message)
    
    def on_rotation_changed(self):
        """Handle rotation slider changes"""
        self.viewer.rotation_x = self.x_slider.value()
        self.viewer.rotation_y = self.y_slider.value()
        self.viewer.update()
    
    def on_zoom_changed(self):
        """Handle zoom slider changes"""
        self.viewer.zoom = self.zoom_slider.value() / 100.0
        self.viewer.update()
    
    def reset_view(self):
        """Reset the view to default"""
        self.x_slider.setValue(0)
        self.y_slider.setValue(0)
        self.zoom_slider.setValue(100)
        self.viewer.rotation_x = 0
        self.viewer.rotation_y = 0
        self.viewer.zoom = 1.0
        self.viewer.update()
