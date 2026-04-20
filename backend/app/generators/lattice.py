"""Lattice/Grid (Woven/Tessellation) geometry generator.

Converts detected grid lines and intersections into polyline grid with mesh infill.
"""
import math
import rhino3dm
import numpy as np


def generate_lattice(extraction_data: dict, member_thickness: float = 0.05,
                      depth: float = 0.15, scale: float = 1.0,
                      bounds: tuple = (10.0, 10.0), **kwargs) -> rhino3dm.File3dm:
    """Generate lattice/grid geometry from extraction data."""
    model = rhino3dm.File3dm()

    grid_layer = rhino3dm.Layer()
    grid_layer.Name = "Lattice_Grid"
    grid_layer.Color = (60, 60, 60, 255)
    model.Layers.Add(grid_layer)
    grid_idx = len(model.Layers) - 1

    node_layer = rhino3dm.Layer()
    node_layer.Name = "Lattice_Nodes"
    node_layer.Color = (200, 60, 60, 255)
    model.Layers.Add(node_layer)
    node_idx = len(model.Layers) - 1

    infill_layer = rhino3dm.Layer()
    infill_layer.Name = "Lattice_Infill"
    infill_layer.Color = (180, 180, 160, 255)
    model.Layers.Add(infill_layer)
    infill_idx = len(model.Layers) - 1

    lines = extraction_data.get("lines", [])

    sx = bounds[0] * scale
    sy = bounds[1] * scale

    if not lines or len(lines) < 2:
        lines = []
        spacing = sx / 10
        for i in range(11):
            x = i * spacing
            lines.append([[x, 0, x, sy]])
        for j in range(11):
            y = j * spacing
            lines.append([[0, y, sx, y]])

    # Normalize lines to bounds
    all_coords = []
    for line_group in lines:
        if isinstance(line_group[0], list):
            coords = line_group[0]
        else:
            coords = line_group
        all_coords.append(coords)

    if all_coords:
        flat = np.array(all_coords, dtype=float)
        x_vals = np.concatenate([flat[:, 0], flat[:, 2]])
        y_vals = np.concatenate([flat[:, 1], flat[:, 3]])
        x_max = max(x_vals.max(), 1)
        y_max = max(y_vals.max(), 1)

        for coords in all_coords:
            x1 = coords[0] / x_max * sx
            y1 = coords[1] / y_max * sy
            x2 = coords[2] / x_max * sx
            y2 = coords[3] / y_max * sy

            polyline = rhino3dm.Polyline(0)
            polyline.Add(x1, y1, 0)
            polyline.Add(x2, y2, 0)

            attr = rhino3dm.ObjectAttributes()
            attr.LayerIndex = grid_idx
            model.Objects.AddCurve(polyline.ToPolylineCurve(), attr)

            polyline_top = rhino3dm.Polyline(0)
            polyline_top.Add(x1, y1, depth * scale)
            polyline_top.Add(x2, y2, depth * scale)
            model.Objects.AddCurve(polyline_top.ToPolylineCurve(), attr)

    # Add node circles at intersections
    intersections = extraction_data.get("intersections", [])
    if intersections:
        int_arr = np.array(intersections, dtype=float)
        ix_max = max(int_arr[:, 0].max(), 1)
        iy_max = max(int_arr[:, 1].max(), 1)
        for pt in intersections:
            nx = float(pt[0]) / ix_max * sx
            ny = float(pt[1]) / iy_max * sy
            circle = rhino3dm.Circle(
                rhino3dm.Point3d(nx, ny, depth * scale),
                member_thickness * scale * 2,
            )
            attr = rhino3dm.ObjectAttributes()
            attr.LayerIndex = node_idx
            model.Objects.AddCurve(circle.ToNurbsCurve(), attr)

    # Infill mesh
    grid_count = 10
    mesh = rhino3dm.Mesh()
    for i in range(grid_count + 1):
        for j in range(grid_count + 1):
            x = (i / grid_count) * sx
            y = (j / grid_count) * sy
            mesh.Vertices.Add(x, y, depth * scale * 0.5)

    for i in range(grid_count):
        for j in range(grid_count):
            v0 = i * (grid_count + 1) + j
            v1 = v0 + 1
            v2 = v0 + (grid_count + 1) + 1
            v3 = v0 + (grid_count + 1)
            mesh.Faces.AddFace(v0, v1, v2, v3)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    attr = rhino3dm.ObjectAttributes()
    attr.LayerIndex = infill_idx
    model.Objects.AddMesh(mesh, attr)

    return model
