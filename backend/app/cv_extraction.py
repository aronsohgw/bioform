"""CV extraction pipeline for biomimicry pattern analysis.

Two-mode essence extraction:
  - Object mode: isolate foreground via GrabCut, extract pattern from object only
  - Pattern mode: pattern fills the frame, extract dominant structure ignoring noise

Simplification-first approach: bilateral filter to smooth noise while preserving
main boundaries, then extract clean contours + structural skeleton.

Features are tagged with hierarchy levels:
  0 = primary   (dominant features — shown at ground floor)
  1 = secondary  (medium detail — appears on mid floors)
  2 = tertiary   (fine detail — appears on upper floors)
"""
import cv2
import numpy as np
from skimage.morphology import skeletonize

# Max dimension for extraction
_MAX_EXTRACT_DIM = 1024
# Feature caps
_MAX_CONTOURS = 150
_MAX_PATHS = 90
_MAX_LINES = 200
_MAX_HOLES = 150


# ─── Preprocessing ───

def _assess_image_quality(gray: np.ndarray) -> dict:
    """Assess image quality to adapt preprocessing."""
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = float(lap.var())
    contrast = float(gray.std())
    noise = float(np.median(np.abs(lap - np.median(lap))))
    return {"sharpness": sharpness, "contrast": contrast, "noise": noise}


def preprocess(image_path: str):
    """Load and preprocess image. Adapts denoising to image quality.

    Returns: (color_img, grayscale, denoised)
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    quality = _assess_image_quality(gray)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    if quality["noise"] < 8.0:
        h = 3
    elif quality["noise"] < 20.0:
        h = 7
    else:
        h = 14
    denoised = cv2.fastNlMeansDenoising(enhanced, h=h)
    return img, gray, denoised


# ─── Mode Detection ───

def detect_mode(gray: np.ndarray) -> str:
    """Auto-detect whether image shows an object or a pattern filling the frame.

    Compares edge density in center 50% vs outer ring.
    If center is much denser → object against background.
    If edges are distributed → pattern fills the frame.
    """
    edges = cv2.Canny(gray, 30, 100)
    h, w = edges.shape
    # Center 50% region
    ch, cw = h // 4, w // 4
    center = edges[ch:h - ch, cw:w - cw]
    # Outer ring (full image minus center)
    total_edge_pixels = np.count_nonzero(edges)
    center_edge_pixels = np.count_nonzero(center)
    outer_edge_pixels = total_edge_pixels - center_edge_pixels

    center_area = center.shape[0] * center.shape[1]
    outer_area = h * w - center_area

    if outer_area == 0 or center_area == 0:
        return "pattern"

    center_density = center_edge_pixels / center_area
    outer_density = outer_edge_pixels / outer_area

    if outer_density > 0 and center_density / outer_density > 2.0:
        return "object"
    return "pattern"


# ─── GrabCut Segmentation ───

def _grabcut_mask(color_img: np.ndarray) -> np.ndarray:
    """Isolate foreground object using GrabCut. Returns binary mask (0/255)."""
    h, w = color_img.shape[:2]
    # Initialize rect at center 80% of image
    margin_x, margin_y = w // 10, h // 10
    rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

    mask = np.zeros((h, w), np.uint8)
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)

    cv2.grabCut(color_img, mask, rect, bg_model, fg_model, 5, cv2.GC_INIT_WITH_RECT)

    # Convert mask: probable/definite foreground → 255, else → 0
    result = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    return result


# ─── Simplification ───

def _simplify(gray: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
    """Edge-preserving simplification using bilateral filter.

    Smooths noise and fine detail while preserving main structural boundaries.
    Optionally applies a foreground mask (object mode).
    """
    if mask is not None:
        gray = cv2.bitwise_and(gray, gray, mask=mask)

    # Bilateral filter: moderate smoothing — preserves edges, removes noise
    # sigmaColor=50 (not 75) keeps more contrast between adjacent features
    simplified = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)

    # Light morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    simplified = cv2.morphologyEx(simplified, cv2.MORPH_CLOSE, kernel)

    return simplified


def _downscale(img):
    """Downscale image for extraction. Returns (scaled_image, scale_factor)."""
    h, w = img.shape[:2] if len(img.shape) == 3 else img.shape
    if max(h, w) <= _MAX_EXTRACT_DIM:
        return img, 1.0
    scale = _MAX_EXTRACT_DIM / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    scaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return scaled, scale


def prepare_for_extraction(color_img, gray, denoised, mode="pattern"):
    """Prepare image for extraction: apply GrabCut mask if object mode, then simplify."""
    img, scale = _downscale(denoised)
    mask = None
    if mode == "object" and color_img is not None:
        color_scaled, _ = _downscale(color_img)
        mask = _grabcut_mask(color_scaled)
    simplified = _simplify(img, mask)
    return simplified, scale, mask


# ─── Shared Contour Extraction ───

def _extract_contours(simplified, top_n=40, epsilon_ratio=0.025, min_area_ratio=0.0001):
    """Extract clean contours from simplified image using dual threshold.

    Uses both adaptive and Otsu thresholds to catch features at different
    contrast levels, then deduplicates. Polygon approximation with moderate
    epsilon for smooth-but-detailed curves.
    Returns list of {points, center, area, hierarchy, quality}.
    """
    h, w = simplified.shape
    img_area = h * w
    min_area = img_area * min_area_ratio

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    # Use Canny edge detection → find contours from edges
    # This finds individual feature boundaries without merging them
    edges = cv2.Canny(simplified, 30, 100)
    edges = cv2.dilate(edges, kernel, iterations=1)  # close small gaps in edges

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    results = []
    seen = set()
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        M = cv2.moments(cnt)
        if M["m00"] <= 0:
            continue
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        # Deduplicate by center proximity
        key = (cx // 5, cy // 5)
        if key in seen:
            continue
        seen.add(key)

        # Moderate epsilon — smooth but retains enough shape
        epsilon = epsilon_ratio * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        pts = [(int(p[0][0]), int(p[0][1])) for p in approx]
        if len(pts) < 3:
            continue

        results.append({
            "points": pts,
            "center": (cx, cy),
            "area": float(area),
            "hierarchy": 0,
            "quality": float(area / img_area),
        })

    # Sort by area descending
    results.sort(key=lambda c: -c["area"])

    # Assign hierarchy by rank: top third = 0, middle = 1, bottom = 2
    n = len(results)
    for i, r in enumerate(results):
        if i < n // 3:
            r["hierarchy"] = 0
        elif i < 2 * n // 3:
            r["hierarchy"] = 1
        else:
            r["hierarchy"] = 2
        r["quality"] = max(0.1, 1.0 - i / max(n, 1))

    return results[:top_n]


# ─── Shared Skeleton Extraction ───

def _extract_skeleton(simplified, min_length_ratio=0.05):
    """Extract structural skeleton paths from simplified image.

    Discards short paths (noise). Returns significant structural paths
    with hierarchy and quality.
    """
    h, w = simplified.shape
    diag = np.sqrt(h ** 2 + w ** 2)
    min_path_len = diag * min_length_ratio

    _, binary = cv2.threshold(simplified, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    skeleton = skeletonize(binary // 255).astype(np.uint8)

    kern3 = np.ones((3, 3), dtype=np.uint8)
    neighbor_count = cv2.filter2D(skeleton, -1, kern3) * skeleton
    junction_mask = neighbor_count > 3
    endpoint_mask = neighbor_count == 2

    raw_paths = _trace_skeleton_paths(skeleton, junction_mask, endpoint_mask, h, w)

    # Filter by minimum length and assign hierarchy
    tagged = []
    if raw_paths:
        lengths = [len(p) for p in raw_paths]
        max_len = max(lengths)
        for p, plen in zip(raw_paths, lengths):
            if plen < min_path_len:
                continue
            # Hierarchy: long=primary, medium=secondary, short=tertiary
            if plen > max_len * 0.4:
                hier = 0
            elif plen > max_len * 0.15:
                hier = 1
            else:
                hier = 2
            quality = min(1.0, plen / max(max_len, 1)) * (1.0 - hier * 0.2)
            tagged.append({
                "points": [(int(r), int(c)) for r, c in p],
                "hierarchy": hier,
                "length": plen,
                "quality": float(quality),
            })

    tagged.sort(key=lambda p: -p["quality"])
    return tagged[:_MAX_PATHS]


def _trace_skeleton_paths(skeleton, junction_mask, endpoint_mask, h, w):
    """Trace skeleton into polyline paths between junction/endpoint nodes."""
    visited = np.zeros_like(skeleton, dtype=bool)
    node_mask = junction_mask | endpoint_mask
    paths = []

    offsets = [(-1, -1), (-1, 0), (-1, 1),
               (0, -1),          (0, 1),
               (1, -1),  (1, 0), (1, 1)]

    node_positions = np.argwhere(node_mask)
    if len(node_positions) > 600:
        kern3 = np.ones((3, 3), dtype=np.uint8)
        nc = cv2.filter2D(skeleton, -1, kern3)
        scores = np.array([nc[r, c] for r, c in node_positions])
        top_indices = np.argsort(-scores)[:600]
        node_positions = node_positions[top_indices]

    for nr, nc in node_positions:
        for dr, dc in offsets:
            r, c = nr + dr, nc + dc
            if r < 0 or r >= h or c < 0 or c >= w:
                continue
            if skeleton[r, c] == 0 or visited[r, c]:
                continue
            if node_mask[r, c]:
                paths.append([(int(nr), int(nc)), (int(r), int(c))])
                continue

            path = [(int(nr), int(nc))]
            cr, cc = r, c
            max_walk = 3000
            steps = 0
            while steps < max_walk:
                steps += 1
                visited[cr, cc] = True
                path.append((int(cr), int(cc)))
                if node_mask[cr, cc]:
                    break
                found = False
                for dr2, dc2 in offsets:
                    nr2, nc2 = cr + dr2, cc + dc2
                    if nr2 < 0 or nr2 >= h or nc2 < 0 or nc2 >= w:
                        continue
                    if skeleton[nr2, nc2] == 0:
                        continue
                    if visited[nr2, nc2] and not node_mask[nr2, nc2]:
                        continue
                    if len(path) >= 2 and nr2 == path[-2][0] and nc2 == path[-2][1]:
                        continue
                    cr, cc = nr2, nc2
                    found = True
                    break
                if not found:
                    break

            if len(path) >= 2:
                paths.append(path)

        if len(paths) >= _MAX_PATHS * 3:
            break

    # Deduplicate
    seen = set()
    unique = []
    for p in paths:
        key = (p[0][0], p[0][1], p[-1][0], p[-1][1])
        key_rev = (p[-1][0], p[-1][1], p[0][0], p[0][1])
        if key not in seen and key_rev not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _score_feature(area, hierarchy, cx, cy, img_w, img_h):
    """Score a feature 0-1 for quality/importance."""
    area_score = min(1.0, np.log1p(area) / 12.0)
    hier_score = 1.0 - hierarchy * 0.25
    if img_w > 0 and img_h > 0:
        dx = (cx / img_w - 0.5) * 2
        dy = (cy / img_h - 0.5) * 2
        centrality = max(0.0, 1.0 - (dx * dx + dy * dy) ** 0.5)
    else:
        centrality = 0.5
    return float(area_score * 0.4 + hier_score * 0.35 + centrality * 0.25)


# ─── Category Extractors ───
# Each uses the shared simplification pipeline then adapts output.

def extract_cellular(denoised: np.ndarray, mode="pattern", color_img=None) -> dict:
    """Extract cell boundaries as clean contours from simplified image."""
    orig_h, orig_w = denoised.shape
    simplified, scale, mask = prepare_for_extraction(
        color_img, None, denoised, mode)

    contours = _extract_contours(simplified, top_n=50, epsilon_ratio=0.02)

    # Scale contour coordinates back to original size
    seed_points = []
    cell_boundaries = []
    for c in contours:
        ox = int(c["center"][0] / scale)
        oy = int(c["center"][1] / scale)
        o_area = c["area"] / (scale * scale)
        pts = [(int(p[0] / scale), int(p[1] / scale)) for p in c["points"]]

        seed_points.append({
            "center": (ox, oy), "area": float(o_area),
            "hierarchy": c["hierarchy"], "quality": c["quality"],
        })
        if len(pts) >= 3:
            cell_boundaries.append({
                "points": pts, "center": (ox, oy),
                "area": float(o_area), "hierarchy": c["hierarchy"],
                "quality": c["quality"],
            })

    flat_seeds = [sp["center"] for sp in seed_points]
    areas = [sp["area"] for sp in seed_points if sp["area"] > 50]

    return {
        "seed_points": flat_seeds,
        "seed_points_hierarchical": seed_points,
        "cell_boundaries": cell_boundaries,
        "avg_cell_size": float(np.mean(areas)) if areas else 0.0,
        "cell_count": len(flat_seeds),
    }


def extract_branching(denoised: np.ndarray, mode="pattern", color_img=None) -> dict:
    """Extract branching skeleton paths from simplified image."""
    orig_h, orig_w = denoised.shape
    simplified, scale, mask = prepare_for_extraction(
        color_img, None, denoised, mode)

    # Primary: skeleton paths
    paths = _extract_skeleton(simplified, min_length_ratio=0.03)

    # Scale coordinates back
    tagged_paths = []
    for p in paths:
        scaled_pts = [(int(r / scale), int(c / scale)) for r, c in p["points"]]
        tagged_paths.append({
            "points": scaled_pts, "hierarchy": p["hierarchy"],
            "length": p["length"], "quality": p["quality"],
        })

    # Secondary: contours for branch point estimation
    contours = _extract_contours(simplified, top_n=20, epsilon_ratio=0.03)

    # Estimate branch points from skeleton junction locations
    h, w = simplified.shape
    _, binary = cv2.threshold(simplified, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    skeleton = skeletonize(binary // 255).astype(np.uint8)
    kern3 = np.ones((3, 3), dtype=np.uint8)
    nc = cv2.filter2D(skeleton, -1, kern3) * skeleton
    branch_points = np.argwhere(nc > 3)
    endpoints = np.argwhere(nc == 2)

    bp_scaled = [(int(r / scale), int(c / scale)) for r, c in branch_points[:200]]
    ep_scaled = [(int(r / scale), int(c / scale)) for r, c in endpoints[:100]]

    return {
        "branch_points": bp_scaled,
        "endpoints": ep_scaled,
        "branch_count": len(bp_scaled),
        "paths": tagged_paths,
    }


def extract_shell(denoised: np.ndarray, mode="pattern", color_img=None) -> dict:
    """Extract height map with curvature from bilateral-filtered surface."""
    orig_h, orig_w = denoised.shape
    height_map = denoised.astype(np.float64) / 255.0

    # Bilateral filter on height map for smooth surface
    height_filtered = cv2.bilateralFilter(
        (height_map * 255).astype(np.uint8), d=9, sigmaColor=75, sigmaSpace=75
    ).astype(np.float64) / 255.0

    # Multi-scale curvature
    curvatures = []
    for sigma in [3, 7, 15]:
        blurred = cv2.GaussianBlur(height_filtered, (0, 0), sigmaX=sigma)
        lap = cv2.Laplacian(blurred, cv2.CV_64F)
        sx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
        curv = np.abs(lap) + np.sqrt(sx ** 2 + sy ** 2) * 0.5
        curvatures.append(curv)

    # Sample on 32-point grid
    grid_size = 32
    step_h = max(1, orig_h // min(grid_size, orig_h))
    step_w = max(1, orig_w // min(grid_size, orig_w))

    control_points = []
    for i in range(0, orig_h, step_h):
        row = []
        for j in range(0, orig_w, step_w):
            height_val = float(height_filtered[i, j])
            curv_fine = float(curvatures[0][i, j])
            curv_medium = float(curvatures[1][i, j])
            curv_coarse = float(curvatures[2][i, j])
            total_curv = curv_fine * 0.5 + curv_medium * 0.3 + curv_coarse * 0.2

            if curv_coarse > curv_fine and curv_coarse > curv_medium:
                hier = 0
            elif curv_medium > curv_fine:
                hier = 1
            else:
                hier = 2
            row.append((j, i, height_val, float(total_curv), hier))
        control_points.append(row)

    return {"control_points": control_points}


def extract_lattice(denoised: np.ndarray, mode="pattern", color_img=None) -> dict:
    """Extract grid lines from simplified image — much cleaner than raw edges."""
    orig_h, orig_w = denoised.shape
    simplified, scale, mask = prepare_for_extraction(
        color_img, None, denoised, mode)
    h, w = simplified.shape
    diag = np.sqrt(h ** 2 + w ** 2)

    # HoughLinesP on simplified image — far fewer noise lines
    edges = cv2.Canny(simplified, 50, 150)
    detected = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30,
                                minLineLength=max(15, int(diag * 0.04)),
                                maxLineGap=12)

    all_lines = []
    seen = set()
    all_angles = []

    if detected is not None:
        for line in detected:
            x1, y1, x2, y2 = line[0]
            key = (x1 // 3, y1 // 3, x2 // 3, y2 // 3)
            key_rev = (x2 // 3, y2 // 3, x1 // 3, y1 // 3)
            if key in seen or key_rev in seen:
                continue
            seen.add(key)
            ox1, oy1 = int(x1 / scale), int(y1 / scale)
            ox2, oy2 = int(x2 / scale), int(y2 / scale)
            length = float(np.sqrt((ox2 - ox1) ** 2 + (oy2 - oy1) ** 2))
            angle = float(np.arctan2(oy2 - oy1, ox2 - ox1))
            quality = _score_feature(length * 10, 0, (ox1 + ox2) / 2,
                                     (oy1 + oy2) / 2, orig_w, orig_h)
            all_lines.append({
                "coords": [ox1, oy1, ox2, oy2],
                "length": length, "angle": angle,
                "hierarchy": 0, "quality": quality,
            })
            all_angles.append(angle)
            if len(all_lines) >= _MAX_LINES:
                break

    # Angle clustering: keep top 3 angle families
    dominant_angles = []
    if all_angles:
        bin_width = np.radians(10)
        bins = max(1, int(np.pi / bin_width))
        hist, bin_edges = np.histogram(np.array(all_angles), bins=bins)
        top_bins = np.argsort(hist)[-3:]
        dominant_angles = [float(bin_edges[b] + bin_width / 2) for b in top_bins if hist[b] > 0]

    # Assign hierarchy by line length
    if all_lines:
        max_len = max(l["length"] for l in all_lines)
        for l in all_lines:
            ratio = l["length"] / max(max_len, 1)
            l["hierarchy"] = 0 if ratio > 0.5 else (1 if ratio > 0.2 else 2)

    all_lines.sort(key=lambda l: -l["quality"])
    all_lines = all_lines[:_MAX_LINES]

    # Intersections from primary lines
    primary = [l["coords"] for l in all_lines if l["hierarchy"] == 0]
    intersections = []
    for i in range(min(len(primary), 40)):
        for j in range(i + 1, min(len(primary), 40)):
            pt = _line_intersection(primary[i], primary[j])
            if pt is not None:
                intersections.append(pt)

    flat_lines = [l["coords"] for l in all_lines]

    return {
        "lines": flat_lines,
        "lines_hierarchical": all_lines,
        "dominant_angles": dominant_angles,
        "intersections": intersections,
        "line_count": len(all_lines),
    }


def _line_intersection(line1, line2):
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-6:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    px = x1 + t * (x2 - x1)
    py = y1 + t * (y2 - y1)
    return (float(px), float(py))


def extract_spiral(denoised: np.ndarray, mode="pattern", color_img=None) -> dict:
    """Extract spiral paths from simplified image with center detection."""
    orig_h, orig_w = denoised.shape
    simplified, scale, mask = prepare_for_extraction(
        color_img, None, denoised, mode)
    h, w = simplified.shape

    # Center detection: try HoughCircles on simplified image
    center_s = None
    circles = cv2.HoughCircles(simplified, cv2.HOUGH_GRADIENT, dp=2,
                                minDist=min(h, w) // 4,
                                param1=100, param2=50,
                                minRadius=min(h, w) // 8,
                                maxRadius=min(h, w) // 2)
    if circles is not None:
        best = circles[0][0]
        center_s = (int(best[0]), int(best[1]))
    if center_s is None:
        edges = cv2.Canny(simplified, 40, 120)
        M = cv2.moments(edges)
        if M["m00"] > 0:
            center_s = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
        else:
            center_s = (w // 2, h // 2)

    # Radial profile
    edges = cv2.Canny(simplified, 30, 100)
    max_radius = min(h, w) // 2
    radial_profile = []
    for angle_deg in range(0, 360, 2):
        angle = np.radians(angle_deg)
        for r in range(1, max_radius):
            x = int(center_s[0] + r * np.cos(angle))
            y = int(center_s[1] + r * np.sin(angle))
            if 0 <= x < w and 0 <= y < h and edges[y, x] > 0:
                radial_profile.append((angle_deg, int(r / scale)))
                break

    arm_count = 1
    if radial_profile:
        hist, _ = np.histogram([rp[0] for rp in radial_profile], bins=180)
        fft = np.fft.fft(hist)
        freqs = np.fft.fftfreq(len(hist))
        magnitudes = np.abs(fft[1:])
        if len(magnitudes) > 0:
            dominant_freq = freqs[np.argmax(magnitudes) + 1]
            if dominant_freq != 0:
                arm_count = max(1, min(12, int(round(abs(1.0 / dominant_freq)))))

    # Skeleton paths from simplified
    paths = _extract_skeleton(simplified, min_length_ratio=0.04)
    spiral_paths = []
    for p in paths:
        scaled_pts = [(int(r / scale), int(c / scale)) for r, c in p["points"]]
        spiral_paths.append({
            "points": scaled_pts, "hierarchy": p["hierarchy"],
            "length": p["length"], "quality": p["quality"],
        })

    center = (int(center_s[0] / scale), int(center_s[1] / scale))
    return {
        "center": center,
        "arm_count": arm_count,
        "radial_profile": radial_profile,
        "max_radius": int(max_radius / scale),
        "paths": spiral_paths,
    }


def extract_porous(denoised: np.ndarray, mode="pattern", color_img=None) -> dict:
    """Extract hole boundaries from simplified image, filtering by circularity."""
    orig_h, orig_w = denoised.shape
    simplified, scale, mask = prepare_for_extraction(
        color_img, None, denoised, mode)
    h, w = simplified.shape
    img_area = h * w

    # Contour extraction on simplified image — noise holes are gone
    contours = _extract_contours(simplified, top_n=_MAX_HOLES, epsilon_ratio=0.03)

    holes = []
    for c in contours:
        ox = int(c["center"][0] / scale)
        oy = int(c["center"][1] / scale)
        o_area = c["area"] / (scale * scale)
        radius = float(np.sqrt(o_area / np.pi))
        pts = [(int(p[0] / scale), int(p[1] / scale)) for p in c["points"]]

        quality = _score_feature(o_area, c["hierarchy"], ox, oy, orig_w, orig_h)

        holes.append({
            "center": (ox, oy), "radius": radius,
            "area": float(o_area), "hierarchy": c["hierarchy"],
            "boundary": pts if len(pts) >= 3 else None,
            "quality": quality,
        })

    holes.sort(key=lambda x: -x.get("quality", 0))
    holes = holes[:_MAX_HOLES]

    # Density map
    grid_n = 8
    density_map = np.zeros((grid_n, grid_n))
    for hole in holes:
        gx = min(int(hole["center"][0] / orig_w * grid_n), grid_n - 1)
        gy = min(int(hole["center"][1] / orig_h * grid_n), grid_n - 1)
        density_map[gy, gx] += 1

    all_radii = [hole["radius"] for hole in holes]
    return {
        "holes": holes,
        "hole_count": len(holes),
        "density_map": density_map.tolist(),
        "avg_hole_radius": float(np.mean(all_radii)) if all_radii else 0.0,
    }


# ─── Dispatch ───

EXTRACTORS = {
    "cellular": extract_cellular,
    "branching": extract_branching,
    "shell": extract_shell,
    "lattice": extract_lattice,
    "spiral": extract_spiral,
    "porous": extract_porous,
}


def extract_all(denoised: np.ndarray, category: str,
                mode: str = "pattern", color_img: np.ndarray = None) -> dict:
    """Run the appropriate extractor for the given category."""
    if category not in EXTRACTORS:
        raise ValueError(f"Unknown category: {category}. Must be one of {list(EXTRACTORS.keys())}")
    return EXTRACTORS[category](denoised, mode=mode, color_img=color_img)
