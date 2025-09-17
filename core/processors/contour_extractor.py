"""
Contour extraction processor
"""
import cv2
import numpy as np
from typing import List
from .base_processor import PipelineStep
from ..models.processing_result import ProcessingResult


class ContourExtractor(PipelineStep):
    """Extracts contours from edge images"""
    
    def __init__(self):
        super().__init__()
        self.min_area = 100  # Minimum contour area
    
    def execute(self, result: ProcessingResult) -> ProcessingResult:
        """Extract contours from edges"""
        if result.edges is None:
            result.set_error("No edges available for contour extraction")
            return result
        
        try:
            params = result.parameters
            
            # Find contours using RETR_EXTERNAL for clean shapes
            contours, _ = cv2.findContours(
                255 - result.edges,  # Invert so dark = fill
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if not contours:
                print("⚠️ No contours found")
                result.contours = []
                return result
            
            print(f"🔍 Found {len(contours)} raw contours")
            
            # Filter contours by area
            filtered_contours = []
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area >= self.min_area:
                    filtered_contours.append(contour)
                    if i < 5:  # Log first few
                        print(f"✅ Contour {i}: area={area:.1f}, points={len(contour)}")
                else:
                    if i < 5:  # Log first few
                        print(f"❌ Contour {i}: area={area:.1f} (too small)")
            
            print(f"🔍 {len(filtered_contours)} contours after area filtering")
            
            # Sort by area and keep top contours
            filtered_contours = sorted(filtered_contours, key=cv2.contourArea, reverse=True)
            max_contours = min(len(filtered_contours), int(params.largest_n * 2))
            contours = filtered_contours[:max_contours]
            
            # Apply gap closing if needed
            if params.gap_threshold > 0:
                contours = self._apply_gap_closing(contours, result.edges, params.gap_threshold)
            
            result.contours = contours
            print(f"✅ Final contours: {len(contours)}")
            
        except Exception as e:
            result.set_error(f"Contour extraction failed: {str(e)}")
        
        return result
    
    def _apply_gap_closing(self, contours: List[np.ndarray], edges: np.ndarray, gap_threshold: float) -> List[np.ndarray]:
        """Apply gap closing to contours"""
        try:
            kernel_size = max(1, int(gap_threshold))
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            
            # Create mask from contours
            combined_mask = np.zeros(edges.shape, dtype=np.uint8)
            cv2.drawContours(combined_mask, contours, -1, 255, -1)
            
            # Apply morphological closing
            closed_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            
            # Find new contours from closed mask
            new_contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if new_contours:
                # Sort by area and keep top contours
                new_contours = sorted(new_contours, key=cv2.contourArea, reverse=True)
                max_contours = min(len(new_contours), len(contours))
                contours = new_contours[:max_contours]
                print(f"🔗 Gap closing resulted in {len(contours)} contours")
            
        except Exception as e:
            print(f"⚠️ Gap closing failed: {e}")
        
        return contours
    
    def validate_input(self, result: ProcessingResult) -> bool:
        """Validate input for contour extraction"""
        if result.edges is None:
            result.set_error("No edges available")
            return False
        
        if result.parameters is None:
            result.set_error("No parameters provided")
            return False
        
        return True
    
    def get_progress_weight(self) -> float:
        """Contour extraction is a significant step"""
        return 0.2
