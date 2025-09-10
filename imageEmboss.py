import os
import sys
import cv2
import numpy as np
import ezdxf
import math
from tkinter import Tk, filedialog, simpledialog, messagebox, ttk, Canvas, PhotoImage, DoubleVar, IntVar, BooleanVar, StringVar
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False
from PIL import Image, ImageTk

# -------------------------
# Helpers
# -------------------------
def choose_input_image():
    Tk().withdraw()
    filetypes = [
        ("Images", "*.jpg;*.jpeg;*.png;*.bmp;*.tif;*.tiff;*.webp"),
        ("All files", "*.*"),
    ]
    path = filedialog.askopenfilename(title="Select an image to convert", filetypes=filetypes)
    return path

def choose_output_dxf(default_name="output.dxf"):
    Tk().withdraw()
    path = filedialog.asksaveasfilename(
        title="Save DXF as",
        defaultextension=".dxf",
        initialfile=default_name,
        filetypes=[("AutoCAD DXF", "*.dxf")],
    )
    return path

def ask_params():
    """
    Ask for a few simple parameters.
    threshold: 0..255 or -1 for Otsu
    morph: kernel size for clean up (odd int). 0 disables.
    largest_n: keep top N largest contours only.
    simplify: Douglas–Peucker epsilon as percentage of image diagonal (0..5 typical). 0 disables.
    """
    Tk().withdraw()
    try:
        threshold = simpledialog.askfloat(
            "Threshold",
            "Threshold 0..255 (-1 = Otsu, recommended):",
            initialvalue=-1.0,
            minvalue=-1.0, maxvalue=255.0)
        if threshold is None: return None

        morph = simpledialog.askinteger(
            "Cleanup",
            "Morph kernel size in px (odd, 0 disables). 3 or 5 is typical:",
            initialvalue=5, minvalue=0, maxvalue=51)
        if morph is None: return None
        if morph % 2 == 0 and morph != 0:
            morph += 1  # ensure odd

        largest_n = simpledialog.askinteger(
            "Limit shapes",
            "Keep N largest contours only (1..50). Use 1–3 to get a bold silhouette:",
            initialvalue=3, minvalue=1, maxvalue=50)
        if largest_n is None: return None

        simplify_pct = simpledialog.askfloat(
            "Simplify",
            "Simplify epsilon as % of image diagonal (0 disables, try 0.2..1.5):",
            initialvalue=0.6, minvalue=0.0, maxvalue=5.0)
        if simplify_pct is None: return None

        mm_per_px = simpledialog.askfloat(
            "Scale",
            "DXF scale in mm per pixel (1.0 = 1 px becomes 1 mm in DXF):",
            initialvalue=0.25, minvalue=0.001, maxvalue=100.0)
        if mm_per_px is None: return None

        invert_bw = messagebox.askyesno(
            "Invert",
            "Invert black/white before vectorizing?\n"
            "Yes = treat light subject on dark background.\n"
            "No = default (dark subject becomes silhouette).")

        return {
            "threshold": threshold,
            "morph": morph,
            "largest_n": largest_n,
            "simplify_pct": simplify_pct,
            "mm_per_px": mm_per_px,
            "invert": invert_bw
        }
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return None

def find_edges_and_contours(img_bgr, params):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Apply bilateral filter
    bilateral = cv2.bilateralFilter(
        gray,
        params["bilateral_diameter"],
        params["bilateral_sigma_color"],
        params["bilateral_sigma_space"]
    )

    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(
        bilateral,
        (params["gaussian_kernel_size"], params["gaussian_kernel_size"]),
        0
    )

    # Apply Canny edge detection
    edges = cv2.Canny(
        blurred,
        params["canny_lower_threshold"],
        params["canny_upper_threshold"]
    )

    # Create kernel based on edge thickness
    kernel_size = max(1, int(params["edge_thickness"]))
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    # Thicken edges using the kernel
    thickened_edges = cv2.dilate(edges, kernel, iterations=1)
    
    # Invert if needed (for silhouette-style output)
    if params["invert"]:
        thickened_edges = 255 - thickened_edges
    
    return thickened_edges

def contours_from_mask(mask, largest_n=3, simplify_pct=0.6, gap_threshold=5.0):
    # Find external contours only
    contours, _ = cv2.findContours(255 - mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # invert so dark = fill

    if not contours:
        return []

    # Keep N largest by area
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:max(1, int(largest_n))]

    # Apply gap threshold to connect nearby contour segments
    if gap_threshold > 0:
        # Apply gap closing to the entire mask first
        kernel_size = max(1, int(gap_threshold))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        # Create a mask from all contours
        combined_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(combined_mask, contours, -1, 255, -1)
        
        # Apply morphological closing to close gaps
        closed_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find new contours from the gap-closed mask
        new_contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if new_contours:
            # Keep the largest contours
            new_contours = sorted(new_contours, key=cv2.contourArea, reverse=True)[:max(1, int(largest_n))]
            contours = new_contours

    if simplify_pct and simplify_pct > 0:
        h, w = mask.shape[:2]
        diag = np.sqrt(w*w + h*h)
        eps = float(simplify_pct) * 0.01 * diag  # percent of diagonal
        simplified = []
        for c in contours:
            approx = cv2.approxPolyDP(c, eps, True)
            simplified.append(approx if len(approx) >= 3 else c)
        contours = simplified

    return contours

def export_dxf(contours, out_path, img_size, mm_per_px=0.25):
    h, w = img_size
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Image coords have origin top-left, y down.
    # DXF uses origin bottom-left, y up.
    # Flip Y and scale to mm.
    for cnt in contours:
        pts = []
        for p in cnt:
            x = float(p[0][0])
            y = float(p[0][1])
            x_mm = x * mm_per_px
            y_mm = (h - y) * mm_per_px
            pts.append((x_mm, y_mm))
        if len(pts) >= 3:
            msp.add_lwpolyline(pts, close=True)

    doc.saveas(out_path)

# -------------------------
# GUI Application
# -------------------------
class ImageEmbossGUI:
    def __init__(self):
        # Use TkinterDnD if available, otherwise fall back to regular Tk
        if DRAG_DROP_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = Tk()
        self.root.title("Image Emboss - Image to DXF Converter")
        self.root.geometry("1200x800")
        
        # Data
        self.original_image = None
        self.current_mask = None
        self.current_contours = []
        self.image_path = None
        
        # Edit mode variables
        self.edit_mode = "view"  # view, paint, eraser, shapes
        self.drawing = False
        self.drawing_points = []
        self.edited_contours = []  # Store manually added contours
        self.erased_contours = set()  # Store indices of erased contours
        self.erased_points = set()  # Store individual erased points
        
        # Store previous slider values for reverting
        self.previous_slider_values = {}
        
        # Default parameters (matching your previous application)
        self.params = {
            "bilateral_diameter": 9,
            "bilateral_sigma_color": 75,
            "bilateral_sigma_space": 75,
            "gaussian_kernel_size": 5,
            "canny_lower_threshold": 30,  # Your default
            "canny_upper_threshold": 100,  # Your default
            "edge_thickness": 2,
            "gap_threshold": 5.0,
            "largest_n": 10,
            "simplify_pct": 0.5,
            "mm_per_px": 0.25,
            "invert": True  # Default to True to focus on subject
        }
        
        # Preset configurations with explicit numeric values
        self.preset_configs = {
            "Default": {
                "bilateral_diameter": 9,
                "bilateral_sigma_color": 75,
                "gaussian_kernel_size": 5,
                "canny_lower_threshold": 30,
                "canny_upper_threshold": 100,
                "edge_thickness": 2.0,
                "gap_threshold": 5.0,
                "largest_n": 10,
                "simplify_pct": 0.5,
                "mm_per_px": 0.25,
                "invert": True
            },
            "High Detail": {
                "bilateral_diameter": 6,
                "bilateral_sigma_color": 60,
                "gaussian_kernel_size": 3,
                "canny_lower_threshold": 20,
                "canny_upper_threshold": 60,
                "edge_thickness": 1.5,
                "gap_threshold": 3.0,
                "largest_n": 15,
                "simplify_pct": 0.3,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Low Noise": {
                "bilateral_diameter": 12,
                "bilateral_sigma_color": 120,
                "gaussian_kernel_size": 7,
                "canny_lower_threshold": 50,
                "canny_upper_threshold": 150,
                "edge_thickness": 3.0,
                "gap_threshold": 6.0,
                "largest_n": 10,
                "simplify_pct": 0.6,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Strong Edges": {
                "bilateral_diameter": 8,
                "bilateral_sigma_color": 40,
                "gaussian_kernel_size": 5,
                "canny_lower_threshold": 30,
                "canny_upper_threshold": 100,
                "edge_thickness": 5.0,
                "gap_threshold": 8.0,
                "largest_n": 3,
                "simplify_pct": 1.0,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Portrait": {
                "bilateral_diameter": 6,
                "bilateral_sigma_color": 60,
                "gaussian_kernel_size": 3,
                "canny_lower_threshold": 20,
                "canny_upper_threshold": 60,
                "edge_thickness": 1.5,
                "gap_threshold": 2.0,
                "largest_n": 5,
                "simplify_pct": 0.4,
                "mm_per_px": 0.25,
                "invert": False
            },
            "Landscape": {
                "bilateral_diameter": 9,
                "bilateral_sigma_color": 90,
                "gaussian_kernel_size": 5,
                "canny_lower_threshold": 30,
                "canny_upper_threshold": 90,
                "edge_thickness": 2.5,
                "gap_threshold": 4.0,
                "largest_n": 20,
                "simplify_pct": 0.3,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Illustration": {
                "bilateral_diameter": 5,
                "bilateral_sigma_color": 25,
                "gaussian_kernel_size": 3,
                "canny_lower_threshold": 15,
                "canny_upper_threshold": 50,
                "edge_thickness": 2.0,
                "gap_threshold": 2.0,
                "largest_n": 10,
                "simplify_pct": 0.2,
                "mm_per_px": 0.25,
                "invert": False
            },
            "Flat (Neutral)": {
                "bilateral_diameter": 7,
                "bilateral_sigma_color": 75,
                "gaussian_kernel_size": 5,
                "canny_lower_threshold": 30,
                "canny_upper_threshold": 100,
                "edge_thickness": 2.0,
                "gap_threshold": 0.0,
                "largest_n": 15,
                "simplify_pct": 0.0,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Max Fidelity": {
                "bilateral_diameter": 6,
                "bilateral_sigma_color": 50,
                "gaussian_kernel_size": 3,
                "canny_lower_threshold": 20,
                "canny_upper_threshold": 70,
                "edge_thickness": 1.2,
                "gap_threshold": 4.0,
                "largest_n": 20,
                "simplify_pct": 0.2,
                "mm_per_px": 0.10,
                "invert": True
            }
        }
        
        # Preset tooltips
        self.preset_tooltips = {
            "Default": "Balanced for general use",
            "High Detail": "Great for photos with fine textures",
            "Low Noise": "Reduces grain for high-ISO images",
            "Strong Edges": "Best for logos and bold artwork",
            "Portrait": "Flattering for faces and skin tones",
            "Landscape": "Crisp and vibrant for scenery",
            "Illustration": "Clean output for digital art",
            "Flat (Neutral)": "Minimal processing, good for editing later",
            "Max Fidelity": "Highest quality, slowest processing"
        }
        
        self.setup_ui()
        self.setup_drag_drop()
        self.setup_loading_overlay()
        self.setup_navigation()
        
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Top frame for file selection and export
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))
        
        # Left side - file selection
        ttk.Button(top_frame, text="Select Image", command=self.load_image).pack(side='left')
        self.status_label = ttk.Label(top_frame, text="No image loaded")
        self.status_label.pack(side='left', padx=(10, 0))
        
        # Right side - scaling and export
        right_controls_frame = ttk.Frame(top_frame)
        right_controls_frame.pack(side='right')
        
        # Image dimensions display
        self.dimensions_label = ttk.Label(right_controls_frame, text="")
        self.dimensions_label.pack(side='left', padx=(0, 10))
        
        # Scale input
        ttk.Label(right_controls_frame, text="Scale:").pack(side='left')
        self.export_scale_var = DoubleVar(value=1.0)
        self.export_scale_entry = ttk.Entry(right_controls_frame, textvariable=self.export_scale_var, width=8)
        self.export_scale_entry.pack(side='left', padx=(5, 5))
        self.export_scale_entry.bind('<KeyRelease>', self.on_export_scale_change)
        self.export_scale_entry.bind('<FocusOut>', self.on_export_scale_change)
        
        # Output size display
        self.output_size_label = ttk.Label(right_controls_frame, text="")
        self.output_size_label.pack(side='left', padx=(0, 10))
        
        # Export button
        ttk.Button(right_controls_frame, text="Export DXF", command=self.export_dxf).pack(side='left')
        
        # Middle frame for image previews
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill='both', expand=True)
        
        # Left panel - original image
        left_frame = ttk.LabelFrame(middle_frame, text="Original Image")
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        self.original_canvas = Canvas(left_frame, bg='white')
        self.original_canvas.pack(fill='both', expand=True)
        
        # Right panel - DXF preview
        right_frame = ttk.LabelFrame(middle_frame, text="DXF Preview")
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Navigation controls at the top
        nav_frame = ttk.Frame(right_frame)
        nav_frame.pack(fill='x', pady=(5, 0))
        
        # Zoom controls
        ttk.Label(nav_frame, text="Zoom:").pack(side='left', padx=(5, 2))
        ttk.Button(nav_frame, text="+", width=3, command=self.zoom_in).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="-", width=3, command=self.zoom_out).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="1:1", width=3, command=self.zoom_reset).pack(side='left', padx=2)
        
        # Separator
        ttk.Separator(nav_frame, orient='vertical').pack(side='left', fill='y', padx=10)
        
        # Pan controls
        ttk.Label(nav_frame, text="Pan:").pack(side='left', padx=(5, 2))
        ttk.Button(nav_frame, text="↑", width=2, command=lambda: self.pan_preview(0, -1)).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="↓", width=2, command=lambda: self.pan_preview(0, 1)).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="←", width=2, command=lambda: self.pan_preview(-1, 0)).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="→", width=2, command=lambda: self.pan_preview(1, 0)).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="⌂", width=2, command=self.pan_reset).pack(side='left', padx=1)
        
        # Separator
        ttk.Separator(nav_frame, orient='vertical').pack(side='left', fill='y', padx=10)
        
        # Edit controls
        ttk.Label(nav_frame, text="Edit:").pack(side='left', padx=(5, 2))
        self.edit_mode_var = StringVar(value="view")
        ttk.Button(nav_frame, text="✏️", width=3, command=lambda: self.set_edit_mode("paint")).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="🧽", width=3, command=lambda: self.set_edit_mode("eraser")).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="📐", width=3, command=lambda: self.set_edit_mode("shapes")).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="👁️", width=3, command=lambda: self.set_edit_mode("view")).pack(side='left', padx=1)
        
        # Shape selection
        self.shape_type_var = StringVar(value="rectangle")
        shape_combo = ttk.Combobox(nav_frame, textvariable=self.shape_type_var,
                                 values=["rectangle", "triangle", "circle"], 
                                 state="readonly", width=8)
        shape_combo.pack(side='left', padx=(5, 0))
        
        self.dxf_canvas = Canvas(right_frame, bg='white')
        self.dxf_canvas.pack(fill='both', expand=True)
        
        # Bottom frame for controls
        bottom_frame = ttk.LabelFrame(main_frame, text="Parameters")
        bottom_frame.pack(fill='x', pady=(10, 0))
        
        # Master Preset dropdown
        preset_frame = ttk.Frame(bottom_frame)
        preset_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(preset_frame, text="Master Preset:").pack(side='left')
        self.preset_var = StringVar(value="Default")
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, 
                                       values=["Custom", "Default", "High Detail", "Low Noise", "Strong Edges", 
                                              "Portrait", "Landscape", "Illustration", "Flat (Neutral)", "Max Fidelity"],
                                       state="readonly", width=15)
        self.preset_combo.pack(side='left', padx=(5, 0))
        self.preset_combo.bind('<<ComboboxSelected>>', lambda e: (
            self.create_tooltip(self.preset_combo, self.preset_tooltips.get(self.preset_var.get(), "Master preset that coordinates all individual slider presets")),
            self.on_preset_change()
        ))
        
        # Create sliders
        self.create_sliders(bottom_frame)
        
    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        if not DRAG_DROP_AVAILABLE:
            # Show a message that drag and drop is not available
            print("Note: Drag and drop not available. Install tkinterdnd2 for drag and drop support.")
            return
            
        # Enable drag and drop on the main window
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)
        
        # Also enable drag and drop on the original image canvas
        self.original_canvas.drop_target_register(DND_FILES)
        self.original_canvas.dnd_bind('<<Drop>>', self.on_drop)
        
        # Add visual feedback
        self.original_canvas.bind('<Enter>', self.on_drag_enter)
        self.original_canvas.bind('<Leave>', self.on_drag_leave)
        
    def on_drag_enter(self, event):
        """Visual feedback when dragging over the canvas"""
        if DRAG_DROP_AVAILABLE:
            self.original_canvas.config(bg='lightblue')
            
    def on_drag_leave(self, event):
        """Remove visual feedback when leaving the canvas"""
        if DRAG_DROP_AVAILABLE:
            self.original_canvas.config(bg='white')
            
    def on_drop(self, event):
        """Handle dropped files"""
        if not DRAG_DROP_AVAILABLE:
            return

        # Get the dropped file path
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]  # Take the first file
            
            # Check if it's an image file
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp']
            if any(file_path.lower().endswith(ext) for ext in image_extensions):
                # Load the image
                self.load_image_from_path(file_path)
            else:
                messagebox.showerror("Error", "Please drop an image file (.jpg, .png, .bmp, etc.)")
                
        # Reset visual feedback
        self.original_canvas.config(bg='white')
        
    def load_image_from_path(self, path):
        """Load image from a given path (used by both file dialog and drag-drop)"""
        self.image_path = path
        self.original_image = cv2.imread(path, cv2.IMREAD_COLOR)
        if self.original_image is not None:
            # Reset edit state for new image
            self.edited_contours = []
            self.erased_contours = set()
            self.erased_points = set()
            self.edit_mode = "view"
            self.dxf_canvas.config(cursor="")
            
            # Update status and dimensions
            h, w = self.original_image.shape[:2]
            self.status_label.config(text=f"Loaded: {os.path.basename(path)}")
            self.dimensions_label.config(text=f"Size: {w}×{h}px")
            
            # Update output size display
            self.on_export_scale_change()
            
            self.display_original_image()
            self.update_preview()
        else:
            messagebox.showerror("Error", "Could not read image.")
            
    def setup_navigation(self):
        """Setup navigation variables and bindings"""
        # Initialize zoom and pan variables
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        # Bind mouse events for zoom, pan, and editing
        self.dxf_canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.dxf_canvas.bind("<Button-1>", self.on_canvas_click)
        self.dxf_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.dxf_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
    def zoom_in(self):
        """Zoom in on the preview"""
        self.zoom_factor *= 1.2
        self.redraw_preview()
        
    def zoom_out(self):
        """Zoom out on the preview"""
        self.zoom_factor /= 1.2
        self.redraw_preview()
        
    def zoom_reset(self):
        """Reset zoom to 1:1"""
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.redraw_preview()
        
    def pan_preview(self, dx, dy):
        """Pan the preview"""
        self.pan_x += dx * 20
        self.pan_y += dy * 20
        self.redraw_preview()
        
    def pan_reset(self):
        """Reset pan position"""
        self.pan_x = 0
        self.pan_y = 0
        self.redraw_preview()
        
    def on_mousewheel(self, event):
        """Handle mouse wheel zoom"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
            
    def on_canvas_click(self, event):
        """Handle canvas click for panning or starting drawing"""
        if self.edit_mode == "view":
            self.last_x = event.x
            self.last_y = event.y
        elif self.edit_mode == "paint":
            self.drawing = True
            self.drawing_points = [(event.x, event.y)]
        elif self.edit_mode == "shapes":
            self.start_shape_drawing(event.x, event.y)
        
    def on_canvas_drag(self, event):
        """Handle canvas drag for panning or drawing"""
        if self.edit_mode == "view":
            # Pan mode
            if hasattr(self, 'last_x'):
                dx = event.x - self.last_x
                dy = event.y - self.last_y
                self.pan_x += dx
                self.pan_y += dy
                self.last_x = event.x
                self.last_y = event.y
                self.redraw_preview()
        elif self.edit_mode == "paint":
            # Paint mode - draw freehand
            if self.drawing:
                self.drawing_points.append((event.x, event.y))
                self.draw_temporary_line()
        elif self.edit_mode == "eraser":
            # Eraser mode - erase along the drag path
            self.erase_along_path(event.x, event.y)
            
    def on_canvas_release(self, event):
        """Handle canvas release for finishing drawing"""
        if self.edit_mode == "paint" and self.drawing:
            self.finish_paint_stroke()
        elif self.edit_mode == "shapes":
            self.finish_shape_drawing(event.x, event.y)
            
    def set_edit_mode(self, mode):
        """Set the current edit mode"""
        self.edit_mode = mode
        self.drawing = False
        self.drawing_points = []
        
        # Update cursor based on mode
        if mode == "view":
            self.dxf_canvas.config(cursor="")
        elif mode == "paint":
            self.dxf_canvas.config(cursor="pencil")
        elif mode == "eraser":
            # Create a custom eraser cursor (gray circle)
            self.dxf_canvas.config(cursor="")
            self.setup_eraser_cursor()
        elif mode == "shapes":
            self.dxf_canvas.config(cursor="crosshair")
            
    def setup_eraser_cursor(self):
        """Setup eraser cursor with gray circle"""
        self.eraser_radius = 15  # Eraser radius in pixels
        self.eraser_circle = None
        
        # Bind mouse motion to show eraser circle
        self.dxf_canvas.bind("<Motion>", self.on_eraser_motion)
        self.dxf_canvas.bind("<Leave>", self.hide_eraser_circle)
        
    def on_eraser_motion(self, event):
        """Show eraser circle at cursor position"""
        if self.edit_mode == "eraser":
            # Remove previous eraser circle
            if self.eraser_circle:
                self.dxf_canvas.delete(self.eraser_circle)
            
            # Draw new eraser circle
            x, y = event.x, event.y
            self.eraser_circle = self.dxf_canvas.create_oval(
                x - self.eraser_radius, y - self.eraser_radius,
                x + self.eraser_radius, y + self.eraser_radius,
                outline="gray", width=2, fill="", tags="eraser_cursor"
            )
            
    def hide_eraser_circle(self, event):
        """Hide eraser circle when mouse leaves canvas"""
        if self.eraser_circle:
            self.dxf_canvas.delete(self.eraser_circle)
            self.eraser_circle = None
            
    def draw_temporary_line(self):
        """Draw temporary line while painting"""
        if len(self.drawing_points) >= 2:
            # Clear previous temporary line
            self.dxf_canvas.delete("temp_line")
            # Draw new temporary line
            points = []
            for x, y in self.drawing_points:
                points.extend([x, y])
            self.dxf_canvas.create_line(points, fill="blue", width=2, tags="temp_line")
            
    def finish_paint_stroke(self):
        """Finish a paint stroke and add it to contours"""
        if len(self.drawing_points) >= 2:
            # Convert canvas coordinates to image coordinates
            image_points = []
            canvas_width = self.dxf_canvas.winfo_width()
            canvas_height = self.dxf_canvas.winfo_height()
            h, w = self.original_image.shape[:2]
            base_scale = min(canvas_width/w, canvas_height/h, 1.0) * 0.9
            scale = base_scale * self.zoom_factor
            center_x = canvas_width//2 + self.pan_x
            center_y = canvas_height//2 + self.pan_y
            
            for x, y in self.drawing_points:
                # Convert back to image coordinates
                img_x = (x - center_x + w*scale//2) / scale
                img_y = (y - center_y + h*scale//2) / scale
                image_points.append([[int(img_x), int(img_y)]])
            
            # Add as new contour
            if len(image_points) >= 2:
                new_contour = np.array(image_points, dtype=np.int32)
                self.edited_contours.append(new_contour)
                self.redraw_preview()
        
        self.drawing = False
        self.drawing_points = []
        self.dxf_canvas.delete("temp_line")
        
    def erase_along_path(self, x, y):
        """Erase along the drag path by modifying contours"""
        if not hasattr(self, 'last_erase_x'):
            self.last_erase_x = x
            self.last_erase_y = y
            return
            
        # Create a mask for the eraser path
        canvas_width = self.dxf_canvas.winfo_width()
        canvas_height = self.dxf_canvas.winfo_height()
        h, w = self.original_image.shape[:2]
        base_scale = min(canvas_width/w, canvas_height/h, 1.0) * 0.9
        scale = base_scale * self.zoom_factor
        center_x = canvas_width//2 + self.pan_x
        center_y = canvas_height//2 + self.pan_y
        
        # Convert canvas coordinates to image coordinates
        img_x1 = (self.last_erase_x - center_x + w*scale//2) / scale
        img_y1 = (self.last_erase_y - center_y + h*scale//2) / scale
        img_x2 = (x - center_x + w*scale//2) / scale
        img_y2 = (y - center_y + h*scale//2) / scale
        
        # Erase radius in image coordinates
        erase_radius_img = self.eraser_radius / scale
        
        # Mark points within eraser radius as erased
        for i, contour in enumerate(self.preview_contours):
            if i in self.erased_contours:
                continue
                
            # Check each point in the contour
            for j, point in enumerate(contour):
                px, py = float(point[0][0]), float(point[0][1])
                
                # Check if point is within eraser radius of the line segment
                distance = self.point_to_line_distance(px, py, img_x1, img_y1, img_x2, img_y2)
                if distance < erase_radius_img:
                    # Mark this point as erased by adding to a set of erased points
                    if not hasattr(self, 'erased_points'):
                        self.erased_points = set()
                    self.erased_points.add((i, j))
        
        self.last_erase_x = x
        self.last_erase_y = y
        self.redraw_preview()
        
    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """Calculate distance from point to line segment"""
        # Vector from line start to end
        line_dx = x2 - x1
        line_dy = y2 - y1
        line_length_sq = line_dx * line_dx + line_dy * line_dy
        
        if line_length_sq == 0:
            # Line is a point
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        
        # Vector from line start to point
        point_dx = px - x1
        point_dy = py - y1
        
        # Project point onto line
        t = max(0, min(1, (point_dx * line_dx + point_dy * line_dy) / line_length_sq))
        
        # Closest point on line segment
        closest_x = x1 + t * line_dx
        closest_y = y1 + t * line_dy
        
        # Distance from point to closest point on line
        return ((px - closest_x) ** 2 + (py - closest_y) ** 2) ** 0.5
                    
    def start_shape_drawing(self, x, y):
        """Start drawing a shape"""
        self.shape_start_x = x
        self.shape_start_y = y
        self.drawing = True
        
    def finish_shape_drawing(self, x, y):
        """Finish drawing a shape"""
        if not self.drawing:
            return
            
        shape_type = self.shape_type_var.get()
        
        if shape_type == "rectangle":
            shape_points = [
                [[self.shape_start_x, self.shape_start_y]],
                [[x, self.shape_start_y]],
                [[x, y]],
                [[self.shape_start_x, y]]
            ]
        elif shape_type == "triangle":
            # Equilateral triangle
            mid_x = (self.shape_start_x + x) / 2
            height = abs(y - self.shape_start_y)
            if y < self.shape_start_y:  # Triangle pointing up
                shape_points = [
                    [[self.shape_start_x, y]],  # Bottom left
                    [[x, y]],                   # Bottom right
                    [[mid_x, self.shape_start_y]]  # Top center
                ]
            else:  # Triangle pointing down
                shape_points = [
                    [[self.shape_start_x, self.shape_start_y]],  # Top left
                    [[x, self.shape_start_y]],                   # Top right
                    [[mid_x, y]]                                 # Bottom center
                ]
        elif shape_type == "circle":
            # Create circle points
            center_x = (self.shape_start_x + x) / 2
            center_y = (self.shape_start_y + y) / 2
            radius = max(abs(x - self.shape_start_x), abs(y - self.shape_start_y)) / 2
            
            # Generate circle points
            num_points = 16
            shape_points = []
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                px = center_x + radius * math.cos(angle)
                py = center_y + radius * math.sin(angle)
                shape_points.append([[px, py]])
        
        # Convert to image coordinates and add as contour
        image_points = []
        canvas_width = self.dxf_canvas.winfo_width()
        canvas_height = self.dxf_canvas.winfo_height()
        h, w = self.original_image.shape[:2]
        base_scale = min(canvas_width/w, canvas_height/h, 1.0) * 0.9
        scale = base_scale * self.zoom_factor
        center_x = canvas_width//2 + self.pan_x
        center_y = canvas_height//2 + self.pan_y
        
        for point in shape_points:
            img_x = (point[0][0] - center_x + w*scale//2) / scale
            img_y = (point[0][1] - center_y + h*scale//2) / scale
            image_points.append([[int(img_x), int(img_y)]])
        
        if len(image_points) >= 3:
            new_contour = np.array(image_points, dtype=np.int32)
            self.edited_contours.append(new_contour)
            self.redraw_preview()
            
        self.drawing = False
            
    def setup_loading_overlay(self):
        """Setup loading overlay for processing feedback"""
        self.loading_frame = None
        self.loading_label = None
        
    def show_loading(self, message="Processing..."):
        """Show loading overlay"""
        if self.loading_frame is None:
            self.loading_frame = ttk.Frame(self.root)
            self.loading_frame.place(relx=0.5, rely=0.5, anchor='center')
            
            # Semi-transparent background
            self.loading_frame.configure(style='Loading.TFrame')
            
            self.loading_label = ttk.Label(self.loading_frame, text=message, 
                                         font=('Arial', 12, 'bold'))
            self.loading_label.pack(pady=20, padx=20)
            
            # Force update
            self.root.update()
            
    def hide_loading(self):
        """Hide loading overlay"""
        if self.loading_frame is not None:
            self.loading_frame.destroy()
            self.loading_frame = None
            self.loading_label = None
            
    def apply_gap_processing(self):
        """Apply gap processing with loading feedback"""
        if self.original_image is None:
            messagebox.showwarning("Warning", "No image loaded.")
            return
            
        self.show_loading("Applying gap processing...")
        
        try:
            # Update gap threshold parameter
            self.params["gap_threshold"] = self.gap_var.get()
            self.gap_label.config(text=f"{self.params['gap_threshold']:.1f}")
            
            # Process contours with gap threshold
            self.current_contours = contours_from_mask(self.current_mask, 
                                                     self.params["largest_n"], 
                                                     self.params["simplify_pct"],
                                                     self.params["gap_threshold"])
            
            # Update preview
            self.display_dxf_preview()
            
        except Exception as e:
            messagebox.showerror("Error", f"Gap processing failed: {str(e)}")
        finally:
            self.hide_loading()
        
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def show_tooltip(event):
            tooltip = Tk()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=text, background="lightyellow", 
                            relief="solid", borderwidth=1, padding=5)
            label.pack()
            widget.tooltip = tooltip
            
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
                
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def create_sliders(self, parent):
        # Bilateral Filter Diameter
        bilateral_d_frame = ttk.Frame(parent)
        bilateral_d_frame.pack(fill='x', pady=2)
        
        # Bilateral Diameter preset
        bilateral_d_preset_frame = ttk.Frame(bilateral_d_frame)
        bilateral_d_preset_frame.pack(side='left')
        self.bilateral_d_preset_var = StringVar(value="Medium")
        bilateral_d_preset_combo = ttk.Combobox(bilateral_d_preset_frame, textvariable=self.bilateral_d_preset_var,
                                              values=["Small", "Medium", "Large"], state="readonly", width=8)
        bilateral_d_preset_combo.pack(side='left')
        bilateral_d_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_bilateral_d_preset_change())
        self.create_tooltip(bilateral_d_preset_combo, "Bilateral diameter presets: Small(6), Medium(9), Large(12)")
        
        bilateral_d_label = ttk.Label(bilateral_d_frame, text="Bilateral Diameter:", width=15)
        bilateral_d_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(bilateral_d_label, "Controls the neighborhood size for bilateral filtering. Larger values smooth more but may blur edges. Range: 5-15")
        
        self.bilateral_d_var = IntVar(value=9)
        self.bilateral_d_scale = ttk.Scale(bilateral_d_frame, from_=5, to=15, 
                                         variable=self.bilateral_d_var, orient='horizontal',
                                         command=self.on_slider_start_change)
        self.bilateral_d_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.bilateral_d_label = ttk.Label(bilateral_d_frame, text="9")
        self.bilateral_d_label.pack(side='right', padx=(5, 0))
        
        # Bilateral Sigma Color
        bilateral_c_frame = ttk.Frame(parent)
        bilateral_c_frame.pack(fill='x', pady=2)
        
        # Bilateral Color preset
        bilateral_c_preset_frame = ttk.Frame(bilateral_c_frame)
        bilateral_c_preset_frame.pack(side='left')
        self.bilateral_c_preset_var = StringVar(value="Medium")
        bilateral_c_preset_combo = ttk.Combobox(bilateral_c_preset_frame, textvariable=self.bilateral_c_preset_var,
                                              values=["Low", "Medium", "High"], state="readonly", width=8)
        bilateral_c_preset_combo.pack(side='left')
        bilateral_c_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_bilateral_c_preset_change())
        self.create_tooltip(bilateral_c_preset_combo, "Bilateral color presets: Low(40), Medium(75), High(120)")
        
        bilateral_c_label = ttk.Label(bilateral_c_frame, text="Bilateral Color σ:", width=15)
        bilateral_c_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(bilateral_c_label, "Controls color similarity threshold for bilateral filtering. Higher values allow more color variation. Range: 25-150")
        
        self.bilateral_c_var = IntVar(value=75)
        self.bilateral_c_scale = ttk.Scale(bilateral_c_frame, from_=25, to=150, 
                                         variable=self.bilateral_c_var, orient='horizontal',
                                         command=self.on_slider_start_change)
        self.bilateral_c_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.bilateral_c_label = ttk.Label(bilateral_c_frame, text="75")
        self.bilateral_c_label.pack(side='right', padx=(5, 0))
        
        # Gaussian Kernel Size
        gaussian_frame = ttk.Frame(parent)
        gaussian_frame.pack(fill='x', pady=2)
        
        # Gaussian preset
        gaussian_preset_frame = ttk.Frame(gaussian_frame)
        gaussian_preset_frame.pack(side='left')
        self.gaussian_preset_var = StringVar(value="Medium")
        gaussian_preset_combo = ttk.Combobox(gaussian_preset_frame, textvariable=self.gaussian_preset_var,
                                           values=["Light", "Medium", "Heavy"], state="readonly", width=8)
        gaussian_preset_combo.pack(side='left')
        gaussian_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_gaussian_preset_change())
        self.create_tooltip(gaussian_preset_combo, "Gaussian blur presets: Light(3), Medium(5), Heavy(7)")
        
        gaussian_label = ttk.Label(gaussian_frame, text="Gaussian Kernel:", width=15)
        gaussian_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(gaussian_label, "Controls the amount of blur applied. Larger values create more smoothing. Must be odd numbers. Range: 3-9")
        
        self.gaussian_var = IntVar(value=5)
        self.gaussian_scale = ttk.Scale(gaussian_frame, from_=3, to=9, 
                                      variable=self.gaussian_var, orient='horizontal',
                                      command=self.on_slider_start_change)
        self.gaussian_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.gaussian_label = ttk.Label(gaussian_frame, text="5")
        self.gaussian_label.pack(side='right', padx=(5, 0))
        
        
        # Canny Edge Detection (Combined preset for both thresholds)
        canny_preset_frame = ttk.Frame(parent)
        canny_preset_frame.pack(fill='x', pady=2)
        
        # Canny preset
        canny_preset_combo_frame = ttk.Frame(canny_preset_frame)
        canny_preset_combo_frame.pack(side='left')
        self.canny_preset_var = StringVar(value="Medium")
        canny_preset_combo = ttk.Combobox(canny_preset_combo_frame, textvariable=self.canny_preset_var,
                                        values=["Sensitive", "Medium", "Conservative"], state="readonly", width=10)
        canny_preset_combo.pack(side='left')
        canny_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_canny_preset_change())
        self.create_tooltip(canny_preset_combo, "Canny edge presets: Sensitive(20/60), Medium(30/100), Conservative(50/150)")
        
        ttk.Label(canny_preset_frame, text="Canny Edge Detection", width=20).pack(side='left', padx=(5, 0))
        
        # Canny Lower Threshold
        canny_l_frame = ttk.Frame(parent)
        canny_l_frame.pack(fill='x', pady=2)
        canny_l_label = ttk.Label(canny_l_frame, text="Canny Lower:", width=15)
        canny_l_label.pack(side='left')
        self.create_tooltip(canny_l_label, "Lower threshold for Canny edge detection. Lower values detect more edges but may include noise. Range: 10-100")
        
        self.canny_l_var = IntVar(value=30)
        self.canny_l_scale = ttk.Scale(canny_l_frame, from_=10, to=100, 
                                     variable=self.canny_l_var, orient='horizontal',
                                     command=self.on_slider_start_change)
        self.canny_l_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.canny_l_label = ttk.Label(canny_l_frame, text="30")
        self.canny_l_label.pack(side='right', padx=(5, 0))
        
        # Canny Upper Threshold
        canny_u_frame = ttk.Frame(parent)
        canny_u_frame.pack(fill='x', pady=2)
        canny_u_label = ttk.Label(canny_u_frame, text="Canny Upper:", width=15)
        canny_u_label.pack(side='left')
        self.create_tooltip(canny_u_label, "Upper threshold for Canny edge detection. Should be 2-3x the lower threshold. Higher values detect only strong edges. Range: 30-200")
        
        self.canny_u_var = IntVar(value=100)
        self.canny_u_scale = ttk.Scale(canny_u_frame, from_=30, to=200, 
                                     variable=self.canny_u_var, orient='horizontal',
                                     command=self.on_slider_start_change)
        self.canny_u_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.canny_u_label = ttk.Label(canny_u_frame, text="100")
        self.canny_u_label.pack(side='right', padx=(5, 0))
        
        # Edge Thickness
        thickness_frame = ttk.Frame(parent)
        thickness_frame.pack(fill='x', pady=2)
        
        # Edge Thickness preset
        thickness_preset_frame = ttk.Frame(thickness_frame)
        thickness_preset_frame.pack(side='left')
        self.thickness_preset_var = StringVar(value="Medium")
        thickness_preset_combo = ttk.Combobox(thickness_preset_frame, textvariable=self.thickness_preset_var,
                                            values=["Thin", "Medium", "Thick"], state="readonly", width=8)
        thickness_preset_combo.pack(side='left')
        thickness_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_thickness_preset_change())
        self.create_tooltip(thickness_preset_combo, "Edge thickness presets: Thin(1.0), Medium(2.5), Thick(6.0)")
        
        thickness_label = ttk.Label(thickness_frame, text="Edge Thickness:", width=15)
        thickness_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(thickness_label, "Controls how thick the detected edges become. Higher values create bolder lines but may merge nearby edges. Range: 1.0-50.0")
        
        self.thickness_var = DoubleVar(value=2.0)
        self.thickness_scale = ttk.Scale(thickness_frame, from_=1.0, to=50.0, 
                                       variable=self.thickness_var, orient='horizontal',
                                       command=self.on_slider_start_change)
        self.thickness_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.thickness_label = ttk.Label(thickness_frame, text="2.0")
        self.thickness_label.pack(side='right', padx=(5, 0))
        
        # Gap Threshold slider
        gap_frame = ttk.Frame(parent)
        gap_frame.pack(fill='x', pady=2)
        
        # Gap Threshold preset
        gap_preset_frame = ttk.Frame(gap_frame)
        gap_preset_frame.pack(side='left')
        self.gap_preset_var = StringVar(value="Medium")
        gap_preset_combo = ttk.Combobox(gap_preset_frame, textvariable=self.gap_preset_var,
                                      values=["None", "Light", "Medium", "Heavy"], state="readonly", width=8)
        gap_preset_combo.pack(side='left')
        gap_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_gap_preset_change())
        self.create_tooltip(gap_preset_combo, "Gap closing presets: None(0), Light(2.5), Medium(5.0), Heavy(10.0)")
        
        gap_label = ttk.Label(gap_frame, text="Gap Threshold:", width=15)
        gap_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(gap_label, "Converts small gaps between contour segments into continuous lines. Higher values connect more segments. Range: 0-20 pixels")
        
        self.gap_var = DoubleVar(value=5.0)
        self.gap_scale = ttk.Scale(gap_frame, from_=0.0, to=20.0, 
                                 variable=self.gap_var, orient='horizontal',
                                 command=self.on_slider_start_change)
        self.gap_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.gap_label = ttk.Label(gap_frame, text="5.0")
        self.gap_label.pack(side='right', padx=(5, 0))
        
        # Largest N slider
        largest_frame = ttk.Frame(parent)
        largest_frame.pack(fill='x', pady=2)
        
        # Largest N preset
        largest_preset_frame = ttk.Frame(largest_frame)
        largest_preset_frame.pack(side='left')
        self.largest_preset_var = StringVar(value="Medium")
        largest_preset_combo = ttk.Combobox(largest_preset_frame, textvariable=self.largest_preset_var,
                                         values=["Few", "Medium", "Many"], state="readonly", width=8)
        largest_preset_combo.pack(side='left')
        largest_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_largest_preset_change())
        self.create_tooltip(largest_preset_combo, "Contour count presets: Few(3), Medium(10), Many(30)")
        
        largest_label = ttk.Label(largest_frame, text="Largest N:", width=15)
        largest_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(largest_label, "Number of largest contours to keep. Use 1-3 for bold silhouettes, higher values for detailed images. Range: 1-50")
        
        self.largest_var = IntVar(value=10)
        self.largest_scale = ttk.Scale(largest_frame, from_=1, to=50, 
                                     variable=self.largest_var, orient='horizontal',
                                     command=self.on_slider_start_change)
        self.largest_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.largest_label = ttk.Label(largest_frame, text="10")
        self.largest_label.pack(side='right', padx=(5, 0))
        
        # Simplify slider
        simplify_frame = ttk.Frame(parent)
        simplify_frame.pack(fill='x', pady=2)
        
        # Simplify preset
        simplify_preset_frame = ttk.Frame(simplify_frame)
        simplify_preset_frame.pack(side='left')
        self.simplify_preset_var = StringVar(value="Medium")
        simplify_preset_combo = ttk.Combobox(simplify_preset_frame, textvariable=self.simplify_preset_var,
                                           values=["Detailed", "Medium", "Simple"], state="readonly", width=8)
        simplify_preset_combo.pack(side='left')
        simplify_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_simplify_preset_change())
        self.create_tooltip(simplify_preset_combo, "Simplification presets: Detailed(0.2), Medium(0.5), Simple(1.0)")
        
        simplify_label = ttk.Label(simplify_frame, text="Simplify %:", width=15)
        simplify_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(simplify_label, "Reduces the number of points in contours. Higher values create simpler shapes but may lose detail. Range: 0.0-2.0%")
        
        self.simplify_var = DoubleVar(value=0.5)
        self.simplify_scale = ttk.Scale(simplify_frame, from_=0.0, to=2.0, 
                                      variable=self.simplify_var, orient='horizontal',
                                      command=self.on_slider_start_change)
        self.simplify_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.simplify_label = ttk.Label(simplify_frame, text="0.5")
        self.simplify_label.pack(side='right', padx=(5, 0))
        
        # Scale slider
        scale_frame = ttk.Frame(parent)
        scale_frame.pack(fill='x', pady=2)
        
        # Scale preset
        scale_preset_frame = ttk.Frame(scale_frame)
        scale_preset_frame.pack(side='left')
        self.scale_preset_var = StringVar(value="Medium")
        scale_preset_combo = ttk.Combobox(scale_preset_frame, textvariable=self.scale_preset_var,
                                        values=["Small", "Medium", "Large"], state="readonly", width=8)
        scale_preset_combo.pack(side='left')
        scale_preset_combo.bind('<<ComboboxSelected>>', lambda e: self.on_scale_preset_change())
        self.create_tooltip(scale_preset_combo, "Scale presets: Small(0.15), Medium(0.25), Large(1.0)")
        
        scale_label = ttk.Label(scale_frame, text="Scale (mm/px):", width=15)
        scale_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(scale_label, "Converts pixels to millimeters in the DXF output. 0.25 means 1 pixel = 0.25mm. Range: 0.01-2.0")
        
        self.scale_var = DoubleVar(value=0.25)
        self.scale_scale = ttk.Scale(scale_frame, from_=0.01, to=2.0, 
                                   variable=self.scale_var, orient='horizontal',
                                   command=self.on_slider_start_change)
        self.scale_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.scale_label = ttk.Label(scale_frame, text="0.25")
        self.scale_label.pack(side='right', padx=(5, 0))
        
        # Invert checkbox
        invert_frame = ttk.Frame(parent)
        invert_frame.pack(fill='x', pady=2)
        self.invert_var = BooleanVar(value=True)
        invert_label = ttk.Checkbutton(invert_frame, text="Invert Black/White", 
                       variable=self.invert_var, command=self.on_param_change)
        invert_label.pack(side='left')
        self.create_tooltip(invert_label, "Inverts the black and white values. Use when your subject is lighter than the background (e.g., white text on dark background)")
        
    def load_image(self):
        filetypes = [
            ("Images", "*.jpg;*.jpeg;*.png;*.bmp;*.tif;*.tiff;*.webp"),
            ("All files", "*.*"),
        ]
        path = filedialog.askopenfilename(title="Select an image to convert", filetypes=filetypes)
        if path:
            self.load_image_from_path(path)
                
    def display_original_image(self):
        if self.original_image is None:
            return
            
        # Convert BGR to RGB for display
        img_rgb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        
        # Resize to fit canvas while maintaining aspect ratio
        canvas_width = self.original_canvas.winfo_width()
        canvas_height = self.original_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            h, w = img_rgb.shape[:2]
            scale = min(canvas_width/w, canvas_height/h, 1.0)
            new_w, new_h = int(w*scale), int(h*scale)
            
            img_resized = cv2.resize(img_rgb, (new_w, new_h))
            self.original_photo = ImageTk.PhotoImage(Image.fromarray(img_resized))
            
            self.original_canvas.delete("all")
            self.original_canvas.create_image(canvas_width//2, canvas_height//2, 
                                            image=self.original_photo, anchor='center')
    
    def update_preview(self):
        if self.original_image is None:
            return
            
        # Update parameters from sliders
        self.params["bilateral_diameter"] = int(self.bilateral_d_var.get())
        self.params["bilateral_sigma_color"] = int(self.bilateral_c_var.get())
        self.params["bilateral_sigma_space"] = int(self.bilateral_c_var.get())  # Use same as color for simplicity
        self.params["gaussian_kernel_size"] = int(self.gaussian_var.get())
        if self.params["gaussian_kernel_size"] % 2 == 0:
            self.params["gaussian_kernel_size"] += 1  # Ensure odd
        self.params["canny_lower_threshold"] = int(self.canny_l_var.get())
        self.params["canny_upper_threshold"] = int(self.canny_u_var.get())
        self.params["edge_thickness"] = self.thickness_var.get()
        self.params["gap_threshold"] = self.gap_var.get()
        self.params["largest_n"] = int(self.largest_var.get())
        self.params["simplify_pct"] = self.simplify_var.get()
        self.params["mm_per_px"] = self.scale_var.get()
        self.params["invert"] = self.invert_var.get()
        
        # Update labels
        self.bilateral_d_label.config(text=str(self.params["bilateral_diameter"]))
        self.bilateral_c_label.config(text=str(self.params["bilateral_sigma_color"]))
        self.gaussian_label.config(text=str(self.params["gaussian_kernel_size"]))
        self.canny_l_label.config(text=str(self.params["canny_lower_threshold"]))
        self.canny_u_label.config(text=str(self.params["canny_upper_threshold"]))
        self.thickness_label.config(text=f"{self.params['edge_thickness']:.1f}")
        self.gap_label.config(text=f"{self.params['gap_threshold']:.1f}")
        self.largest_label.config(text=str(self.params["largest_n"]))
        self.simplify_label.config(text=f"{self.params['simplify_pct']:.1f}")
        self.scale_label.config(text=f"{self.params['mm_per_px']:.3f}")
        
        # Process image with gap processing for preview
        self.current_mask = find_edges_and_contours(self.original_image, self.params)
        self.current_contours = contours_from_mask(self.current_mask, 
                                                 self.params["largest_n"], 
                                                 self.params["simplify_pct"],
                                                 self.params["gap_threshold"])
        
        # Display DXF preview
        self.display_dxf_preview()
        
    def display_dxf_preview(self):
        if not self.current_contours or self.original_image is None:
            self.dxf_canvas.delete("all")
            return
            
        # Store contours for redrawing
        self.preview_contours = self.current_contours
        self.redraw_preview()
        
    def redraw_preview(self):
        """Redraw the preview with current zoom and pan settings"""
        if not hasattr(self, 'preview_contours') or not self.preview_contours or self.original_image is None:
            self.dxf_canvas.delete("all")
            return

        # Clear canvas
        self.dxf_canvas.delete("all")
        
        # Get canvas dimensions
        canvas_width = self.dxf_canvas.winfo_width()
        canvas_height = self.dxf_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return

        # Calculate base scale to fit contours in canvas
        h, w = self.original_image.shape[:2]
        base_scale = min(canvas_width/w, canvas_height/h, 1.0) * 0.9
        
        # Apply zoom factor
        scale = base_scale * self.zoom_factor
        
        # Calculate center position with pan offset
        center_x = canvas_width//2 + self.pan_x
        center_y = canvas_height//2 + self.pan_y
        
        # Draw original contours (excluding erased points)
        for i, contour in enumerate(self.preview_contours):
            if i in self.erased_contours:
                continue
                
            points = []
            for j, point in enumerate(contour):
                # Skip erased points
                if hasattr(self, 'erased_points') and (i, j) in self.erased_points:
                    continue
                    
                x = float(point[0][0]) * scale + center_x - w*scale//2
                y = float(point[0][1]) * scale + center_y - h*scale//2
                points.extend([x, y])
            
            if len(points) >= 6:  # At least 3 points (x,y pairs)
                # Use dark green for meaningful contours, red for noise/small contours
                area = cv2.contourArea(contour)
                color = 'dark green' if area > 100 else 'red'
                # Adjust line width based on zoom
                line_width = max(1, int(2 * self.zoom_factor))
                # Draw as line instead of polygon to avoid auto-completion
                self.dxf_canvas.create_line(points, fill=color, width=line_width)
        
        # Draw edited contours (manually added)
        for contour in self.edited_contours:
            points = []
            for point in contour:
                x = float(point[0][0]) * scale + center_x - w*scale//2
                y = float(point[0][1]) * scale + center_y - h*scale//2
                points.extend([x, y])
            
            if len(points) >= 6:  # At least 3 points (x,y pairs)
                # Use blue for manually added contours
                line_width = max(1, int(2 * self.zoom_factor))
                self.dxf_canvas.create_line(points, fill='blue', width=line_width)
    
    def on_param_change(self, event=None):
        # Check if user has made edits
        if self.has_edits():
            result = messagebox.askyesnocancel(
                "Unsaved Edits",
                "You have unsaved edits (eraser or paint strokes).\n\n"
                "Changing parameters will lose your edits.\n\n"
                "Do you want to continue and lose your edits?",
                icon='warning'
            )
            if result is None:  # Cancel
                # Revert slider values to previous state
                self.revert_slider_values()
                return
            elif result is False:  # No
                # Revert slider values to previous state
                self.revert_slider_values()
                return
            # If result is True (Yes), continue with parameter change
        
        # Set preset to Custom when user manually changes parameters
        if self.preset_var.get() != "Custom":
            self.preset_var.set("Custom")
        self.update_preview()
    
    def has_edits(self):
        """Check if user has made any edits"""
        return len(self.edited_contours) > 0 or len(self.erased_contours) > 0 or len(self.erased_points) > 0
    
    def store_slider_values(self):
        """Store current slider values for potential reverting"""
        self.previous_slider_values = {
            "bilateral_d": self.bilateral_d_var.get(),
            "bilateral_c": self.bilateral_c_var.get(),
            "gaussian": self.gaussian_var.get(),
            "canny_l": self.canny_l_var.get(),
            "canny_u": self.canny_u_var.get(),
            "thickness": self.thickness_var.get(),
            "gap": self.gap_var.get(),
            "largest": self.largest_var.get(),
            "simplify": self.simplify_var.get(),
            "scale": self.scale_var.get(),
            "invert": self.invert_var.get()
        }
    
    def revert_slider_values(self):
        """Revert slider values to previous state"""
        if not self.previous_slider_values:
            return
            
        self.bilateral_d_var.set(self.previous_slider_values["bilateral_d"])
        self.bilateral_c_var.set(self.previous_slider_values["bilateral_c"])
        self.gaussian_var.set(self.previous_slider_values["gaussian"])
        self.canny_l_var.set(self.previous_slider_values["canny_l"])
        self.canny_u_var.set(self.previous_slider_values["canny_u"])
        self.thickness_var.set(self.previous_slider_values["thickness"])
        self.gap_var.set(self.previous_slider_values["gap"])
        self.largest_var.set(self.previous_slider_values["largest"])
        self.simplify_var.set(self.previous_slider_values["simplify"])
        self.scale_var.set(self.previous_slider_values["scale"])
        self.invert_var.set(self.previous_slider_values["invert"])
        
        # Update labels to reflect reverted values
        self.bilateral_d_label.config(text=str(self.previous_slider_values["bilateral_d"]))
        self.bilateral_c_label.config(text=str(self.previous_slider_values["bilateral_c"]))
        self.gaussian_label.config(text=str(self.previous_slider_values["gaussian"]))
        self.canny_l_label.config(text=str(self.previous_slider_values["canny_l"]))
        self.canny_u_label.config(text=str(self.previous_slider_values["canny_u"]))
        self.thickness_label.config(text=f"{self.previous_slider_values['thickness']:.1f}")
        self.gap_label.config(text=f"{self.previous_slider_values['gap']:.1f}")
        self.largest_label.config(text=str(self.previous_slider_values["largest"]))
        self.simplify_label.config(text=f"{self.previous_slider_values['simplify']:.1f}")
        self.scale_label.config(text=f"{self.previous_slider_values['scale']:.3f}")
    
    def on_slider_start_change(self, event=None):
        """Called when slider starts changing - store current values first"""
        # Store current values before any change
        self.store_slider_values()
        # Then proceed with normal parameter change
        self.on_param_change(event)
    
    # Individual preset change methods
    def on_bilateral_d_preset_change(self):
        presets = {"Small": 6, "Medium": 9, "Large": 12}
        preset = self.bilateral_d_preset_var.get()
        if preset in presets:
            self.store_slider_values()  # Store before change
            self.bilateral_d_var.set(presets[preset])
            self.bilateral_d_label.config(text=str(presets[preset]))
            self.on_param_change()
    
    def on_bilateral_c_preset_change(self):
        presets = {"Low": 40, "Medium": 75, "High": 120}
        preset = self.bilateral_c_preset_var.get()
        if preset in presets:
            self.store_slider_values()
            self.bilateral_c_var.set(presets[preset])
            self.bilateral_c_label.config(text=str(presets[preset]))
            self.on_param_change()
    
    def on_gaussian_preset_change(self):
        presets = {"Light": 3, "Medium": 5, "Heavy": 7}
        preset = self.gaussian_preset_var.get()
        if preset in presets:
            self.store_slider_values()
            self.gaussian_var.set(presets[preset])
            self.gaussian_label.config(text=str(presets[preset]))
            self.on_param_change()
    
    def on_canny_preset_change(self):
        presets = {
            "Sensitive": {"lower": 20, "upper": 60},
            "Medium": {"lower": 30, "upper": 100},
            "Conservative": {"lower": 50, "upper": 150}
        }
        preset = self.canny_preset_var.get()
        if preset in presets:
            self.store_slider_values()
            self.canny_l_var.set(presets[preset]["lower"])
            self.canny_u_var.set(presets[preset]["upper"])
            self.canny_l_label.config(text=str(presets[preset]["lower"]))
            self.canny_u_label.config(text=str(presets[preset]["upper"]))
            self.on_param_change()
    
    def on_thickness_preset_change(self):
        presets = {"Thin": 1.0, "Medium": 2.5, "Thick": 6.0}
        preset = self.thickness_preset_var.get()
        if preset in presets:
            self.store_slider_values()
            self.thickness_var.set(presets[preset])
            self.thickness_label.config(text=str(presets[preset]))
            self.on_param_change()
    
    def on_gap_preset_change(self):
        presets = {"None": 0.0, "Light": 2.5, "Medium": 5.0, "Heavy": 10.0}
        preset = self.gap_preset_var.get()
        if preset in presets:
            self.store_slider_values()
            self.gap_var.set(presets[preset])
            self.gap_label.config(text=str(presets[preset]))
            self.on_param_change()
    
    def on_largest_preset_change(self):
        presets = {"Few": 3, "Medium": 10, "Many": 30}
        preset = self.largest_preset_var.get()
        if preset in presets:
            self.store_slider_values()
            self.largest_var.set(presets[preset])
            self.largest_label.config(text=str(presets[preset]))
            self.on_param_change()
    
    def on_simplify_preset_change(self):
        presets = {"Detailed": 0.2, "Medium": 0.5, "Simple": 1.0}
        preset = self.simplify_preset_var.get()
        if preset in presets:
            self.store_slider_values()
            self.simplify_var.set(presets[preset])
            self.simplify_label.config(text=str(presets[preset]))
            self.on_param_change()
    
    def on_scale_preset_change(self):
        presets = {"Small": 0.15, "Medium": 0.25, "Large": 1.0}
        preset = self.scale_preset_var.get()
        if preset in presets:
            self.store_slider_values()
            self.scale_var.set(presets[preset])
            self.scale_label.config(text=str(presets[preset]))
            self.on_param_change()
    
    def on_export_scale_change(self, event=None):
        """Update output size display when export scale changes"""
        if self.original_image is not None:
            try:
                scale = float(self.export_scale_var.get())
                if scale > 0:
                    h, w = self.original_image.shape[:2]
                    new_h = int(h * scale)
                    new_w = int(w * scale)
                    self.output_size_label.config(text=f"Output: {new_w}×{new_h}px")
                else:
                    self.output_size_label.config(text="Invalid scale")
            except ValueError:
                self.output_size_label.config(text="Invalid scale")
    
        
    def on_preset_change(self, event=None):
        preset = self.preset_var.get()
        if preset == "Custom":
            return

        config = self.preset_configs.get(preset)
        if not config:
            return

        # Store current values before applying preset
        self.store_slider_values()

        # Apply preset values directly to tkinter variables
        self.bilateral_d_var.set(config["bilateral_diameter"])
        self.bilateral_c_var.set(config["bilateral_sigma_color"])
        self.gaussian_var.set(config["gaussian_kernel_size"])
        self.canny_l_var.set(config["canny_lower_threshold"])
        self.canny_u_var.set(config["canny_upper_threshold"])
        self.thickness_var.set(config["edge_thickness"])
        self.gap_var.set(config["gap_threshold"])
        self.largest_var.set(config["largest_n"])
        self.simplify_var.set(config["simplify_pct"])
        self.scale_var.set(config["mm_per_px"])
        self.invert_var.set(config["invert"])

        # Update labels to reflect new values
        self.bilateral_d_label.config(text=str(config["bilateral_diameter"]))
        self.bilateral_c_label.config(text=str(config["bilateral_sigma_color"]))
        self.gaussian_label.config(text=str(config["gaussian_kernel_size"]))
        self.canny_l_label.config(text=str(config["canny_lower_threshold"]))
        self.canny_u_label.config(text=str(config["canny_upper_threshold"]))
        self.thickness_label.config(text=str(config["edge_thickness"]))
        self.gap_label.config(text=str(config["gap_threshold"]))
        self.largest_label.config(text=str(config["largest_n"]))
        self.simplify_label.config(text=str(config["simplify_pct"]))
        self.scale_label.config(text=str(config["mm_per_px"]))

        # Reset zoom/pan when preset changes
        self.zoom_reset()
        self.pan_reset()

        # Update preview
        self.update_preview()
        
    def export_dxf(self):
        if self.image_path is None:
            messagebox.showwarning("Warning", "No image loaded.")
            return
            
        # Validate export scale
        try:
            export_scale = float(self.export_scale_var.get())
            if export_scale <= 0:
                messagebox.showerror("Error", "Export scale must be greater than 0.")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid export scale value.")
            return

        self.show_loading("Preparing DXF export...")
        
        try:
            # Process contours with gap threshold for export
            export_contours = contours_from_mask(self.current_mask, 
                                               self.params["largest_n"], 
                                               self.params["simplify_pct"],
                                               self.params["gap_threshold"])
            
            # Filter out erased contours and add edited contours
            filtered_contours = []
            for i, contour in enumerate(export_contours):
                if i not in self.erased_contours:
                    filtered_contours.append(contour)
            
            # Add manually edited contours
            filtered_contours.extend(self.edited_contours)
            
            if not filtered_contours:
                messagebox.showwarning("Warning", "No contours found for export.")
                return
                
            # Get scaled dimensions for filename
            h, w = self.original_image.shape[:2]
            new_h, new_w = int(h * export_scale), int(w * export_scale)
            base_name = os.path.splitext(os.path.basename(self.image_path))[0]
            default_name = f"{base_name}_{new_w}x{new_h}.dxf"
            
            out_path = filedialog.asksaveasfilename(
                title="Save DXF as",
                defaultextension=".dxf",
                initialfile=default_name,
                filetypes=[("AutoCAD DXF", "*.dxf")],
            )
            
            if out_path:
                # Calculate the effective mm_per_px based on export scale
                # The scale slider controls the base mm_per_px, export scale multiplies the output size
                effective_mm_per_px = self.params["mm_per_px"] / export_scale
                
                export_dxf(filtered_contours, out_path, self.current_mask.shape[:2], 
                          effective_mm_per_px)
                messagebox.showinfo("Success", f"DXF saved to:\n{out_path}\nSize: {new_w}×{new_h}px")
                
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {str(e)}")
        finally:
            self.hide_loading()
    
    def run(self):
        self.root.mainloop()

# -------------------------
# Main
# -------------------------
def main():
    app = ImageEmbossGUI()
    app.run()

if __name__ == "__main__":
    main()
