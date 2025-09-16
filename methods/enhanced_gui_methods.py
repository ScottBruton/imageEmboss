"""
Enhanced GUI Methods with Performance Optimizations
Integrates parallel processing, Numba acceleration, and improved algorithms into the GUI
"""

import numpy as np
import cv2
import time
import logging
from typing import List, Tuple, Dict, Optional, Callable
import multiprocessing as mp

# Import our enhanced modules
from .performance_processor import PerformanceProcessor, ProcessingConfig
from .enhanced_helpers import EnhancedImageProcessor
from .enhanced_step_export import EnhancedStepExporter

# Import original GUI methods for fallback
from .gui_methods import GUIMethods


class EnhancedGUIMethods(GUIMethods):
    """Enhanced GUI methods with performance optimizations"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize performance configuration
        self.performance_config = ProcessingConfig(
            max_workers=mp.cpu_count(),
            use_numba=True,
            use_cadquery=True,
            parallel_extrusion=True,
            enable_profiling=False,
            log_performance=True
        )
        
        # Initialize performance processors
        self.performance_processor = PerformanceProcessor(self.performance_config)
        self.enhanced_image_processor = EnhancedImageProcessor(self.performance_config)
        self.enhanced_step_exporter = EnhancedStepExporter(self.performance_config)
        
        # Performance monitoring
        self.performance_logger = logging.getLogger('EnhancedGUIMethods')
        self.processing_times = {}
        
        # Add performance settings to the GUI
        self._setup_performance_settings()
    
    def _setup_performance_settings(self):
        """Setup performance-related settings in the GUI"""
        # Add performance configuration to params
        if not hasattr(self, 'params'):
            self.params = {}
        
        # Performance settings
        self.params['use_parallel_processing'] = True
        self.params['use_numba_acceleration'] = True
        self.params['use_enhanced_cadquery'] = True
        self.params['enable_performance_profiling'] = False
        self.params['max_workers'] = mp.cpu_count()
        self.params['chunk_size'] = 10
    
    def update_preview_enhanced(self, progress_callback: Callable = None):
        """
        Enhanced preview update with performance optimizations
        """
        if not hasattr(self, 'original_image') or self.original_image is None:
            return
        
        start_time = time.time()
        self.performance_logger.info("Starting enhanced preview update")
        
        try:
            # Update parameters from sliders
            self.update_parameters_from_sliders()
            
            if progress_callback:
                progress_callback(10, "Starting enhanced edge detection...")
            
            # Use enhanced edge detection
            if self.params.get('use_parallel_processing', True):
                # Process in parallel
                edges = self.enhanced_image_processor.find_edges_and_contours_enhanced(
                    self.original_image, self.params, progress_callback
                )
            else:
                # Fallback to original method
                from .helpers import find_edges_and_contours
                edges = find_edges_and_contours(self.original_image, self.params)
            
            if progress_callback:
                progress_callback(50, "Extracting contours...")
            
            # Use enhanced contour extraction
            if self.params.get('use_parallel_processing', True):
                contours = self.enhanced_image_processor.contours_from_mask_enhanced(
                    edges,
                    self.params.get("largest_n", 3),
                    self.params.get("simplify_pct", 0.6),
                    self.params.get("gap_threshold", 5.0),
                    progress_callback
                )
            else:
                # Fallback to original method
                from .helpers import contours_from_mask
                contours = contours_from_mask(
                    edges,
                    self.params.get("largest_n", 3),
                    self.params.get("simplify_pct", 0.6),
                    self.params.get("gap_threshold", 5.0)
                )
            
            # Store results
            self.current_contours = contours
            
            if progress_callback:
                progress_callback(90, "Updating display...")
            
            # Update display
            self.display_dxf_preview()
            
            elapsed_time = time.time() - start_time
            self.processing_times['preview_update'] = elapsed_time
            self.performance_logger.info(f"Enhanced preview update completed in {elapsed_time:.2f}s")
            
            if progress_callback:
                progress_callback(100, "Preview update completed!")
            
            # Update status bar with performance info
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(
                    f"Enhanced processing completed in {elapsed_time:.2f}s "
                    f"({len(contours)} contours found)"
                )
            
        except Exception as e:
            self.performance_logger.error(f"Enhanced preview update failed: {e}")
            # Fallback to original method
            self.update_preview()
    
    def process_area_for_edges_enhanced(self, scene_point, radius, params=None, progress_callback: Callable = None):
        """
        Enhanced area processing with performance optimizations
        """
        if not hasattr(self, 'original_image') or self.original_image is None:
            return
        
        start_time = time.time()
        self.performance_logger.info(f"Starting enhanced area processing at {scene_point} with radius {radius}")
        
        try:
            # Use provided params or current params
            params_to_use = params or self.params.copy()
            
            # Convert scene point to image coordinates
            x = int(scene_point.x())
            y = int(scene_point.y())
            
            # Define ROI bounds
            x1 = max(0, x - radius)
            y1 = max(0, y - radius)
            x2 = min(self.original_image.shape[1], x + radius)
            y2 = min(self.original_image.shape[0], y + radius)
            
            # Extract ROI
            roi = self.original_image[y1:y2, x1:x2]
            
            if roi.size == 0:
                self.performance_logger.warning("Empty ROI")
                return
            
            if progress_callback:
                progress_callback(20, "Processing ROI with enhanced methods...")
            
            # Use enhanced edge detection on ROI
            if self.params.get('use_parallel_processing', True):
                edges = self.enhanced_image_processor.find_edges_and_contours_enhanced(
                    roi, params_to_use, progress_callback
                )
            else:
                # Fallback to original method
                from .helpers import find_edges_and_contours
                edges = find_edges_and_contours(roi, params_to_use)
            
            if progress_callback:
                progress_callback(60, "Extracting contours from ROI...")
            
            # Use enhanced contour extraction
            if self.params.get('use_parallel_processing', True):
                area_contours = self.enhanced_image_processor.contours_from_mask_enhanced(
                    edges,
                    params_to_use.get("largest_n", 3),
                    params_to_use.get("simplify_pct", 0.6),
                    params_to_use.get("gap_threshold", 5.0),
                    progress_callback
                )
            else:
                # Fallback to original method
                from .helpers import contours_from_mask
                area_contours = contours_from_mask(
                    edges,
                    params_to_use.get("largest_n", 3),
                    params_to_use.get("simplify_pct", 0.6),
                    params_to_use.get("gap_threshold", 5.0)
                )
            
            if progress_callback:
                progress_callback(80, "Adjusting contours to global coordinates...")
            
            # Adjust contours back to full image coordinates
            adjusted_contours = []
            for contour in area_contours:
                adjusted_contour = contour.copy()
                adjusted_contour[:, :, 0] += x1  # Add x offset
                adjusted_contour[:, :, 1] += y1  # Add y offset
                adjusted_contours.append(adjusted_contour)
            
            # Filter out tiny contours
            filtered_contours = []
            for i, contour in enumerate(adjusted_contours):
                contour_float32 = contour.astype(np.float32)
                area = cv2.contourArea(contour_float32)
                if area > 20:  # Only keep contours with area > 20 pixels
                    filtered_contours.append(contour)
                    self.performance_logger.debug(f"Kept contour {i} with area {area:.1f}")
                else:
                    self.performance_logger.debug(f"Filtered out contour {i} with area {area:.1f} (too small)")
            
            if progress_callback:
                progress_callback(90, "Merging with existing contours...")
            
            # Handle intersections with existing contours
            if filtered_contours:
                self.current_contours = self.handle_contour_intersections(self.current_contours, filtered_contours)
                self.display_dxf_preview()
                
                elapsed_time = time.time() - start_time
                self.processing_times['area_processing'] = elapsed_time
                self.performance_logger.info(f"Enhanced area processing completed in {elapsed_time:.2f}s")
                
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage(
                        f"Enhanced area processing completed in {elapsed_time:.2f}s "
                        f"({len(filtered_contours)} new contours added)"
                    )
            else:
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage("No significant edges found in the selected area")
            
            if progress_callback:
                progress_callback(100, "Area processing completed!")
            
        except Exception as e:
            self.performance_logger.error(f"Enhanced area processing failed: {e}")
            # Fallback to original method
            self.process_area_for_edges(scene_point, radius, params)
    
    def export_dxf_enhanced(self, progress_callback: Callable = None):
        """
        Enhanced DXF export with performance optimizations
        """
        if not hasattr(self, 'current_contours') or not self.current_contours:
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage("No contours to export")
            return
        
        start_time = time.time()
        self.performance_logger.info("Starting enhanced DXF export")
        
        try:
            # Get export parameters
            from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
            
            # Choose export format
            format_choice, ok = QInputDialog.getItem(
                self, "Export Format", "Choose export format:",
                ["DXF", "STEP", "STL"], 0, False
            )
            
            if not ok:
                return
            
            # Get output file path
            if format_choice == "DXF":
                file_filter = "DXF Files (*.dxf)"
            elif format_choice == "STEP":
                file_filter = "STEP Files (*.step)"
            else:  # STL
                file_filter = "STL Files (*.stl)"
            
            out_path, _ = QFileDialog.getSaveFileName(
                self, f"Save {format_choice} File", "", file_filter
            )
            
            if not out_path:
                return
            
            # Get extrusion height for 3D formats
            extrude_height = 1.0
            if format_choice in ["STEP", "STL"]:
                extrude_height, ok = QInputDialog.getDouble(
                    self, "Extrusion Height", "Enter extrusion height (mm):",
                    extrude_height, 0.1, 100.0, 1
                )
                if not ok:
                    return
            
            if progress_callback:
                progress_callback(10, f"Starting enhanced {format_choice} export...")
            
            # Use enhanced export methods
            success = False
            if format_choice == "DXF":
                # Use original DXF export for now (can be enhanced later)
                from .helpers import export_dxf
                success = export_dxf(
                    self.current_contours, out_path, 
                    self.original_image.shape[:2], 
                    self.params.get('mm_per_px', 0.25)
                )
            elif format_choice == "STEP":
                success = self.enhanced_step_exporter.export_step_file_enhanced(
                    self.current_contours, out_path,
                    self.original_image.shape[:2],
                    self.params.get('mm_per_px', 0.25),
                    extrude_height,
                    progress_callback
                )
            elif format_choice == "STL":
                success = self.enhanced_step_exporter.export_stl_file_enhanced(
                    self.current_contours, out_path,
                    self.original_image.shape[:2],
                    self.params.get('mm_per_px', 0.25),
                    extrude_height,
                    progress_callback
                )
            
            elapsed_time = time.time() - start_time
            self.processing_times['export'] = elapsed_time
            
            if success:
                self.performance_logger.info(f"Enhanced {format_choice} export completed in {elapsed_time:.2f}s")
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage(f"Enhanced {format_choice} export completed in {elapsed_time:.2f}s")
                
                # Show success message
                QMessageBox.information(
                    self, "Export Successful",
                    f"Enhanced {format_choice} file exported successfully!\n"
                    f"Processing time: {elapsed_time:.2f}s\n"
                    f"Contours exported: {len(self.current_contours)}"
                )
                
                # Open 3D viewer for 3D formats
                if format_choice in ["STEP", "STL"]:
                    self._open_3d_viewer(out_path)
            else:
                self.performance_logger.error(f"Enhanced {format_choice} export failed")
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage(f"Enhanced {format_choice} export failed")
                
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Enhanced {format_choice} export failed. Please check the logs for details."
                )
            
        except Exception as e:
            self.performance_logger.error(f"Enhanced export failed: {e}")
            # Fallback to original method
            self.export_dxf()
    
    def _open_3d_viewer(self, file_path: str):
        """Open 3D viewer for exported files"""
        try:
            from .step_viewer_dialog import StepViewerDialog
            viewer = StepViewerDialog(self, file_path)
            viewer.exec()
        except Exception as e:
            self.performance_logger.warning(f"Failed to open 3D viewer: {e}")
    
    def toggle_performance_mode(self):
        """Toggle between performance and compatibility modes"""
        if self.params.get('use_parallel_processing', True):
            # Switch to compatibility mode
            self.params['use_parallel_processing'] = False
            self.params['use_numba_acceleration'] = False
            self.params['use_enhanced_cadquery'] = False
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage("Switched to compatibility mode")
        else:
            # Switch to performance mode
            self.params['use_parallel_processing'] = True
            self.params['use_numba_acceleration'] = True
            self.params['use_enhanced_cadquery'] = True
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage("Switched to performance mode")
    
    def show_performance_stats(self):
        """Show performance statistics"""
        try:
            from PySide6.QtWidgets import QMessageBox
            
            stats_text = "Performance Statistics:\n\n"
            
            if self.processing_times:
                for operation, time_taken in self.processing_times.items():
                    stats_text += f"{operation.replace('_', ' ').title()}: {time_taken:.2f}s\n"
            else:
                stats_text += "No performance data available yet.\n"
            
            stats_text += f"\nConfiguration:\n"
            stats_text += f"Parallel Processing: {'Enabled' if self.params.get('use_parallel_processing', True) else 'Disabled'}\n"
            stats_text += f"Numba Acceleration: {'Enabled' if self.params.get('use_numba_acceleration', True) else 'Disabled'}\n"
            stats_text += f"Enhanced CADQuery: {'Enabled' if self.params.get('use_enhanced_cadquery', True) else 'Disabled'}\n"
            stats_text += f"Max Workers: {self.params.get('max_workers', mp.cpu_count())}\n"
            stats_text += f"Chunk Size: {self.params.get('chunk_size', 10)}\n"
            
            QMessageBox.information(self, "Performance Statistics", stats_text)
            
        except Exception as e:
            self.performance_logger.error(f"Failed to show performance stats: {e}")
    
    def benchmark_performance(self):
        """Run performance benchmark"""
        try:
            if not hasattr(self, 'current_contours') or not self.current_contours:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "No Contours", "No contours available for benchmarking. Please process an image first.")
                return
            
            from PySide6.QtWidgets import QProgressDialog
            from .performance_processor import benchmark_performance
            
            # Create progress dialog
            progress = QProgressDialog("Running performance benchmark...", "Cancel", 0, 100, self)
            progress.setWindowModality(2)  # Qt.ApplicationModal
            progress.show()
            
            def progress_callback(value, message):
                progress.setValue(value)
                progress.setLabelText(message)
                if progress.wasCanceled():
                    return False
                return True
            
            # Run benchmark
            results = benchmark_performance(
                self.current_contours,
                self.original_image.shape[:2],
                self.params,
                iterations=3
            )
            
            progress.close()
            
            # Show results
            from PySide6.QtWidgets import QMessageBox
            
            results_text = "Performance Benchmark Results:\n\n"
            results_text += f"Standard Processing: {results['standard']['mean_time']:.2f}s ± {results['standard']['std_time']:.2f}s\n"
            results_text += f"Parallel Processing: {results['parallel']['mean_time']:.2f}s ± {results['parallel']['std_time']:.2f}s\n"
            results_text += f"Speedup: {results['speedup_parallel']:.2f}x\n"
            
            if 'numba' in results:
                results_text += f"Numba Processing: {results['numba']['mean_time']:.2f}s ± {results['numba']['std_time']:.2f}s\n"
                results_text += f"Numba Speedup: {results['speedup_numba']:.2f}x\n"
            
            QMessageBox.information(self, "Benchmark Results", results_text)
            
        except Exception as e:
            self.performance_logger.error(f"Benchmark failed: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Benchmark Failed", f"Performance benchmark failed: {e}")


# Mixin class for easy integration
class PerformanceMixin:
    """Mixin class to add performance features to existing GUI classes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize performance features
        self.performance_config = ProcessingConfig()
        self.performance_processor = PerformanceProcessor(self.performance_config)
        self.enhanced_image_processor = EnhancedImageProcessor(self.performance_config)
        self.enhanced_step_exporter = EnhancedStepExporter(self.performance_config)
        
        # Add performance methods
        self.toggle_performance_mode = EnhancedGUIMethods.toggle_performance_mode
        self.show_performance_stats = EnhancedGUIMethods.show_performance_stats
        self.benchmark_performance = EnhancedGUIMethods.benchmark_performance
