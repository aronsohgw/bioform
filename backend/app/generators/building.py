"""Building variation generators — facade, structure, room layout.

Each generator creates a complete .3dm model by:
1. Building the envelope (floors, walls) via building_core
2. Applying pattern-specific geometry via pattern_applicators or room_generator
"""
import math
import rhino3dm
import numpy as np
from scipy.spatial import Delaunay

from app.generators.building_core import (
    add_layer,
    attr,
    generate_building_envelope,
    get_per_floor_wall_surfaces,
    evolve_pattern_params,
    add_solid_column,
    add_solid_beam,
)
from app.generators.pattern_applicators import apply_pattern_to_wall
from app.generators.room_generator import generate_rooms_on_floor


# ─── Structural columns ───

def _add_branching_columns(model, layer_idx, ox, oy, fw, fd, z, fh, extraction):
    """Branching tree-columns from floor to ceiling as solid meshes."""
    branch_count = max(extraction.get("branch_count", 3), 2)
    nx = max(2, int(fw / 6))
    ny = max(2, int(fd / 6))

    for i in range(nx):
        for j in range(ny):
            cx = ox + (i + 0.5) / nx * fw
            cy = oy + (j + 0.5) / ny * fd
            add_solid_column(model, layer_idx, cx, cy, z, z + fh * 0.6, radius=0.15)
            for b in range(min(branch_count, 4)):
                angle = b * 2 * math.pi / min(branch_count, 4)
                spread = min(fw, fd) / nx * 0.4
                bx = cx + spread * math.cos(angle)
                by = cy + spread * math.sin(angle)
                add_solid_beam(model, layer_idx, (cx, cy), (bx, by),
                               z + fh, beam_depth=fh * 0.4, beam_width=0.12)


def _add_voronoi_columns(model, layer_idx, ox, oy, fw, fd, z, fh, extraction):
    """Voronoi-derived irregular column layout as solid meshes."""
    seed_points = extraction.get("seed_points", [])
    if len(seed_points) < 3:
        _add_grid_columns(model, layer_idx, ox, oy, fw, fd, z, fh)
        return
    pts = np.array(seed_points, dtype=float)
    pts[:, 0] = (pts[:, 0] / max(pts[:, 0].max(), 1)) * fw + ox
    pts[:, 1] = (pts[:, 1] / max(pts[:, 1].max(), 1)) * fd + oy
    for pt in pts:
        add_solid_column(model, layer_idx, float(pt[0]), float(pt[1]), z, z + fh)


def _add_grid_columns(model, layer_idx, ox, oy, fw, fd, z, fh):
    """Regular grid columns as solid meshes."""
    nx = max(2, int(fw / 6))
    ny = max(2, int(fd / 6))
    for i in range(nx):
        for j in range(ny):
            cx = ox + (i + 0.5) / nx * fw
            cy = oy + (j + 0.5) / ny * fd
            add_solid_column(model, layer_idx, cx, cy, z, z + fh)


# ─── Structural beams ───

def _add_structural_beams(model, layer_idx, column_positions, z_top, beam_depth=0.4,
                           max_span=None):
    """Connect columns with beams at floor plate level using Delaunay triangulation."""
    if len(column_positions) < 3:
        for i in range(len(column_positions)):
            for j in range(i + 1, len(column_positions)):
                p1, p2 = column_positions[i], column_positions[j]
                if max_span and math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) > max_span:
                    continue
                add_solid_beam(model, layer_idx, p1, p2, z_top, beam_depth)
        return

    pts = np.array(column_positions)
    tri = Delaunay(pts)
    edges = set()
    for simplex in tri.simplices:
        for i in range(3):
            j = (i + 1) % 3
            edge = tuple(sorted([simplex[i], simplex[j]]))
            edges.add(edge)

    for i, j in edges:
        p1, p2 = pts[i], pts[j]
        span = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
        if max_span and span > max_span:
            continue
        add_solid_beam(model, layer_idx, p1, p2, z_top, beam_depth)


def _get_pattern_column_positions(extraction, category, ox, oy, fw, fd, target_count):
    """Extract column positions from pattern data, normalized to floor bounds."""
    rng = np.random.default_rng(42)

    if category == "cellular":
        seed_points = extraction.get("seed_points", [])
        if len(seed_points) >= 3:
            pts = np.array(seed_points, dtype=float)
            pts[:, 0] = (pts[:, 0] / max(pts[:, 0].max(), 1)) * fw + ox
            pts[:, 1] = (pts[:, 1] / max(pts[:, 1].max(), 1)) * fd + oy
            if len(pts) > target_count:
                indices = rng.choice(len(pts), target_count, replace=False)
                pts = pts[indices]
            return pts.tolist()

    elif category == "branching":
        branch_points = extraction.get("branch_points", [])
        if len(branch_points) >= 3:
            pts = np.array(branch_points, dtype=float)
            pts[:, 0] = (pts[:, 0] / max(pts[:, 0].max(), 1)) * fd + oy
            pts[:, 1] = (pts[:, 1] / max(pts[:, 1].max(), 1)) * fw + ox
            pts = pts[:, ::-1]
            if len(pts) > target_count:
                indices = rng.choice(len(pts), target_count, replace=False)
                pts = pts[indices]
            return pts.tolist()

    elif category == "porous":
        holes = extraction.get("holes", [])
        if len(holes) >= 3:
            positions = []
            max_cx = max(h["center"][0] for h in holes) or 1
            max_cy = max(h["center"][1] for h in holes) or 1
            for h in holes[:target_count]:
                px = h["center"][0] / max_cx * fw + ox
                py = h["center"][1] / max_cy * fd + oy
                positions.append((px, py))
            return positions

    elif category == "lattice":
        intersections = extraction.get("intersections", [])
        if len(intersections) >= 3:
            pts = np.array(intersections[:target_count * 2], dtype=float)
            x_max = max(pts[:, 0].max(), 1)
            y_max = max(pts[:, 1].max(), 1)
            pts[:, 0] = pts[:, 0] / x_max * fw + ox
            pts[:, 1] = pts[:, 1] / y_max * fd + oy
            if len(pts) > target_count:
                indices = rng.choice(len(pts), target_count, replace=False)
                pts = pts[indices]
            return pts.tolist()

    return []


# ─── Variation generators ───

def generate_facade_variation(brief: dict, extraction: dict, category: str,
                               custom_params: dict = None) -> rhino3dm.File3dm:
    """Variation A: Pattern applied as facade treatment on building walls."""
    model = generate_building_envelope(brief)
    facade_idx = add_layer(model, "Facade_Pattern", (108, 99, 255, 255))

    per_floor = get_per_floor_wall_surfaces(brief)
    for floor_info in per_floor:
        t = floor_info["t"]
        fl = floor_info["floor"]
        evo = evolve_pattern_params(category, extraction, t, fl["width"], fl["depth"],
                                     base_depth=0.08)

        if custom_params:
            size = custom_params.get("pattern_size", 1.0)
            reps = custom_params.get("pattern_repetitions", 3)
            simplicity = custom_params.get("pattern_simplicity", 0.5)

            evo["scale_factor"] *= size
            evo["density_mult"] *= (reps / 3.0)
            evo["depth"] *= (0.5 + size * 0.5)

            if "cell_count" in evo:
                evo["cell_count"] = max(4, int(evo["cell_count"] * (reps / 3.0) / max(size, 0.3)))
            if "subdivide" in evo:
                evo["subdivide"] = simplicity < 0.4
            if "branch_depth" in evo:
                evo["branch_depth"] = max(1, int(evo["branch_depth"] * (1.0 - simplicity)))
            if "irregularity" in evo:
                evo["irregularity"] *= (1.0 - simplicity * 0.7)

        for name, wall in floor_info["walls"].items():
            apply_pattern_to_wall(model, facade_idx, wall, extraction, category,
                                   depth=0.08, evo=evo)

    return model


def generate_structural_variation(brief: dict, extraction: dict, category: str,
                                   custom_params: dict = None) -> rhino3dm.File3dm:
    """Variation B: Columns + beams derived from the natural pattern."""
    model = generate_building_envelope(brief)
    col_idx = add_layer(model, "Structural_Columns", (78, 205, 196, 255))
    beam_idx = add_layer(model, "Structural_Beams", (100, 180, 170, 255))

    column_spacing = 6.0
    beam_depth = 0.4
    pattern_influence = 0.7
    if custom_params:
        column_spacing = custom_params.get("column_spacing", 6.0)
        beam_depth = custom_params.get("beam_depth", 0.4)
        pattern_influence = custom_params.get("pattern_influence", 0.7)

    floors = brief["floors"]
    w, d = brief["bounds"]

    for fl in floors:
        fw, fd_fl, fh = fl["width"], fl["depth"], fl["height"]
        z = fl["z_offset"]
        ox = (w - fw) / 2
        oy = (d - fd_fl) / 2

        nx = max(2, int(fw / column_spacing))
        ny = max(2, int(fd_fl / column_spacing))
        grid_positions = []
        for i in range(nx):
            for j in range(ny):
                gx = ox + (i + 0.5) / nx * fw
                gy = oy + (j + 0.5) / ny * fd_fl
                grid_positions.append((gx, gy))

        pattern_positions = _get_pattern_column_positions(
            extraction, category, ox, oy, fw, fd_fl, len(grid_positions)
        )

        if pattern_positions and len(pattern_positions) >= 2:
            n = min(len(grid_positions), len(pattern_positions))
            grid_arr = np.array(grid_positions[:n])
            pat_arr = np.array(pattern_positions[:n])
            final_positions = (
                grid_arr * (1 - pattern_influence) + pat_arr * pattern_influence
            ).tolist()
        else:
            final_positions = grid_positions

        for pos in final_positions:
            add_solid_column(model, col_idx, float(pos[0]), float(pos[1]), z, z + fh)

        _add_structural_beams(model, beam_idx, final_positions, z + fh,
                               beam_depth=beam_depth,
                               max_span=column_spacing * 2)

    return model


def generate_room_variation(brief: dict, extraction: dict, category: str,
                             custom_params: dict = None) -> rhino3dm.File3dm:
    """Variation C: Pattern shapes rooms, corridors, and spaces on floor plates."""
    model = generate_building_envelope(brief)
    wall_layer = add_layer(model, "Room_Walls", (180, 140, 255, 255))
    floor_layer = add_layer(model, "Room_Floors", (160, 160, 170, 255))
    corridor_layer = add_layer(model, "Corridors", (78, 205, 196, 255))

    params = {
        "room_count": 8,
        "corridor_width": 2.0,
        "openness": 0.3,
    }
    if custom_params:
        params.update(custom_params)

    floors = brief["floors"]
    w, d = brief["bounds"]

    for fl in floors:
        fw, fd_fl, fh = fl["width"], fl["depth"], fl["height"]
        z = fl["z_offset"]
        ox = (w - fw) / 2
        oy = (d - fd_fl) / 2

        generate_rooms_on_floor(model, wall_layer, floor_layer, corridor_layer,
                                 ox, oy, fw, fd_fl, z, fh, extraction, category, params)

    return model
