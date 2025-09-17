"""
Threading utilities for responsive UI
"""
import threading
import time
from typing import Callable, Optional, Any
from PySide6.QtCore import QThread, Signal, QObject


class ProcessingWorker(QObject):
    """Worker thread for image processing"""
    
    # Signals
    progress_updated = Signal(int)
    step_started = Signal(str)
    step_completed = Signal(str)
    processing_completed = Signal(object)  # ProcessingResult
    processing_failed = Signal(str)
    processing_cancelled = Signal()
    
    def __init__(self, pipeline, image_path: str, parameters):
        super().__init__()
        self.pipeline = pipeline
        self.image_path = image_path
        self.parameters = parameters
        self.cancelled = False
        self.result = None
    
    def run(self):
        """Execute processing in worker thread"""
        try:
            # Add observer for progress updates
            self.pipeline.add_observer(self._on_pipeline_event)
            
            # Execute processing
            self.result = self.pipeline.process(self.image_path, self.parameters)
            
            if self.cancelled:
                self.processing_cancelled.emit()
            elif self.result.success:
                self.processing_completed.emit(self.result)
            else:
                self.processing_failed.emit(self.result.error_message or "Processing failed")
                
        except Exception as e:
            self.processing_failed.emit(f"Processing error: {str(e)}")
        finally:
            # Remove observer
            self.pipeline.remove_observer(self._on_pipeline_event)
    
    def cancel(self):
        """Cancel processing"""
        self.cancelled = True
        if self.result:
            self.pipeline.cancel(self.result)
    
    def _on_pipeline_event(self, event_type: str, result):
        """Handle pipeline events"""
        if self.cancelled:
            return
        
        if "step_" in event_type and "_started" in event_type:
            step_name = event_type.replace("step_", "").replace("_started", "")
            self.step_started.emit(step_name)
        elif "step_" in event_type and "_completed" in event_type:
            step_name = event_type.replace("step_", "").replace("_completed", "")
            self.step_completed.emit(step_name)
        elif event_type == "processing_completed":
            self.processing_completed.emit(result)
        elif event_type == "processing_failed":
            self.processing_failed.emit(result.error_message or "Processing failed")
        elif event_type == "processing_cancelled":
            self.processing_cancelled.emit()
        
        # Update progress
        if hasattr(result, 'progress'):
            self.progress_updated.emit(result.progress)


class ThreadedImageProcessor:
    """Manages threaded image processing"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.current_worker = None
        self.current_thread = None
        self.is_processing = False
        self.processing_timer = None
        self.debounce_delay = 300  # ms
    
    def start_processing(self, image_path: str, parameters):
        """Start processing in background thread"""
        # Cancel any existing processing
        self.cancel_processing()
        
        # Create worker and thread
        self.current_worker = ProcessingWorker(
            self.main_window.pipeline, image_path, parameters
        )
        self.current_thread = QThread()
        
        # Move worker to thread
        self.current_worker.moveToThread(self.current_thread)
        
        # Connect signals
        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.processing_completed.connect(self._on_processing_completed)
        self.current_worker.processing_failed.connect(self._on_processing_failed)
        self.current_worker.processing_cancelled.connect(self._on_processing_cancelled)
        self.current_worker.progress_updated.connect(self._on_progress_updated)
        self.current_worker.step_started.connect(self._on_step_started)
        self.current_worker.step_completed.connect(self._on_step_completed)
        
        # Clean up thread when done
        self.current_worker.processing_completed.connect(self.current_thread.quit)
        self.current_worker.processing_failed.connect(self.current_thread.quit)
        self.current_worker.processing_cancelled.connect(self.current_thread.quit)
        self.current_thread.finished.connect(self.current_worker.deleteLater)
        self.current_thread.finished.connect(self.current_thread.deleteLater)
        
        # Start processing
        self.is_processing = True
        self.current_thread.start()
        
        print("🚀 Started threaded processing")
    
    def cancel_processing(self):
        """Cancel current processing"""
        if self.current_worker and self.is_processing:
            self.current_worker.cancel()
            self.is_processing = False
            print("⏹️ Cancelled processing")
    
    def _on_processing_completed(self, result):
        """Handle processing completion"""
        self.is_processing = False
        self.main_window.on_processing_completed(result)
        print("✅ Processing completed")
    
    def _on_processing_failed(self, error_message):
        """Handle processing failure"""
        self.is_processing = False
        self.main_window.on_processing_failed(error_message)
        print(f"❌ Processing failed: {error_message}")
    
    def _on_processing_cancelled(self):
        """Handle processing cancellation"""
        self.is_processing = False
        self.main_window.on_processing_cancelled()
        print("⏹️ Processing cancelled")
    
    def _on_progress_updated(self, progress):
        """Handle progress updates"""
        self.main_window.on_progress_updated(progress)
    
    def _on_step_started(self, step_name):
        """Handle step start"""
        self.main_window.on_step_started(step_name)
    
    def _on_step_completed(self, step_name):
        """Handle step completion"""
        self.main_window.on_step_completed(step_name)
