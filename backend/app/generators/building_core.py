"""Core building geometry — envelope, floor plates, walls, solid helpers.

Shared by all variation generators. Contains no pattern-specific logic.
"""
import math
import rhino3dm


# ─── Layer helpers ───

def add_layer(model, name, color):
    layer = rhino3dm.Layer()
    layer.Name = name
    layer.Color = color
    model.Layers.Add(layer)
    return len(model.Layers) - 1


def attr(layer_idx):
    attr = rhino3dm.ObjectAttributes()
    attr.LayerIndex = layer_idx
    return attr


# ─── Building Envelope ───

def generate_building_envelope(brief: dict) -> rhino3dm.File3dm:
    """Generate base building: site boundary, floor plates, wall outlines."""
    model = rhino3dm.File3dm()
    model.Settings.ModelUnitSystem = rhino3dm.UnitSystem.Meters

    site_idx = add_layer(model, "Site_Boundary", (100, 100, 100, 255))
    floor_idx = add_layer(model, "Floor_Plates", (180, 180, 180, 255))
    wall_idx = add_layer(model, "Walls", (140, 140, 140, 255))

    w, d = brief["bounds"]
    floors = brief["floors"]
    polygon = brief.get("site_polygon", [(0, 0), (w, 0), (w, d), (0, d)])

    # Site boundary at ground level
    site_pl = rhino3dm.Polyline(0)
    for pt in polygon:
        site_pl.Add(float(pt[0]), float(pt[1]), 0.0)
    site_pl.Add(float(polygon[0][0]), float(polygon[0][1]), 0.0)
    model.Objects.AddCurve(site_pl.ToPolylineCurve(), attr(site_idx))

    # Floor plates + wall outlines per floor
    for fl in floors:
        fw, fd, fh = fl["width"], fl["depth"], fl["height"]
        z = fl["z_offset"]
        ox = (w - fw) / 2
        oy = (d - fd) / 2

        add_floor_plate(model, floor_idx, ox, oy, fw, fd, z)
        add_wall_outlines(model, wall_idx, ox, oy, fw, fd, z, fh)

    # Roof plate
    last = floors[-1]
    roof_z = last["z_offset"] + last["height"]
    ox = (w - last["width"]) / 2
    oy = (d - last["depth"]) / 2
    add_floor_plate(model, floor_idx, ox, oy, last["width"], last["depth"], roof_z)

    return model


# ─── Floor Plates ───

def add_floor_plate(model, layer_idx, ox, oy, w, d, z):
    """Add a rectangular floor plate as a solid box mesh (200mm thick)."""
    FLOOR_THICKNESS = 0.2
    z_bot = z - FLOOR_THICKNESS
    z_top = z

    mesh = rhino3dm.Mesh()
    mesh.Vertices.Add(ox, oy, z_bot)
    mesh.Vertices.Add(ox + w, oy, z_bot)
    mesh.Vertices.Add(ox + w, oy + d, z_bot)
    mesh.Vertices.Add(ox, oy + d, z_bot)
    mesh.Vertices.Add(ox, oy, z_top)
    mesh.Vertices.Add(ox + w, oy, z_top)
    mesh.Vertices.Add(ox + w, oy + d, z_top)
    mesh.Vertices.Add(ox, oy + d, z_top)

    mesh.Faces.AddFace(0, 3, 2, 1)   # bottom
    mesh.Faces.AddFace(4, 5, 6, 7)   # top
    mesh.Faces.AddFace(0, 1, 5, 4)   # front
    mesh.Faces.AddFace(1, 2, 6, 5)   # right
    mesh.Faces.AddFace(2, 3, 7, 6)   # back
    mesh.Faces.AddFace(3, 0, 4, 7)   # left

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    model.Objects.AddMesh(mesh, attr(layer_idx))


# ─── Wall Outlines ───

def add_wall_outlines(model, layer_idx, ox, oy, w, d, z, h):
    """Add wall panels as solid box meshes (100mm thick)."""
    WALL_THICKNESS = 0.1

    walls = [
        ((ox, oy), (ox + w, oy), 0, -1),
        ((ox + w, oy), (ox + w, oy + d), 1, 0),
        ((ox + w, oy + d), (ox, oy + d), 0, 1),
        ((ox, oy + d), (ox, oy), -1, 0),
    ]
    for (x1, y1), (x2, y2), nx, ny in walls:
        ox1 = x1 + nx * WALL_THICKNESS
        oy1 = y1 + ny * WALL_THICKNESS
        ox2 = x2 + nx * WALL_THICKNESS
        oy2 = y2 + ny * WALL_THICKNESS

        mesh = rhino3dm.Mesh()
        mesh.Vertices.Add(x1, y1, z)
        mesh.Vertices.Add(x2, y2, z)
        mesh.Vertices.Add(ox2, oy2, z)
        mesh.Vertices.Add(ox1, oy1, z)
        mesh.Vertices.Add(x1, y1, z + h)
        mesh.Vertices.Add(x2, y2, z + h)
        mesh.Vertices.Add(ox2, oy2, z + h)
        mesh.Vertices.Add(ox1, oy1, z + h)

        mesh.Faces.AddFace(0, 1, 2, 3)
        mesh.Faces.AddFace(4, 7, 6, 5)
        mesh.Faces.AddFace(0, 4, 5, 1)
        mesh.Faces.AddFace(3, 2, 6, 7)
        mesh.Faces.AddFace(0, 3, 7, 4)
        mesh.Faces.AddFace(1, 5, 6, 2)

        mesh.Normals.ComputeNormals()
        mesh.Compact()
        model.Objects.AddMesh(mesh, attr(layer_idx))


# ─── Solid geometry helpers ───

COLUMN_RADIUS = 0.15
COLUMN_SEGMENTS = 12


def add_solid_column(model, layer_idx, cx, cy, z_bot, z_top, radius=COLUMN_RADIUS):
    """Add a column as a solid cylindrical mesh."""
    segs = COLUMN_SEGMENTS
    mesh = rhino3dm.Mesh()

    for i in range(segs):
        angle = 2 * math.pi * i / segs
        mesh.Vertices.Add(cx + radius * math.cos(angle), cy + radius * math.sin(angle), z_bot)
    for i in range(segs):
        angle = 2 * math.pi * i / segs
        mesh.Vertices.Add(cx + radius * math.cos(angle), cy + radius * math.sin(angle), z_top)
    mesh.Vertices.Add(cx, cy, z_bot)
    mesh.Vertices.Add(cx, cy, z_top)
    bc = 2 * segs
    tc = 2 * segs + 1

    for i in range(segs):
        j = (i + 1) % segs
        mesh.Faces.AddFace(bc, j, i)
    for i in range(segs):
        j = (i + 1) % segs
        mesh.Faces.AddFace(tc, segs + i, segs + j)
    for i in range(segs):
        j = (i + 1) % segs
        mesh.Faces.AddFace(i, j, segs + j, segs + i)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    model.Objects.AddMesh(mesh, attr(layer_idx))


def add_solid_beam(model, layer_idx, p1, p2, z_top, beam_depth, beam_width=0.2):
    """Add a beam as a solid rectangular box mesh between two column positions."""
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    z_bot = z_top - beam_depth

    dx, dy = x2 - x1, y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1e-6:
        return
    hw = beam_width / 2
    nx, ny = -dy / length * hw, dx / length * hw

    mesh = rhino3dm.Mesh()
    mesh.Vertices.Add(x1 - nx, y1 - ny, z_bot)
    mesh.Vertices.Add(x1 + nx, y1 + ny, z_bot)
    mesh.Vertices.Add(x2 + nx, y2 + ny, z_bot)
    mesh.Vertices.Add(x2 - nx, y2 - ny, z_bot)
    mesh.Vertices.Add(x1 - nx, y1 - ny, z_top)
    mesh.Vertices.Add(x1 + nx, y1 + ny, z_top)
    mesh.Vertices.Add(x2 + nx, y2 + ny, z_top)
    mesh.Vertices.Add(x2 - nx, y2 - ny, z_top)

    mesh.Faces.AddFace(0, 3, 2, 1)
    mesh.Faces.AddFace(4, 5, 6, 7)
    mesh.Faces.AddFace(0, 1, 5, 4)
    mesh.Faces.AddFace(2, 3, 7, 6)
    mesh.Faces.AddFace(0, 4, 7, 3)
    mesh.Faces.AddFace(1, 2, 6, 5)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    model.Objects.AddMesh(mesh, attr(layer_idx))


# ─── Wall surface helpers ───

def get_wall_surfaces(brief):
    """Return wall definitions for each facade (legacy: single bounding-box wall)."""
    floors = brief["floors"]
    w, d = brief["bounds"]
    total_h = brief["total_height"]
    active = brief.get("active_facades", ["north", "south", "east", "west"])

    base_fl = floors[0]
    fw, fd = base_fl["width"], base_fl["depth"]
    ox = (w - fw) / 2
    oy = (d - fd) / 2

    walls = {}
    walls["south"] = {"origin": (ox, oy, 0), "u": (1, 0, 0), "v": (0, 0, 1),
                       "width": fw, "height": total_h, "normal": (0, -1, 0)}
    walls["north"] = {"origin": (ox, oy + fd, 0), "u": (1, 0, 0), "v": (0, 0, 1),
                       "width": fw, "height": total_h, "normal": (0, 1, 0)}
    walls["east"] = {"origin": (ox + fw, oy, 0), "u": (0, 1, 0), "v": (0, 0, 1),
                      "width": fd, "height": total_h, "normal": (1, 0, 0)}
    walls["west"] = {"origin": (ox, oy, 0), "u": (0, 1, 0), "v": (0, 0, 1),
                      "width": fd, "height": total_h, "normal": (-1, 0, 0)}

    return {k: v for k, v in walls.items() if k in active}


def get_per_floor_wall_surfaces(brief):
    """Return wall definitions per floor — each floor gets its own wall segments."""
    floors = brief["floors"]
    w, d = brief["bounds"]
    num_floors = len(floors)
    active = brief.get("active_facades", ["north", "south", "east", "west"])

    per_floor = []
    for fi, fl in enumerate(floors):
        fw, fd, fh = fl["width"], fl["depth"], fl["height"]
        z = fl["z_offset"]
        ox = (w - fw) / 2
        oy = (d - fd) / 2
        t = fi / max(num_floors - 1, 1)

        walls = {}
        if "south" in active:
            walls["south"] = {"origin": (ox, oy, z), "u": (1, 0, 0), "v": (0, 0, 1),
                               "width": fw, "height": fh, "normal": (0, -1, 0)}
        if "north" in active:
            walls["north"] = {"origin": (ox, oy + fd, z), "u": (1, 0, 0), "v": (0, 0, 1),
                               "width": fw, "height": fh, "normal": (0, 1, 0)}
        if "east" in active:
            walls["east"] = {"origin": (ox + fw, oy, z), "u": (0, 1, 0), "v": (0, 0, 1),
                              "width": fd, "height": fh, "normal": (1, 0, 0)}
        if "west" in active:
            walls["west"] = {"origin": (ox, oy, z), "u": (0, 1, 0), "v": (0, 0, 1),
                              "width": fd, "height": fh, "normal": (-1, 0, 0)}

        per_floor.append({
            "floor_index": fi,
            "t": t,
            "floor": fl,
            "walls": walls,
        })

    return per_floor


# ─── Pattern evolution ───

def evolve_pattern_params(category, extraction, t, floor_width, floor_depth, base_depth=0.08):
    """Compute evolved pattern parameters for a floor at vertical position t (0=ground, 1=top)."""
    depth_curve = base_depth * (1.0 + 0.6 * t)
    density_mult = 1.0 + 1.2 * t
    scale_factor = 1.0 - 0.3 * t

    params = {
        "depth": depth_curve,
        "density_mult": density_mult,
        "scale_factor": scale_factor,
        "t": t,
        "floor_width": floor_width,
        "floor_depth": floor_depth,
    }

    if category == "cellular":
        base_count = extraction.get("cell_count", 20)
        params["cell_count"] = int(base_count * density_mult)
        params["irregularity"] = 0.1 + 0.5 * t
        params["subdivide"] = t > 0.5
        params["min_cell_area"] = max(0.05, 0.2 * scale_factor)
    elif category == "branching":
        params["branch_depth"] = max(1, int(2 + 3 * t))
        params["branch_angle_spread"] = 25 + 35 * t
        params["taper"] = 0.8 - 0.3 * t
    elif category == "porous":
        params["hole_scale"] = 1.2 - 0.6 * t
        params["density_gradient"] = density_mult
        params["min_radius"] = 0.05 * scale_factor
    elif category == "lattice":
        base_angles = extraction.get("dominant_angles", [0.0, math.pi / 2])
        rotation = t * math.pi / 6
        params["angles"] = [a + rotation for a in base_angles[:2]]
        params["spacing_mult"] = scale_factor
    elif category == "spiral":
        params["phase_shift"] = t * math.pi
        params["tightness"] = 1.0 + 2.0 * t
        params["arm_count"] = extraction.get("arm_count", 3)
    elif category == "shell":
        params["curvature_amp"] = 1.0 + 1.5 * t
        params["fold_freq"] = 1.0 + t

    return params
