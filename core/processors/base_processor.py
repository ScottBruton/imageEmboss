"""
Base processor class for pipeline steps
"""
from abc import ABC, abstractmethod
from typing import Any
import numpy as np
from ..models.processing_result import ProcessingResult


class PipelineStep(ABC):
    """Abstract base class for pipeline processing steps"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.supports_gpu = False
    
    @abstractmethod
    def execute(self, result: ProcessingResult) -> ProcessingResult:
        """
        Execute the processing step
        
        Args:
            result: Current processing result
            
        Returns:
            Updated processing result
        """
        pass
    
    def supports_gpu_acceleration(self) -> bool:
        """Check if this step supports GPU acceleration"""
        return self.supports_gpu
    
    def execute_gpu(self, result: ProcessingResult) -> ProcessingResult:
        """Execute step with GPU acceleration (override if supported)"""
        return self.execute_cpu(result)
    
    def execute_cpu(self, result: ProcessingResult) -> ProcessingResult:
        """Execute step with CPU (default implementation)"""
        return self.execute(result)
    
    def validate_input(self, result: ProcessingResult) -> bool:
        """Validate input data for this step"""
        return True
    
    def get_progress_weight(self) -> float:
        """Get relative weight of this step for progress calculation"""
        return 1.0
    
    def log_step_start(self, result: ProcessingResult):
        """Log step start"""
        print(f"🔄 {self.name}: Starting...")
    
    def log_step_complete(self, result: ProcessingResult):
        """Log step completion"""
        print(f"✅ {self.name}: Completed")
    
    def log_step_error(self, result: ProcessingResult, error: Exception):
        """Log step error"""
        print(f"❌ {self.name}: Error - {error}")
    
    def safe_execute(self, result: ProcessingResult) -> ProcessingResult:
        """Execute step with error handling"""
        try:
            if not self.validate_input(result):
                result.set_error(f"Invalid input for {self.name}")
                return result
            
            self.log_step_start(result)
            result = self.execute(result)
            self.log_step_complete(result)
            return result
            
        except Exception as e:
            self.log_step_error(result, e)
            result.set_error(f"{self.name} failed: {str(e)}")
            return result
