#!/usr/bin/env python3
"""
ImageEmboss - Main Application Entry Point
MVVM Architecture with Dark Theme
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGridLayout
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPalette, QColor, QFont

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from views.main_window import MainWindow
from viewmodels.main_viewmodel import MainViewModel
from models.application_state import ApplicationState


class DarkTheme:
    """Dark theme configuration for the application"""
    
    # Color palette
    PRIMARY = QColor(33, 37, 43)      # Dark blue-gray
    SECONDARY = QColor(44, 49, 58)    # Slightly lighter blue-gray
    ACCENT = QColor(52, 144, 220)     # Blue accent
    SUCCESS = QColor(40, 167, 69)     # Green for success states
    WARNING = QColor(255, 193, 7)     # Yellow for warnings
    ERROR = QColor(220, 53, 69)       # Red for errors
    TEXT_PRIMARY = QColor(255, 255, 255)    # White text
    TEXT_SECONDARY = QColor(173, 181, 189)  # Light gray text
    BORDER = QColor(73, 80, 87)       # Border color
    
    @staticmethod
    def apply_theme(app: QApplication):
        """Apply dark theme to the application"""
        palette = QPalette()
        
        # Window colors
        palette.setColor(QPalette.ColorRole.Window, DarkTheme.PRIMARY)
        palette.setColor(QPalette.ColorRole.WindowText, DarkTheme.TEXT_PRIMARY)
        
        # Base colors (for input fields, etc.)
        palette.setColor(QPalette.ColorRole.Base, DarkTheme.SECONDARY)
        palette.setColor(QPalette.ColorRole.AlternateBase, DarkTheme.PRIMARY)
        
        # Text colors
        palette.setColor(QPalette.ColorRole.Text, DarkTheme.TEXT_PRIMARY)
        palette.setColor(QPalette.ColorRole.BrightText, DarkTheme.TEXT_PRIMARY)
        
        # Button colors
        palette.setColor(QPalette.ColorRole.Button, DarkTheme.SECONDARY)
        palette.setColor(QPalette.ColorRole.ButtonText, DarkTheme.TEXT_PRIMARY)
        
        # Highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, DarkTheme.ACCENT)
        palette.setColor(QPalette.ColorRole.HighlightedText, DarkTheme.TEXT_PRIMARY)
        
        # Border color
        palette.setColor(QPalette.ColorRole.Mid, DarkTheme.BORDER)
        
        app.setPalette(palette)


def main():
    """Main application entry point"""
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("ImageEmboss")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ImageEmboss")
    
    # Apply dark theme
    DarkTheme.apply_theme(app)
    
    # Set application font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Create application state
    app_state = ApplicationState()
    
    # Create main viewmodel
    main_viewmodel = MainViewModel(app_state)
    
    # Create main window
    main_window = MainWindow(main_viewmodel)
    
    # Show main window
    main_window.show()
    
    # Start the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
