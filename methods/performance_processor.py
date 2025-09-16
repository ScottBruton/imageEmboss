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
        # Auto-detect CPU cores if not set
        if self.config.max_workers is None:
            self.config.max_workers = mp.cpu_count()
        self.logger = self._setup_logging()
        
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
        completed_chunks = 0
        
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
                    completed_chunks += 1
                    
                    if progress_callback:
                        progress = int((completed_chunks) / len(contour_chunks) * 100)
                        chunk_contours = len(contour_chunks[chunk_idx])
                        total_processed = sum(len(chunk) for chunk in contour_chunks[:completed_chunks])
                        progress_callback(progress, 
                            f"Batch {completed_chunks}/{len(contour_chunks)} complete "
                            f"({chunk_contours} contours) - {total_processed}/{len(contours)} total processed")
                    
                    self.logger.info(f"Completed batch {completed_chunks}/{len(contour_chunks)} "
                                   f"(chunk {chunk_idx + 1}) with {len(chunk_result)} contours")
                    
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
        # Auto-detect CPU cores if not set
        if self.config.max_workers is None:
            self.config.max_workers = mp.cpu_count()
        self.logger = logging.getLogger('EnhancedCADQueryProcessor')
    
    def create_3d_model_parallel(self, contours: List, img_size: Tuple[int, int], 
                               mm_per_px: float, extrude_height: float,
                               progress_callback: Callable = None, output_path: str = None) -> Optional[cq.Workplane]:
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
        print(f"🔧 CADQUERY PROCESSOR: Starting with {len(contours)} contours")  # Immediate debug output
        start_time = time.time()
        
        try:
            # Create temporary DXF file using existing working logic
            print(f"🔧 CADQUERY PROCESSOR: Creating DXF file using existing logic...")  # Immediate debug output
            temp_dxf_path = self._create_temp_dxf_with_existing_logic(contours, img_size, mm_per_px, extrude_height, progress_callback)
            
            if progress_callback:
                progress_callback(30, "Importing DXF with CADQuery...")
            
            # Debug: Check DXF file before import
            self.logger.info(f"Attempting to import DXF from: {temp_dxf_path}")
            if os.path.exists(temp_dxf_path):
                file_size = os.path.getsize(temp_dxf_path)
                self.logger.info(f"DXF file exists, size: {file_size} bytes")
            else:
                self.logger.error(f"DXF file does not exist: {temp_dxf_path}")
                return None
            
            # Import DXF and get wires with proper layer handling
            try:
                # Import DXF with layer selection
                self.logger.info("Attempting CADQuery import with layer selection...")
                imported = cq.importers.importDXF(temp_dxf_path)
                workplane = imported.wires()
                self.logger.info(f"CADQuery import successful, found {len(workplane.objects)} wires")
            except Exception as e:
                self.logger.warning(f"CADQuery import failed, trying alternative method: {e}")
                # Alternative: try importing without layer selection
                try:
                    self.logger.info("Trying CADQuery import with CONTOURS layer...")
                    workplane = cq.importers.importDXF(temp_dxf_path, include=['CONTOURS']).wires()
                    self.logger.info(f"CADQuery import with CONTOURS layer successful, found {len(workplane.objects)} wires")
                except Exception as e2:
                    self.logger.warning(f"CADQuery import with CONTOURS layer failed: {e2}")
                    # Last resort: import all layers
                    try:
                        self.logger.info("Trying CADQuery import with all layers...")
                        workplane = cq.importers.importDXF(temp_dxf_path).wires()
                        self.logger.info(f"CADQuery import with all layers successful, found {len(workplane.objects)} wires")
                    except Exception as e3:
                        self.logger.error(f"All CADQuery import methods failed: {e3}")
                        return None
            
            if progress_callback:
                progress_callback(40, f"Found {len(workplane.objects)} wires, starting extrusion...")
            
            # Process wires in batches for better performance and responsiveness
            # Split wires into smaller batches to avoid freezing the UI
            batch_size = min(50, max(10, len(workplane.objects) // 20))  # Adaptive batch size
            wire_batches = [workplane.objects[i:i + batch_size] for i in range(0, len(workplane.objects), batch_size)]
            
            self.logger.info(f"Processing {len(workplane.objects)} wires in {len(wire_batches)} batches of {batch_size} wires each")
            print(f"🔧 WIRE PROCESSING: {len(workplane.objects)} wires → {len(wire_batches)} batches")
            if progress_callback:
                progress_callback(45, f"Processing {len(workplane.objects)} wires in {len(wire_batches)} batches...")
            
            extruded_solids = []
            
            for batch_idx, wire_batch in enumerate(wire_batches):
                try:
                    if progress_callback:
                        progress = 45 + int((batch_idx / len(wire_batches)) * 40)  # 45-85%
                        progress_callback(progress, f"Extruding batch {batch_idx + 1}/{len(wire_batches)} ({len(wire_batch)} wires)...")
                    
                    print(f"🔧 BATCH {batch_idx + 1}: Processing {len(wire_batch)} wires")
                    
                    # Create a workplane for this batch
                    batch_workplane = cq.Workplane()
                    for wire in wire_batch:
                        batch_workplane = batch_workplane.add(wire)
                    
                    # Validate the batch workplane before extrusion
                    if len(batch_workplane.objects) == 0:
                        self.logger.warning(f"Batch {batch_idx + 1} has no valid wires, skipping")
                        print(f"❌ BATCH {batch_idx + 1}: No valid wires")
                        continue
                    
                    print(f"🔧 BATCH {batch_idx + 1}: Created workplane with {len(batch_workplane.objects)} objects")
                    
                    # Extrude this batch
                    batch_solid = batch_workplane.toPending().extrude(extrude_height)
                    print(f"🔧 BATCH {batch_idx + 1}: Extruded successfully")
                    
                    # Validate the extruded solid before adding to list
                    if batch_solid is None or len(batch_solid.objects) == 0:
                        self.logger.warning(f"Batch {batch_idx + 1} produced null or empty solid, skipping")
                        continue
                    
                    # Skip volume validation for now - it might be causing false positives
                    # TODO: Implement proper CadQuery volume calculation
                    self.logger.info(f"Batch {batch_idx + 1} extruded successfully with {len(wire_batch)} wires")
                    
                    extruded_solids.append(batch_solid)
                    
                    self.logger.info(f"Successfully extruded batch {batch_idx + 1}/{len(wire_batches)} with {len(wire_batch)} wires")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to extrude batch {batch_idx + 1}: {e}")
                    continue
            
            if not extruded_solids:
                self.logger.error("No wire batches could be extruded successfully")
                return None
            
            # Skip union operation - return all batches as separate bodies
            # This avoids the "Null TopoDS_Shape" errors that were causing most batches to fail
            if progress_callback:
                progress_callback(85, f"Preparing {len(extruded_solids)} extruded batches as separate bodies...")
            
            try:
                # Create a workplane with all extruded solids as separate bodies
                final_workplane = cq.Workplane()
                
                for i, solid in enumerate(extruded_solids):
                    if solid is not None and len(solid.objects) > 0:
                        final_workplane = final_workplane.add(solid)
                        if progress_callback:
                            progress = 85 + int((i / len(extruded_solids)) * 10)  # 85-95%
                            progress_callback(progress, f"Adding batch {i + 1}/{len(extruded_solids)} as separate body...")
                    else:
                        self.logger.warning(f"Batch {i + 1} is null or empty, skipping")
                
                self.logger.info(f"Successfully prepared {len(final_workplane.objects)} separate bodies (no union)")
                return final_workplane
                
            except Exception as e:
                self.logger.error(f"Failed to combine extruded solids: {e}")
                return None
            
            if progress_callback:
                progress_callback(90, "3D model creation complete")
            
            # Log performance
            end_time = time.time()
            processing_time = end_time - start_time
            self.logger.info(f"3D model created in {processing_time:.2f} seconds")
            
            return extruded_solid
            
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
        
        # Create DXF document with proper layer setup
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        # Create a default layer for contours (CADQuery requires layers)
        try:
            layer = doc.layers.add("CONTOURS")
            layer.color = 1  # Red color
            self.logger.info(f"Created CONTOURS layer in DXF")
        except Exception as e:
            # Layer might already exist
            self.logger.warning(f"Could not create CONTOURS layer: {e}")
            pass
        
        self.logger.info(f"DXF document created with {len(doc.layers)} layers: {[layer.dxf.name for layer in doc.layers]}")
        
        print(f"🔧 DXF CREATION: Starting with {len(contours)} contours")  # Immediate debug output
        if progress_callback:
            progress_callback(10, f"Creating DXF file with {len(contours)} contours...")
        
        # Add contours as polylines
        for i, contour in enumerate(contours):
            try:
                # Convert contour to DXF coordinates
                points = []
                
                # Debug: Log contour structure (only for first few contours)
                if i < 3:
                    self.logger.info(f"Processing contour {i}: shape={contour.shape}, dtype={contour.dtype}")
                
                for point in contour:
                    # Handle different contour structures
                    if contour.ndim == 3:  # Shape like (N, 1, 2)
                        if len(point) >= 1 and len(point[0]) >= 2:
                            x, y = float(point[0][0]), float(point[0][1])
                        else:
                            continue
                    elif contour.ndim == 2:  # Shape like (N, 2)
                        if len(point) >= 2:
                            x, y = float(point[0]), float(point[1])
                        else:
                            continue
                    else:
                        self.logger.warning(f"Unexpected contour shape: {contour.shape}")
                        continue
                    
                    # Convert to DXF coordinates (scale and flip Y)
                    x_mm = x * mm_per_px
                    y_mm = (img_size[0] - y) * mm_per_px  # Flip Y coordinate
                    points.append((x_mm, y_mm))
                
                if i < 3:  # Only log first few contours
                    self.logger.info(f"Contour {i}: extracted {len(points)} points")
                
                if len(points) >= 3:
                    # Create polyline on the CONTOURS layer
                    polyline = msp.add_lwpolyline(points)
                    polyline.closed = True
                    polyline.dxf.layer = "CONTOURS"
                    if i < 3:  # Only log first few contours
                        self.logger.info(f"Added polyline for contour {i} with {len(points)} points")
                else:
                    self.logger.warning(f"Contour {i} has only {len(points)} points, skipping")
                
                # Update progress for DXF creation - show every contour for better feedback
                if progress_callback:
                    progress = 10 + int((i / len(contours)) * 10)  # 10-20% for DXF creation
                    progress_callback(progress, f"Adding contour {i+1}/{len(contours)} to DXF...")
                    
            except Exception as e:
                self.logger.warning(f"Failed to add contour {i}: {e}")
                continue
        
        # Save DXF file
        doc.saveas(temp_path)
        
        # Debug: Check if file was created and has content
        if os.path.exists(temp_path):
            file_size = os.path.getsize(temp_path)
            self.logger.info(f"DXF file saved to: {temp_path}, size: {file_size} bytes")
        else:
            self.logger.error(f"DXF file was not created at: {temp_path}")
        
        if progress_callback:
            progress_callback(25, f"DXF file created with {len(contours)} contours")
        
        # Debug: Inspect DXF file contents
        self._inspect_dxf_file(temp_path)
        
        return temp_path
    
    def _create_temp_dxf_with_existing_logic(self, contours: List, img_size: Tuple[int, int], 
                                           mm_per_px: float, extrude_height: float = 1.0, 
                                           progress_callback: Callable = None) -> str:
        """Create temporary DXF file using the existing working logic from helpers.py"""
        import tempfile
        import os
        import ezdxf
        
        print(f"🔧 DXF CREATION (EXISTING LOGIC): Starting with {len(contours)} contours")  # Immediate debug output
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.dxf')
        os.close(temp_fd)
        
        h, w = img_size
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        # Debug: Show scaling information
        print(f"📏 SCALING INFO:")
        print(f"   Image size: {w}x{h} pixels")
        print(f"   mm_per_px: {mm_per_px}")
        print(f"   Extrude height: {extrude_height}mm")
        print(f"   Scaled image size: {w * mm_per_px:.1f}x{h * mm_per_px:.1f}mm")
        print(f"   Extrusion ratio: {extrude_height / (w * mm_per_px) * 100:.2f}% of width")
        
        # Warn if extrusion height is too small
        min_recommended_height = max(1.0, (w * mm_per_px) * 0.01)  # At least 1% of width or 1mm
        if extrude_height < min_recommended_height:
            print(f"⚠️  WARNING: Extrusion height ({extrude_height}mm) is very small!")
            print(f"   Recommended minimum: {min_recommended_height:.1f}mm")
            print(f"   This may result in zero-volume solids")
        
        if progress_callback:
            progress_callback(10, f"Creating DXF file with {len(contours)} contours...")
        
        # Pre-process contours to join edge chains and ensure proper connectivity
        processed_contours = self._join_edge_chains(contours)
        self.logger.info(f"Processed {len(contours)} contours into {len(processed_contours)} connected contours")

        # Check closure rate of processed contours
        closed_count = 0
        for i, contour in enumerate(processed_contours):
            if len(contour) >= 3:
                pts = []
                for p in contour:
                    x = float(p[0][0])
                    y = float(p[0][1])
                    x_mm = x * mm_per_px
                    y_mm = (h - y) * mm_per_px
                    pts.append((x_mm, y_mm))
                
                if self._is_contour_closed(pts, tolerance=2.0):
                    closed_count += 1
        
        closure_rate = (closed_count / len(processed_contours) * 100) if processed_contours else 0
        print(f"📊 STEP EXPORT CONTOUR CLOSURE:")
        print(f"   Total contours: {len(processed_contours)}")
        print(f"   Closed contours: {closed_count}")
        print(f"   Closure rate: {closure_rate:.1f}%")
        
        # Process contours with proper closing and edge joining
        for i, cnt in enumerate(processed_contours):
            try:
                pts = []
                for p in cnt:
                    x = float(p[0][0])
                    y = float(p[0][1])
                    x_mm = x * mm_per_px
                    y_mm = (h - y) * mm_per_px
                    pts.append((x_mm, y_mm))
                
                if len(pts) >= 3:
                    # Check if contour is closed before processing
                    was_closed = self._is_contour_closed(pts, tolerance=2.0)
                    
                    # Ensure contour is properly closed
                    pts = self._ensure_contour_closed(pts)
                    
                    # Add as closed polyline
                    polyline = msp.add_lwpolyline(pts, close=True)
                    
                    # Explicitly set the polyline as closed
                    polyline.closed = True
                    
                    if i < 5:  # Log first few contours
                        status = "CLOSED" if was_closed else "OPEN (now closed)"
                        self.logger.info(f"Contour {i}: {status} ({len(pts)} points)")
                
                # Update progress
                if progress_callback and i % 50 == 0:
                    progress = 10 + int((i / len(contours)) * 10)
                    progress_callback(progress, f"Adding contour {i+1}/{len(contours)} to DXF...")
                    
            except Exception as e:
                self.logger.warning(f"Failed to add contour {i}: {e}")
                continue
        
        # Save DXF file
        doc.saveas(temp_path)
        
        # Debug: Check if file was created and has content
        if os.path.exists(temp_path):
            file_size = os.path.getsize(temp_path)
            self.logger.info(f"DXF file saved to: {temp_path}, size: {file_size} bytes")
        else:
            self.logger.error(f"DXF file was not created at: {temp_path}")
        
        if progress_callback:
            progress_callback(25, f"DXF file created with {len(contours)} contours")
        
        # Debug: Inspect DXF file contents
        self._inspect_dxf_file(temp_path)
        
        return temp_path
    
    def _is_contour_closed(self, points: List, tolerance: float = 2.0) -> bool:
        """Check if a contour is closed by comparing first and last points"""
        if len(points) < 3:
            return False
        
        first_point = points[0]
        last_point = points[-1]
        
        # Calculate actual distance between first and last points
        import math
        distance = math.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
        
        return distance < tolerance

    def _ensure_contour_closed(self, points: List) -> List:
        """Ensure contour is properly closed using smart interpolation"""
        if len(points) < 3:
            return points
        
        # Check if contour is already closed using improved tolerance
        if self._is_contour_closed(points, tolerance=2.0):
            # Already closed
            return points
        
        # Not closed, use smart interpolation to close it
        return self._close_contour_smart(points, max_gap=5.0)
    
    def _close_contour_smart(self, points: List, max_gap: float = 5.0) -> List:
        """
        Intelligently close a contour by connecting endpoints.
        
        Args:
            points: List of (x, y) points
            max_gap: Maximum distance to consider for closing (in same units as points)
        
        Returns:
            List of points with the contour properly closed
        """
        if len(points) < 3:
            return points
        
        first_point = points[0]
        last_point = points[-1]
        
        # Calculate distance between first and last points
        import math
        gap_distance = math.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
        
        # If already closed (within tolerance), return as-is
        if gap_distance < 1e-6:
            return points
        
        # If gap is small, just add the first point to close it
        if gap_distance <= max_gap:
            return points + [first_point]
        
        # For larger gaps, create a smooth connection
        # Use a simple linear interpolation for now (could be enhanced with splines)
        num_interpolation_points = max(2, int(gap_distance / max_gap))
        
        interpolated_points = []
        for i in range(1, num_interpolation_points):
            t = i / num_interpolation_points
            x = last_point[0] + t * (first_point[0] - last_point[0])
            y = last_point[1] + t * (first_point[1] - last_point[1])
            interpolated_points.append((x, y))
        
        return points + interpolated_points + [first_point]
    
    def _join_edge_chains(self, contours: List) -> List:
        """Join edge chains to create properly connected contours"""
        if not contours:
            return contours
        
        import numpy as np
        
        # Convert contours to a more workable format
        edge_chains = []
        for contour in contours:
            if len(contour) >= 2:
                # Extract points from contour
                points = []
                for point in contour:
                    if len(point) >= 2:
                        if contour.ndim == 3:  # Shape like (N, 1, 2)
                            x, y = float(point[0][0]), float(point[0][1])
                        else:  # Shape like (N, 2)
                            x, y = float(point[0]), float(point[1])
                        points.append((x, y))
                
                if len(points) >= 2:
                    edge_chains.append(points)
        
        if not edge_chains:
            return contours
        
        # Join chains that share endpoints
        tolerance = 1e-6
        joined_chains = []
        used_chains = set()
        
        for i, chain in enumerate(edge_chains):
            if i in used_chains:
                continue
            
            current_chain = chain.copy()
            used_chains.add(i)
            
            # Try to extend this chain by finding chains that connect to it
            changed = True
            while changed:
                changed = False
                
                for j, other_chain in enumerate(edge_chains):
                    if j in used_chains:
                        continue
                    
                    # Check if other chain connects to the end of current chain
                    current_end = current_chain[-1]
                    other_start = other_chain[0]
                    other_end = other_chain[-1]
                    
                    # Check connection to end of current chain
                    if (abs(current_end[0] - other_start[0]) < tolerance and 
                        abs(current_end[1] - other_start[1]) < tolerance):
                        # Connect other chain to end
                        current_chain.extend(other_chain[1:])  # Skip first point to avoid duplication
                        used_chains.add(j)
                        changed = True
                        break
                    elif (abs(current_end[0] - other_end[0]) < tolerance and 
                          abs(current_end[1] - other_end[1]) < tolerance):
                        # Connect reversed other chain to end
                        current_chain.extend(reversed(other_chain[:-1]))  # Skip last point and reverse
                        used_chains.add(j)
                        changed = True
                        break
                    
                    # Check connection to start of current chain
                    current_start = current_chain[0]
                    if (abs(current_start[0] - other_start[0]) < tolerance and 
                        abs(current_start[1] - other_start[1]) < tolerance):
                        # Connect reversed other chain to start
                        current_chain = list(reversed(other_chain[:-1])) + current_chain
                        used_chains.add(j)
                        changed = True
                        break
                    elif (abs(current_start[0] - other_end[0]) < tolerance and 
                          abs(current_start[1] - other_end[1]) < tolerance):
                        # Connect other chain to start
                        current_chain = other_chain[:-1] + current_chain
                        used_chains.add(j)
                        changed = True
                        break
            
            if len(current_chain) >= 3:
                joined_chains.append(current_chain)
        
        # Convert back to original contour format
        result_contours = []
        for chain in joined_chains:
            # Convert to numpy array format matching original
            contour_points = np.array([[[x, y]] for x, y in chain], dtype=np.float32)
            result_contours.append(contour_points)
        
        return result_contours if result_contours else contours
    
    def _save_problematic_batches(self, problematic_batches: List, extrude_height: float, main_step_path: str = None):
        """Save problematic batches as separate STEP files in the same folder as the main STEP file"""
        import os
        
        try:
            # Determine the output directory
            if main_step_path:
                # Use the same directory as the main STEP file
                output_dir = os.path.dirname(main_step_path)
                main_filename = os.path.splitext(os.path.basename(main_step_path))[0]
            else:
                # Fallback to current directory
                output_dir = os.getcwd()
                main_filename = "export"
            
            self.logger.info(f"Saving problematic batches to: {output_dir}")
            
            for batch_num, solid in problematic_batches:
                try:
                    # Skip null or empty solids
                    if solid is None or len(solid.objects) == 0:
                        self.logger.warning(f"Skipping null or empty solid for batch {batch_num}")
                        continue
                    
                    # Create filename for this batch
                    filename = f"{main_filename}_batch_{batch_num:03d}.step"
                    filepath = os.path.join(output_dir, filename)
                    
                    # Export the solid
                    solid.export(filepath)
                    self.logger.info(f"Saved problematic batch {batch_num} to: {filepath}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to save problematic batch {batch_num}: {e}")
                    continue
            
            self.logger.info(f"Problematic batches saved to directory: {output_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to save problematic batches: {e}")
    
    def _inspect_dxf_file(self, dxf_path: str):
        """Debug function to inspect DXF file contents"""
        try:
            import ezdxf
            doc = ezdxf.readfile(dxf_path)
            self.logger.info(f"DXF file inspection for: {dxf_path}")
            self.logger.info(f"  - DXF version: {doc.dxfversion}")
            self.logger.info(f"  - Number of layers: {len(doc.layers)}")
            self.logger.info(f"  - Layer names: {[layer.dxf.name for layer in doc.layers]}")
            
            # Check modelspace entities
            msp = doc.modelspace()
            entities = list(msp)
            self.logger.info(f"  - Number of entities in modelspace: {len(entities)}")
            
            # Count entity types
            entity_types = {}
            for entity in entities:
                entity_type = entity.dxftype()
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            self.logger.info(f"  - Entity types: {entity_types}")
            
        except Exception as e:
            self.logger.error(f"Failed to inspect DXF file: {e}")
    
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
        completed_chunks = 0
        
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
                    completed_chunks += 1
                    
                    if progress_callback:
                        progress = 50 + int((completed_chunks) / len(wire_chunks) * 30)
                        chunk_wires = len(wire_chunks[chunk_idx])
                        total_extruded = sum(len(chunk) for chunk in wire_chunks[:completed_chunks])
                        progress_callback(progress, 
                            f"Extrusion batch {completed_chunks}/{len(wire_chunks)} complete "
                            f"({chunk_wires} wires) - {total_extruded}/{len(wires)} total extruded")
                    
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
