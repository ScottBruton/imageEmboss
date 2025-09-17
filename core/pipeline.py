"""
Main processing pipeline for ImageEmboss
"""
import time
from typing import List, Callable, Optional
from .models.processing_result import ProcessingResult
from .models.parameters import ProcessingParameters
from .processors.image_loader import ImageLoader
from .processors.edge_detector import EdgeDetector
from .processors.contour_extractor import ContourExtractor
from .processors.spline_generator import SplineGenerator
from .processors.exporters.dxf_exporter import DXFExporter
from .processors.exporters.step_exporter import STEPExporter


class ImageProcessingPipeline:
    """Main processing pipeline using Pipeline pattern"""
    
    def __init__(self):
        """Initialize pipeline with processing steps"""
        self.steps = [
            ImageLoader(),
            EdgeDetector(),
            ContourExtractor(),
            SplineGenerator(),
            DXFExporter(),
            STEPExporter()
        ]
        self.observers: List[Callable] = []
        self.start_time = 0.0
    
    def add_observer(self, observer: Callable):
        """Add observer for pipeline events"""
        self.observers.append(observer)
    
    def remove_observer(self, observer: Callable):
        """Remove observer"""
        if observer in self.observers:
            self.observers.remove(observer)
    
    def notify_observers(self, event_type: str, data: ProcessingResult):
        """Notify all observers of pipeline events"""
        for observer in self.observers:
            try:
                observer(event_type, data)
            except Exception as e:
                print(f"Error in observer: {e}")
    
    def process(self, image_path: str, parameters: ProcessingParameters) -> ProcessingResult:
        """
        Execute the complete processing pipeline
        
        Args:
            image_path: Path to input image
            parameters: Processing parameters
            
        Returns:
            ProcessingResult with all processing data
        """
        self.start_time = time.time()
        result = ProcessingResult()
        result.image_path = image_path
        result.parameters = parameters
        
        try:
            # Execute each step in sequence
            for i, step in enumerate(self.steps):
                if result.cancelled:
                    break
                
                # Update progress
                progress = int((i / len(self.steps)) * 100)
                result.update_progress(progress)
                
                # Notify observers
                self.notify_observers(f"step_{i}_started", result)
                
                # Execute step
                result = step.execute(result)
                
                # Store step result
                result.add_step_result(step.__class__.__name__, result)
                
                # Notify observers
                self.notify_observers(f"step_{i}_completed", result)
                
                # Check for errors
                if not result.success:
                    break
            
            # Final progress update
            if result.success and not result.cancelled:
                result.update_progress(100)
                result.processing_time = time.time() - self.start_time
                
                # Update statistics
                result.contour_count = len(result.contours)
                result.spline_count = len(result.splines)
                
                self.notify_observers("processing_completed", result)
            else:
                self.notify_observers("processing_failed", result)
                
        except Exception as e:
            result.set_error(f"Pipeline error: {str(e)}")
            self.notify_observers("processing_error", result)
        
        return result
    
    def cancel(self, result: ProcessingResult):
        """Cancel current processing"""
        result.set_cancelled()
        self.notify_observers("processing_cancelled", result)
    
    def get_step_names(self) -> List[str]:
        """Get list of step names"""
        return [step.__class__.__name__ for step in self.steps]
    
    def get_step_count(self) -> int:
        """Get total number of steps"""
        return len(self.steps)
