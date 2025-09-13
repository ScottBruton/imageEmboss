"""
Additional methods for the main GUI class
"""
import os
import cv2
import numpy as np
import math
from PySide6.QtWidgets import QMessageBox, QFileDialog, QApplication, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QPainterPath, QPolygonF, QCursor, QTransform

from .helpers import find_edges_and_contours, contours_from_mask, export_dxf
from .graphics_items import (DrawingPathItem, DrawingLineItem, DrawingRectItem, 
                           DrawingEllipseItem, DrawingPolygonItem)


class GUIMethods:
    """Mixin class containing additional methods for the main GUI"""
    
    def setup_menu(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        load_action = self.create_action('Load Image', 'Ctrl+O', self.load_image)
        file_menu.addAction(load_action)
        
        export_action = self.create_action('Export DXF', 'Ctrl+E', self.export_dxf)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = self.create_action('Exit', 'Ctrl+Q', self.close)
        file_menu.addAction(exit_action)
    
    def create_action(self, text, shortcut, callback):
        """Create a QAction with shortcut and callback"""
        from PySide6.QtGui import QAction
        action = QAction(text, self)
        action.setShortcut(shortcut)
        action.triggered.connect(callback)
        return action
    
    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
    
    def load_image(self):
        """Load an image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select an image to convert",
            "", "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp);;All files (*.*)"
        )
        
        if file_path:
            self.load_image_from_path(file_path)
    
    def load_image_from_path(self, path):
        """Load image from a given path"""
        self.image_path = path
        self.original_image = cv2.imread(path, cv2.IMREAD_COLOR)
        
        # Clear undo/redo stacks when loading new image
        self.dxf_view.clear_undo_redo_stacks()
        
        if self.original_image is not None:
            # Reset edit state for new image
            self.edited_contours = []
            self.erased_contours = set()
            self.erased_points = set()
            self.edit_mode = "view"
            
            # Clear drawing items
            self.dxf_view.clear_drawing_items()
            
            # Update status and dimensions
            h, w = self.original_image.shape[:2]
            self.status_label.setText(f"Loaded: {os.path.basename(path)}")
            self.dimensions_label.setText(f"Size: {w}×{h}px")
            
            # Update output size display
            self.on_export_scale_change()
            
            # Display original image
            self.display_original_image()
            
            # Update preview
            self.update_preview()
            
            # Fit images to view after loading
            QTimer.singleShot(50, self.fit_images_to_view)
            
            self.status_bar.showMessage(f"Loaded: {os.path.basename(path)}")
        else:
            QMessageBox.critical(self, "Error", "Could not read image.")
    
    def display_original_image(self):
        """Display the original image in the left panel"""
        if self.original_image is None:
            return
        
        # Convert BGR to RGB for display
        img_rgb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        self.original_view.set_image(img_rgb)
    
    def update_preview(self):
        """Update the DXF preview"""
        if self.original_image is None:
            return
        
        # Update parameters from sliders
        self.params["bilateral_diameter"] = self.bilateral_d_slider.value()
        self.params["bilateral_sigma_color"] = self.bilateral_c_slider.value()
        self.params["bilateral_sigma_space"] = self.bilateral_c_slider.value()
        self.params["gaussian_kernel_size"] = self.gaussian_slider.value()
        if self.params["gaussian_kernel_size"] % 2 == 0:
            self.params["gaussian_kernel_size"] += 1  # Ensure odd
        self.params["canny_lower_threshold"] = self.canny_l_slider.value()
        self.params["canny_upper_threshold"] = self.canny_u_slider.value()
        self.params["edge_thickness"] = self.thickness_slider.value()
        self.params["gap_threshold"] = self.gap_slider.value()
        self.params["largest_n"] = self.largest_slider.value()
        self.params["simplify_pct"] = self.simplify_slider.value() / 100.0
        self.params["mm_per_px"] = self.scale_slider.value() / 100.0
        self.params["invert"] = self.invert_checkbox.isChecked()
        
        # Update labels
        self.bilateral_d_label.setText(str(self.params["bilateral_diameter"]))
        self.bilateral_c_label.setText(str(self.params["bilateral_sigma_color"]))
        self.gaussian_label.setText(str(self.params["gaussian_kernel_size"]))
        self.canny_l_label.setText(str(self.params["canny_lower_threshold"]))
        self.canny_u_label.setText(str(self.params["canny_upper_threshold"]))
        self.thickness_label.setText(f"{self.params['edge_thickness']:.1f}")
        self.gap_label.setText(f"{self.params['gap_threshold']:.1f}")
        self.largest_label.setText(str(self.params["largest_n"]))
        self.simplify_label.setText(f"{self.params['simplify_pct']:.1f}")
        self.scale_label.setText(f"{self.params['mm_per_px']:.3f}")
        
        # Process image
        self.current_mask = find_edges_and_contours(self.original_image, self.params)
        self.current_contours = contours_from_mask(
            self.current_mask, 
            self.params["largest_n"], 
            self.params["simplify_pct"],
            self.params["gap_threshold"]
        )
        
        # Display DXF preview
        self.display_dxf_preview()
    
    def display_dxf_preview(self):
        """Display the DXF preview"""
        if not self.current_contours or self.original_image is None:
            self.dxf_view.scene.clear()
            return
        
        # Clear the scene but keep the image
        items_to_remove = []
        for item in self.dxf_view.scene.items():
            if not isinstance(item, type(self.dxf_view.image_item)):
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.dxf_view.scene.removeItem(item)
        
        # Create a white background if no image is set
        if not self.dxf_view.image_item:
            h, w = self.original_image.shape[:2]
            white_image = np.ones((h, w, 3), dtype=np.uint8) * 255
            self.dxf_view.set_image(white_image)
        
        # Draw contours as graphics items
        for i, contour in enumerate(self.current_contours):
            if i in self.erased_contours:
                continue
            
            # Create a list of points for the contour
            points = []
            for j, point in enumerate(contour):
                if (i, j) not in self.erased_points:
                    points.append([point[0][0], point[0][1]])
            
            if len(points) >= 3:
                # Create a path for the contour
                path = QPainterPath()
                path.moveTo(points[0][0], points[0][1])
                for point in points[1:]:
                    path.lineTo(point[0], point[1])
                path.closeSubpath()
                
                # Create graphics item with solid line
                area = cv2.contourArea(contour)
                color = QColor(0, 100, 0) if area > 100 else QColor(255, 0, 0)
                pen = QPen(color, 2, Qt.SolidLine)
                
                from PySide6.QtWidgets import QGraphicsPathItem
                path_item = QGraphicsPathItem(path)
                path_item.setPen(pen)
                self.dxf_view.scene.addItem(path_item)
        
        # Draw edited contours (manually added)
        for contour in self.edited_contours:
            points = []
            for point in contour:
                points.append([point[0][0], point[0][1]])
            
            if len(points) >= 3:
                # Create a path for the contour
                path = QPainterPath()
                path.moveTo(points[0][0], points[0][1])
                for point in points[1:]:
                    path.lineTo(point[0], point[1])
                path.closeSubpath()
                
                # Create graphics item with blue color
                pen = QPen(QColor(0, 0, 255), 2, Qt.SolidLine)
                
                from PySide6.QtWidgets import QGraphicsPathItem
                path_item = QGraphicsPathItem(path)
                path_item.setPen(pen)
                self.dxf_view.scene.addItem(path_item)
    
    def on_param_change(self):
        """Handle parameter changes"""
        # Set preset to Custom when user manually changes parameters
        if self.preset_combo.currentText() != "Custom":
            self.preset_combo.setCurrentText("Custom")
        
        self.update_preview()
    
    def on_preset_change(self, preset_name):
        """Handle preset changes"""
        if preset_name == "Custom":
            return
        
        config = self.preset_configs.get(preset_name)
        if not config:
            return
        
        # Apply preset values
        self.bilateral_d_slider.setValue(config["bilateral_diameter"])
        self.bilateral_c_slider.setValue(config["bilateral_sigma_color"])
        self.gaussian_slider.setValue(config["gaussian_kernel_size"])
        self.canny_l_slider.setValue(config["canny_lower_threshold"])
        self.canny_u_slider.setValue(config["canny_upper_threshold"])
        self.thickness_slider.setValue(int(config["edge_thickness"]))
        self.gap_slider.setValue(int(config["gap_threshold"]))
        self.largest_slider.setValue(config["largest_n"])
        self.simplify_slider.setValue(int(config["simplify_pct"] * 100))
        self.scale_slider.setValue(int(config["mm_per_px"] * 100))
        self.invert_checkbox.setChecked(config["invert"])
        
        # Update preview
        self.update_preview()
    
    def on_export_scale_change(self):
        """Update output size display when export scale changes"""
        if self.original_image is not None:
            scale = self.export_scale_input.value()
            h, w = self.original_image.shape[:2]
            new_h = int(h * scale)
            new_w = int(w * scale)
            self.output_size_label.setText(f"Output: {new_w}×{new_h}px")
    
    def on_bilateral_d_preset_change(self, preset):
        """Handle bilateral diameter preset change"""
        presets = {"Small": 6, "Medium": 9, "Large": 12}
        if preset in presets:
            self.bilateral_d_slider.setValue(presets[preset])
            self.bilateral_d_label.setText(str(presets[preset]))
            self.on_param_change()
    
    def on_bilateral_c_preset_change(self, preset):
        """Handle bilateral color preset change"""
        presets = {"Low": 40, "Medium": 75, "High": 120}
        if preset in presets:
            self.bilateral_c_slider.setValue(presets[preset])
            self.bilateral_c_label.setText(str(presets[preset]))
            self.on_param_change()
    
    def on_gaussian_preset_change(self, preset):
        """Handle gaussian preset change"""
        presets = {"Light": 3, "Medium": 5, "Heavy": 7}
        if preset in presets:
            self.gaussian_slider.setValue(presets[preset])
            self.gaussian_label.setText(str(presets[preset]))
            self.on_param_change()
    
    def on_canny_preset_change(self, preset):
        """Handle canny preset change"""
        presets = {
            "Sensitive": {"lower": 20, "upper": 60},
            "Medium": {"lower": 30, "upper": 100},
            "Conservative": {"lower": 50, "upper": 150}
        }
        if preset in presets:
            self.canny_l_slider.setValue(presets[preset]["lower"])
            self.canny_l_label.setText(str(presets[preset]["lower"]))
            self.canny_u_slider.setValue(presets[preset]["upper"])
            self.canny_u_label.setText(str(presets[preset]["upper"]))
            self.on_param_change()
    
    def on_thickness_preset_change(self, preset):
        """Handle thickness preset change"""
        presets = {"Thin": 1, "Medium": 3, "Thick": 6}
        if preset in presets:
            self.thickness_slider.setValue(presets[preset])
            self.thickness_label.setText(str(presets[preset]))
            self.on_param_change()
    
    def on_gap_preset_change(self, preset):
        """Handle gap preset change"""
        presets = {"None": 0, "Light": 3, "Medium": 5, "Heavy": 10}
        if preset in presets:
            self.gap_slider.setValue(presets[preset])
            self.gap_label.setText(str(presets[preset]))
            self.on_param_change()
    
    def on_largest_preset_change(self, preset):
        """Handle largest preset change"""
        presets = {"Few": 3, "Medium": 10, "Many": 30}
        if preset in presets:
            self.largest_slider.setValue(presets[preset])
            self.largest_label.setText(str(presets[preset]))
            self.on_param_change()
    
    def on_simplify_preset_change(self, preset):
        """Handle simplify preset change"""
        presets = {"Detailed": 20, "Medium": 50, "Simple": 100}
        if preset in presets:
            self.simplify_slider.setValue(presets[preset])
            self.simplify_label.setText(str(presets[preset]))
            self.on_param_change()
    
    def on_scale_preset_change(self, preset):
        """Handle scale preset change"""
        presets = {"Small": 15, "Medium": 25, "Large": 100}
        if preset in presets:
            self.scale_slider.setValue(presets[preset])
            self.scale_label.setText(str(presets[preset]))
            self.on_param_change()
    
    def zoom_in(self):
        """Zoom in on the preview"""
        # Get center of view for zoom
        center = self.dxf_view.mapToScene(self.dxf_view.viewport().rect().center())
        old_pos = center
        
        # Apply zoom
        self.dxf_view.scale(1.2, 1.2)
        
        # Keep center position stable
        new_pos = self.dxf_view.mapToScene(self.dxf_view.viewport().rect().center())
        delta = new_pos - old_pos
        self.dxf_view.translate(delta.x(), delta.y())
    
    def zoom_out(self):
        """Zoom out on the preview"""
        # Get center of view for zoom
        center = self.dxf_view.mapToScene(self.dxf_view.viewport().rect().center())
        old_pos = center
        
        # Apply zoom
        self.dxf_view.scale(0.8, 0.8)
        
        # Keep center position stable
        new_pos = self.dxf_view.mapToScene(self.dxf_view.viewport().rect().center())
        delta = new_pos - old_pos
        self.dxf_view.translate(delta.x(), delta.y())
    
    def zoom_reset(self):
        """Reset zoom to fit"""
        self.dxf_view.reset_view()
    
    def pan_preview(self, dx, dy):
        """Pan the preview"""
        # Use QGraphicsView's built-in pan functionality
        self.dxf_view.horizontalScrollBar().setValue(
            self.dxf_view.horizontalScrollBar().value() - dx * 20
        )
        self.dxf_view.verticalScrollBar().setValue(
            self.dxf_view.verticalScrollBar().value() - dy * 20
        )
    
    def pan_reset(self):
        """Reset pan position"""
        self.dxf_view.reset_view()
    
    def set_edit_mode(self, mode):
        """Set the edit mode for the DXF view"""
        if mode == "shapes":
            # For shapes mode, get the actual shape type from the combo box
            shape_type = self.shape_combo.currentText().lower()
            self.dxf_view.set_edit_mode(shape_type)
            self.dxf_view.set_shape_type(shape_type)
            self.edit_mode = shape_type
        else:
            self.dxf_view.set_edit_mode(mode)
            self.edit_mode = mode
        
        # Set cursor based on mode
        if mode == "view":
            cursor = QCursor(Qt.ArrowCursor)
        elif mode in ["paint", "eraser", "line", "shapes"]:
            cursor = QCursor(Qt.CrossCursor)  # Cross cursor for all drawing modes
        else:
            cursor = QCursor(Qt.ArrowCursor)
        
        # Apply cursor to both views
        self.original_view.setCursor(cursor)
        self.dxf_view.setCursor(cursor)
    
    def set_shape_mode(self):
        """Set shape drawing mode"""
        shape_type = self.shape_combo.currentText().lower()
        self.dxf_view.set_shape_type(shape_type)
        self.dxf_view.set_edit_mode(shape_type)
        self.edit_mode = shape_type
    
    def undo_action(self):
        """Undo the last drawing action"""
        print(f"DEBUG: undo_action called - can_undo: {self.dxf_view.can_undo()}")
        if self.dxf_view.can_undo():
            self.dxf_view.undo_last_action()
            self.status_bar.showMessage("Action undone")
        else:
            self.status_bar.showMessage("Nothing to undo")
    
    def redo_action(self):
        """Redo the last undone action"""
        print(f"DEBUG: redo_action called - can_redo: {self.dxf_view.can_redo()}")
        if self.dxf_view.can_redo():
            self.dxf_view.redo_last_action()
            self.status_bar.showMessage("Action redone")
        else:
            self.status_bar.showMessage("Nothing to redo")
    
    def reset_edits(self):
        """Reset all edits and revert to original preview"""
        print(f"DEBUG: reset_edits called - undo_stack size: {len(self.dxf_view.undo_stack)}, redo_stack size: {len(self.dxf_view.redo_stack)}")
        
        # Undo all actions in the undo stack to get back to the beginning
        undo_count = 0
        while self.dxf_view.can_undo():
            self.dxf_view.undo_last_action()
            undo_count += 1
        
        print(f"DEBUG: reset_edits - undone {undo_count} actions")
        
        # Clear both stacks completely
        self.dxf_view.clear_undo_redo_stacks()
        
        # Reset edit state
        self.edited_contours = []
        self.erased_contours = set()
        self.erased_points = set()
        self.edit_mode = "view"
        
        # Reset view to fit the preview in the container (1:1 fit)
        if self.dxf_view.image_item is not None:
            # Fit the image to view (this is what 1:1 should mean - fit to container)
            self.dxf_view.fitInView(self.dxf_view.image_item, Qt.KeepAspectRatio)
            self.dxf_view.zoom_factor = 1.0
        
        # Update status
        if undo_count > 0:
            self.status_bar.showMessage(f"Reset complete - {undo_count} actions undone")
        else:
            self.status_bar.showMessage("Already at clean state - no edits to reset")
    
    def on_gap_enabled_toggled(self, enabled):
        """Handle gap threshold enable/disable toggle"""
        self.gap_slider.setEnabled(enabled)
        if not enabled:
            self.gap_slider.setValue(0)
            self.gap_label.setText("0.0")
        self.on_param_change()  # Update preview
    
    def force_maximize(self):
        """Force the window to maximize"""
        # Try multiple methods to ensure maximization
        self.setWindowState(Qt.WindowMaximized)
        self.showMaximized()
        
        # Try setting geometry to screen size as backup
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            self.setGeometry(screen_geometry)
        
        # Force update
        self.update()
        self.repaint()
    
    def showEvent(self, event):
        """Handle show event to ensure maximization"""
        super().showEvent(event)
        if not self.isMaximized():
            self.showMaximized()
    
    def fit_images_to_view(self):
        """Fit both images to their respective views"""
        if hasattr(self, 'original_view') and self.original_view.image_item is not None:
            self.original_view.fitInView(self.original_view.image_item, Qt.KeepAspectRatio)
            self.original_view.zoom_factor = 1.0
        
        if hasattr(self, 'dxf_view') and self.dxf_view.image_item is not None:
            self.dxf_view.fitInView(self.dxf_view.image_item, Qt.KeepAspectRatio)
            self.dxf_view.zoom_factor = 1.0
    
    def on_shape_type_change(self, shape_type):
        """Handle shape type change"""
        if self.edit_mode in ["rectangle", "triangle", "circle"]:
            self.dxf_view.set_shape_type(shape_type)
    
    def convert_drawing_items_to_contours(self):
        """Convert drawing items to contours for DXF export"""
        contours = []
        drawing_items = self.dxf_view.get_drawing_items()
        
        for item in drawing_items:
            if isinstance(item, DrawingPathItem):
                # Convert path to contour points
                path = item.path()
                points = []
                for i in range(path.elementCount()):
                    element = path.elementAt(i)
                    points.append([[int(element.x), int(element.y)]])
                if len(points) >= 3:
                    contours.append(np.array(points, dtype=np.int32))
            
            elif isinstance(item, DrawingLineItem):
                # Convert line to contour points
                line = item.line()
                points = [
                    [[int(line.p1().x()), int(line.p1().y())]],
                    [[int(line.p2().x()), int(line.p2().y())]]
                ]
                contours.append(np.array(points, dtype=np.int32))
            
            elif isinstance(item, DrawingRectItem):
                # Convert rectangle to contour points
                rect = item.rect()
                points = [
                    [[int(rect.left()), int(rect.top())]],
                    [[int(rect.right()), int(rect.top())]],
                    [[int(rect.right()), int(rect.bottom())]],
                    [[int(rect.left()), int(rect.bottom())]],
                    [[int(rect.left()), int(rect.top())]]  # Close the rectangle
                ]
                contours.append(np.array(points, dtype=np.int32))
            
            elif isinstance(item, DrawingEllipseItem):
                # Convert ellipse to contour points
                rect = item.rect()
                center_x = rect.center().x()
                center_y = rect.center().y()
                radius_x = rect.width() / 2
                radius_y = rect.height() / 2
                
                # Generate circle points
                num_points = 16
                points = []
                for i in range(num_points):
                    angle = 2 * math.pi * i / num_points
                    x = center_x + radius_x * math.cos(angle)
                    y = center_y + radius_y * math.sin(angle)
                    points.append([[int(x), int(y)]])
                # Close the circle
                points.append([[int(center_x + radius_x), int(center_y)]])
                contours.append(np.array(points, dtype=np.int32))
            
            elif isinstance(item, DrawingPolygonItem):
                # Convert polygon to contour points
                polygon = item.polygon()
                points = []
                for i in range(polygon.size()):
                    point = polygon.point(i)
                    points.append([[int(point.x()), int(point.y())]])
                if len(points) >= 3:
                    contours.append(np.array(points, dtype=np.int32))
        
        return contours
    
    def export_dxf(self):
        """Export the DXF file"""
        if self.image_path is None:
            QMessageBox.warning(self, "Warning", "No image loaded.")
            return
        
        # Get export scale
        export_scale = self.export_scale_input.value()
        
        # Get file path
        h, w = self.original_image.shape[:2]
        new_h, new_w = int(h * export_scale), int(w * export_scale)
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        default_name = f"{base_name}_{new_w}x{new_h}.dxf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DXF as",
            default_name, "AutoCAD DXF (*.dxf)"
        )
        
        if file_path:
            try:
                # Process contours for export
                export_contours = contours_from_mask(
                    self.current_mask, 
                    self.params["largest_n"], 
                    self.params["simplify_pct"],
                    self.params["gap_threshold"]
                )
                
                # Filter out erased contours and add edited contours
                filtered_contours = []
                for i, contour in enumerate(export_contours):
                    if i not in self.erased_contours:
                        # Filter out individual erased points
                        filtered_contour = []
                        for j, point in enumerate(contour):
                            if (i, j) not in self.erased_points:
                                filtered_contour.append(point)
                        if len(filtered_contour) >= 3:
                            filtered_contours.append(np.array(filtered_contour, dtype=np.int32))
                
                # Add manually edited contours
                filtered_contours.extend(self.edited_contours)
                
                # Convert drawing items to contours
                drawing_contours = self.convert_drawing_items_to_contours()
                filtered_contours.extend(drawing_contours)
                
                if not filtered_contours:
                    QMessageBox.warning(self, "Warning", "No contours found for export.")
                    return
                
                # Calculate effective mm_per_px
                effective_mm_per_px = self.params["mm_per_px"] / export_scale
                
                # Export DXF
                export_dxf(filtered_contours, file_path, self.current_mask.shape[:2], 
                          effective_mm_per_px)
                
                QMessageBox.information(self, "Success", 
                                      f"DXF saved to:\n{file_path}\nSize: {new_w}×{new_h}px")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
