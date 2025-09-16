"""
Enhanced STEP Export Module with Performance Optimizations
Integrates parallel processing, Numba acceleration, and improved CADQuery handling
"""

import os
import tempfile
import time
import logging
from typing import List, Tuple, Optional, Callable
import numpy as np

# Import our performance processor
from .performance_processor import EnhancedCADQueryProcessor, ProcessingConfig, benchmark_performance

# Optional imports with fallbacks
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    print("CadQuery not available - using fallback methods")

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("Trimesh not available - using fallback methods")

import ezdxf


class EnhancedStepExporter:
    """Enhanced STEP exporter with performance optimizations"""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.cadquery_processor = EnhancedCADQueryProcessor(config)
        self.logger = logging.getLogger('EnhancedStepExporter')
    
    def export_step_file_enhanced(self, contours: List, out_path: str, img_size: Tuple[int, int], 
                                 mm_per_px: float = 0.25, extrude_height: float = 1.0, 
                                 progress_callback: Callable = None) -> bool:
        """
        Enhanced STEP file export with performance optimizations
        
        Args:
            contours: List of contours to export
            out_path: Output file path
            img_size: Image dimensions (height, width)
            mm_per_px: Scale factor in mm per pixel
            extrude_height: Extrusion height in mm
            progress_callback: Optional progress callback
            
        Returns:
            True if successful, False otherwise
        """
        if not contours:
            self.logger.warning("No contours to export")
            return False
        
        self.logger.info(f"Enhanced STEP export: {len(contours)} contours, {extrude_height}mm height")
        print(f"🔧 ENHANCED EXPORT: Starting with {len(contours)} contours")  # Immediate debug output
        start_time = time.time()
        
        try:
            # Create 3D model using enhanced CADQuery processor
            if progress_callback:
                progress_callback(5, f"Starting enhanced processing of {len(contours)} contours...")
                print(f"🔧 ENHANCED EXPORT: Progress callback called with 5%")  # Immediate debug output
            
            workplane = self.cadquery_processor.create_3d_model_parallel(
                contours, img_size, mm_per_px, extrude_height, progress_callback
            )
            
            if workplane is None:
                self.logger.error("Failed to create 3D model")
                return False
            
            # Check if there were any problematic batches
            if hasattr(self.cadquery_processor, 'problematic_batches_saved'):
                self.logger.info("Some batches were saved as separate files due to union issues")
            
            if progress_callback:
                progress_callback(85, "3D model created, exporting to STEP file...")
            
            # Export to STEP file
            workplane.export(out_path)
            
            if progress_callback:
                progress_callback(95, "STEP file saved, creating STL preview...")
            
            # Create STL preview file
            stl_path = out_path.replace('.step', '_preview.stl')
            try:
                workplane.export(stl_path)
                self.logger.info(f"Created STL preview: {stl_path}")
            except Exception as e:
                self.logger.warning(f"Failed to create STL preview: {e}")
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Enhanced STEP export completed in {elapsed_time:.2f}s")
            
            if progress_callback:
                progress_callback(100, f"STEP export completed! ({elapsed_time:.1f}s, {len(contours)} contours)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Enhanced STEP export failed: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False
    
    def export_stl_file_enhanced(self, contours: List, out_path: str, img_size: Tuple[int, int], 
                                mm_per_px: float = 0.25, extrude_height: float = 1.0, 
                                progress_callback: Callable = None) -> bool:
        """
        Enhanced STL file export with performance optimizations
        
        Args:
            contours: List of contours to export
            out_path: Output file path
            img_size: Image dimensions (height, width)
            mm_per_px: Scale factor in mm per pixel
            extrude_height: Extrusion height in mm
            progress_callback: Optional progress callback
            
        Returns:
            True if successful, False otherwise
        """
        if not contours:
            self.logger.warning("No contours to export")
            return False
        
        self.logger.info(f"Enhanced STL export: {len(contours)} contours, {extrude_height}mm height")
        start_time = time.time()
        
        try:
            # Create 3D model using enhanced CADQuery processor
            if progress_callback:
                progress_callback(10, "Creating 3D model with enhanced processing...")
            
            workplane = self.cadquery_processor.create_3d_model_parallel(
                contours, img_size, mm_per_px, extrude_height, progress_callback
            )
            
            if workplane is None:
                self.logger.error("Failed to create 3D model")
                return False
            
            if progress_callback:
                progress_callback(90, "Exporting STL file...")
            
            # Export to STL file
            workplane.export(out_path)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Enhanced STL export completed in {elapsed_time:.2f}s")
            
            if progress_callback:
                progress_callback(100, "STL export completed!")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Enhanced STL export failed: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False
    
    def export_with_benchmark(self, contours: List, out_path: str, img_size: Tuple[int, int], 
                             mm_per_px: float = 0.25, extrude_height: float = 1.0, 
                             progress_callback: Callable = None) -> Tuple[bool, dict]:
        """
        Export with performance benchmarking
        
        Returns:
            Tuple of (success, benchmark_results)
        """
        if not self.config.enable_profiling:
            # Regular export without benchmarking
            success = self.export_step_file_enhanced(contours, out_path, img_size, mm_per_px, extrude_height, progress_callback)
            return success, {}
        
        self.logger.info("Running performance benchmark...")
        
        # Benchmark contour processing
        benchmark_results = benchmark_performance(contours, img_size, {
            'simplify_pct': 0.6,
            'gap_threshold': 5.0
        })
        
        # Export with timing
        start_time = time.time()
        success = self.export_step_file_enhanced(contours, out_path, img_size, mm_per_px, extrude_height, progress_callback)
        export_time = time.time() - start_time
        
        benchmark_results['export_time'] = export_time
        benchmark_results['total_contours'] = len(contours)
        benchmark_results['contours_per_second'] = len(contours) / export_time if export_time > 0 else 0
        
        self.logger.info(f"Benchmark results: {benchmark_results}")
        
        return success, benchmark_results


def export_step_file_enhanced(contours: List, out_path: str, img_size: Tuple[int, int], 
                             mm_per_px: float = 0.25, extrude_height: float = 1.0, 
                             progress_callback: Callable = None, config: ProcessingConfig = None) -> bool:
    """
    Enhanced STEP file export function (backward compatible)
    
    Args:
        contours: List of contours to export
        out_path: Output file path
        img_size: Image dimensions (height, width)
        mm_per_px: Scale factor in mm per pixel
        extrude_height: Extrusion height in mm
        progress_callback: Optional progress callback
        config: Processing configuration
        
    Returns:
        True if successful, False otherwise
    """
    exporter = EnhancedStepExporter(config)
    return exporter.export_step_file_enhanced(contours, out_path, img_size, mm_per_px, extrude_height, progress_callback)


def export_stl_file_enhanced(contours: List, out_path: str, img_size: Tuple[int, int], 
                            mm_per_px: float = 0.25, extrude_height: float = 1.0, 
                            progress_callback: Callable = None, config: ProcessingConfig = None) -> bool:
    """
    Enhanced STL file export function (backward compatible)
    
    Args:
        contours: List of contours to export
        out_path: Output file path
        img_size: Image dimensions (height, width)
        mm_per_px: Scale factor in mm per pixel
        extrude_height: Extrusion height in mm
        progress_callback: Optional progress callback
        config: Processing configuration
        
    Returns:
        True if successful, False otherwise
    """
    exporter = EnhancedStepExporter(config)
    return exporter.export_stl_file_enhanced(contours, out_path, img_size, mm_per_px, extrude_height, progress_callback)


def export_with_benchmark(contours: List, out_path: str, img_size: Tuple[int, int], 
                         mm_per_px: float = 0.25, extrude_height: float = 1.0, 
                         progress_callback: Callable = None, config: ProcessingConfig = None) -> Tuple[bool, dict]:
    """
    Export with performance benchmarking (backward compatible)
    
    Returns:
        Tuple of (success, benchmark_results)
    """
    exporter = EnhancedStepExporter(config)
    return exporter.export_with_benchmark(contours, out_path, img_size, mm_per_px, extrude_height, progress_callback)


# Fallback functions for when enhanced features are not available
def export_step_file_fallback(contours: List, out_path: str, img_size: Tuple[int, int], 
                             mm_per_px: float = 0.25, extrude_height: float = 1.0, 
                             progress_callback: Callable = None) -> bool:
    """
    Fallback STEP export using trimesh (when CADQuery is not available)
    """
    if not TRIMESH_AVAILABLE:
        print("ERROR: Neither CADQuery nor Trimesh available for 3D export")
        return False
    
    try:
        h, w = img_size
        print(f"Creating STL file with Trimesh fallback: {len(contours)} contours, {extrude_height}mm extrusion height")
        
        if progress_callback:
            progress_callback(10, "Creating 3D mesh with Trimesh...")
        
        # Convert contours to 2D points
        all_points = []
        for contour in contours:
            for point in contour:
                if len(point) >= 2:
                    if isinstance(point[0], (list, tuple, np.ndarray)):
                        x, y = float(point[0][0]), float(point[0][1])
                    else:
                        x, y = float(point[0]), float(point[1])
                    
                    # Convert to DXF coordinates
                    x_mm = x * mm_per_px
                    y_mm = (h - y) * mm_per_px
                    all_points.append([x_mm, y_mm, 0])  # Start at Z=0
        
        if len(all_points) < 3:
            print("ERROR: Not enough points to create 3D model")
            return False
        
        # Create 2D mesh
        points_2d = np.array(all_points)[:, :2]  # Remove Z coordinate for 2D processing
        
        # Create a simple extruded mesh using trimesh
        # This is a simplified approach - for production use, consider more sophisticated mesh generation
        mesh = trimesh.creation.extrude_polygon(
            trimesh.path.polygons.Polygon(points_2d), 
            height=extrude_height
        )
        
        if progress_callback:
            progress_callback(80, "Saving STL file...")
        
        # Export as STL (trimesh doesn't directly support STEP)
        mesh.export(out_path.replace('.step', '.stl'))
        
        if progress_callback:
            progress_callback(100, "STL export completed!")
        
        print(f"Successfully exported {len(contours)} contours to {out_path.replace('.step', '.stl')} using Trimesh fallback")
        return True
        
    except Exception as e:
        print(f"ERROR: Trimesh fallback export failed: {e}")
        if progress_callback:
            progress_callback(0, f"Error: {str(e)}")
        return False
