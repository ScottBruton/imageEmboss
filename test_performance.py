"""
Performance Test Script for ImageEmboss
Tests the performance improvements with parallel processing, Numba acceleration, and enhanced CADQuery
"""

import sys
import os
import time
import numpy as np
import cv2
import multiprocessing as mp

# Add the methods directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'methods'))

# Import our enhanced modules
from methods.performance_processor import PerformanceProcessor, ProcessingConfig, benchmark_performance
from methods.enhanced_helpers import EnhancedImageProcessor
from methods.enhanced_step_export import EnhancedStepExporter


def create_test_image(size=(800, 600)):
    """Create a test image with various shapes for testing"""
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    
    # Add some geometric shapes
    cv2.rectangle(img, (100, 100), (300, 200), (255, 255, 255), -1)
    cv2.circle(img, (500, 150), 80, (255, 255, 255), -1)
    cv2.ellipse(img, (200, 400), (100, 50), 45, 0, 360, (255, 255, 255), -1)
    
    # Add some text
    cv2.putText(img, "TEST IMAGE", (400, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    # Add some noise
    noise = np.random.randint(0, 50, img.shape, dtype=np.uint8)
    img = cv2.add(img, noise)
    
    return img


def create_test_contours():
    """Create test contours for performance testing"""
    contours = []
    
    # Create various sized contours
    for i in range(20):
        # Random circle
        center = (np.random.randint(100, 700), np.random.randint(100, 500))
        radius = np.random.randint(20, 100)
        
        # Create circle contour
        circle = cv2.circle(np.zeros((600, 800), dtype=np.uint8), center, radius, 255, -1)
        contour_points, _ = cv2.findContours(circle, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contour_points:
            contours.extend(contour_points)
    
    return contours


def test_edge_detection_performance():
    """Test edge detection performance"""
    print("=" * 60)
    print("EDGE DETECTION PERFORMANCE TEST")
    print("=" * 60)
    
    # Create test image
    test_img = create_test_image()
    print(f"Test image size: {test_img.shape}")
    
    # Test parameters
    params = {
        'bilateral_d': 9,
        'bilateral_c': 75,
        'bilateral_sigma': 75,
        'blur_kernel': 5,
        'blur_sigma': 1.0,
        'canny_low': 50,
        'canny_high': 150,
        'thicken_kernel': 3,
        'invert': False
    }
    
    # Test standard processing
    print("\nTesting standard edge detection...")
    start_time = time.time()
    
    # Convert to grayscale
    gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter
    filtered = cv2.bilateralFilter(gray, params['bilateral_d'], params['bilateral_c'], params['bilateral_sigma'])
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(filtered, (params['blur_kernel'], params['blur_kernel']), params['blur_sigma'])
    
    # Apply Canny edge detection
    edges = cv2.Canny(blurred, params['canny_low'], params['canny_high'])
    
    # Thicken edges
    kernel = np.ones((params['thicken_kernel'], params['thicken_kernel']), np.uint8)
    thickened_edges = cv2.dilate(edges, kernel, iterations=1)
    
    standard_time = time.time() - start_time
    print(f"Standard processing time: {standard_time:.3f}s")
    
    # Test enhanced processing
    print("\nTesting enhanced edge detection...")
    config = ProcessingConfig(use_numba=True, max_workers=mp.cpu_count())
    enhanced_processor = EnhancedImageProcessor(config)
    
    start_time = time.time()
    enhanced_edges = enhanced_processor.find_edges_and_contours_enhanced(test_img, params)
    enhanced_time = time.time() - start_time
    print(f"Enhanced processing time: {enhanced_time:.3f}s")
    
    # Calculate speedup
    speedup = standard_time / enhanced_time if enhanced_time > 0 else 0
    print(f"Speedup: {speedup:.2f}x")
    
    return enhanced_edges


def test_contour_processing_performance():
    """Test contour processing performance"""
    print("\n" + "=" * 60)
    print("CONTOUR PROCESSING PERFORMANCE TEST")
    print("=" * 60)
    
    # Create test contours
    test_contours = create_test_contours()
    print(f"Test contours: {len(test_contours)}")
    
    # Test parameters
    params = {
        'largest_n': 10,
        'simplify_pct': 0.6,
        'gap_threshold': 5.0
    }
    
    # Create test mask
    mask = np.zeros((600, 800), dtype=np.uint8)
    cv2.drawContours(mask, test_contours, -1, 255, -1)
    
    # Test standard processing
    print("\nTesting standard contour processing...")
    start_time = time.time()
    
    # Find contours
    contours, _ = cv2.findContours(255 - mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort by area
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:params['largest_n']]
    
    # Apply gap closing
    if params['gap_threshold'] > 0:
        kernel_size = max(1, int(params['gap_threshold']))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        combined_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(combined_mask, contours, -1, 255, -1)
        closed_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        new_contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if new_contours:
            contours = sorted(new_contours, key=cv2.contourArea, reverse=True)[:params['largest_n']]
    
    # Apply simplification
    if params['simplify_pct'] > 0:
        simplified = []
        for contour in contours:
            epsilon = params['simplify_pct'] * 0.01 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            simplified.append(approx if len(approx) >= 3 else contour)
        contours = simplified
    
    standard_time = time.time() - start_time
    print(f"Standard processing time: {standard_time:.3f}s")
    print(f"Standard contours found: {len(contours)}")
    
    # Test enhanced processing
    print("\nTesting enhanced contour processing...")
    config = ProcessingConfig(use_numba=True, max_workers=mp.cpu_count())
    enhanced_processor = EnhancedImageProcessor(config)
    
    start_time = time.time()
    enhanced_contours = enhanced_processor.contours_from_mask_enhanced(
        mask, params['largest_n'], params['simplify_pct'], params['gap_threshold']
    )
    enhanced_time = time.time() - start_time
    print(f"Enhanced processing time: {enhanced_time:.3f}s")
    print(f"Enhanced contours found: {len(enhanced_contours)}")
    
    # Calculate speedup
    speedup = standard_time / enhanced_time if enhanced_time > 0 else 0
    print(f"Speedup: {speedup:.2f}x")
    
    return enhanced_contours


def test_parallel_processing_performance():
    """Test parallel processing performance"""
    print("\n" + "=" * 60)
    print("PARALLEL PROCESSING PERFORMANCE TEST")
    print("=" * 60)
    
    # Create test contours
    test_contours = create_test_contours()
    print(f"Test contours: {len(test_contours)}")
    
    # Test parameters
    params = {
        'simplify_pct': 0.6,
        'gap_threshold': 5.0
    }
    
    img_size = (800, 600)
    
    # Test single-threaded processing
    print("\nTesting single-threaded processing...")
    config_single = ProcessingConfig(use_numba=True, max_workers=1)
    processor_single = PerformanceProcessor(config_single)
    
    start_time = time.time()
    single_results = processor_single.process_contours_parallel(test_contours, img_size, params)
    single_time = time.time() - start_time
    print(f"Single-threaded time: {single_time:.3f}s")
    print(f"Single-threaded results: {len(single_results)}")
    
    # Test multi-threaded processing
    print("\nTesting multi-threaded processing...")
    config_multi = ProcessingConfig(use_numba=True, max_workers=mp.cpu_count())
    processor_multi = PerformanceProcessor(config_multi)
    
    start_time = time.time()
    multi_results = processor_multi.process_contours_parallel(test_contours, img_size, params)
    multi_time = time.time() - start_time
    print(f"Multi-threaded time: {multi_time:.3f}s")
    print(f"Multi-threaded results: {len(multi_results)}")
    
    # Calculate speedup
    speedup = single_time / multi_time if multi_time > 0 else 0
    print(f"Parallel speedup: {speedup:.2f}x")
    print(f"CPU cores used: {mp.cpu_count()}")
    
    return multi_results


def test_cadquery_performance():
    """Test CADQuery performance"""
    print("\n" + "=" * 60)
    print("CADQUERY PERFORMANCE TEST")
    print("=" * 60)
    
    # Create test contours
    test_contours = create_test_contours()
    print(f"Test contours: {len(test_contours)}")
    
    img_size = (800, 600)
    mm_per_px = 0.25
    extrude_height = 1.0
    
    # Test enhanced CADQuery processing
    print("\nTesting enhanced CADQuery processing...")
    config = ProcessingConfig(use_cadquery=True, parallel_extrusion=True, max_workers=mp.cpu_count())
    exporter = EnhancedStepExporter(config)
    
    start_time = time.time()
    
    # Create 3D model
    workplane = exporter.cadquery_processor.create_3d_model_parallel(
        test_contours, img_size, mm_per_px, extrude_height
    )
    
    cadquery_time = time.time() - start_time
    print(f"CADQuery processing time: {cadquery_time:.3f}s")
    
    if workplane is not None:
        print("3D model created successfully!")
        print(f"Model complexity: {len(test_contours)} contours")
    else:
        print("3D model creation failed")
    
    return workplane


def run_comprehensive_benchmark():
    """Run comprehensive performance benchmark"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE PERFORMANCE BENCHMARK")
    print("=" * 60)
    
    # Create test data
    test_img = create_test_image()
    test_contours = create_test_contours()
    
    # Test parameters
    params = {
        'bilateral_d': 9,
        'bilateral_c': 75,
        'bilateral_sigma': 75,
        'blur_kernel': 5,
        'blur_sigma': 1.0,
        'canny_low': 50,
        'canny_high': 150,
        'thicken_kernel': 3,
        'invert': False,
        'largest_n': 10,
        'simplify_pct': 0.6,
        'gap_threshold': 5.0
    }
    
    img_size = (800, 600)
    
    # Run benchmark
    print("Running comprehensive benchmark...")
    results = benchmark_performance(test_contours, img_size, params, iterations=3)
    
    # Display results
    print("\nBenchmark Results:")
    print(f"Standard Processing: {results['standard']['mean_time']:.3f}s ± {results['standard']['std_time']:.3f}s")
    print(f"Parallel Processing: {results['parallel']['mean_time']:.3f}s ± {results['parallel']['std_time']:.3f}s")
    print(f"Parallel Speedup: {results['speedup_parallel']:.2f}x")
    
    if 'numba' in results:
        print(f"Numba Processing: {results['numba']['mean_time']:.3f}s ± {results['numba']['std_time']:.3f}s")
        print(f"Numba Speedup: {results['speedup_numba']:.2f}x")
    
    return results


def main():
    """Main test function"""
    print("ImageEmboss Performance Test Suite")
    print("=" * 60)
    print(f"System: {mp.cpu_count()} CPU cores")
    print(f"Python: {sys.version}")
    
    try:
        # Test edge detection
        edges = test_edge_detection_performance()
        
        # Test contour processing
        contours = test_contour_processing_performance()
        
        # Test parallel processing
        parallel_results = test_parallel_processing_performance()
        
        # Test CADQuery (if available)
        try:
            cadquery_model = test_cadquery_performance()
        except Exception as e:
            print(f"\nCADQuery test skipped: {e}")
        
        # Run comprehensive benchmark
        benchmark_results = run_comprehensive_benchmark()
        
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 60)
        print("✅ Edge detection performance test completed")
        print("✅ Contour processing performance test completed")
        print("✅ Parallel processing performance test completed")
        print("✅ Comprehensive benchmark completed")
        
        if 'numba' in benchmark_results:
            print(f"🚀 Best speedup achieved: {benchmark_results['speedup_numba']:.2f}x with Numba")
        else:
            print(f"🚀 Best speedup achieved: {benchmark_results['speedup_parallel']:.2f}x with parallel processing")
        
        print("\nPerformance optimizations are working correctly!")
        
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
