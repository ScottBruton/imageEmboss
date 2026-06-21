"""Silhouette extraction and single-stroke DXF export."""

from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np

Point = Tuple[float, float]
Path = List[Point]


def rgb_array_from_pixmap(pixmap) -> np.ndarray:
    """Convert a QPixmap to an RGB uint8 array."""
    from PySide6.QtGui import QImage

    qimage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
    width = qimage.width()
    height = qimage.height()
    ptr = qimage.bits()
    bytes_per_line = qimage.bytesPerLine()
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        line_start = y * bytes_per_line
        line_data = np.frombuffer(ptr, dtype=np.uint8, count=width * 3, offset=line_start)
        arr[y, :, :] = line_data.reshape(width, 3)
    return arr


def extract_silhouette(rgb_array: np.ndarray) -> tuple[np.ndarray, list]:
    """
    Find the foreground/background boundary (outer silhouette).

    Returns a 1-pixel boundary mask and the corresponding contours.
    """
    gray = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, foreground = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )

    boundary = np.zeros(gray.shape, dtype=np.uint8)
    if contours:
        cv2.drawContours(boundary, contours, -1, 255, 1)

    return (boundary > 0).astype(np.uint8), contours


def contours_to_paths(
    contours: list,
    close: bool = False,
    simplify_epsilon: float = 1.0,
) -> List[Path]:
    """Convert OpenCV contours to polyline paths."""
    paths: List[Path] = []
    for contour in contours:
        if len(contour) < 2:
            continue
        if simplify_epsilon > 0:
            contour = cv2.approxPolyDP(contour, simplify_epsilon, close)
        points = [(float(x), float(y)) for x, y in contour.reshape(-1, 2)]
        if close and points and points[0] != points[-1]:
            points.append(points[0])
        if len(points) >= 2:
            paths.append(points)
    return paths


def mask_to_centerline_paths(
    mask: np.ndarray,
    simplify_epsilon: float = 1.0,
) -> List[Path]:
    """
    Reduce a binary edge mask to single-stroke centerlines via skeletonization.
    Avoids double-line pairs from thick or paired edge pixels.
    """
    from skimage.morphology import skeletonize

    binary = mask.astype(bool)
    if not binary.any():
        return []

    skeleton = skeletonize(binary).astype(np.uint8)
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    paths: List[Path] = []
    for contour in contours:
        if len(contour) < 2:
            continue
        if simplify_epsilon > 0:
            contour = cv2.approxPolyDP(contour, simplify_epsilon, False)
        points = [(float(x), float(y)) for x, y in contour.reshape(-1, 2)]
        if len(points) >= 2:
            paths.append(points)
    return paths


def export_paths_to_dxf(paths: List[Path], filepath: str, image_height: int) -> int:
    """
    Export paths as open stroke polylines (single centerlines, not filled shapes).
    Returns the number of entities written.
    """
    import ezdxf

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    count = 0

    for path in paths:
        if len(path) < 2:
            continue
        points = [(x, image_height - y) for x, y in path]
        closed = len(points) > 2 and points[0] == points[-1]
        if closed:
            points = points[:-1]
        msp.add_lwpolyline(points, close=closed, dxfattribs={"layer": "STROKES"})
        count += 1

    doc.saveas(filepath)
    return count
