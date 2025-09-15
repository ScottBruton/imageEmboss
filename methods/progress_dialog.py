"""
Progress dialog for export operations
Shows progress and disables the main application during processing
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QFont


class ProgressDialog(QDialog):
    """Progress dialog that shows export progress and disables the main app"""
    
    def __init__(self, parent=None, title="Exporting...", message="Please wait while the file is being exported."):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        # Disable the parent window
        if self.parent:
            self.parent.setEnabled(False)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Message label
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        self.message_label.setFont(font)
        layout.addWidget(self.message_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Cancel button (initially hidden)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.cancel_button.setVisible(True)  # Show cancel button by default
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
        
        # Center the dialog
        self.center_on_parent()
        
        # Show the dialog
        self.show()
        
        # Force the dialog to be on top
        self.raise_()
        self.activateWindow()
    
    def center_on_parent(self):
        """Center the dialog on the parent window"""
        if self.parent:
            parent_geometry = self.parent.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
    
    def update_progress(self, value, status_text=""):
        """Update the progress bar and status text"""
        self.progress_bar.setValue(value)
        if status_text:
            self.status_label.setText(status_text)
        # Force update
        self.repaint()
    
    def set_message(self, message):
        """Update the main message"""
        self.message_label.setText(message)
    
    def set_status(self, status):
        """Update the status text"""
        self.status_label.setText(status)
    
    def show_cancel_button(self, show=True):
        """Show or hide the cancel button"""
        self.cancel_button.setVisible(show)
    
    def cancel_operation(self):
        """Handle cancel button click"""
        # If there's a worker thread, cancel it
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()
        self.close()
    
    def closeEvent(self, event):
        """Handle dialog close - re-enable parent window"""
        if self.parent:
            self.parent.setEnabled(True)
        super().closeEvent(event)
    
    def finish_success(self, message="Export completed successfully!"):
        """Show completion message and close after a delay"""
        self.update_progress(100, message)
        self.show_cancel_button(False)
        
        # Close after 2 seconds
        QTimer.singleShot(2000, self.close)
    
    def finish_error(self, error_message="Export failed!"):
        """Show error message and allow user to close"""
        self.update_progress(0, error_message)
        self.show_cancel_button(True)
        self.cancel_button.setText("Close")


class ExportWorker(QThread):
    """Worker thread for export operations"""
    
    progress_updated = Signal(int, str)  # value, status
    finished = Signal(bool, str)  # success, message
    
    def __init__(self, export_function, *args, **kwargs):
        super().__init__()
        self.export_function = export_function
        self.args = args
        self.kwargs = kwargs
        self.cancelled = False
    
    def run(self):
        """Run the export function with progress updates"""
        try:
            self.progress_updated.emit(10, "Preparing export...")
            
            # Create progress callback function
            def progress_callback(value, message):
                self.progress_updated.emit(value, message)
            
            # Add progress callback to kwargs if not already present
            if 'progress_callback' not in self.kwargs:
                self.kwargs['progress_callback'] = progress_callback
            
            # Call the export function
            success = self.export_function(*self.args, **self.kwargs)
            
            if success:
                self.progress_updated.emit(100, "Export completed!")
                self.finished.emit(True, "Export completed successfully!")
            else:
                self.progress_updated.emit(0, "Export failed!")
                self.finished.emit(False, "Export failed!")
                
        except Exception as e:
            self.progress_updated.emit(0, f"Error: {str(e)}")
            self.finished.emit(False, f"Export failed: {str(e)}")
    
    def cancel(self):
        """Cancel the export operation"""
        self.cancelled = True
