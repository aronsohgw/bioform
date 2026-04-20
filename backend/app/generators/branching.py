"""Branching (Fractal/Dendritic) geometry generator.

Converts branch points and endpoints into a curve network representing
structural columns or canopy branching.
"""
import math
import rhino3dm
import numpy as np


def generate_branching(extraction_data: dict, branch_angle: float = 30.0,
                        taper_ratio: float = 0.7, levels: int = 4,
                        scale: float = 1.0, height: float = 10.0,
                        **kwargs) -> rhino3dm.File3dm:
    """Generate branching curve network from extraction data."""
    model = rhino3dm.File3dm()

    trunk_layer = rhino3dm.Layer()
    trunk_layer.Name = "Branch_Trunk"
    trunk_layer.Color = (120, 80, 40, 255)
    model.Layers.Add(trunk_layer)
    trunk_idx = len(model.Layers) - 1

    branch_layer = rhino3dm.Layer()
    branch_layer.Name = "Branch_Secondary"
    branch_layer.Color = (160, 120, 60, 255)
    model.Layers.Add(branch_layer)
    branch_idx = len(model.Layers) - 1

    tip_layer = rhino3dm.Layer()
    tip_layer.Name = "Branch_Tips"
    tip_layer.Color = (100, 160, 60, 255)
    model.Layers.Add(tip_layer)
    tip_idx = len(model.Layers) - 1

    branch_points = extraction_data.get("branch_points", [])
    num_branches = max(2, min(len(branch_points), 5)) if branch_points else 2
    angle_rad = math.radians(branch_angle)

    root_x, root_y, root_z = 0.0, 0.0, 0.0
    if branch_points:
        pts = np.array(branch_points, dtype=float)
        max_dim = max(pts.max(), 1)
        root_x = (pts[:, 1].mean() / max_dim) * scale * 5.0
        root_y = (pts[:, 0].mean() / max_dim) * scale * 5.0

    _generate_branch_tree(
        model, trunk_idx, branch_idx, tip_idx,
        start=rhino3dm.Point3d(root_x, root_y, root_z),
        direction=(0, 0, 1),
        length=height * scale,
        angle_spread=angle_rad,
        num_children=num_branches,
        taper=taper_ratio,
        level=0,
        max_level=levels,
    )

    return model


def _generate_branch_tree(model, trunk_idx, branch_idx, tip_idx,
                           start, direction, length,
                           angle_spread, num_children, taper,
                           level, max_level):
    """Recursively generate branch curves."""
    dx, dy, dz = direction
    norm = math.sqrt(dx**2 + dy**2 + dz**2)
    if norm < 1e-6:
        return
    dx, dy, dz = dx / norm, dy / norm, dz / norm

    end = rhino3dm.Point3d(
        start.X + dx * length,
        start.Y + dy * length,
        start.Z + dz * length,
    )

    polyline = rhino3dm.Polyline(0)
    polyline.Add(start.X, start.Y, start.Z)
    polyline.Add(end.X, end.Y, end.Z)
    curve = polyline.ToPolylineCurve()

    if level == 0:
        layer_idx = trunk_idx
    elif level < max_level:
        layer_idx = branch_idx
    else:
        layer_idx = tip_idx

    attr = rhino3dm.ObjectAttributes()
    attr.LayerIndex = layer_idx
    model.Objects.AddCurve(curve, attr)

    if level >= max_level:
        return

    child_length = length * taper

    for i in range(num_children):
        frac = (i / max(num_children - 1, 1)) - 0.5 if num_children > 1 else 0
        angle = frac * angle_spread * 2

        if abs(dz) < 0.9:
            perp_x, perp_y, perp_z = -dy, dx, 0
        else:
            perp_x, perp_y, perp_z = 1, 0, 0

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        twist = (i * 2 * math.pi / num_children)
        cos_t = math.cos(twist)
        sin_t = math.sin(twist)

        new_dx = dx * cos_a + perp_x * sin_a * cos_t
        new_dy = dy * cos_a + perp_y * sin_a + sin_t * 0.3
        new_dz = dz * cos_a + perp_z * sin_a

        _generate_branch_tree(
            model, trunk_idx, branch_idx, tip_idx,
            start=end,
            direction=(new_dx, new_dy, new_dz),
            length=child_length,
            angle_spread=angle_spread,
            num_children=max(2, num_children - 1),
            taper=taper,
            level=level + 1,
            max_level=max_level,
        )
