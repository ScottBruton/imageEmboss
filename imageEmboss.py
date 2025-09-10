import cv2, ezdxf

# Load silhouette
img = cv2.imread("wedding_silhouette.png", cv2.IMREAD_GRAYSCALE)
_, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

doc = ezdxf.new()
msp = doc.modelspace()
for cnt in contours:
    points = [(float(p[0][0]), float(p[0][1])) for p in cnt]
    if len(points) > 2:
        msp.add_lwpolyline(points, close=True)

doc.saveas("wedding_silhouette.dxf")
