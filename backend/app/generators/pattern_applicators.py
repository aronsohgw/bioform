"""Pattern applicators — map extracted features onto wall surfaces.

Each category (cellular, branching, lattice, porous, spiral, shell) has its
own applicator that reads hierarchical extraction data and draws geometry
on the building walls. Progressive detail: hierarchy 0 at ground, 1 mid, 2 top.
"""
import math
import rhino3dm
import numpy as np
from scipy.spatial import Voronoi, KDTree

from app.generators.building_core import attr

# Max features per wall — raised thanks to KDTree + LOD
MAX_SEED_POINTS = 200
MAX_LINES = 300
MAX_HOLES = 200
MAX_PATHS = 120


def _lod_cap_for_wall(wall_width, wall_height, max_cap):
    """Return feature cap proportional to wall area. Small walls get fewer features."""
    wall_area = wall_width * wall_height
    # Reference area: 10m x 3m = 30 m² gets the full cap
    ref_area = 30.0
    ratio = min(wall_area / ref_area, 1.0)
    return max(8, int(max_cap * ratio))


def _filter_features_by_position(features, key_fn, img_w, img_h, wall_u_range, wall_v_range):
    """Pre-filter features to those within the wall's coordinate range.

    key_fn extracts (x, y) from a feature. Coordinates are normalized from
    image space to wall UV space. Returns features that fall within the range.
    """
    if not features or img_w <= 0 or img_h <= 0:
        return features
    # For now, pass all features since walls typically cover the full image.
    # This becomes useful when we have multi-building or partial facades.
    return features


# ─── Pattern on wall surface ───

def _apply_voronoi_to_wall(model, layer_idx, wall, seed_points, cell_count, depth=0.08,
                            evo=None):
    """Map voronoi cells onto a wall surface as extruded panels.

    With evolution params (evo): cell count adapts, subdivision adds detail,
    irregularity jitters seeds, and depth varies per cell based on distance from center.
    """
    o = wall["origin"]
    u = wall["u"]
    v = wall["v"]
    n = wall["normal"]
    ww = wall["width"]
    wh = wall["height"]

    # LOD: cap features based on wall size
    lod_cap = _lod_cap_for_wall(ww, wh, MAX_SEED_POINTS)

    # Evolution parameters
    if evo:
        cell_count = evo.get("cell_count", cell_count)
        depth = evo.get("depth", depth)
        irregularity = evo.get("irregularity", 0.0)
        do_subdivide = evo.get("subdivide", False)
        t = evo.get("t", 0.0)
    else:
        irregularity = 0.0
        do_subdivide = False
        t = 0.0

    # Use a seed based on floor position so each floor gets a unique but deterministic pattern
    floor_seed = 42 + int(t * 1000)
    rng = np.random.default_rng(floor_seed)

    # Determine max hierarchy to include based on floor position
    max_hierarchy = 0 if t < 0.25 else (1 if t < 0.6 else 2)

    # Generate seed points normalized to wall dimensions
    # Use hierarchical data if available to progressively add detail
    hier_seeds = None
    if hasattr(seed_points, '__len__') and seed_points and isinstance(seed_points[0], dict):
        # Hierarchical seed points — filter by floor level
        hier_seeds = seed_points
    elif evo and "seed_points_hierarchical" in (evo or {}):
        hier_seeds = evo.get("seed_points_hierarchical")

    if hier_seeds:
        filtered = [(sp["center"][0], sp["center"][1]) for sp in hier_seeds
                     if sp.get("hierarchy", 0) <= max_hierarchy]
        # LOD cap based on wall size
        if len(filtered) > lod_cap:
            filtered = filtered[:lod_cap]
        if len(filtered) >= 4:
            pts = np.array(filtered, dtype=float)
            pts[:, 0] = (pts[:, 0] / max(pts[:, 0].max(), 1)) * ww
            pts[:, 1] = (pts[:, 1] / max(pts[:, 1].max(), 1)) * wh
        else:
            pts = np.column_stack([rng.uniform(0, ww, max(cell_count, 12)),
                                    rng.uniform(0, wh, max(cell_count, 12))])
    elif seed_points and len(seed_points) >= 4:
        pts = np.array(seed_points[:lod_cap], dtype=float)
        pts[:, 0] = (pts[:, 0] / max(pts[:, 0].max(), 1)) * ww
        pts[:, 1] = (pts[:, 1] / max(pts[:, 1].max(), 1)) * wh
        if len(pts) < cell_count:
            extra = cell_count - len(pts)
            new_pts = np.column_stack([rng.uniform(0, ww, extra), rng.uniform(0, wh, extra)])
            pts = np.vstack([pts, new_pts])
        elif len(pts) > cell_count:
            indices = rng.choice(len(pts), cell_count, replace=False)
            pts = pts[indices]
    else:
        count = max(cell_count, 12)
        pts = np.column_stack([rng.uniform(0, ww, count), rng.uniform(0, wh, count)])

    # Apply irregularity jitter — makes the pattern more organic at higher floors
    if irregularity > 0:
        jitter_scale = min(ww, wh) * 0.05 * irregularity
        pts += rng.normal(0, jitter_scale, pts.shape)
        pts[:, 0] = np.clip(pts[:, 0], 0, ww)
        pts[:, 1] = np.clip(pts[:, 1], 0, wh)

    # Subdivision: split large cells by adding midpoints between distant seeds
    # Uses KDTree for O(n log n) pair finding instead of O(n²) brute force
    if do_subdivide and len(pts) >= 4:
        threshold = min(ww, wh) / math.sqrt(max(cell_count, 4)) * 1.5
        tree = KDTree(pts)
        pairs = tree.query_pairs(threshold * 2)  # find pairs within 2x threshold
        sub_pts = []
        for i, j in pairs:
            dist = np.linalg.norm(pts[i] - pts[j])
            if dist > threshold:
                mid = (pts[i] + pts[j]) / 2
                mid += rng.normal(0, dist * 0.1, 2)
                sub_pts.append(mid)
        if sub_pts:
            sub_arr = np.array(sub_pts)
            sub_arr[:, 0] = np.clip(sub_arr[:, 0], 0, ww)
            sub_arr[:, 1] = np.clip(sub_arr[:, 1], 0, wh)
            pts = np.vstack([pts, sub_arr])

    # Add boundary points for Voronoi
    margin = max(ww, wh) * 2
    boundary = np.array([[-margin, -margin], [ww + margin, -margin],
                          [-margin, wh + margin], [ww + margin, wh + margin]])
    all_pts = np.vstack([pts, boundary])

    vor = Voronoi(all_pts)

    # Center of wall for depth variation
    center_u, center_v = ww / 2, wh / 2

    # Batch mesh: collect all cells into one mesh per wall (reduces object count 10-50x)
    mesh = rhino3dm.Mesh()
    vert_offset = 0

    for pi, region_idx in enumerate(vor.point_region[:len(pts)]):
        region = vor.regions[region_idx]
        if not region or -1 in region:
            continue
        verts = [vor.vertices[i] for i in region]
        if len(verts) < 3:
            continue

        # Clip to wall bounds
        clipped = [(max(0, min(vv[0], ww)), max(0, min(vv[1], wh))) for vv in verts]
        unique = [clipped[0]]
        for cv in clipped[1:]:
            if abs(cv[0] - unique[-1][0]) > 0.01 or abs(cv[1] - unique[-1][1]) > 0.01:
                unique.append(cv)
        if len(unique) < 3:
            continue

        # Per-cell depth variation: cells near center are deeper, edges shallower
        cell_cx = np.mean([c[0] for c in unique])
        cell_cy = np.mean([c[1] for c in unique])
        dist_from_center = math.sqrt(((cell_cx - center_u) / ww) ** 2 +
                                      ((cell_cy - center_v) / wh) ** 2)
        cell_depth = depth * (0.4 + 0.8 * (1 - min(dist_from_center, 1.0)))
        cell_depth *= (0.85 + 0.3 * rng.random())

        # Add vertices for this cell into the batched mesh
        nc = len(unique)
        base = vert_offset

        for cv in unique:
            x = o[0] + u[0] * cv[0] + v[0] * cv[1]
            y = o[1] + u[1] * cv[0] + v[1] * cv[1]
            z = o[2] + u[2] * cv[0] + v[2] * cv[1]
            mesh.Vertices.Add(x, y, z)
        for cv in unique:
            x = o[0] + u[0] * cv[0] + v[0] * cv[1] + n[0] * cell_depth
            y = o[1] + u[1] * cv[0] + v[1] * cv[1] + n[1] * cell_depth
            z = o[2] + u[2] * cv[0] + v[2] * cv[1] + n[2] * cell_depth
            mesh.Vertices.Add(x, y, z)

        for i in range(1, nc - 1):
            mesh.Faces.AddFace(base + 0, base + i, base + i + 1)
        for i in range(1, nc - 1):
            mesh.Faces.AddFace(base + nc, base + nc + i + 1, base + nc + i)
        for i in range(nc):
            j = (i + 1) % nc
            mesh.Faces.AddFace(base + i, base + j, base + nc + j, base + nc + i)

        vert_offset += nc * 2

    if vert_offset > 0:
        mesh.Normals.ComputeNormals()
        mesh.Compact()
        model.Objects.AddMesh(mesh, attr(layer_idx))


def _apply_lines_to_wall(model, layer_idx, wall, lines_data, depth=0.05, evo=None):
    """Map lattice lines onto a wall surface using hierarchical extraction data.

    With hierarchy: primary lines shown at ground, secondary/tertiary revealed higher up.
    Rotation evolution applied per floor.
    """
    o = wall["origin"]
    u = wall["u"]
    v = wall["v"]
    n = wall["normal"]
    ww = wall["width"]
    wh = wall["height"]

    if evo:
        t = evo.get("t", 0.0)
        angles = evo.get("angles", [0.0, math.pi / 2])
        spacing_mult = evo.get("spacing_mult", 1.0)
        depth = evo.get("depth", depth)
    else:
        t = 0.0
        angles = [0.0, math.pi / 2]
        spacing_mult = 1.0

    rng = np.random.default_rng(42 + int(t * 1000))

    # LOD cap based on wall size
    lod_cap = _lod_cap_for_wall(ww, wh, MAX_LINES)

    # Use hierarchical lines if available, otherwise fall back to flat list
    hier_lines = lines_data.get("lines_hierarchical", [])[:lod_cap]
    flat_lines = lines_data.get("lines", [])[:lod_cap]

    # Determine max hierarchy to show based on floor position
    max_hierarchy = 0 if t < 0.25 else (1 if t < 0.6 else 2)

    if hier_lines:
        # Hierarchical extraction data — use it with progressive reveal
        all_coords = []
        for hl in hier_lines:
            all_coords.append(hl["coords"])
        if not all_coords:
            return

        flat = np.array(all_coords, dtype=float)
        x_max = max(np.concatenate([flat[:, 0], flat[:, 2]]).max(), 1)
        y_max = max(np.concatenate([flat[:, 1], flat[:, 3]]).max(), 1)

        for hl in hier_lines:
            if hl["hierarchy"] > max_hierarchy:
                continue
            coords = hl["coords"]
            u1 = coords[0] / x_max * ww
            v1 = coords[1] / y_max * wh
            u2 = coords[2] / x_max * ww
            v2 = coords[3] / y_max * wh

            # Apply rotation evolution
            if evo and t > 0:
                cu, cv_c = ww / 2, wh / 2
                rotation = t * math.pi / 12
                cos_r, sin_r = math.cos(rotation), math.sin(rotation)
                u1, v1 = (cu + (u1 - cu) * cos_r - (v1 - cv_c) * sin_r,
                           cv_c + (u1 - cu) * sin_r + (v1 - cv_c) * cos_r)
                u2, v2 = (cu + (u2 - cu) * cos_r - (v2 - cv_c) * sin_r,
                           cv_c + (u2 - cu) * sin_r + (v2 - cv_c) * cos_r)

            u1 = max(0, min(u1, ww))
            v1 = max(0, min(v1, wh))
            u2 = max(0, min(u2, ww))
            v2 = max(0, min(v2, wh))
            _add_line_on_wall(model, layer_idx, o, u, v, u1, v1, u2, v2)

    elif flat_lines:
        # Flat lines — backward compat, draw all
        coords_list = []
        for line_group in flat_lines:
            coords = line_group[0] if isinstance(line_group[0], list) else line_group
            coords_list.append(coords)

        if coords_list:
            flat = np.array(coords_list, dtype=float)
            x_max = max(np.concatenate([flat[:, 0], flat[:, 2]]).max(), 1)
            y_max = max(np.concatenate([flat[:, 1], flat[:, 3]]).max(), 1)

            for coords in coords_list:
                u1 = coords[0] / x_max * ww
                v1 = coords[1] / y_max * wh
                u2 = coords[2] / x_max * ww
                v2 = coords[3] / y_max * wh
                u1 = max(0, min(u1, ww))
                v1 = max(0, min(v1, wh))
                u2 = max(0, min(u2, ww))
                v2 = max(0, min(v2, wh))
                _add_line_on_wall(model, layer_idx, o, u, v, u1, v1, u2, v2)
    else:
        # No extraction data — generative grid fallback
        num_u = max(4, int(10 * (1.0 / spacing_mult)))
        num_v = max(3, int(8 * (1.0 / spacing_mult)))
        spacing_u = ww / num_u
        spacing_v = wh / num_v

        for i in range(num_u + 1):
            uu = i * spacing_u
            _add_line_on_wall(model, layer_idx, o, u, v, uu, 0, uu, wh)
        for j in range(num_v + 1):
            vv = j * spacing_v
            _add_line_on_wall(model, layer_idx, o, u, v, 0, vv, ww, vv)

        if t > 0.2:
            diag_density = int(3 + 6 * t)
            for i in range(diag_density):
                u_start = rng.uniform(0, ww * 0.8)
                v_start = rng.uniform(0, wh * 0.8)
                span = min(ww, wh) * (0.2 + 0.3 * rng.random())
                angle = angles[0] + rng.uniform(-0.3, 0.3)
                u_end = min(ww, u_start + span * math.cos(angle))
                v_end = min(wh, v_start + span * math.sin(angle))
                _add_line_on_wall(model, layer_idx, o, u, v, u_start, v_start, u_end, v_end)


def _add_line_on_wall(model, layer_idx, o, u_dir, v_dir, u1, v1, u2, v2):
    """Helper: add a single line segment on a wall surface."""
    pl = rhino3dm.Polyline(0)
    x1 = o[0] + u_dir[0] * u1 + v_dir[0] * v1
    y1 = o[1] + u_dir[1] * u1 + v_dir[1] * v1
    z1 = o[2] + u_dir[2] * u1 + v_dir[2] * v1
    x2 = o[0] + u_dir[0] * u2 + v_dir[0] * v2
    y2 = o[1] + u_dir[1] * u2 + v_dir[1] * v2
    z2 = o[2] + u_dir[2] * u2 + v_dir[2] * v2
    pl.Add(x1, y1, z1)
    pl.Add(x2, y2, z2)
    model.Objects.AddCurve(pl.ToPolylineCurve(), attr(layer_idx))


def _add_wall_branches(model, layer_idx, o, u_dir, v_dir, n, ww, wh,
                        parent_lines, levels, depth, rng):
    """Recursively add sub-branches sprouting from existing lines on a wall."""
    if levels <= 0 or not parent_lines:
        return

    child_lines = []
    for (u1, v1, u2, v2) in parent_lines:
        # Branch from midpoint or random point along parent
        branch_t = 0.3 + 0.4 * rng.random()
        bu = u1 + (u2 - u1) * branch_t
        bv = v1 + (v2 - v1) * branch_t

        # Parent direction
        du = u2 - u1
        dv = v2 - v1
        length = math.sqrt(du ** 2 + dv ** 2)
        if length < 0.01:
            continue

        # Branch in two directions (rotated from parent)
        branch_len = length * (0.4 + 0.2 * rng.random())
        for sign in [-1, 1]:
            angle = sign * (math.pi / 4 + rng.uniform(-0.3, 0.3))
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            bdu = (du * cos_a - dv * sin_a) / length * branch_len
            bdv = (du * sin_a + dv * cos_a) / length * branch_len
            eu = max(0, min(ww, bu + bdu))
            ev = max(0, min(wh, bv + bdv))
            _add_line_on_wall(model, layer_idx, o, u_dir, v_dir, bu, bv, eu, ev)
            child_lines.append((bu, bv, eu, ev))

    _add_wall_branches(model, layer_idx, o, u_dir, v_dir, n, ww, wh,
                        child_lines, levels - 1, depth * 0.6, rng)


def _apply_circles_to_wall(model, layer_idx, wall, holes_data, depth=0.06, evo=None):
    """Map porous hole pattern onto a wall surface with hierarchy-based progressive reveal.

    Hierarchy 0 (primary): large perforations shown at ground floor
    Hierarchy 1 (secondary): medium holes appear mid-height
    Hierarchy 2 (tertiary): fine perforations appear on upper floors
    """
    o = wall["origin"]
    u = wall["u"]
    v = wall["v"]
    n = wall["normal"]
    ww = wall["width"]
    wh = wall["height"]

    if evo:
        t = evo.get("t", 0.0)
        hole_scale = evo.get("hole_scale", 1.0)
        density_gradient = evo.get("density_gradient", 1.0)
        depth = evo.get("depth", depth)
    else:
        t = 0.0
        hole_scale = 1.0
        density_gradient = 1.0

    rng = np.random.default_rng(42 + int(t * 1000))

    lod_cap = _lod_cap_for_wall(ww, wh, MAX_HOLES)
    holes = holes_data.get("holes", [])[:lod_cap]

    # Determine max hierarchy to show based on floor position
    max_hierarchy = 0 if t < 0.25 else (1 if t < 0.6 else 2)

    if holes:
        max_cx = max(h["center"][0] for h in holes) or 1
        max_cy = max(h["center"][1] for h in holes) or 1
        max_r = max(h["radius"] for h in holes) or 1

        for hole in holes:
            # Filter by hierarchy if available
            hier = hole.get("hierarchy", 0)
            if hier > max_hierarchy:
                continue

            cu = hole["center"][0] / max_cx * ww * 0.9 + ww * 0.05
            cv_val = hole["center"][1] / max_cy * wh * 0.9 + wh * 0.05
            r = hole["radius"] / max_r * min(ww, wh) * 0.04 * hole_scale
            r = max(r, 0.03)

            # Depth varies: deeper holes near center + hierarchy affects depth
            dist_from_center = math.sqrt(((cu / ww) - 0.5) ** 2 + ((cv_val / wh) - 0.5) ** 2)
            local_depth = depth * (0.5 + 0.7 * (1 - min(dist_from_center * 2, 1.0)))
            # Primary holes are deeper, tertiary are shallower
            local_depth *= (1.0 - hier * 0.25)

            cx = o[0] + u[0] * cu + v[0] * cv_val + n[0] * local_depth
            cy = o[1] + u[1] * cu + v[1] * cv_val + n[1] * local_depth
            cz = o[2] + u[2] * cu + v[2] * cv_val + n[2] * local_depth

            # Use actual boundary contour if available for faithful shape
            boundary = hole.get("boundary")
            if boundary and len(boundary) >= 3:
                # Map boundary polygon onto wall
                b_arr = np.array(boundary, dtype=float)
                b_cx = hole["center"][0]
                b_cy = hole["center"][1]
                pl = rhino3dm.Polyline(0)
                for bpt in boundary:
                    # Offset from center, scale to wall-space radius
                    bu = cu + (bpt[0] - b_cx) / max_cx * ww * 0.9
                    bv = cv_val + (bpt[1] - b_cy) / max_cy * wh * 0.9
                    bu = max(0, min(bu, ww))
                    bv = max(0, min(bv, wh))
                    bx = o[0] + u[0] * bu + v[0] * bv + n[0] * local_depth
                    by = o[1] + u[1] * bu + v[1] * bv + n[1] * local_depth
                    bz = o[2] + u[2] * bu + v[2] * bv + n[2] * local_depth
                    pl.Add(bx, by, bz)
                # Close the polygon
                first = boundary[0]
                fu = cu + (first[0] - b_cx) / max_cx * ww * 0.9
                fv = cv_val + (first[1] - b_cy) / max_cy * wh * 0.9
                fu = max(0, min(fu, ww))
                fv = max(0, min(fv, wh))
                fx = o[0] + u[0] * fu + v[0] * fv + n[0] * local_depth
                fy = o[1] + u[1] * fu + v[1] * fv + n[1] * local_depth
                fz = o[2] + u[2] * fu + v[2] * fv + n[2] * local_depth
                pl.Add(fx, fy, fz)
                if pl.Count >= 3:
                    model.Objects.AddCurve(pl.ToPolylineCurve(), attr(layer_idx))
            else:
                # Fallback to circle
                circle = rhino3dm.Circle(rhino3dm.Point3d(cx, cy, cz), r)
                model.Objects.AddCurve(circle.ToNurbsCurve(), attr(layer_idx))
    else:
        # Generative porous pattern with density gradient
        grid_u = max(4, int(8 * density_gradient))
        grid_v = max(6, int(12 * density_gradient))
        for i in range(grid_u):
            for j in range(grid_v):
                cu = (i + 0.5) / grid_u * ww
                cv_val = (j + 0.5) / grid_v * wh
                # Radial density gradient that shifts with floor position
                center_bias_u = 0.5 + 0.2 * math.sin(t * math.pi)
                center_bias_v = 0.5
                dist = math.sqrt(((cu / ww) - center_bias_u) ** 2 +
                                  ((cv_val / wh) - center_bias_v) ** 2)
                r = (0.3 + 0.4 * (1 - min(dist * 2, 1.0))) * ww / grid_u * 0.3 * hole_scale
                # Add randomness
                r *= (0.7 + 0.6 * rng.random())

                local_depth = depth * (0.4 + 0.8 * (1 - dist))
                cx = o[0] + u[0] * cu + v[0] * cv_val + n[0] * local_depth
                cy = o[1] + u[1] * cu + v[1] * cv_val + n[1] * local_depth
                cz = o[2] + u[2] * cu + v[2] * cv_val + n[2] * local_depth

                circle = rhino3dm.Circle(rhino3dm.Point3d(cx, cy, cz), max(r, 0.03))
                model.Objects.AddCurve(circle.ToNurbsCurve(), attr(layer_idx))


def _apply_branching_to_wall(model, layer_idx, wall, extraction, depth=0.08, evo=None):
    """Map organic branching pattern onto a wall surface using traced skeleton paths.

    Paths are drawn as polylines with thickness based on hierarchy level.
    Primary trunks are thicker, secondary branches taper, tertiary are finest.
    Cross-connections emerge at higher floors for structural density.
    """
    o = wall["origin"]
    u = wall["u"]
    v = wall["v"]
    n = wall["normal"]
    ww = wall["width"]
    wh = wall["height"]

    if evo:
        t = evo.get("t", 0.0)
        depth = evo.get("depth", depth)
        branch_depth_level = evo.get("branch_depth", 3)
        branch_angle_spread = evo.get("branch_angle_spread", 45)
        taper = evo.get("taper", 0.6)
    else:
        t = 0.0
        branch_depth_level = 3
        branch_angle_spread = 45
        taper = 0.6

    rng = np.random.default_rng(42 + int(t * 1000))

    lod_cap = _lod_cap_for_wall(ww, wh, MAX_PATHS)
    paths = extraction.get("paths", [])[:lod_cap]
    branch_points = extraction.get("branch_points", [])
    endpoints = extraction.get("endpoints", [])

    if paths and len(paths) >= 2:
        # ── Use actual extracted skeleton paths ──
        # Find image bounds from path data to normalize coordinates
        all_pts = []
        for p in paths:
            pts = p["points"] if isinstance(p, dict) else p
            all_pts.extend(pts)
        if not all_pts:
            return
        all_arr = np.array(all_pts, dtype=float)
        r_min, c_min = all_arr.min(axis=0)
        r_max, c_max = all_arr.max(axis=0)
        r_range = max(r_max - r_min, 1)
        c_range = max(c_max - c_min, 1)

        # Width of extruded rib per hierarchy level
        rib_widths = {0: depth * 1.5, 1: depth * 0.9, 2: depth * 0.5}

        # Filter by hierarchy at lower floors (show fewer small branches at base)
        max_hierarchy = 0 if t < 0.2 else (1 if t < 0.5 else 2)

        for path_data in paths:
            if isinstance(path_data, dict):
                pts = path_data["points"]
                hierarchy = path_data.get("hierarchy", 1)
            else:
                pts = path_data
                hierarchy = 1

            if hierarchy > max_hierarchy:
                continue

            if len(pts) < 2:
                continue

            # Subsample long paths to keep polyline resolution reasonable
            step = max(1, len(pts) // 80)
            sampled = pts[::step]
            if sampled[-1] != pts[-1]:
                sampled.append(pts[-1])

            # Map image (row, col) → wall (u, v) coordinates
            rib_depth = rib_widths.get(hierarchy, depth * 0.5)
            # Add slight depth variation per floor
            rib_depth *= (0.7 + 0.6 * t)

            pl = rhino3dm.Polyline(0)
            for (pr, pc) in sampled:
                uu = ((pc - c_min) / c_range) * ww
                vv = ((pr - r_min) / r_range) * wh
                # Clamp to wall
                uu = max(0, min(uu, ww))
                vv = max(0, min(vv, wh))
                x = o[0] + u[0] * uu + v[0] * vv
                y = o[1] + u[1] * uu + v[1] * vv
                z = o[2] + u[2] * uu + v[2] * vv
                pl.Add(x, y, z)

            if pl.Count >= 2:
                model.Objects.AddCurve(pl.ToPolylineCurve(), attr(layer_idx))

            # Also add an offset copy (extruded outward) for rib depth
            pl_ext = rhino3dm.Polyline(0)
            for (pr, pc) in sampled:
                uu = ((pc - c_min) / c_range) * ww
                vv = ((pr - r_min) / r_range) * wh
                uu = max(0, min(uu, ww))
                vv = max(0, min(vv, wh))
                x = o[0] + u[0] * uu + v[0] * vv + n[0] * rib_depth
                y = o[1] + u[1] * uu + v[1] * vv + n[1] * rib_depth
                z = o[2] + u[2] * uu + v[2] * vv + n[2] * rib_depth
                pl_ext.Add(x, y, z)

            if pl_ext.Count >= 2:
                model.Objects.AddCurve(pl_ext.ToPolylineCurve(), attr(layer_idx))

            # Connect base to extruded with cross-ribs for solid appearance
            cross_step = max(1, len(sampled) // 6)
            for ci in range(0, len(sampled), cross_step):
                pr, pc = sampled[ci]
                uu = ((pc - c_min) / c_range) * ww
                vv = ((pr - r_min) / r_range) * wh
                uu = max(0, min(uu, ww))
                vv = max(0, min(vv, wh))
                x_base = o[0] + u[0] * uu + v[0] * vv
                y_base = o[1] + u[1] * uu + v[1] * vv
                z_base = o[2] + u[2] * uu + v[2] * vv
                x_ext = x_base + n[0] * rib_depth
                y_ext = y_base + n[1] * rib_depth
                z_ext = z_base + n[2] * rib_depth
                rib = rhino3dm.Polyline(0)
                rib.Add(x_base, y_base, z_base)
                rib.Add(x_ext, y_ext, z_ext)
                model.Objects.AddCurve(rib.ToPolylineCurve(), attr(layer_idx))

    else:
        # ── Generative branching from branch_points / endpoints ──
        # Build organic tree structure instead of grid fallback
        if branch_points and len(branch_points) >= 2:
            bp_arr = np.array(branch_points, dtype=float)
            bp_min = bp_arr.min(axis=0)
            bp_max = bp_arr.max(axis=0)
            bp_range = np.maximum(bp_max - bp_min, 1)

            # Normalize to wall coords
            bp_norm = []
            for bp in branch_points:
                uu = ((bp[1] - bp_min[1]) / bp_range[1]) * ww
                vv = ((bp[0] - bp_min[0]) / bp_range[0]) * wh
                bp_norm.append((uu, vv))

            # Connect with organic tree: find nearest-neighbor chain
            used = [False] * len(bp_norm)
            # Start from bottom-center-most point (likely trunk base)
            start_idx = min(range(len(bp_norm)),
                            key=lambda i: abs(bp_norm[i][0] - ww / 2) + (wh - bp_norm[i][1]))
            used[start_idx] = True
            queue = [start_idx]
            connections = []

            while queue:
                ci = queue.pop(0)
                cu, cv_c = bp_norm[ci]
                # Connect to nearest unused points
                dists = []
                for ni in range(len(bp_norm)):
                    if used[ni]:
                        continue
                    d = math.sqrt((bp_norm[ni][0] - cu) ** 2 + (bp_norm[ni][1] - cv_c) ** 2)
                    dists.append((d, ni))
                dists.sort()
                # Connect to up to 3 nearest
                max_conn = min(3, max(1, branch_depth_level))
                for d, ni in dists[:max_conn]:
                    if d > max(ww, wh) * 0.5:
                        break
                    connections.append((ci, ni))
                    used[ni] = True
                    queue.append(ni)

            for ci, ni in connections:
                u1, v1 = bp_norm[ci]
                u2, v2 = bp_norm[ni]
                _add_line_on_wall(model, layer_idx, o, u, v, u1, v1, u2, v2)
        else:
            # Last resort: generate organic branching from scratch
            _generate_organic_branches(model, layer_idx, o, u, v, n, ww, wh,
                                        depth, branch_depth_level, branch_angle_spread,
                                        taper, t, rng)


def _generate_organic_branches(model, layer_idx, o, u_dir, v_dir, n, ww, wh,
                                depth, max_levels, angle_spread, taper, t, rng):
    """Generate organic branching pattern from scratch (no extraction data)."""
    # Start with 1-2 trunks from the bottom
    trunk_count = 1 + int(t > 0.3)
    for ti in range(trunk_count):
        base_u = ww * (0.3 + 0.4 * ti / max(trunk_count - 1, 1)) if trunk_count > 1 else ww * 0.5
        base_u += rng.uniform(-ww * 0.05, ww * 0.05)

        _draw_branch(model, layer_idx, o, u_dir, v_dir, n,
                     base_u, 0.0, base_u + rng.uniform(-ww * 0.05, ww * 0.05), wh,
                     ww, wh, depth, max_levels, angle_spread, taper, rng, level=0)


def _draw_branch(model, layer_idx, o, u_dir, v_dir, n,
                 u1, v1, u2, v2, ww, wh, depth, levels_left, angle_spread, taper, rng,
                 level=0):
    """Recursively draw a branching structure on a wall surface."""
    if levels_left <= 0:
        return

    # Draw this branch as a polyline with slight organic curve
    steps = max(8, 20 - level * 4)
    pl = rhino3dm.Polyline(0)
    du, dv = u2 - u1, v2 - v1
    branch_len = math.sqrt(du ** 2 + dv ** 2)
    if branch_len < ww * 0.02:
        return

    # Rib depth tapers with hierarchy
    rib_depth = depth * (1.0 - level * 0.25)
    perp_u = -dv / branch_len
    perp_v = du / branch_len

    for si in range(steps + 1):
        t_s = si / steps
        # Slight sinusoidal wobble for organic feel
        wobble = math.sin(t_s * math.pi * 2) * branch_len * 0.03 * (1 + level * 0.5)
        uu = u1 + du * t_s + perp_u * wobble
        vv = v1 + dv * t_s + perp_v * wobble
        uu = max(0, min(uu, ww))
        vv = max(0, min(vv, wh))
        x = o[0] + u_dir[0] * uu + v_dir[0] * vv
        y = o[1] + u_dir[1] * uu + v_dir[1] * vv
        z = o[2] + u_dir[2] * uu + v_dir[2] * vv
        pl.Add(x, y, z)

    if pl.Count >= 2:
        model.Objects.AddCurve(pl.ToPolylineCurve(), attr(layer_idx))

    # Extruded copy for depth
    pl_ext = rhino3dm.Polyline(0)
    for si in range(steps + 1):
        t_s = si / steps
        wobble = math.sin(t_s * math.pi * 2) * branch_len * 0.03 * (1 + level * 0.5)
        uu = u1 + du * t_s + perp_u * wobble
        vv = v1 + dv * t_s + perp_v * wobble
        uu = max(0, min(uu, ww))
        vv = max(0, min(vv, wh))
        x = o[0] + u_dir[0] * uu + v_dir[0] * vv + n[0] * rib_depth
        y = o[1] + u_dir[1] * uu + v_dir[1] * vv + n[1] * rib_depth
        z = o[2] + u_dir[2] * uu + v_dir[2] * vv + n[2] * rib_depth
        pl_ext.Add(x, y, z)
    if pl_ext.Count >= 2:
        model.Objects.AddCurve(pl_ext.ToPolylineCurve(), attr(layer_idx))

    # Spawn child branches
    num_children = rng.integers(1, 4)
    for _ in range(num_children):
        # Branch off at a random point along this branch (biased toward middle-upper)
        branch_t = rng.uniform(0.3, 0.85)
        bu = u1 + du * branch_t
        bv = v1 + dv * branch_t

        # Branch angle
        angle = rng.uniform(-angle_spread, angle_spread) * math.pi / 180
        child_len = branch_len * taper * rng.uniform(0.5, 0.9)
        # Direction: parent direction rotated
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        cdu = (du * cos_a - dv * sin_a) / branch_len * child_len
        cdv = (du * sin_a + dv * cos_a) / branch_len * child_len

        eu = max(0, min(ww, bu + cdu))
        ev = max(0, min(wh, bv + cdv))

        _draw_branch(model, layer_idx, o, u_dir, v_dir, n,
                     bu, bv, eu, ev, ww, wh, depth * taper, levels_left - 1,
                     angle_spread * 1.1, taper, rng, level=level + 1)


def apply_pattern_to_wall(model, layer_idx, wall, extraction, category, depth=0.08,
                           evo=None):
    """Dispatch pattern application based on category, with optional evolution params."""
    if category == "cellular":
        # Pass hierarchical seeds if available, otherwise flat list
        seeds = extraction.get("seed_points_hierarchical", extraction.get("seed_points", []))
        _apply_voronoi_to_wall(model, layer_idx, wall, seeds,
                                extraction.get("cell_count", 20), depth, evo=evo)
    elif category == "branching":
        _apply_branching_to_wall(model, layer_idx, wall, extraction, depth, evo=evo)
    elif category == "lattice":
        _apply_lines_to_wall(model, layer_idx, wall, extraction, depth, evo=evo)
    elif category == "porous":
        _apply_circles_to_wall(model, layer_idx, wall, extraction, depth, evo=evo)
    elif category == "spiral":
        _apply_spiral_to_wall(model, layer_idx, wall, extraction, evo=evo)
    elif category == "shell":
        _apply_shell_to_wall(model, layer_idx, wall, extraction, depth, evo=evo)
    else:
        _apply_voronoi_to_wall(model, layer_idx, wall, [], 20, depth, evo=evo)


def _apply_spiral_to_wall(model, layer_idx, wall, extraction, evo=None):
    """Map spiral curves onto a wall surface using traced paths when available.

    If the extraction includes traced skeleton paths (from the actual image),
    uses those directly with hierarchy-based progressive reveal.
    Otherwise falls back to parametric spiral generation.
    """
    o = wall["origin"]
    u = wall["u"]
    v = wall["v"]
    ww = wall["width"]
    wh = wall["height"]

    if evo:
        t_floor = evo.get("t", 0.0)
        phase_shift = evo.get("phase_shift", 0.0)
        tightness = evo.get("tightness", 1.0)
        arm_count = evo.get("arm_count", extraction.get("arm_count", 3))
    else:
        t_floor = 0.0
        phase_shift = 0.0
        tightness = 1.0
        arm_count = extraction.get("arm_count", 3)

    rng = np.random.default_rng(42 + int(t_floor * 1000))

    # ── Try traced paths first (faithful to source image) ──
    lod_cap = _lod_cap_for_wall(ww, wh, MAX_PATHS)
    paths = extraction.get("paths", [])[:lod_cap]
    max_hierarchy = 0 if t_floor < 0.25 else (1 if t_floor < 0.6 else 2)

    if paths and len(paths) >= 2:
        all_pts = []
        for p in paths:
            pts = p["points"] if isinstance(p, dict) else p
            all_pts.extend(pts)
        if all_pts:
            all_arr = np.array(all_pts, dtype=float)
            r_min, c_min = all_arr.min(axis=0)
            r_max, c_max = all_arr.max(axis=0)
            r_range = max(r_max - r_min, 1)
            c_range = max(c_max - c_min, 1)

            for path_data in paths:
                if isinstance(path_data, dict):
                    pts = path_data["points"]
                    hier = path_data.get("hierarchy", 1)
                else:
                    pts = path_data
                    hier = 1
                if hier > max_hierarchy or len(pts) < 2:
                    continue

                step = max(1, len(pts) // 100)
                sampled = pts[::step]
                if sampled[-1] != pts[-1]:
                    sampled.append(pts[-1])

                pl = rhino3dm.Polyline(0)
                for (pr, pc) in sampled:
                    uu = ((pc - c_min) / c_range) * ww
                    vv = ((pr - r_min) / r_range) * wh
                    uu = max(0, min(uu, ww))
                    vv = max(0, min(vv, wh))
                    x = o[0] + u[0] * uu + v[0] * vv
                    y = o[1] + u[1] * uu + v[1] * vv
                    z = o[2] + u[2] * uu + v[2] * vv
                    pl.Add(x, y, z)
                if pl.Count >= 2:
                    model.Objects.AddCurve(pl.ToPolylineCurve(), attr(layer_idx))
            return  # used traced paths, skip parametric

    # ── Parametric spiral fallback ──
    for arm in range(arm_count):
        arm_offset = arm * (2 * math.pi / arm_count) + phase_shift
        pl = rhino3dm.Polyline(0)
        steps = int(200 + 300 * tightness)
        for i in range(steps):
            t = i / steps
            theta = t * 4 * math.pi * tightness + arm_offset
            amplitude = 0.4 * (0.3 + 0.7 * t) * (1.0 - 0.2 * t_floor)
            uu = (0.5 + amplitude * math.sin(theta)) * ww
            vv = t * wh
            x = o[0] + u[0] * uu + v[0] * vv
            y = o[1] + u[1] * uu + v[1] * vv
            z = o[2] + u[2] * uu + v[2] * vv
            pl.Add(x, y, z)
        if pl.Count >= 2:
            model.Objects.AddCurve(pl.ToPolylineCurve(), attr(layer_idx))

    # Cross-connecting arcs at higher floors
    if t_floor > 0.25:
        num_connectors = int(3 + 8 * t_floor)
        for ci in range(num_connectors):
            ct = (ci + 0.5) / num_connectors
            vv = ct * wh
            theta1 = ct * 4 * math.pi * tightness + phase_shift
            theta2 = theta1 + 2 * math.pi / arm_count
            arc_pl = rhino3dm.Polyline(0)
            for si in range(60):
                st = si / 59
                theta_i = theta1 + (theta2 - theta1) * st
                amp = 0.4 * (0.3 + 0.7 * ct) * (1.0 - 0.2 * t_floor)
                uu = (0.5 + amp * math.sin(theta_i)) * ww
                x = o[0] + u[0] * uu + v[0] * vv
                y = o[1] + u[1] * uu + v[1] * vv
                z = o[2] + u[2] * uu + v[2] * vv
                arc_pl.Add(x, y, z)
            if arc_pl.Count >= 2:
                model.Objects.AddCurve(arc_pl.ToPolylineCurve(), attr(layer_idx))


def _apply_shell_to_wall(model, layer_idx, wall, extraction, depth, evo=None):
    """Map shell/curvature pattern onto wall as undulating NURBS surface.

    With evolution: curvature amplitude increases, fold frequency grows,
    and a secondary high-frequency ripple layer emerges at upper floors.
    """
    o = wall["origin"]
    u_dir = wall["u"]
    v_dir = wall["v"]
    n = wall["normal"]
    ww = wall["width"]
    wh = wall["height"]

    if evo:
        t_floor = evo.get("t", 0.0)
        curvature_amp = evo.get("curvature_amp", 1.0)
        fold_freq = evo.get("fold_freq", 1.0)
        depth = evo.get("depth", depth)
    else:
        t_floor = 0.0
        curvature_amp = 1.0
        fold_freq = 1.0

    control_points = extraction.get("control_points", [])
    grid_u, grid_v = 20, 24

    surface = rhino3dm.NurbsSurface.Create(3, False, 4, 4, grid_u, grid_v)
    for i in range(grid_u + 2):
        surface.KnotsU[i] = float(i)
    for j in range(grid_v + 2):
        surface.KnotsV[j] = float(j)

    for i in range(grid_u):
        for j in range(grid_v):
            uu = (i / (grid_u - 1)) * ww
            vv = (j / (grid_v - 1)) * wh

            # Base depth from control points or primary wave
            if control_points and len(control_points) > j and len(control_points[0]) > i:
                cp = control_points[min(j, len(control_points) - 1)][min(i, len(control_points[0]) - 1)]
                d = float(cp[2]) * depth * 2 * curvature_amp
            else:
                d = depth * (0.5 + 0.5 * math.sin(i * 0.8 * fold_freq) *
                             math.cos(j * 0.6 * fold_freq)) * curvature_amp

            # Secondary ripple layer that emerges at higher floors
            if t_floor > 0.2:
                ripple_intensity = (t_floor - 0.2) / 0.8  # 0 to 1 over upper 80%
                ripple = depth * 0.3 * ripple_intensity * (
                    math.sin(i * 2.5 * fold_freq) * math.sin(j * 2.0 * fold_freq) +
                    0.3 * math.sin(i * 4.0) * math.cos(j * 3.5)
                )
                d += ripple

            x = o[0] + u_dir[0] * uu + v_dir[0] * vv + n[0] * d
            y = o[1] + u_dir[1] * uu + v_dir[1] * vv + n[1] * d
            z = o[2] + u_dir[2] * uu + v_dir[2] * vv + n[2] * d
            surface.Points[i, j] = rhino3dm.Point4d(x, y, z, 1.0)

    model.Objects.AddSurface(surface, attr(layer_idx))


# ─── Structural pattern between floors ───
