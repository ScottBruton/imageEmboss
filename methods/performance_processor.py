"""
Performance-Optimized Contour Processing Module
Implements parallel processing, Numba acceleration, and enhanced CADQuery integration
"""

import numpy as np
import cv2
import multiprocessing as mp
from multiprocessing import Pool, Manager
from typing import List, Tuple, Dict, Optional, Callable
import time
import os
import tempfile
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging

# Optional imports with fallbacks
try:
    import numba
    from numba import jit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("Numba not available - using standard Python for numerical operations")

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    print("CadQuery not available - using fallback methods")

import ezdxf


@dataclass
class ProcessingConfig:
    """Configuration for performance-optimized processing"""
    # Multiprocessing settings
    max_workers: int = None  # None = auto-detect CPU cores
    chunk_size: int = 10  # Number of contours per process
    
    # Numba settings
    use_numba: bool = True
    numba_cache: bool = True
    
    # CADQuery settings
    use_cadquery: bool = True
    parallel_extrusion: bool = True
    
    # Performance monitoring
    enable_profiling: bool = False
    log_performance: bool = True


class PerformanceProcessor:
    """Main class for performance-optimized contour processing"""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.logger = self._setup_logging()
        
        # Auto-detect CPU cores if not specified
        if self.config.max_workers is None:
            self.config.max_workers = mp.cpu_count()
        
        self.logger.info(f"PerformanceProcessor initialized with {self.config.max_workers} workers")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for performance monitoring"""
        logger = logging.getLogger('PerformanceProcessor')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def process_contours_parallel(self, contours: List, img_size: Tuple[int, int], 
                                params: Dict, progress_callback: Callable = None) -> List:
        """
        Process contours in parallel using multiprocessing
        
        Args:
            contours: List of contours to process
            img_size: Image dimensions (height, width)
            params: Processing parameters
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of processed contours
        """
        if not contours:
            return []
        
        self.logger.info(f"Processing {len(contours)} contours in parallel")
        start_time = time.time()
        
        # Split contours into chunks for parallel processing
        chunk_size = self.config.chunk_size
        contour_chunks = [contours[i:i + chunk_size] for i in range(0, len(contours), chunk_size)]
        
        self.logger.info(f"Split into {len(contour_chunks)} chunks of max {chunk_size} contours each")
        
        # Process chunks in parallel
        processed_contours = []
        
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all chunks
            future_to_chunk = {
                executor.submit(self._process_contour_chunk, chunk, img_size, params, i): i
                for i, chunk in enumerate(contour_chunks)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk_idx = future_to_chunk[future]
                try:
                    chunk_result = future.result()
                    processed_contours.extend(chunk_result)
                    
                    if progress_callback:
                        progress = int((chunk_idx + 1) / len(contour_chunks) * 100)
                        progress_callback(progress, f"Processed chunk {chunk_idx + 1}/{len(contour_chunks)}")
                    
                    self.logger.info(f"Completed chunk {chunk_idx + 1}/{len(contour_chunks)}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing chunk {chunk_idx}: {e}")
                    continue
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Parallel processing completed in {elapsed_time:.2f}s")
        
        return processed_contours
    
    def _process_contour_chunk(self, contour_chunk: List, img_size: Tuple[int, int], 
                              params: Dict, chunk_idx: int) -> List:
        """Process a single chunk of contours (runs in separate process)"""
        try:
            # Import here to avoid issues with multiprocessing
            from .helpers import find_edges_and_contours, contours_from_mask
            
            processed_contours = []
            
            for i, contour in enumerate(contour_chunk):
                try:
                    # Apply Numba-accelerated processing if available
                    if NUMBA_AVAILABLE and self.config.use_numba:
                        processed_contour = self._numba_process_contour(contour, params)
                    else:
                        # Fallback to standard processing
                        processed_contour = self._standard_process_contour(contour, params)
                    
                    if processed_contour is not None:
                        processed_contours.append(processed_contour)
                        
                except Exception as e:
                    print(f"Error processing contour {i} in chunk {chunk_idx}: {e}")
                    continue
            
            return processed_contours
            
        except Exception as e:
            print(f"Error in chunk {chunk_idx}: {e}")
            return []
    
    def _numba_process_contour(self, contour, params: Dict):
        """Process contour using Numba-accelerated functions"""
        if not NUMBA_AVAILABLE:
            return self._standard_process_contour(contour, params)
        
        try:
            # Convert contour to numpy array for Numba processing
            if isinstance(contour, list):
                contour_array = np.array(contour, dtype=np.float32)
            else:
                contour_array = contour.astype(np.float32)
            
            # Apply Numba-accelerated simplification
            simplified = self._numba_simplify_contour(contour_array, params.get('simplify_pct', 0.6))
            
            return simplified
            
        except Exception as e:
            print(f"Numba processing failed, falling back to standard: {e}")
            return self._standard_process_contour(contour, params)
    
    def _standard_process_contour(self, contour, params: Dict):
        """Standard contour processing (fallback)"""
        try:
            # Apply standard OpenCV processing
            if isinstance(contour, list):
                contour_array = np.array(contour, dtype=np.float32)
            else:
                contour_array = contour.astype(np.float32)
            
            # Apply simplification using OpenCV
            simplify_pct = params.get('simplify_pct', 0.6)
            if simplify_pct > 0:
                epsilon = simplify_pct * 0.01 * cv2.arcLength(contour_array, True)
                simplified = cv2.approxPolyDP(contour_array, epsilon, True)
                return simplified
            
            return contour_array
            
        except Exception as e:
            print(f"Standard processing failed: {e}")
            return None


# Numba-accelerated functions (only defined if Numba is available)
if NUMBA_AVAILABLE:
    
    @jit(nopython=True, cache=True)
    def _numba_simplify_contour(contour_points: np.ndarray, simplify_pct: float) -> np.ndarray:
        """
        Numba-accelerated contour simplification using Douglas-Peucker algorithm
        """
        if len(contour_points) < 3:
            return contour_points
        
        # Calculate epsilon based on contour perimeter
        perimeter = 0.0
        for i in range(len(contour_points)):
            p1 = contour_points[i]
            p2 = contour_points[(i + 1) % len(contour_points)]
            perimeter += np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        
        epsilon = simplify_pct * 0.01 * perimeter
        
        # Simplified Douglas-Peucker implementation
        if epsilon <= 0:
            return contour_points
        
        # Find the point with maximum distance from the line between first and last points
        max_dist = 0.0
        max_index = 0
        first_point = contour_points[0]
        last_point = contour_points[-1]
        
        for i in range(1, len(contour_points) - 1):
            point = contour_points[i]
            # Calculate distance from point to line
            dist = _point_to_line_distance(point, first_point, last_point)
            if dist > max_dist:
                max_dist = dist
                max_index = i
        
        # If max distance is greater than epsilon, recursively simplify
        if max_dist > epsilon:
            # Recursively simplify both segments
            left_segment = _numba_simplify_contour(contour_points[:max_index + 1], simplify_pct)
            right_segment = _numba_simplify_contour(contour_points[max_index:], simplify_pct)
            
            # Combine results (remove duplicate middle point)
            result = np.vstack((left_segment[:-1], right_segment))
            return result
        else:
            # All points are close to the line, return just endpoints
            return np.array([first_point, last_point])
    
    @jit(nopython=True, cache=True)
    def _point_to_line_distance(point: np.ndarray, line_start: np.ndarray, line_end: np.ndarray) -> float:
        """Calculate distance from point to line segment"""
        # Vector from line_start to line_end
        line_vec = line_end - line_start
        # Vector from line_start to point
        point_vec = point - line_start
        
        # Project point_vec onto line_vec
        line_len_sq = line_vec[0]**2 + line_vec[1]**2
        if line_len_sq == 0:
            return np.sqrt(point_vec[0]**2 + point_vec[1]**2)
        
        t = (point_vec[0] * line_vec[0] + point_vec[1] * line_vec[1]) / line_len_sq
        t = max(0.0, min(1.0, t))  # Clamp to line segment
        
        # Find closest point on line segment
        closest_point = line_start + t * line_vec
        
        # Return distance to closest point
        return np.sqrt((point[0] - closest_point[0])**2 + (point[1] - closest_point[1])**2)


class EnhancedCADQueryProcessor:
    """Enhanced CADQuery integration with parallel processing"""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.logger = logging.getLogger('EnhancedCADQueryProcessor')
    
    def create_3d_model_parallel(self, contours: List, img_size: Tuple[int, int], 
                               mm_per_px: float, extrude_height: float,
                               progress_callback: Callable = None) -> Optional[cq.Workplane]:
        """
        Create 3D model using CADQuery with parallel processing
        
        Args:
            contours: List of contours to extrude
            img_size: Image dimensions
            mm_per_px: Scale factor
            extrude_height: Extrusion height in mm
            progress_callback: Optional progress callback
            
        Returns:
            CADQuery Workplane with extruded model
        """
        if not CADQUERY_AVAILABLE:
            self.logger.error("CADQuery not available")
            return None
        
        if not contours:
            self.logger.warning("No contours provided")
            return None
        
        self.logger.info(f"Creating 3D model from {len(contours)} contours")
        start_time = time.time()
        
        try:
            # Create temporary DXF file
            temp_dxf_path = self._create_temp_dxf(contours, img_size, mm_per_px, progress_callback)
            
            if progress_callback:
                progress_callback(30, "Importing DXF with CADQuery...")
            
            # Import DXF and get wires
            workplane = cq.importers.importDXF(temp_dxf_path).wires()
            
            if progress_callback:
                progress_callback(50, "Processing wires in parallel...")
            
            # Process wires in parallel if enabled
            if self.config.parallel_extrusion and len(workplane.objects) > 1:
                extruded_solids = self._extrude_wires_parallel(workplane.objects, extrude_height, progress_callback)
            else:
                extruded_solids = self._extrude_wires_sequential(workplane.objects, extrude_height, progress_callback)
            
            if not extruded_solids:
                self.logger.error("No wires could be extruded successfully")
                return None
            
            if progress_callback:
                progress_callback(90, "Combining solids...")
            
            # Combine all extruded solids
            if len(extruded_solids) == 1:
                final_solid = extruded_solids[0]
            else:
                # Union all solids
                final_solid = extruded_solids[0]
                for solid in extruded_solids[1:]:
                    try:
                        final_solid = final_solid.union(solid)
                    except Exception as e:
                        self.logger.warning(f"Failed to union solid: {e}")
                        continue
            
            if progress_callback:
                progress_callback(100, "3D model creation completed!")
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"3D model created in {elapsed_time:.2f}s")
            
            return cq.Workplane().add(final_solid)
            
        except Exception as e:
            self.logger.error(f"Error creating 3D model: {e}")
            return None
        
        finally:
            # Clean up temporary file
            try:
                if 'temp_dxf_path' in locals():
                    os.unlink(temp_dxf_path)
            except:
                pass
    
    def _create_temp_dxf(self, contours: List, img_size: Tuple[int, int], 
                        mm_per_px: float, progress_callback: Callable = None) -> str:
        """Create temporary DXF file with contours"""
        h, w = img_size
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.dxf')
        os.close(temp_fd)
        
        # Create DXF document
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        if progress_callback:
            progress_callback(10, "Creating DXF file...")
        
        # Add contours as polylines
        for i, contour in enumerate(contours):
            try:
                # Convert contour to DXF coordinates
                points = []
                for point in contour:
                    if len(point) >= 2:
                        if isinstance(point[0], (list, tuple, np.ndarray)):
                            x, y = float(point[0][0]), float(point[0][1])
                        else:
                            x, y = float(point[0]), float(point[1])
                        
                        # Convert to DXF coordinates
                        x_mm = x * mm_per_px
                        y_mm = (h - y) * mm_per_px
                        points.append((x_mm, y_mm))
                
                if len(points) >= 3:
                    # Create polyline
                    polyline = msp.add_lwpolyline(points)
                    polyline.closed = True
                    
            except Exception as e:
                self.logger.warning(f"Failed to add contour {i}: {e}")
                continue
        
        # Save DXF file
        doc.saveas(temp_path)
        
        if progress_callback:
            progress_callback(20, "DXF file created")
        
        return temp_path
    
    def _extrude_wires_parallel(self, wires: List, extrude_height: float, 
                               progress_callback: Callable = None) -> List:
        """Extrude wires in parallel"""
        if not self.config.parallel_extrusion:
            return self._extrude_wires_sequential(wires, extrude_height, progress_callback)
        
        self.logger.info(f"Extruding {len(wires)} wires in parallel")
        
        # Split wires into chunks for parallel processing
        chunk_size = max(1, len(wires) // self.config.max_workers)
        wire_chunks = [wires[i:i + chunk_size] for i in range(0, len(wires), chunk_size)]
        
        extruded_solids = []
        
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all chunks
            future_to_chunk = {
                executor.submit(self._extrude_wire_chunk, chunk, extrude_height): i
                for i, chunk in enumerate(wire_chunks)
            }
            
            # Collect results
            for future in as_completed(future_to_chunk):
                chunk_idx = future_to_chunk[future]
                try:
                    chunk_solids = future.result()
                    extruded_solids.extend(chunk_solids)
                    
                    if progress_callback:
                        progress = 50 + int((chunk_idx + 1) / len(wire_chunks) * 30)
                        progress_callback(progress, f"Extruded chunk {chunk_idx + 1}/{len(wire_chunks)}")
                    
                except Exception as e:
                    self.logger.error(f"Error extruding chunk {chunk_idx}: {e}")
                    continue
        
        return extruded_solids
    
    def _extrude_wire_chunk(self, wire_chunk: List, extrude_height: float) -> List:
        """Extrude a chunk of wires (runs in separate process)"""
        try:
            import cadquery as cq
            
            extruded_solids = []
            
            for wire in wire_chunk:
                try:
                    extruded = wire.toPending().extrude(extrude_height)
                    extruded_solids.append(extruded)
                except Exception as e:
                    print(f"Failed to extrude wire: {e}")
                    continue
            
            return extruded_solids
            
        except Exception as e:
            print(f"Error in wire chunk processing: {e}")
            return []
    
    def _extrude_wires_sequential(self, wires: List, extrude_height: float, 
                                 progress_callback: Callable = None) -> List:
        """Extrude wires sequentially (fallback)"""
        extruded_solids = []
        
        for i, wire in enumerate(wires):
            try:
                if progress_callback:
                    progress = 50 + int((i + 1) / len(wires) * 30)
                    progress_callback(progress, f"Extruding wire {i + 1}/{len(wires)}")
                
                extruded = wire.toPending().extrude(extrude_height)
                extruded_solids.append(extruded)
                
            except Exception as e:
                self.logger.warning(f"Failed to extrude wire {i}: {e}")
                continue
        
        return extruded_solids


def benchmark_performance(contours: List, img_size: Tuple[int, int], 
                         params: Dict, iterations: int = 3) -> Dict:
    """
    Benchmark performance improvements
    
    Args:
        contours: Test contours
        img_size: Image dimensions
        params: Processing parameters
        iterations: Number of benchmark iterations
        
    Returns:
        Dictionary with benchmark results
    """
    results = {}
    
    # Test standard processing
    print("Benchmarking standard processing...")
    standard_times = []
    for i in range(iterations):
        start_time = time.time()
        processor = PerformanceProcessor(ProcessingConfig(use_numba=False, max_workers=1))
        processor.process_contours_parallel(contours, img_size, params)
        standard_times.append(time.time() - start_time)
    
    results['standard'] = {
        'mean_time': np.mean(standard_times),
        'std_time': np.std(standard_times),
        'times': standard_times
    }
    
    # Test parallel processing
    print("Benchmarking parallel processing...")
    parallel_times = []
    for i in range(iterations):
        start_time = time.time()
        processor = PerformanceProcessor(ProcessingConfig(use_numba=False, max_workers=mp.cpu_count()))
        processor.process_contours_parallel(contours, img_size, params)
        parallel_times.append(time.time() - start_time)
    
    results['parallel'] = {
        'mean_time': np.mean(parallel_times),
        'std_time': np.std(parallel_times),
        'times': parallel_times
    }
    
    # Test with Numba (if available)
    if NUMBA_AVAILABLE:
        print("Benchmarking Numba-accelerated processing...")
        numba_times = []
        for i in range(iterations):
            start_time = time.time()
            processor = PerformanceProcessor(ProcessingConfig(use_numba=True, max_workers=mp.cpu_count()))
            processor.process_contours_parallel(contours, img_size, params)
            numba_times.append(time.time() - start_time)
        
        results['numba'] = {
            'mean_time': np.mean(numba_times),
            'std_time': np.std(numba_times),
            'times': numba_times
        }
    
    # Calculate speedup ratios
    results['speedup_parallel'] = results['standard']['mean_time'] / results['parallel']['mean_time']
    if 'numba' in results:
        results['speedup_numba'] = results['standard']['mean_time'] / results['numba']['mean_time']
    
    return results
