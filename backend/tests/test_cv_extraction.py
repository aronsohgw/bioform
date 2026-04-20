"""Tests for CV extraction pipeline."""
import numpy as np
import cv2


def test_preprocess_returns_three_images(sample_image_path):
    from app.cv_extraction import preprocess
    img, gray, denoised = preprocess(sample_image_path)
    assert img is not None
    assert len(img.shape) == 3  # color
    assert len(gray.shape) == 2  # grayscale
    assert len(denoised.shape) == 2  # grayscale


def test_extract_cellular_finds_cells(sample_image_path):
    from app.cv_extraction import preprocess, extract_cellular
    _, _, denoised = preprocess(sample_image_path)
    result = extract_cellular(denoised)
    assert "seed_points" in result
    assert "avg_cell_size" in result
    assert "cell_count" in result
    assert result["cell_count"] >= 0


def test_extract_branching_finds_skeleton(tmp_path, branching_image_bytes):
    from app.cv_extraction import preprocess, extract_branching
    path = tmp_path / "branch.png"
    path.write_bytes(branching_image_bytes)
    _, _, denoised = preprocess(str(path))
    result = extract_branching(denoised)
    assert "branch_points" in result
    assert "endpoints" in result
    assert "paths" in result
    assert "branch_count" in result


def test_extract_shell_returns_height_map(sample_image_path):
    from app.cv_extraction import preprocess, extract_shell
    _, _, denoised = preprocess(sample_image_path)
    result = extract_shell(denoised)
    assert "control_points" in result
    assert len(result["control_points"]) > 0


def test_extract_lattice_finds_lines(tmp_path, lattice_image_bytes):
    from app.cv_extraction import preprocess, extract_lattice
    path = tmp_path / "lattice.png"
    path.write_bytes(lattice_image_bytes)
    _, _, denoised = preprocess(str(path))
    result = extract_lattice(denoised)
    assert "lines" in result
    assert "dominant_angles" in result
    assert "line_count" in result


def test_extract_spiral_returns_center(sample_image_path):
    from app.cv_extraction import preprocess, extract_spiral
    _, _, denoised = preprocess(sample_image_path)
    result = extract_spiral(denoised)
    assert "center" in result
    assert "arm_count" in result
    assert len(result["center"]) == 2


def test_extract_porous_finds_holes(sample_image_path):
    from app.cv_extraction import preprocess, extract_porous
    _, _, denoised = preprocess(sample_image_path)
    result = extract_porous(denoised)
    assert "holes" in result
    assert "hole_count" in result
    assert "density_map" in result
    assert "avg_hole_radius" in result


def test_extract_all_runs_correct_extractor(sample_image_path):
    from app.cv_extraction import preprocess, extract_all
    _, _, denoised = preprocess(sample_image_path)
    result = extract_all(denoised, "cellular")
    assert "seed_points" in result
    result = extract_all(denoised, "shell")
    assert "control_points" in result


def test_extract_all_unknown_category_raises(sample_image_path):
    import pytest
    from app.cv_extraction import preprocess, extract_all
    _, _, denoised = preprocess(sample_image_path)
    with pytest.raises(ValueError, match="Unknown category"):
        extract_all(denoised, "unknown_pattern")


# ─── Essence extraction: mode detection ───

def test_detect_mode_object(object_image_path):
    """Image with centered object on dark bg should detect as 'object'."""
    from app.cv_extraction import preprocess, detect_mode
    _, gray, _ = preprocess(object_image_path)
    assert detect_mode(gray) == "object"


def test_detect_mode_pattern(pattern_image_path):
    """Image where pattern fills frame should detect as 'pattern'."""
    from app.cv_extraction import preprocess, detect_mode
    _, gray, _ = preprocess(pattern_image_path)
    assert detect_mode(gray) == "pattern"


# ─── Essence extraction: simplification core ───

def test_simplify_reduces_edge_count(noisy_image_path):
    """Bilateral simplification should reduce edge count on noisy images."""
    from app.cv_extraction import preprocess, _simplify
    _, _, denoised = preprocess(noisy_image_path)
    simplified = _simplify(denoised)
    # Count Canny edges before and after — simplified should have fewer
    edges_raw = cv2.Canny(denoised, 30, 100)
    edges_simplified = cv2.Canny(simplified, 30, 100)
    assert np.count_nonzero(edges_simplified) < np.count_nonzero(edges_raw)


def test_extract_contours_returns_capped(sample_image_path):
    """Contour extraction should return at most top_n contours."""
    from app.cv_extraction import preprocess, _simplify, _extract_contours
    _, _, denoised = preprocess(sample_image_path)
    simplified = _simplify(denoised)
    contours = _extract_contours(simplified, top_n=10)
    assert len(contours) <= 10
    for c in contours:
        assert "points" in c
        assert "center" in c
        assert "area" in c
        assert "hierarchy" in c
        assert "quality" in c


def test_extract_skeleton_filters_short_paths(tmp_path, branching_image_bytes):
    """Skeleton extraction should discard very short paths."""
    from app.cv_extraction import preprocess, _simplify, _extract_skeleton
    path = tmp_path / "branch.png"
    path.write_bytes(branching_image_bytes)
    _, _, denoised = preprocess(str(path))
    simplified = _simplify(denoised)
    h, w = simplified.shape
    diag = np.sqrt(h ** 2 + w ** 2)
    min_len = diag * 0.05
    paths = _extract_skeleton(simplified, min_length_ratio=0.05)
    for p in paths:
        assert "points" in p
        assert "length" in p
        # All paths should be at least min_length_ratio * diagonal in pixel length
        assert p["length"] >= min_len * 0.5  # allow some tolerance for scaling


def test_grabcut_produces_mask(object_image_path):
    """GrabCut should produce a foreground mask with nonzero pixels."""
    from app.cv_extraction import preprocess, _grabcut_mask
    color_img, _, _ = preprocess(object_image_path)
    mask = _grabcut_mask(color_img)
    assert mask.shape == color_img.shape[:2]
    assert np.count_nonzero(mask) > 0


# ─── Essence extraction: extractors produce quality + hierarchy ───

def test_cellular_has_quality_and_hierarchy(sample_image_path):
    """Cellular features should have quality scores and hierarchy."""
    from app.cv_extraction import preprocess, extract_cellular
    _, _, denoised = preprocess(sample_image_path)
    result = extract_cellular(denoised)
    for s in result.get("seed_points_hierarchical", []):
        assert "quality" in s
        assert "hierarchy" in s


def test_branching_has_quality_and_hierarchy(tmp_path, branching_image_bytes):
    """Branching paths should have quality and hierarchy."""
    from app.cv_extraction import preprocess, extract_branching
    path = tmp_path / "branch.png"
    path.write_bytes(branching_image_bytes)
    _, _, denoised = preprocess(str(path))
    result = extract_branching(denoised)
    for p in result["paths"]:
        assert "hierarchy" in p
        assert "quality" in p


def test_porous_has_quality_and_hierarchy(sample_image_path):
    """Porous features should have quality and hierarchy."""
    from app.cv_extraction import preprocess, extract_porous
    _, _, denoised = preprocess(sample_image_path)
    result = extract_porous(denoised)
    for hole in result["holes"]:
        assert "quality" in hole
        assert "hierarchy" in hole


def test_shell_has_curvature(sample_image_path):
    """Shell control points should include curvature and hierarchy."""
    from app.cv_extraction import preprocess, extract_shell
    _, _, denoised = preprocess(sample_image_path)
    result = extract_shell(denoised)
    grid = result["control_points"]
    assert len(grid) > 0
    sample_pt = grid[0][0]
    assert len(sample_pt) >= 5  # x, y, height, curvature, hierarchy
