"""
DXF Viewer Dialog - Modal window for viewing exported DXF files
"""
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor

from .graphics_view import DXFViewer


class DXFViewerDialog(QDialog):
    """Modal dialog for viewing exported DXF files with navigation"""
    
    def __init__(self, dxf_files, parent=None):
        super().__init__(parent)
        
        self.dxf_files = dxf_files
        self.setWindowTitle("DXF Viewer")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Set dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: white;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #606060;
                padding: 8px 16px;
                border-radius: 4px;
                color: white;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QPushButton:disabled {
                background-color: #2b2b2b;
                color: #666666;
                border: 1px solid #404040;
            }
            QLabel {
                color: white;
            }
        """)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title bar
        title_layout = QHBoxLayout()
        
        # File info label
        self.file_info_label = QLabel("")
        self.file_info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_layout.addWidget(self.file_info_label)
        
        title_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
        """)
        close_btn.clicked.connect(self.accept)
        title_layout.addWidget(close_btn)
        
        layout.addLayout(title_layout)
        
        # Navigation bar
        nav_layout = QHBoxLayout()
        
        # Previous button
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.setFixedHeight(35)
        self.prev_btn.clicked.connect(self.previous_file)
        nav_layout.addWidget(self.prev_btn)
        
        nav_layout.addStretch()
        
        # File name label
        self.filename_label = QLabel("")
        self.filename_label.setStyleSheet("font-size: 12px; color: #cccccc;")
        self.filename_label.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(self.filename_label)
        
        nav_layout.addStretch()
        
        # Next button
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setFixedHeight(35)
        self.next_btn.clicked.connect(self.next_file)
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        
        # DXF viewer
        self.dxf_viewer = DXFViewer(self)
        self.dxf_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.dxf_viewer)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        zoom_fit_btn = QPushButton("Fit to View")
        zoom_fit_btn.setFixedHeight(30)
        zoom_fit_btn.clicked.connect(self.fit_to_view)
        zoom_layout.addWidget(zoom_fit_btn)
        
        zoom_100_btn = QPushButton("100%")
        zoom_100_btn.setFixedHeight(30)
        zoom_100_btn.clicked.connect(self.zoom_100)
        zoom_layout.addWidget(zoom_100_btn)
        
        bottom_layout.addLayout(zoom_layout)
        bottom_layout.addStretch()
        
        # Close button
        close_dialog_btn = QPushButton("Close")
        close_dialog_btn.setFixedHeight(35)
        close_dialog_btn.setFixedWidth(100)
        close_dialog_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_dialog_btn)
        
        layout.addLayout(bottom_layout)
        
        # Load DXF files
        self.dxf_viewer.load_dxf_files(self.dxf_files)
        self.update_navigation()
        
    def update_navigation(self):
        """Update navigation buttons and labels"""
        if not self.dxf_files:
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.file_info_label.setText("No DXF files to view")
            self.filename_label.setText("")
            return
            
        # Update buttons
        self.prev_btn.setEnabled(self.dxf_viewer.current_index > 0)
        self.next_btn.setEnabled(self.dxf_viewer.current_index < len(self.dxf_files) - 1)
        
        # Update labels
        filename = self.dxf_viewer.get_current_filename()
        file_info = self.dxf_viewer.get_file_info()
        
        self.file_info_label.setText(f"DXF Viewer - {file_info}")
        self.filename_label.setText(filename)
        
    def previous_file(self):
        """Navigate to previous file"""
        if self.dxf_viewer.previous_file():
            self.update_navigation()
            
    def next_file(self):
        """Navigate to next file"""
        if self.dxf_viewer.next_file():
            self.update_navigation()
            
    def fit_to_view(self):
        """Fit DXF content to view"""
        if self.dxf_viewer.scene.itemsBoundingRect().isValid():
            self.dxf_viewer.fitInView(self.dxf_viewer.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            
    def zoom_100(self):
        """Reset zoom to 100%"""
        self.dxf_viewer.resetTransform()
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Left:
            self.previous_file()
        elif event.key() == Qt.Key_Right:
            self.next_file()
        elif event.key() == Qt.Key_Escape:
            self.accept()
        elif event.key() == Qt.Key_F:
            self.fit_to_view()
        elif event.key() == Qt.Key_1:
            self.zoom_100()
        else:
            super().keyPressEvent(event)
