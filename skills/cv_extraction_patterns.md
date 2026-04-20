# Skill: CV Extraction Patterns

OpenCV and scikit-image recipes for extracting geometric data from nature images, organized by biomimicry category.

## When to Use
When implementing or modifying the CV extraction pipeline. Each category has a specific extraction strategy that feeds into 3D generation.

## General Preprocessing (all categories)

```python
import cv2
import numpy as np
from skimage import filters, morphology, measure, feature

def preprocess(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Normalize contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    # Denoise
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
    return img, gray, denoised
```

## Category: Cellular (Voronoi, Honeycomb, Foam)

**Goal**: Extract cell centers (seed points) + cell boundaries

```python
def extract_cellular(denoised):
    # Edge detection for cell walls
    edges = cv2.Canny(denoised, 50, 150)

    # Find contours (cell boundaries)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Cell centers = centroids of contours
    seed_points = []
    for cnt in contours:
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            seed_points.append((cx, cy))

    # Average cell size
    areas = [cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 50]
    avg_cell_size = np.mean(areas) if areas else 0

    return {
        "seed_points": seed_points,
        "contours": contours,
        "avg_cell_size": avg_cell_size,
        "cell_count": len(seed_points),
    }
```

**Feeds into**: Voronoi diagram → mesh panels in rhino3dm

## Category: Branching (Fractal, Vascular, Dendritic)

**Goal**: Extract skeleton (centerlines) + branching points + branch angles

```python
from skimage.morphology import skeletonize

def extract_branching(denoised):
    # Threshold to binary
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Skeletonize
    skeleton = skeletonize(binary // 255).astype(np.uint8) * 255

    # Find branch points (pixels with >2 neighbors)
    kernel = np.ones((3, 3), dtype=np.uint8)
    neighbor_count = cv2.filter2D(skeleton // 255, -1, kernel) * (skeleton // 255)
    branch_points = np.argwhere(neighbor_count > 3)  # >2 neighbors + self

    # Find endpoints (pixels with exactly 1 neighbor)
    endpoints = np.argwhere(neighbor_count == 2)

    # Extract branch segments as polylines
    # Use cv2.findContours on skeleton for connected segments
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    return {
        "skeleton": skeleton,
        "branch_points": branch_points.tolist(),
        "endpoints": endpoints.tolist(),
        "segments": contours,
        "branch_count": len(branch_points),
    }
```

**Feeds into**: Curve network → structural columns/beams in rhino3dm

## Category: Shell/Surface (Curvature, Folding, Minimal Surfaces)

**Goal**: Extract height/depth map + curvature values

```python
def extract_shell(denoised):
    # Gradient magnitude as proxy for surface slope
    grad_x = cv2.Sobel(denoised, cv2.CV_64F, 1, 0, ksize=5)
    grad_y = cv2.Sobel(denoised, cv2.CV_64F, 0, 1, ksize=5)
    gradient_mag = np.sqrt(grad_x**2 + grad_y**2)

    # Intensity as height map (lighter = higher)
    height_map = denoised.astype(np.float64) / 255.0

    # Gaussian curvature approximation
    blurred = cv2.GaussianBlur(height_map, (0, 0), sigmaX=3)
    laplacian = cv2.Laplacian(blurred, cv2.CV_64F)

    # Sample control points on a grid
    h, w = height_map.shape
    grid_size = 20
    control_points = []
    for i in range(0, h, h // grid_size):
        row = []
        for j in range(0, w, w // grid_size):
            row.append((j, i, float(height_map[i, j])))
        control_points.append(row)

    return {
        "height_map": height_map,
        "curvature_map": laplacian,
        "gradient_magnitude": gradient_mag,
        "control_points": control_points,
    }
```

**Feeds into**: NURBS surface with Z-displacement in rhino3dm

## Category: Lattice/Grid (Woven, Interlocking, Tessellation)

**Goal**: Extract grid lines + intersection points + cell shapes

```python
def extract_lattice(denoised):
    # Line detection via Hough transform
    edges = cv2.Canny(denoised, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                             minLineLength=30, maxLineGap=10)

    # Detect dominant angles (grid orientation)
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1)
            angles.append(angle)

    # Cluster angles to find grid directions
    angles = np.array(angles)
    # Simple: find 2 dominant angle clusters
    hist, bin_edges = np.histogram(angles, bins=36)
    dominant_angles = bin_edges[np.argsort(hist)[-2:]]

    # Find intersections
    intersections = []
    if lines is not None:
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                pt = line_intersection(lines[i][0], lines[j][0])
                if pt is not None:
                    intersections.append(pt)

    return {
        "lines": lines.tolist() if lines is not None else [],
        "dominant_angles": dominant_angles.tolist(),
        "intersections": intersections,
        "line_count": len(lines) if lines is not None else 0,
    }

def line_intersection(line1, line2):
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-6:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    px = x1 + t * (x2 - x1)
    py = y1 + t * (y2 - y1)
    return (px, py)
```

**Feeds into**: Polyline grid + mesh infill in rhino3dm

## Category: Spiral (Fibonacci, Helical, Growth)

**Goal**: Extract spiral center + arm count + growth rate

```python
def extract_spiral(denoised):
    # Edge detection
    edges = cv2.Canny(denoised, 30, 100)

    # Find center of spiral (likely center of mass of edges)
    M = cv2.moments(edges)
    if M["m00"] > 0:
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
    else:
        h, w = edges.shape
        center = (w // 2, h // 2)

    # Radial profile — sample intensity along radial lines from center
    num_radials = 360
    max_radius = min(edges.shape) // 2
    radial_profile = []
    for angle_deg in range(num_radials):
        angle = np.radians(angle_deg)
        for r in range(1, max_radius):
            x = int(center[0] + r * np.cos(angle))
            y = int(center[1] + r * np.sin(angle))
            if 0 <= x < edges.shape[1] and 0 <= y < edges.shape[0]:
                if edges[y, x] > 0:
                    radial_profile.append((angle_deg, r))
                    break

    # Estimate spiral arm count via angular periodicity
    if radial_profile:
        angles_at_edge = [rp[0] for rp in radial_profile]
        # FFT on angular distribution to find dominant frequency
        hist, _ = np.histogram(angles_at_edge, bins=360)
        fft = np.fft.fft(hist)
        freqs = np.fft.fftfreq(len(hist))
        dominant_freq = freqs[np.argmax(np.abs(fft[1:])) + 1]
        arm_count = max(1, int(round(abs(1.0 / dominant_freq)))) if dominant_freq != 0 else 1
    else:
        arm_count = 1

    return {
        "center": center,
        "arm_count": arm_count,
        "radial_profile": radial_profile,
        "max_radius": max_radius,
    }
```

**Feeds into**: Helical curves with fibonacci spacing in rhino3dm

## Category: Porous (Perforated, Gradient Density)

**Goal**: Extract hole positions + sizes + density gradient

```python
def extract_porous(denoised):
    # Threshold to find holes (dark regions)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    # Find hole contours
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    holes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 20:
            continue
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            radius = np.sqrt(area / np.pi)
            holes.append({"center": (cx, cy), "radius": float(radius), "area": float(area)})

    # Density gradient — divide image into grid, count holes per cell
    h, w = denoised.shape
    grid_n = 8
    density_map = np.zeros((grid_n, grid_n))
    for hole in holes:
        gx = min(int(hole["center"][0] / w * grid_n), grid_n - 1)
        gy = min(int(hole["center"][1] / h * grid_n), grid_n - 1)
        density_map[gy, gx] += 1

    return {
        "holes": holes,
        "hole_count": len(holes),
        "density_map": density_map.tolist(),
        "avg_hole_radius": np.mean([h["radius"] for h in holes]) if holes else 0,
    }
```

**Feeds into**: Mesh surface with boolean-subtracted circles/polygons in rhino3dm

## Output Format

All extraction functions return a dict. The generation pipeline expects:
```python
{
    "category": "cellular",       # detected category
    "confidence": 0.85,           # from LLM classification
    "extraction_data": { ... },   # category-specific data from above
    "image_dimensions": (w, h),   # original image size
    "normalized": True,           # whether coordinates are 0-1 normalized
}
```
