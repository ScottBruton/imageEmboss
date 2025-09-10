import os
import sys
import cv2
import numpy as np
import ezdxf
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
        
        # Default parameters
        self.params = {
            "bilateral_diameter": 9,
            "bilateral_sigma_color": 75,
            "bilateral_sigma_space": 75,
            "gaussian_kernel_size": 5,
            "canny_lower_threshold": 50,
            "canny_upper_threshold": 150,
            "edge_thickness": 2,
            "gap_threshold": 5.0,
            "largest_n": 10,
            "simplify_pct": 0.5,
            "mm_per_px": 0.25,
            "invert": True  # Default to True to focus on subject
        }
        
        self.setup_ui()
        self.setup_drag_drop()
        self.setup_loading_overlay()
        
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Top frame for file selection
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(top_frame, text="Select Image", command=self.load_image).pack(side='left')
        self.status_label = ttk.Label(top_frame, text="No image loaded")
        self.status_label.pack(side='left', padx=(10, 0))
        
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
        
        self.dxf_canvas = Canvas(right_frame, bg='white')
        self.dxf_canvas.pack(fill='both', expand=True)
        
        # Bottom frame for controls
        bottom_frame = ttk.LabelFrame(main_frame, text="Parameters")
        bottom_frame.pack(fill='x', pady=(10, 0))
        
        # Preset dropdown
        preset_frame = ttk.Frame(bottom_frame)
        preset_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(preset_frame, text="Preset:").pack(side='left')
        self.preset_var = StringVar(value="Custom")
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, 
                                       values=["Custom", "People/Portraits", "Objects/Products", "Text/Logos", "Landscapes", "High Contrast"],
                                       state="readonly", width=15)
        self.preset_combo.pack(side='left', padx=(5, 0))
        self.preset_combo.bind('<<ComboboxSelected>>', self.on_preset_change)
        
        # Create sliders
        self.create_sliders(bottom_frame)
        
        # Export button
        export_frame = ttk.Frame(main_frame)
        export_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(export_frame, text="Export DXF", command=self.export_dxf).pack(side='right')
        
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
            self.status_label.config(text=f"Loaded: {os.path.basename(path)}")
            self.display_original_image()
            self.update_preview()
        else:
            messagebox.showerror("Error", "Could not read image.")
            
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
        bilateral_d_label = ttk.Label(bilateral_d_frame, text="Bilateral Diameter:", width=15)
        bilateral_d_label.pack(side='left')
        self.create_tooltip(bilateral_d_label, "Controls the neighborhood size for bilateral filtering. Larger values smooth more but may blur edges. Range: 5-15")
        
        self.bilateral_d_var = IntVar(value=9)
        self.bilateral_d_scale = ttk.Scale(bilateral_d_frame, from_=5, to=15, 
                                         variable=self.bilateral_d_var, orient='horizontal',
                                         command=self.on_param_change)
        self.bilateral_d_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.bilateral_d_label = ttk.Label(bilateral_d_frame, text="9")
        self.bilateral_d_label.pack(side='right', padx=(5, 0))
        
        # Bilateral Sigma Color
        bilateral_c_frame = ttk.Frame(parent)
        bilateral_c_frame.pack(fill='x', pady=2)
        bilateral_c_label = ttk.Label(bilateral_c_frame, text="Bilateral Color σ:", width=15)
        bilateral_c_label.pack(side='left')
        self.create_tooltip(bilateral_c_label, "Controls color similarity threshold for bilateral filtering. Higher values allow more color variation. Range: 10-200")
        
        self.bilateral_c_var = IntVar(value=75)
        self.bilateral_c_scale = ttk.Scale(bilateral_c_frame, from_=10, to=200, 
                                         variable=self.bilateral_c_var, orient='horizontal',
                                         command=self.on_param_change)
        self.bilateral_c_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.bilateral_c_label = ttk.Label(bilateral_c_frame, text="75")
        self.bilateral_c_label.pack(side='right', padx=(5, 0))
        
        # Gaussian Kernel Size
        gaussian_frame = ttk.Frame(parent)
        gaussian_frame.pack(fill='x', pady=2)
        gaussian_label = ttk.Label(gaussian_frame, text="Gaussian Kernel:", width=15)
        gaussian_label.pack(side='left')
        self.create_tooltip(gaussian_label, "Controls the amount of blur applied. Larger values create more smoothing. Must be odd numbers. Range: 3-15")
        
        self.gaussian_var = IntVar(value=5)
        self.gaussian_scale = ttk.Scale(gaussian_frame, from_=3, to=15, 
                                      variable=self.gaussian_var, orient='horizontal',
                                      command=self.on_param_change)
        self.gaussian_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.gaussian_label = ttk.Label(gaussian_frame, text="5")
        self.gaussian_label.pack(side='right', padx=(5, 0))
        
        # Canny Lower Threshold
        canny_l_frame = ttk.Frame(parent)
        canny_l_frame.pack(fill='x', pady=2)
        canny_l_label = ttk.Label(canny_l_frame, text="Canny Lower:", width=15)
        canny_l_label.pack(side='left')
        self.create_tooltip(canny_l_label, "Lower threshold for Canny edge detection. Lower values detect more edges but may include noise. Range: 10-200")
        
        self.canny_l_var = IntVar(value=50)
        self.canny_l_scale = ttk.Scale(canny_l_frame, from_=10, to=200, 
                                     variable=self.canny_l_var, orient='horizontal',
                                     command=self.on_param_change)
        self.canny_l_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.canny_l_label = ttk.Label(canny_l_frame, text="50")
        self.canny_l_label.pack(side='right', padx=(5, 0))
        
        # Canny Upper Threshold
        canny_u_frame = ttk.Frame(parent)
        canny_u_frame.pack(fill='x', pady=2)
        canny_u_label = ttk.Label(canny_u_frame, text="Canny Upper:", width=15)
        canny_u_label.pack(side='left')
        self.create_tooltip(canny_u_label, "Upper threshold for Canny edge detection. Should be 2-3x the lower threshold. Higher values detect only strong edges. Range: 50-300")
        
        self.canny_u_var = IntVar(value=150)
        self.canny_u_scale = ttk.Scale(canny_u_frame, from_=50, to=300, 
                                     variable=self.canny_u_var, orient='horizontal',
                                     command=self.on_param_change)
        self.canny_u_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.canny_u_label = ttk.Label(canny_u_frame, text="150")
        self.canny_u_label.pack(side='right', padx=(5, 0))
        
        # Edge Thickness
        thickness_frame = ttk.Frame(parent)
        thickness_frame.pack(fill='x', pady=2)
        thickness_label = ttk.Label(thickness_frame, text="Edge Thickness:", width=15)
        thickness_label.pack(side='left')
        self.create_tooltip(thickness_label, "Controls how thick the detected edges become. Higher values create bolder lines but may merge nearby edges. Range: 1.0-50.0")
        
        self.thickness_var = DoubleVar(value=2.0)
        self.thickness_scale = ttk.Scale(thickness_frame, from_=1.0, to=50.0, 
                                       variable=self.thickness_var, orient='horizontal',
                                       command=self.on_param_change)
        self.thickness_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.thickness_label = ttk.Label(thickness_frame, text="2.0")
        self.thickness_label.pack(side='right', padx=(5, 0))
        
        # Gap Threshold slider
        gap_frame = ttk.Frame(parent)
        gap_frame.pack(fill='x', pady=2)
        gap_label = ttk.Label(gap_frame, text="Gap Threshold:", width=15)
        gap_label.pack(side='left')
        self.create_tooltip(gap_label, "Converts small gaps between contour segments into continuous lines. Higher values connect more segments. Range: 0-20 pixels")
        
        self.gap_var = DoubleVar(value=5.0)
        self.gap_scale = ttk.Scale(gap_frame, from_=0.0, to=20.0, 
                                 variable=self.gap_var, orient='horizontal',
                                 command=self.on_param_change)
        self.gap_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.gap_label = ttk.Label(gap_frame, text="5.0")
        self.gap_label.pack(side='right', padx=(5, 0))
        
        # Largest N slider
        largest_frame = ttk.Frame(parent)
        largest_frame.pack(fill='x', pady=2)
        largest_label = ttk.Label(largest_frame, text="Largest N:", width=15)
        largest_label.pack(side='left')
        self.create_tooltip(largest_label, "Number of largest contours to keep. Use 1-3 for bold silhouettes, higher values for detailed images. Range: 1-50")
        
        self.largest_var = IntVar(value=10)
        self.largest_scale = ttk.Scale(largest_frame, from_=1, to=50, 
                                     variable=self.largest_var, orient='horizontal',
                                     command=self.on_param_change)
        self.largest_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.largest_label = ttk.Label(largest_frame, text="10")
        self.largest_label.pack(side='right', padx=(5, 0))
        
        # Simplify slider
        simplify_frame = ttk.Frame(parent)
        simplify_frame.pack(fill='x', pady=2)
        simplify_label = ttk.Label(simplify_frame, text="Simplify %:", width=15)
        simplify_label.pack(side='left')
        self.create_tooltip(simplify_label, "Reduces the number of points in contours. Higher values create simpler shapes but may lose detail. Range: 0.0-2.0%")
        
        self.simplify_var = DoubleVar(value=0.5)
        self.simplify_scale = ttk.Scale(simplify_frame, from_=0.0, to=2.0, 
                                      variable=self.simplify_var, orient='horizontal',
                                      command=self.on_param_change)
        self.simplify_scale.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.simplify_label = ttk.Label(simplify_frame, text="0.5")
        self.simplify_label.pack(side='right', padx=(5, 0))
        
        # Scale slider
        scale_frame = ttk.Frame(parent)
        scale_frame.pack(fill='x', pady=2)
        scale_label = ttk.Label(scale_frame, text="Scale (mm/px):", width=15)
        scale_label.pack(side='left')
        self.create_tooltip(scale_label, "Converts pixels to millimeters in the DXF output. 0.25 means 1 pixel = 0.25mm. Range: 0.01-2.0")
        
        self.scale_var = DoubleVar(value=0.25)
        self.scale_scale = ttk.Scale(scale_frame, from_=0.01, to=2.0, 
                                   variable=self.scale_var, orient='horizontal',
                                   command=self.on_param_change)
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
            
        # Clear canvas
        self.dxf_canvas.delete("all")
        
        # Get canvas dimensions
        canvas_width = self.dxf_canvas.winfo_width()
        canvas_height = self.dxf_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
            
        # Calculate scale to fit contours in canvas
        h, w = self.original_image.shape[:2]
        scale = min(canvas_width/w, canvas_height/h, 1.0) * 0.9
        
        # Check if we have meaningful contours (not just noise)
        meaningful_contours = []
        for contour in self.current_contours:
            # Filter out very small contours (likely noise)
            area = cv2.contourArea(contour)
            if area > 100:  # Minimum area threshold
                meaningful_contours.append(contour)
        
        # Draw contours with different colors based on whether they're meaningful
        for i, contour in enumerate(self.current_contours):
            points = []
            for point in contour:
                x = float(point[0][0]) * scale + canvas_width//2 - w*scale//2
                y = float(point[0][1]) * scale + canvas_height//2 - h*scale//2
                points.extend([x, y])
            
            if len(points) >= 6:  # At least 3 points (x,y pairs)
                # Use dark green for meaningful contours, red for noise/small contours
                area = cv2.contourArea(contour)
                color = 'dark green' if area > 100 else 'red'
                self.dxf_canvas.create_polygon(points, outline=color, fill='', width=2)
    
    def on_param_change(self, event=None):
        # Set preset to Custom when user manually changes parameters
        if self.preset_var.get() != "Custom":
            self.preset_var.set("Custom")
        self.update_preview()
        
    def on_preset_change(self, event=None):
        preset = self.preset_var.get()
        if preset == "Custom":
            return
            
        # Define presets - optimized for actual detection
        presets = {
            "People/Portraits": {
                "bilateral_diameter": 9,
                "bilateral_sigma_color": 75,
                "gaussian_kernel_size": 5,
                "canny_lower_threshold": 20,
                "canny_upper_threshold": 60,
                "edge_thickness": 2.0,
                "gap_threshold": 3.0,
                "largest_n": 5,
                "simplify_pct": 0.3,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Objects/Products": {
                "bilateral_diameter": 7,
                "bilateral_sigma_color": 50,
                "gaussian_kernel_size": 3,
                "canny_lower_threshold": 15,
                "canny_upper_threshold": 45,
                "edge_thickness": 1.5,
                "gap_threshold": 2.0,
                "largest_n": 8,
                "simplify_pct": 0.2,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Text/Logos": {
                "bilateral_diameter": 5,
                "bilateral_sigma_color": 30,
                "gaussian_kernel_size": 3,
                "canny_lower_threshold": 10,
                "canny_upper_threshold": 30,
                "edge_thickness": 1.0,
                "gap_threshold": 1.0,
                "largest_n": 4,
                "simplify_pct": 0.1,
                "mm_per_px": 0.25,
                "invert": True
            },
            "Landscapes": {
                "bilateral_diameter": 11,
                "bilateral_sigma_color": 80,
                "gaussian_kernel_size": 7,
                "canny_lower_threshold": 25,
                "canny_upper_threshold": 75,
                "edge_thickness": 2.5,
                "gap_threshold": 4.0,
                "largest_n": 10,
                "simplify_pct": 0.4,
                "mm_per_px": 0.25,
                "invert": True
            },
            "High Contrast": {
                "bilateral_diameter": 9,
                "bilateral_sigma_color": 60,
                "gaussian_kernel_size": 5,
                "canny_lower_threshold": 30,
                "canny_upper_threshold": 90,
                "edge_thickness": 3.0,
                "gap_threshold": 5.0,
                "largest_n": 3,
                "simplify_pct": 0.6,
                "mm_per_px": 0.25,
                "invert": True
            }
        }
        
        if preset in presets:
            # Update all sliders with preset values
            preset_params = presets[preset]
            self.bilateral_d_var.set(preset_params["bilateral_diameter"])
            self.bilateral_c_var.set(preset_params["bilateral_sigma_color"])
            self.gaussian_var.set(preset_params["gaussian_kernel_size"])
            self.canny_l_var.set(preset_params["canny_lower_threshold"])
            self.canny_u_var.set(preset_params["canny_upper_threshold"])
            self.thickness_var.set(preset_params["edge_thickness"])
            self.gap_var.set(preset_params["gap_threshold"])
            self.largest_var.set(preset_params["largest_n"])
            self.simplify_var.set(preset_params["simplify_pct"])
            self.scale_var.set(preset_params["mm_per_px"])
            self.invert_var.set(preset_params["invert"])
            
            # Update preview
            self.update_preview()
        
    def export_dxf(self):
        if self.image_path is None:
            messagebox.showwarning("Warning", "No image loaded.")
            return
            
        self.show_loading("Preparing DXF export...")
        
        try:
            # Process contours with gap threshold for export
            export_contours = contours_from_mask(self.current_mask, 
                                               self.params["largest_n"], 
                                               self.params["simplify_pct"],
                                               self.params["gap_threshold"])
            
            if not export_contours:
                messagebox.showwarning("Warning", "No contours found for export.")
                return
                
            default_name = os.path.splitext(os.path.basename(self.image_path))[0] + "_silhouette.dxf"
            out_path = filedialog.asksaveasfilename(
                title="Save DXF as",
                defaultextension=".dxf",
                initialfile=default_name,
                filetypes=[("AutoCAD DXF", "*.dxf")],
            )
            
            if out_path:
                export_dxf(export_contours, out_path, self.current_mask.shape[:2], 
                          self.params["mm_per_px"])
                messagebox.showinfo("Success", f"DXF saved to:\n{out_path}")
                
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
