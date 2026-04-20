"""Room generation — layout rooms, corridors, and spaces on floor plates.

Dispatches to category-specific room generators (Voronoi, lattice grid,
branching corridor spine) based on the detected biomimicry pattern.
"""
import math
import rhino3dm
import numpy as np
from scipy.spatial import Voronoi

from app.generators.building_core import attr


# ─── Room generation helpers ───

def _clip_polygon_to_rect(polygon, x_min, y_min, x_max, y_max):
    """Sutherland-Hodgman polygon clipping against a rectangle."""
    def clip_edge(poly, edge_func, inside_func):
        if not poly:
            return []
        output = []
        for i in range(len(poly)):
            curr = poly[i]
            prev = poly[i - 1]
            curr_inside = inside_func(curr)
            prev_inside = inside_func(prev)
            if curr_inside:
                if not prev_inside:
                    output.append(edge_func(prev, curr))
                output.append(curr)
            elif prev_inside:
                output.append(edge_func(prev, curr))
        return output

    def intersect_left(p1, p2):
        t = (x_min - p1[0]) / (p2[0] - p1[0]) if abs(p2[0] - p1[0]) > 1e-10 else 0
        return (x_min, p1[1] + t * (p2[1] - p1[1]))

    def intersect_right(p1, p2):
        t = (x_max - p1[0]) / (p2[0] - p1[0]) if abs(p2[0] - p1[0]) > 1e-10 else 0
        return (x_max, p1[1] + t * (p2[1] - p1[1]))

    def intersect_bottom(p1, p2):
        t = (y_min - p1[1]) / (p2[1] - p1[1]) if abs(p2[1] - p1[1]) > 1e-10 else 0
        return (p1[0] + t * (p2[0] - p1[0]), y_min)

    def intersect_top(p1, p2):
        t = (y_max - p1[1]) / (p2[1] - p1[1]) if abs(p2[1] - p1[1]) > 1e-10 else 0
        return (p1[0] + t * (p2[0] - p1[0]), y_max)

    result = list(polygon)
    result = clip_edge(result, intersect_left, lambda p: p[0] >= x_min)
    result = clip_edge(result, intersect_right, lambda p: p[0] <= x_max)
    result = clip_edge(result, intersect_bottom, lambda p: p[1] >= y_min)
    result = clip_edge(result, intersect_top, lambda p: p[1] <= y_max)
    return result


def _add_room_walls(model, layer_idx, polygon, z, wall_height):
    """Add wall panels as solid box meshes for a room polygon at given z level.

    Accepts 2+ points. For 2 points, creates a single wall segment.
    For 3+ points, creates wall segments around the polygon perimeter.
    """
    WALL_THICKNESS = 0.1  # 100mm
    if len(polygon) < 2:
        return
    # For 2-point "polygon", just create one wall segment (no wrapping)
    num_segments = len(polygon) - 1 if len(polygon) == 2 else len(polygon)
    for i in range(num_segments):
        j = (i + 1) % len(polygon)
        p1, p2 = polygon[i], polygon[j]
        x1, y1 = float(p1[0]), float(p1[1])
        x2, y2 = float(p2[0]), float(p2[1])

        # Compute outward normal for this wall segment
        dx, dy = x2 - x1, y2 - y1
        seg_len = math.sqrt(dx * dx + dy * dy)
        if seg_len < 1e-6:
            continue
        nx, ny = -dy / seg_len * WALL_THICKNESS, dx / seg_len * WALL_THICKNESS

        mesh = rhino3dm.Mesh()
        mesh.Vertices.Add(x1, y1, z)               # 0
        mesh.Vertices.Add(x2, y2, z)               # 1
        mesh.Vertices.Add(x2 + nx, y2 + ny, z)     # 2
        mesh.Vertices.Add(x1 + nx, y1 + ny, z)     # 3
        mesh.Vertices.Add(x1, y1, z + wall_height)               # 4
        mesh.Vertices.Add(x2, y2, z + wall_height)               # 5
        mesh.Vertices.Add(x2 + nx, y2 + ny, z + wall_height)     # 6
        mesh.Vertices.Add(x1 + nx, y1 + ny, z + wall_height)     # 7

        mesh.Faces.AddFace(0, 1, 2, 3)   # bottom
        mesh.Faces.AddFace(4, 7, 6, 5)   # top
        mesh.Faces.AddFace(0, 4, 5, 1)   # inner
        mesh.Faces.AddFace(3, 2, 6, 7)   # outer
        mesh.Faces.AddFace(0, 3, 7, 4)   # start cap
        mesh.Faces.AddFace(1, 5, 6, 2)   # end cap

        mesh.Normals.ComputeNormals()
        mesh.Compact()
        model.Objects.AddMesh(mesh, attr(layer_idx))


def _add_room_floor_mesh(model, layer_idx, polygon, z):
    """Add a filled floor mesh as a solid slab (200mm thick)."""
    FLOOR_THICKNESS = 0.2  # 200mm
    if len(polygon) < 3:
        return
    n = len(polygon)
    mesh = rhino3dm.Mesh()

    # Bottom vertices (0..n-1), top vertices (n..2n-1)
    for pt in polygon:
        mesh.Vertices.Add(float(pt[0]), float(pt[1]), z - FLOOR_THICKNESS)
    for pt in polygon:
        mesh.Vertices.Add(float(pt[0]), float(pt[1]), z)

    # Bottom face (winding reversed for downward normal)
    for i in range(1, n - 1):
        mesh.Faces.AddFace(0, i + 1, i)
    # Top face
    for i in range(1, n - 1):
        mesh.Faces.AddFace(n, n + i, n + i + 1)
    # Side faces
    for i in range(n):
        j = (i + 1) % n
        mesh.Faces.AddFace(i, j, n + j, n + i)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    model.Objects.AddMesh(mesh, attr(layer_idx))


def _generate_voronoi_rooms(model, wall_layer, floor_layer, corridor_layer,
                             ox, oy, fw, fd, z, fh, extraction, custom_params):
    """Generate rooms from Voronoi cells on the floor plate."""
    room_count = int(custom_params.get("room_count", 8))
    corridor_width = custom_params.get("corridor_width", 2.0)
    openness = custom_params.get("openness", 0.3)
    wall_height = fh - 0.2  # leave gap for ceiling

    rng = np.random.default_rng(42 + int(z * 100))

    # Generate seed points for rooms
    seed_points = extraction.get("seed_points", [])
    if seed_points and len(seed_points) >= 3:
        pts = np.array(seed_points, dtype=float)
        pts[:, 0] = (pts[:, 0] / max(pts[:, 0].max(), 1)) * fw + ox
        pts[:, 1] = (pts[:, 1] / max(pts[:, 1].max(), 1)) * fd + oy
        # Resample to match room_count
        if len(pts) > room_count:
            indices = rng.choice(len(pts), room_count, replace=False)
            pts = pts[indices]
        elif len(pts) < room_count:
            extra = np.column_stack([
                rng.uniform(ox, ox + fw, room_count - len(pts)),
                rng.uniform(oy, oy + fd, room_count - len(pts)),
            ])
            pts = np.vstack([pts, extra])
    else:
        pts = np.column_stack([
            rng.uniform(ox + corridor_width, ox + fw - corridor_width, room_count),
            rng.uniform(oy + corridor_width, oy + fd - corridor_width, room_count),
        ])

    # Add boundary points for Voronoi
    margin = max(fw, fd) * 2
    boundary = np.array([
        [ox - margin, oy - margin], [ox + fw + margin, oy - margin],
        [ox - margin, oy + fd + margin], [ox + fw + margin, oy + fd + margin],
    ])
    all_pts = np.vstack([pts, boundary])

    vor = Voronoi(all_pts)

    rooms = []
    for pi, region_idx in enumerate(vor.point_region[:len(pts)]):
        region = vor.regions[region_idx]
        if not region or -1 in region:
            continue
        verts = [vor.vertices[i] for i in region]
        if len(verts) < 3:
            continue

        # Clip to floor boundary
        clipped = _clip_polygon_to_rect(verts, ox, oy, ox + fw, oy + fd)
        if len(clipped) < 3:
            continue

        rooms.append(clipped)

    # Draw rooms — skip some walls based on openness
    for room in rooms:
        skip = rng.random() < openness
        if not skip:
            _add_room_walls(model, wall_layer, room, z, wall_height)
        _add_room_floor_mesh(model, floor_layer, room, z)

    # Add corridor spine down the center
    _add_corridor_spine(model, corridor_layer, ox, oy, fw, fd, z, corridor_width)


def _generate_lattice_rooms(model, wall_layer, floor_layer, corridor_layer,
                             ox, oy, fw, fd, z, fh, extraction, custom_params):
    """Generate rooms from grid lines on the floor plate."""
    room_count = int(custom_params.get("room_count", 8))
    corridor_width = custom_params.get("corridor_width", 2.0)
    openness = custom_params.get("openness", 0.3)
    wall_height = fh - 0.2

    rng = np.random.default_rng(42 + int(z * 100))

    # Determine grid divisions from room_count
    nx = max(2, int(math.sqrt(room_count * fw / fd)))
    ny = max(2, int(room_count / nx))

    # Get angles from extraction or use orthogonal
    dominant_angles = extraction.get("dominant_angles", [0.0, math.pi / 2])
    angle = dominant_angles[0] if dominant_angles else 0.0
    # Keep angle small enough that rooms are usable
    angle = max(-math.pi / 6, min(math.pi / 6, angle))

    # Generate grid lines
    for i in range(1, nx):
        u = ox + i * fw / nx
        # Slight rotation for visual interest
        offset = math.tan(angle) * fd * 0.3
        pl = rhino3dm.Polyline(0)
        pl.Add(u - offset, oy, z)
        pl.Add(u + offset, oy + fd, z)
        model.Objects.AddCurve(pl.ToPolylineCurve(), attr(wall_layer))
        # Wall as solid mesh
        if rng.random() > openness:
            _add_room_walls(model, wall_layer, [(u, oy), (u, oy + fd)], z, wall_height)

    for j in range(1, ny):
        v = oy + j * fd / ny
        pl = rhino3dm.Polyline(0)
        pl.Add(ox, v, z)
        pl.Add(ox + fw, v, z)
        model.Objects.AddCurve(pl.ToPolylineCurve(), attr(wall_layer))
        if rng.random() > openness:
            _add_room_walls(model, wall_layer, [(ox, v), (ox + fw, v)], z, wall_height)

    # Floor meshes per cell
    for i in range(nx):
        for j in range(ny):
            x1, x2 = ox + i * fw / nx, ox + (i + 1) * fw / nx
            y1, y2 = oy + j * fd / ny, oy + (j + 1) * fd / ny
            cell = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            _add_room_floor_mesh(model, floor_layer, cell, z)

    _add_corridor_spine(model, corridor_layer, ox, oy, fw, fd, z, corridor_width)


def _generate_branching_rooms(model, wall_layer, floor_layer, corridor_layer,
                               ox, oy, fw, fd, z, fh, extraction, custom_params):
    """Generate rooms using branching pattern — main spine is corridor, branches create rooms."""
    room_count = int(custom_params.get("room_count", 8))
    corridor_width = custom_params.get("corridor_width", 2.0)
    openness = custom_params.get("openness", 0.3)
    wall_height = fh - 0.2

    rng = np.random.default_rng(42 + int(z * 100))

    # Main corridor spine along the longer axis
    if fw >= fd:
        # Horizontal spine
        spine_y = oy + fd / 2
        spine_start = (ox, spine_y)
        spine_end = (ox + fw, spine_y)
        room_dir = "vertical"
    else:
        # Vertical spine
        spine_x = ox + fw / 2
        spine_start = (spine_x, oy)
        spine_end = (spine_x, oy + fd)
        room_dir = "horizontal"

    # Draw corridor
    hw = corridor_width / 2
    if room_dir == "vertical":
        corridor_poly = [
            (ox, spine_y - hw), (ox + fw, spine_y - hw),
            (ox + fw, spine_y + hw), (ox, spine_y + hw),
        ]
        _add_room_floor_mesh(model, corridor_layer, corridor_poly, z)
        # Corridor walls as solid meshes
        for y_wall in [spine_y - hw, spine_y + hw]:
            _add_room_walls(model, corridor_layer,
                            [(ox, y_wall), (ox + fw, y_wall)], z, wall_height)

        # Rooms on each side of corridor
        rooms_per_side = max(1, room_count // 2)
        room_width = fw / rooms_per_side
        for side, (y_start, y_end) in enumerate([(oy, spine_y - hw), (spine_y + hw, oy + fd)]):
            if y_end - y_start < 1.0:
                continue
            for ri in range(rooms_per_side):
                x1 = ox + ri * room_width
                x2 = x1 + room_width
                room = [(x1, y_start), (x2, y_start), (x2, y_end), (x1, y_end)]
                _add_room_floor_mesh(model, floor_layer, room, z)
                if rng.random() > openness:
                    _add_room_walls(model, wall_layer, room, z, wall_height)
    else:
        corridor_poly = [
            (spine_start[0] - hw, oy), (spine_start[0] + hw, oy),
            (spine_start[0] + hw, oy + fd), (spine_start[0] - hw, oy + fd),
        ]
        _add_room_floor_mesh(model, corridor_layer, corridor_poly, z)
        for x_wall in [spine_start[0] - hw, spine_start[0] + hw]:
            _add_room_walls(model, corridor_layer,
                            [(x_wall, oy), (x_wall, oy + fd)], z, wall_height)

        rooms_per_side = max(1, room_count // 2)
        room_depth = fd / rooms_per_side
        for side, (x_start, x_end) in enumerate([(ox, spine_start[0] - hw),
                                                   (spine_start[0] + hw, ox + fw)]):
            if x_end - x_start < 1.0:
                continue
            for ri in range(rooms_per_side):
                y1 = oy + ri * room_depth
                y2 = y1 + room_depth
                room = [(x_start, y1), (x_end, y1), (x_end, y2), (x_start, y2)]
                _add_room_floor_mesh(model, floor_layer, room, z)
                if rng.random() > openness:
                    _add_room_walls(model, wall_layer, room, z, wall_height)

    # Add branch corridors from extraction data
    branch_points = extraction.get("branch_points", [])
    if branch_points and len(branch_points) >= 2:
        for bp in branch_points[:min(len(branch_points), room_count // 2)]:
            by, bx = bp[0], bp[1] if len(bp) > 1 else bp[0]
            # Normalize to floor
            bx_n = ox + (bx / max(max(b[1] for b in branch_points if len(b) > 1), 1)) * fw
            by_n = oy + (by / max(max(b[0] for b in branch_points), 1)) * fd
            # Short branch corridor from spine
            if room_dir == "vertical":
                br_pl = rhino3dm.Polyline(0)
                br_pl.Add(bx_n, spine_y, z)
                br_pl.Add(bx_n, by_n, z)
                model.Objects.AddCurve(br_pl.ToPolylineCurve(), attr(corridor_layer))


def _generate_default_rooms(model, wall_layer, floor_layer, corridor_layer,
                             ox, oy, fw, fd, z, fh, extraction, custom_params):
    """Fallback room generation — simple grid with corridor."""
    _generate_lattice_rooms(model, wall_layer, floor_layer, corridor_layer,
                             ox, oy, fw, fd, z, fh, extraction, custom_params)


def _add_corridor_spine(model, layer_idx, ox, oy, fw, fd, z, corridor_width):
    """Add a central corridor mesh on the floor plate."""
    hw = corridor_width / 2
    if fw >= fd:
        # Horizontal corridor
        cy = oy + fd / 2
        corridor = [(ox, cy - hw), (ox + fw, cy - hw),
                     (ox + fw, cy + hw), (ox, cy + hw)]
    else:
        cx = ox + fw / 2
        corridor = [(cx - hw, oy), (cx + hw, oy),
                     (cx + hw, oy + fd), (cx - hw, oy + fd)]
    _add_room_floor_mesh(model, layer_idx, corridor, z)


def generate_rooms_on_floor(model, wall_layer, floor_layer, corridor_layer,
                             ox, oy, fw, fd, z, fh, extraction, category, custom_params):
    """Dispatch room generation based on category."""
    if category == "cellular":
        _generate_voronoi_rooms(model, wall_layer, floor_layer, corridor_layer,
                                 ox, oy, fw, fd, z, fh, extraction, custom_params)
    elif category == "lattice":
        _generate_lattice_rooms(model, wall_layer, floor_layer, corridor_layer,
                                 ox, oy, fw, fd, z, fh, extraction, custom_params)
    elif category == "branching":
        _generate_branching_rooms(model, wall_layer, floor_layer, corridor_layer,
                                   ox, oy, fw, fd, z, fh, extraction, custom_params)
    else:
        # Porous, spiral, shell — use Voronoi as a good default for organic patterns
        _generate_voronoi_rooms(model, wall_layer, floor_layer, corridor_layer,
                                 ox, oy, fw, fd, z, fh, extraction, custom_params)

