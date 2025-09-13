"""
ImageEmboss - Image to DXF Converter
Main application entry point
"""
import sys
from PySide6.QtWidgets import QApplication

from methods.main_gui import ImageEmbossGUI


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Image Emboss")
    app.setApplicationVersion("2.0")
    
    window = ImageEmbossGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
