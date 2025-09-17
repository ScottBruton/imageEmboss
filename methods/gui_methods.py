"""
Additional methods for the main GUI class
"""
import os
import cv2
import numpy as np
import math
from PySide6.QtWidgets import QMessageBox, QFileDialog, QApplication, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QTimer, QPointF
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
    
    def load_image_from_path(self, path, skip_edge_processing=False):
        """Load image from a given path"""
        self.image_path = path
        self.original_image = cv2.imread(path, cv2.IMREAD_COLOR)
        
        # Clear undo/redo stacks when loading new image
        self.dxf_view.clear_undo_redo_stacks()
        
        if self.original_image is not None:
            # Reset edit state for new image (only if not loading project)
            if not skip_edge_processing:
                self.edited_contours = []
                self.erased_contours = set()
                self.erased_points = set()
            self.edit_mode = "view"
            
            # Clear drawing items
            self.dxf_view.clear_drawing_items()
            
            # Store original pixmap for transparent background
            img_rgb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            h, w, ch = img_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.original_pixmap = QPixmap.fromImage(qt_image)
            
            # Update status and dimensions
            h, w = self.original_image.shape[:2]
            self.status_label.setText(f"Loaded: {os.path.basename(path)}")
            self.dimensions_label.setText(f"Size: {w}×{h}px")
            
            # Update output size display
            self.on_export_scale_change()
            
            # Display original image
            self.display_original_image()
            
            # Update preview (only if not skipping edge processing)
            if not skip_edge_processing:
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
        
        # Process image (skip if loading project to preserve saved contours)
        if not hasattr(self, 'loading_project') or not self.loading_project:
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
        
        # Clear the scene completely to avoid duplicate background items
        self.dxf_view.scene.clear()
        
        # Add original image as background FIRST
        if hasattr(self, 'original_pixmap') and self.original_pixmap:
            # Add the full original image as background
            background_item = QGraphicsPixmapItem(self.original_pixmap)
            background_item.setZValue(-100)  # Way behind everything
            background_item.is_background = True  # Mark as background
            
            # Set transparency based on slider value
            transparency = getattr(self, 'background_transparency', 0) / 100.0
            opacity = 1.0 - transparency
            print(f"DEBUG: Setting background opacity to {opacity} (transparency: {transparency})")
            background_item.setOpacity(opacity)  # 0% slider = opaque, 100% slider = transparent
            
            self.dxf_view.scene.addItem(background_item)
            
            # Set this as the image_item for coordinate transformation
            self.dxf_view.image_item = background_item
            
            print(f"DEBUG: Background item added with opacity {opacity}")
        else:
            print("DEBUG: No original_pixmap found")
        
        # No need for white background - we want the original image to show through
        
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
                # Calculate contour area (ensure correct data type for OpenCV compatibility)
                contour_float32 = contour.astype(np.float32)
                area = cv2.contourArea(contour_float32)
                
                # Since we're using RETR_EXTERNAL, all contours should be closed
                # Let's fill all contours with positive area
                is_closed = area > 0
                
                
                # Create a path for the contour
                path = QPainterPath()
                path.moveTo(points[0][0], points[0][1])
                for point in points[1:]:
                    path.lineTo(point[0], point[1])
                
                # Always close the path for filled contours
                if is_closed:
                    path.closeSubpath()
                
                # Create graphics item with solid line
                color = QColor(0, 100, 0) if area > 100 else QColor(255, 0, 0)
                pen = QPen(color, 2, Qt.SolidLine)
                
                if is_closed:
                    # Use QGraphicsPolygonItem for filled contours
                    from PySide6.QtWidgets import QGraphicsPolygonItem
                    
                    # Create polygon from points
                    polygon = QPolygonF()
                    for point in points:
                        polygon.append(QPointF(point[0], point[1]))
                    
                    polygon_item = QGraphicsPolygonItem(polygon)
                    polygon_item.setPen(pen)
                    polygon_item.setZValue(1)  # Above background
                    
                    # Add transparent light green fill
                    light_green = QColor(144, 238, 144, 80)  # Light green with transparency
                    polygon_item.setBrush(light_green)
                    
                    self.dxf_view.scene.addItem(polygon_item)
                else:
                    # Use QGraphicsPathItem for non-filled contours
                    from PySide6.QtWidgets import QGraphicsPathItem
                    path_item = QGraphicsPathItem(path)
                    path_item.setPen(pen)
                    path_item.setZValue(1)  # Above background
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
                path_item.setZValue(1)  # Above background
                self.dxf_view.scene.addItem(path_item)
    
    def on_param_change(self):
        """Handle parameter changes"""
        # Set preset to Custom when user manually changes parameters
        if self.preset_combo.currentText() != "Custom":
            self.preset_combo.setCurrentText("Custom")
        
        # Always update the parameters (needed for area processing tool)
        self.update_parameters_from_sliders()
        
        # Only update preview if settings are not locked
        # Check if we're in the main GUI class and if settings are locked
        if hasattr(self, 'settings_locked') and self.settings_locked:
            print("DEBUG: Settings locked - slider changes will only affect area processing tool")
        else:
            self.update_preview()
    
    def update_parameters_from_sliders(self):
        """Update parameters from slider values without triggering preview"""
        # Update bilateral parameters
        self.params['bilateral_diameter'] = self.bilateral_d_slider.value()
        self.params['bilateral_sigma_color'] = self.bilateral_c_slider.value()
        # Note: bilateral_sigma_space is not controlled by a slider, it uses the same value as sigma_color
        
        # Update Gaussian parameter
        self.params['gaussian_kernel_size'] = self.gaussian_slider.value()
        
        # Update Canny parameters
        self.params['canny_lower_threshold'] = self.canny_l_slider.value()
        self.params['canny_upper_threshold'] = self.canny_u_slider.value()
        
        # Update other parameters
        self.params['edge_thickness'] = self.thickness_slider.value()
        self.params['gap_threshold'] = self.gap_slider.value()
        self.params['simplify_pct'] = self.simplify_slider.value()
        self.params['mm_per_px'] = self.scale_slider.value() / 1000.0
        
        # Always update labels to reflect current slider values
        self.bilateral_d_label.setText(str(self.params['bilateral_diameter']))
        self.bilateral_c_label.setText(str(self.params['bilateral_sigma_color']))
        self.gaussian_label.setText(str(self.params['gaussian_kernel_size']))
        self.canny_l_label.setText(str(self.params['canny_lower_threshold']))
        self.canny_u_label.setText(str(self.params['canny_upper_threshold']))
        self.thickness_label.setText(str(self.params['edge_thickness']))
        self.gap_label.setText(str(self.params['gap_threshold']))
        self.simplify_label.setText(str(self.params['simplify_pct']))
        self.scale_label.setText(str(self.params['mm_per_px']))
        
        # Debug output to confirm parameter updates
        print(f"DEBUG: Parameters updated - Canny: {self.params['canny_lower_threshold']}-{self.params['canny_upper_threshold']}")
    
    def on_transparency_change(self):
        """Handle background transparency changes"""
        # Update the transparency value
        self.background_transparency = self.transparency_slider.value()
        
        print(f"DEBUG: Transparency changed to {self.background_transparency}%")
        
        # Update the label
        self.transparency_label.setText(f"{self.background_transparency}%")
        
        # Refresh the preview to apply new transparency
        self.display_dxf_preview()
    
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
        
        # Update parameters from sliders (this happens automatically via slider change events)
        # But we need to handle the locked state properly
        if hasattr(self, 'settings_locked') and self.settings_locked:
            print(f"DEBUG: Preset '{preset_name}' applied to edge tool only (settings locked)")
            self.status_bar.showMessage(f"Preset '{preset_name}' applied to edge tool only (settings locked)")
            # Don't update preview when locked - only edge tool will use new settings
        else:
            print(f"DEBUG: Preset '{preset_name}' applied to full image processing")
            self.status_bar.showMessage(f"Preset '{preset_name}' applied to full image processing")
            # Update preview when not locked
            self.update_preview()
        
        self.invert_checkbox.setChecked(config["invert"])
    
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
        elif mode in ["paint", "eraser", "line", "shapes", "area_process", "edge_draw"]:
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
    
    def save_undo_state(self):
        """Save current contour state for undo/redo operations"""
        if hasattr(self, 'current_contours'):
            # Create a deep copy of current contours for undo
            import copy
            self.undo_contours = copy.deepcopy(self.current_contours)
            print(f"DEBUG: Saved undo state with {len(self.current_contours)} contours")
    
    def undo_action(self):
        """Undo the last action (drawing or edge detection)"""
        # First try to undo edge detection if we have saved contours
        if hasattr(self, 'undo_contours') and self.undo_contours is not None:
            print(f"DEBUG: Undoing edge detection - restoring {len(self.undo_contours)} contours")
            self.current_contours = self.undo_contours.copy()
            self.undo_contours = None  # Clear the undo state
            self.update_preview()  # Refresh the preview
            self.status_bar.showMessage("Edge detection undone")
            return
        
        # Fall back to drawing undo
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
    
    def process_area_for_edges(self, scene_point, radius, params=None):
        """Process a circular area for edge detection and add new contours"""
        if self.original_image is None:
            return
        
        h, w = self.original_image.shape[:2]
        
        # Transform scene coordinates to image coordinates
        if self.dxf_view.image_item:
            image_rect = self.dxf_view.image_item.boundingRect()
            x = int((scene_point.x() / image_rect.width()) * w)
            y = int((scene_point.y() / image_rect.height()) * h)
            
            # Clamp to image bounds
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
        else:
            return
        
        # Extract a rectangular region around the point
        x1 = max(0, x - radius)
        y1 = max(0, y - radius)
        x2 = min(w, x + radius)
        y2 = min(h, y + radius)
        
        # Extract the rectangular area from the original image
        roi = self.original_image[y1:y2, x1:x2]
        
        # Use provided parameters or current parameters
        # When settings are locked, the area processing tool should use current slider values
        if params is not None:
            params_to_use = params
            print(f"DEBUG: Using provided parameters for area processing")
        else:
            # Always use current parameters (updated from sliders)
            params_to_use = self.params
            print(f"DEBUG: Using current parameters for area processing - Canny: {params_to_use['canny_lower_threshold']}-{params_to_use['canny_upper_threshold']}, Settings locked: {getattr(self, 'settings_locked', False)}")
        
        # Process this area for edges using the same parameters
        edges = find_edges_and_contours(roi, params_to_use)
        
        # Debug: Check if edges were found
        edge_pixels = np.sum(edges > 0)
        print(f"DEBUG: Found {edge_pixels} edge pixels in ROI of size {roi.shape}")
        
        # Find contours in this area
        area_contours = contours_from_mask(
            edges,
            params_to_use["largest_n"],
            params_to_use["simplify_pct"],
            params_to_use["gap_threshold"]
        )
        
        print(f"DEBUG: Found {len(area_contours)} raw contours in area")
        
        # Adjust contours back to full image coordinates
        adjusted_contours = []
        for contour in area_contours:
            # Offset the contour coordinates back to the full image
            adjusted_contour = contour.copy()
            adjusted_contour[:, :, 0] += x1  # Add x offset
            adjusted_contour[:, :, 1] += y1  # Add y offset
            adjusted_contours.append(adjusted_contour)
        
        # Filter out tiny contours (artifacts)
        filtered_contours = []
        for i, contour in enumerate(adjusted_contours):
            contour_float32 = contour.astype(np.float32)
            area = cv2.contourArea(contour_float32)
            if area > 20:  # Only keep contours with area > 20 pixels (reduced for fine details)
                filtered_contours.append(contour)
                print(f"DEBUG: Kept contour {i} with area {area:.1f}")
            else:
                print(f"DEBUG: Filtered out contour {i} with area {area:.1f} (too small)")
        
        # Add new contours to existing ones with intersection handling
        if filtered_contours:
            print(f"DEBUG: Before intersection handling - existing: {len(self.current_contours)}, new: {len(filtered_contours)}")
            
            # Save state for undo before making changes
            self.save_undo_state()
            
            # Check for intersections and break up existing contours
            self.current_contours = self.handle_contour_intersections(self.current_contours, filtered_contours)
            
            print(f"DEBUG: After intersection handling - total: {len(self.current_contours)}")
            
            # Refresh the preview
            self.display_dxf_preview()
            
            # Show status message
            self.status_bar.showMessage(f"Added {len(filtered_contours)} new contours from area processing")
        else:
            self.status_bar.showMessage("No significant edges found in the selected area")

    def handle_contour_intersections(self, existing_contours, new_contours):
        """Handle intersections between existing and new contours"""
        print(f"DEBUG: handle_contour_intersections called with {len(existing_contours)} existing, {len(new_contours)} new")
        
        if not existing_contours:
            print("DEBUG: No existing contours, returning new contours")
            return new_contours
        
        if not new_contours:
            print("DEBUG: No new contours, returning existing contours")
            return existing_contours
        
        h, w = self.original_image.shape[:2]
        print(f"DEBUG: Image dimensions: {w}x{h}")
        
        # Create a combined mask from all existing contours
        existing_mask = np.zeros((h, w), dtype=np.uint8)
        for contour in existing_contours:
            cv2.fillPoly(existing_mask, [contour], 255)
        
        # Create a combined mask from all new contours
        new_mask = np.zeros((h, w), dtype=np.uint8)
        for contour in new_contours:
            cv2.fillPoly(new_mask, [contour], 255)
        
        
        # NEVER remove existing contours when finding new edges - only add new ones
        # Start with all existing contours
        result_contours = list(existing_contours)
        
        # Add all new contours
        result_contours.extend(new_contours)
        
        # Simple merging: combine overlapping contours using union
        result_contours = self.simple_merge_overlaps(result_contours)
        print(f"DEBUG: Kept all existing contours and added {len(new_contours)} new contours, then merged overlaps")
        
        print(f"DEBUG: Final result: {len(result_contours)} total contours")
        
        return result_contours

    def simple_merge_overlaps(self, contours):
        """Simple merging approach used in professional software - just union overlapping contours"""
        if len(contours) <= 1:
            return contours
        
        print(f"DEBUG: Simple merging {len(contours)} contours")
        
        # Create a single mask from all contours
        h, w = self.original_image.shape[:2]
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        
        # Fill all contours into the same mask (union operation)
        for contour in contours:
            cv2.fillPoly(combined_mask, [contour], 255)
        
        # Find all contours in the combined mask
        merged_contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if merged_contours:
            print(f"DEBUG: Simple merge result: {len(contours)} -> {len(merged_contours)} contours")
            return merged_contours
        else:
            print(f"DEBUG: Simple merge failed, keeping original contours")
            return contours

    def safe_merge_overlapping_contours(self, contours):
        """Safe merging that never loses edges - only merges when it's safe to do so"""
        if len(contours) <= 1:
            return contours
        
        print(f"DEBUG: Safe merging {len(contours)} contours")
        
        # Create a list to track which contours have been processed
        processed_indices = set()
        result_contours = []
        
        for i, contour1 in enumerate(contours):
            if i in processed_indices:
                continue
                
            # Find all contours that overlap with this one
            overlapping_contours = [contour1]
            
            for j, contour2 in enumerate(contours[i+1:], i+1):
                if j in processed_indices:
                    continue
                    
                if self.contours_overlap(contour1, contour2):
                    overlapping_contours.append(contour2)
                    processed_indices.add(j)
                    print(f"DEBUG: Found overlap between contours {i} and {j}")
            
            # Try to merge overlapping contours
            if len(overlapping_contours) > 1:
                merged_contour = self.merge_contours(overlapping_contours)
                if merged_contour is not None:
                    result_contours.append(merged_contour)
                    print(f"DEBUG: Successfully merged {len(overlapping_contours)} overlapping contours")
                else:
                    # If merge failed, keep ALL overlapping contours (never lose edges)
                    result_contours.extend(overlapping_contours)
                    print(f"DEBUG: Merge failed, kept all {len(overlapping_contours)} overlapping contours")
            else:
                # No overlaps, add the original contour
                result_contours.append(contour1)
        
        print(f"DEBUG: Safe merge result: {len(contours)} -> {len(result_contours)} contours")
        return result_contours

    def merge_overlapping_contours(self, contours):
        """Simple post-processing: merge any overlapping contours"""
        if len(contours) <= 1:
            return contours
        
        print(f"DEBUG: Checking {len(contours)} contours for overlaps")
        
        # Create a list to track which contours have been merged
        merged_indices = set()
        result_contours = []
        
        for i, contour1 in enumerate(contours):
            if i in merged_indices:
                continue
                
            # Find all contours that overlap with this one
            overlapping_contours = [contour1]
            
            for j, contour2 in enumerate(contours[i+1:], i+1):
                if j in merged_indices:
                    continue
                    
                if self.contours_overlap(contour1, contour2):
                    overlapping_contours.append(contour2)
                    merged_indices.add(j)
                    print(f"DEBUG: Found overlap between contours {i} and {j}")
            
            # If we found overlapping contours, try to merge them
            if len(overlapping_contours) > 1:
                merged_contour = self.merge_contours(overlapping_contours)
                if merged_contour is not None:
                    result_contours.append(merged_contour)
                    print(f"DEBUG: Merged {len(overlapping_contours)} overlapping contours")
                else:
                    # If merge failed, add ALL overlapping contours (don't lose any)
                    result_contours.extend(overlapping_contours)
                    print(f"DEBUG: Merge failed, kept all {len(overlapping_contours)} overlapping contours")
            else:
                # No overlaps, add the original contour
                result_contours.append(contour1)
        
        print(f"DEBUG: Reduced {len(contours)} contours to {len(result_contours)} after merging overlaps")
        return result_contours

    def contours_overlap(self, contour1, contour2):
        """Check if two contours overlap by checking if their bounding boxes intersect"""
        try:
            # Get bounding rectangles
            x1, y1, w1, h1 = cv2.boundingRect(contour1)
            x2, y2, w2, h2 = cv2.boundingRect(contour2)
            
            # Check if bounding rectangles intersect
            return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)
            
        except Exception as e:
            print(f"DEBUG: Error in contours_overlap: {e}")
            return False


    def is_filled_area_scenario(self, existing_contour, new_contour):
        """Determine if this is a filled area scenario (remove parent) vs edge extension scenario (keep both)"""
        try:
            # Get bounding boxes
            x1, y1, w1, h1 = cv2.boundingRect(existing_contour)
            x2, y2, w2, h2 = cv2.boundingRect(new_contour)
            
            # Calculate areas
            existing_contour_float32 = existing_contour.astype(np.float32)
            new_contour_float32 = new_contour.astype(np.float32)
            existing_area = cv2.contourArea(existing_contour_float32)
            new_area = cv2.contourArea(new_contour_float32)
            
            # Calculate intersection area
            intersection_x = max(x1, x2)
            intersection_y = max(y1, y2)
            intersection_w = min(x1 + w1, x2 + w2) - intersection_x
            intersection_h = min(y1 + h1, y2 + h2) - intersection_y
            
            if intersection_w <= 0 or intersection_h <= 0:
                return False
            
            intersection_area = intersection_w * intersection_h
            
            # Calculate overlap ratios
            new_overlap_ratio = intersection_area / (w2 * h2) if w2 * h2 > 0 else 0
            existing_overlap_ratio = intersection_area / (w1 * h1) if w1 * h1 > 0 else 0
            
            # If new contour is mostly contained within existing contour's bounding box
            # and the new contour is significantly smaller, it's likely a filled area scenario
            if new_overlap_ratio > 0.8 and existing_overlap_ratio < 0.3:
                print(f"DEBUG: Filled area scenario - new overlap: {new_overlap_ratio:.2f}, existing overlap: {existing_overlap_ratio:.2f}")
                return True
            
            # If new contour is much smaller than existing contour, it's likely a filled area scenario
            if new_area < existing_area * 0.3:
                print(f"DEBUG: Filled area scenario - new area: {new_area:.0f}, existing area: {existing_area:.0f}")
                return True
            
            # Otherwise, it's likely an edge extension scenario
            print(f"DEBUG: Edge extension scenario - new overlap: {new_overlap_ratio:.2f}, existing overlap: {existing_overlap_ratio:.2f}")
            return False
            
        except Exception as e:
            print(f"DEBUG: Error in is_filled_area_scenario: {e}")
            # Default to edge extension scenario (safer)
            return False

    def contours_intersect_detailed(self, contour1, contour2):
        """Check if two contours intersect using multiple methods"""
        try:
            # Method 1: Bounding rectangle intersection
            rect1 = cv2.boundingRect(contour1)
            rect2 = cv2.boundingRect(contour2)
            
            x1, y1, w1, h1 = rect1
            x2, y2, w2, h2 = rect2
            
            if not (x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2):
                return False
            
            # Method 2: Check if contours actually share pixels (more conservative)
            # Create masks for both contours
            h, w = self.original_image.shape[:2]
            mask1 = np.zeros((h, w), dtype=np.uint8)
            mask2 = np.zeros((h, w), dtype=np.uint8)
            
            cv2.fillPoly(mask1, [contour1], 255)
            cv2.fillPoly(mask2, [contour2], 255)
            
            # Check if masks actually overlap (share pixels)
            intersection = cv2.bitwise_and(mask1, mask2)
            overlap_pixels = np.sum(intersection > 0)
            
            # Only consider it an intersection if there's significant pixel overlap
            # (at least 10 pixels overlap to avoid noise)
            return overlap_pixels > 10
            
        except Exception as e:
            print(f"DEBUG: Error in contours_intersect_detailed: {e}")
            # Fallback to simple bounding rectangle check
            return True

    def subtract_new_from_existing(self, existing_contour, new_contours):
        """Subtract new contours from an existing contour and return remaining pieces"""
        h, w = self.original_image.shape[:2]
        
        # Create mask for existing contour
        existing_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(existing_mask, [existing_contour], 255)
        
        # Create mask for new contours
        new_mask = np.zeros((h, w), dtype=np.uint8)
        for new_contour in new_contours:
            cv2.fillPoly(new_mask, [new_contour], 255)
        
        # Subtract new contours from existing contour
        remaining_mask = cv2.bitwise_and(existing_mask, cv2.bitwise_not(new_mask))
        
        # Find remaining contours
        remaining_contours, _ = cv2.findContours(remaining_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter out tiny pieces
        filtered_remaining = []
        for contour in remaining_contours:
            contour_float32 = contour.astype(np.float32)
            area = cv2.contourArea(contour_float32)
            if area > 50:  # Only keep significant remaining pieces
                filtered_remaining.append(contour)
        
        return filtered_remaining


    def erase_area_edges(self, scene_point, radius):
        """Erase edges within the specified circular area"""
        print(f"DEBUG: *** ERASE METHOD CALLED *** at {scene_point} with radius {radius}")
        
        if not self.dxf_view.image_item:
            print("DEBUG: No image item found for erasing, returning")
            return
        
        # Transform scene coordinates to image coordinates
        image_rect = self.dxf_view.image_item.boundingRect()
        scene_x = scene_point.x()
        scene_y = scene_point.y()
        
        # Convert to image coordinates
        image_x = int((scene_x - image_rect.x()) * self.original_image.shape[1] / image_rect.width())
        image_y = int((scene_y - image_rect.y()) * self.original_image.shape[0] / image_rect.height())
        
        # Clamp to image bounds
        image_x = max(0, min(image_x, self.original_image.shape[1] - 1))
        image_y = max(0, min(image_y, self.original_image.shape[0] - 1))
        
        # Create circular mask for erasing
        h, w = self.original_image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (image_x, image_y), radius, 255, -1)
        
        # Save state for undo before making changes
        self.save_undo_state()
        
        # Find contours that intersect with the erase area
        contours_to_remove = []
        remaining_contours = []
        
        for contour in self.current_contours:
            # Fast intersection check using bounding box first
            x, y, w_contour, h_contour = cv2.boundingRect(contour)
            
            # Check if bounding box intersects with erase circle
            # Calculate distance from circle center to bounding box
            closest_x = max(x, min(image_x, x + w_contour))
            closest_y = max(y, min(image_y, y + h_contour))
            distance = np.sqrt((closest_x - image_x)**2 + (closest_y - image_y)**2)
            
            if distance <= radius:
                # Bounding box intersects with erase circle - remove contour
                contours_to_remove.append(contour)
                print(f"DEBUG: Removing contour that intersects with erase area (distance: {distance:.1f})")
            else:
                # Contour doesn't intersect, keep it
                remaining_contours.append(contour)
        
        # Update contours - simply remove intersecting ones
        self.current_contours = remaining_contours
        
        # Refresh the preview
        self.display_dxf_preview()
        
        # Show status message
        erased_count = len(contours_to_remove)
        self.status_bar.showMessage(f"Erased {erased_count} contours in the selected area")

    def merge_area_edges(self, scene_point, radius):
        """Merge nearby contours within the specified circular area"""
        print(f"DEBUG: *** MERGE METHOD CALLED *** at {scene_point} with radius {radius}")
        
        if not self.dxf_view.image_item:
            print("DEBUG: No image item found for merging, returning")
            return
        
        # Transform scene coordinates to image coordinates
        image_rect = self.dxf_view.image_item.boundingRect()
        scene_x = scene_point.x()
        scene_y = scene_point.y()
        
        # Convert to image coordinates
        image_x = int((scene_x - image_rect.x()) * self.original_image.shape[1] / image_rect.width())
        image_y = int((scene_y - image_rect.y()) * self.original_image.shape[0] / image_rect.height())
        
        # Clamp to image bounds
        image_x = max(0, min(image_x, self.original_image.shape[1] - 1))
        image_y = max(0, min(image_y, self.original_image.shape[0] - 1))
        
        print(f"DEBUG: Image coordinates: ({image_x}, {image_y})")
        print(f"DEBUG: Current contours count: {len(self.current_contours)}")
        
        # Find contours that are within the merge area
        contours_in_area = []
        remaining_contours = []
        
        for i, contour in enumerate(self.current_contours):
            # Check if contour center or any point is within the merge circle
            # Get contour center
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # Check if center is within merge circle
                distance = np.sqrt((cx - image_x)**2 + (cy - image_y)**2)
                if distance <= radius:
                    contours_in_area.append(contour)
                    print(f"DEBUG: Contour {i} center ({cx}, {cy}) is within merge area (distance: {distance})")
                else:
                    remaining_contours.append(contour)
            else:
                remaining_contours.append(contour)
        
        print(f"DEBUG: Found {len(contours_in_area)} contours in merge area")
        
        if len(contours_in_area) > 1:
            # Merge the contours in the area
            merged_contour = self.merge_contours(contours_in_area)
            if merged_contour is not None:
                remaining_contours.append(merged_contour)
                self.current_contours = remaining_contours
                
                # Refresh the preview
                self.display_dxf_preview()
                
                # Show status message
                self.status_bar.showMessage(f"Merged {len(contours_in_area)} contours into 1")
                print(f"DEBUG: Successfully merged {len(contours_in_area)} contours")
            else:
                self.status_bar.showMessage("Could not merge contours")
                print("DEBUG: Failed to merge contours")
        else:
            self.status_bar.showMessage("Need at least 2 contours to merge")
            print("DEBUG: Not enough contours to merge")

    def merge_contours(self, contours):
        """Merge multiple contours into one"""
        if len(contours) < 2:
            return contours[0] if contours else None
        
        # Create a combined mask from all contours
        h, w = self.original_image.shape[:2]
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        
        for contour in contours:
            cv2.fillPoly(combined_mask, [contour], 255)
        
        # Find all contours in the combined shape (including separate pieces)
        merged_contours, _ = cv2.findContours(combined_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        if merged_contours:
            # If we have multiple separate contours, we need to handle them differently
            if len(merged_contours) == 1:
                # Single merged contour - return it
                return merged_contours[0]
            else:
                # Multiple separate contours - this means the merge didn't work as expected
                # Return None to indicate merge failure (so we keep original contours)
                print(f"DEBUG: Merge resulted in {len(merged_contours)} separate contours - merge failed")
                return None
        
        return None

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
        """Export the DXF file and open the enhanced DXF editor"""
        if self.image_path is None:
            QMessageBox.warning(self, "Warning", "No image loaded.")
            return
        
        # Get export scale
        export_scale = self.export_scale_input.value()
        
        # Only offer DXF export - CAD exports will be available after DXF creation
        from PySide6.QtWidgets import QMessageBox, QPushButton
        
        format_msg = QMessageBox()
        format_msg.setWindowTitle("Export DXF")
        format_msg.setText("Export DXF file:")
        format_msg.setInformativeText("DXF: 2D vector format\n\nAfter DXF export, you can edit and convert to splines,\nthen export to STEP, STL, or OBJ formats.")
        
        dxf_btn = QPushButton("Export DXF")
        cancel_btn = QPushButton("Cancel")
        
        format_msg.addButton(dxf_btn, QMessageBox.ActionRole)
        format_msg.addButton(cancel_btn, QMessageBox.RejectRole)
        
        format_result = format_msg.exec()
        
        if format_result == QMessageBox.RejectRole:  # Cancel
            return
        
        # Get DXF file path
        h, w = self.original_image.shape[:2]
        new_h, new_w = int(h * export_scale), int(w * export_scale)
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        
        # DXF file dialog
        default_name = f"{base_name}_{new_w}x{new_h}.dxf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DXF as",
            default_name, "AutoCAD DXF (*.dxf)"
        )
        
        if file_path:
            try:
                # Use current_contours as the primary source (includes all edge detection work)
                if hasattr(self, 'current_contours') and self.current_contours:
                    import copy
                    export_contours = copy.deepcopy(self.current_contours)
                else:
                    export_contours = []
                
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
                
                print(f"DEBUG: DXF Export - Using {len(export_contours)} current contours + {len(self.edited_contours)} edited contours = {len(filtered_contours)} total")
                
                # Convert drawing items to contours
                drawing_contours = self.convert_drawing_items_to_contours()
                filtered_contours.extend(drawing_contours)
                
                if not filtered_contours:
                    QMessageBox.warning(self, "Warning", "No contours found for export.")
                    return
                
                # Calculate effective mm_per_px
                effective_mm_per_px = self.params["mm_per_px"] / export_scale
                
                # Export DXF using the existing helper function
                from methods.helpers import export_dxf
                export_dxf(filtered_contours, file_path, self.current_mask.shape[:2], 
                          effective_mm_per_px)
                
                # Open enhanced DXF preview/editor window
                self.open_dxf_editor(file_path, filtered_contours, effective_mm_per_px)
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export DXF: {str(e)}")
                return
    
    def open_dxf_editor(self, dxf_path, contours, mm_per_px):
        """Open the enhanced DXF editor dialog"""
        try:
            from methods.dxf_editor_dialog import DXFEditorDialog
            
            # Create and show the DXF editor dialog
            editor_dialog = DXFEditorDialog(dxf_path, contours, mm_per_px, self)
            editor_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open DXF editor: {str(e)}")
    
    def on_export_finished(self, success, message, file_path, height, format_type, progress_dialog):
        """Handle export completion from worker thread (legacy method - not used in new workflow)"""
        if success:
            progress_dialog.finish_success(f"{format_type} export completed successfully!")
        else:
            progress_dialog.finish_error(f"{format_type} export failed!")
        
        # Clean up worker thread
        if hasattr(self, 'export_worker'):
            self.export_worker.deleteLater()
            delattr(self, 'export_worker')
