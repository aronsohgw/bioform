"""Porous (Perforated/Gradient Density) geometry generator.

Converts hole positions and density map into mesh surface with perforations.
"""
import math
import rhino3dm
import numpy as np


def generate_porous(extraction_data: dict, panel_depth: float = 0.1,
                     scale: float = 1.0, bounds: tuple = (10.0, 10.0),
                     **kwargs) -> rhino3dm.File3dm:
    """Generate perforated panel mesh from porous extraction data."""
    model = rhino3dm.File3dm()

    panel_layer = rhino3dm.Layer()
    panel_layer.Name = "Porous_Panel"
    panel_layer.Color = (200, 200, 200, 255)
    model.Layers.Add(panel_layer)
    panel_idx = len(model.Layers) - 1

    hole_layer = rhino3dm.Layer()
    hole_layer.Name = "Porous_Holes"
    hole_layer.Color = (80, 80, 80, 255)
    model.Layers.Add(hole_layer)
    hole_idx = len(model.Layers) - 1

    outline_layer = rhino3dm.Layer()
    outline_layer.Name = "Porous_Outline"
    outline_layer.Color = (40, 40, 40, 255)
    model.Layers.Add(outline_layer)
    outline_idx = len(model.Layers) - 1

    holes = extraction_data.get("holes", [])
    avg_radius = extraction_data.get("avg_hole_radius", 5.0)

    sx = bounds[0] * scale
    sy = bounds[1] * scale
    d = panel_depth * scale

    # Base panel mesh (box)
    mesh = rhino3dm.Mesh()
    mesh.Vertices.Add(0, 0, 0)
    mesh.Vertices.Add(sx, 0, 0)
    mesh.Vertices.Add(sx, sy, 0)
    mesh.Vertices.Add(0, sy, 0)
    mesh.Vertices.Add(0, 0, d)
    mesh.Vertices.Add(sx, 0, d)
    mesh.Vertices.Add(sx, sy, d)
    mesh.Vertices.Add(0, sy, d)

    mesh.Faces.AddFace(0, 1, 2, 3)
    mesh.Faces.AddFace(4, 7, 6, 5)
    mesh.Faces.AddFace(0, 4, 5, 1)
    mesh.Faces.AddFace(1, 5, 6, 2)
    mesh.Faces.AddFace(2, 6, 7, 3)
    mesh.Faces.AddFace(3, 7, 4, 0)

    mesh.Normals.ComputeNormals()
    mesh.Compact()

    attr = rhino3dm.ObjectAttributes()
    attr.LayerIndex = panel_idx
    model.Objects.AddMesh(mesh, attr)

    # Create hole circles
    if holes:
        max_cx = max(h["center"][0] for h in holes) or 1
        max_cy = max(h["center"][1] for h in holes) or 1
        max_r = max(h["radius"] for h in holes) or 1

        for hole in holes:
            cx = hole["center"][0] / max_cx * sx * 0.9 + sx * 0.05
            cy = hole["center"][1] / max_cy * sy * 0.9 + sy * 0.05
            r = hole["radius"] / max_r * avg_radius * scale * 0.05
            r = max(r, 0.05 * scale)

            # Circle on bottom and top
            for z in [0.0, d]:
                circle = rhino3dm.Circle(rhino3dm.Point3d(cx, cy, z), r)
                attr_h = rhino3dm.ObjectAttributes()
                attr_h.LayerIndex = hole_idx
                model.Objects.AddCurve(circle.ToNurbsCurve(), attr_h)

            # Connecting lines at cardinal points
            for angle in range(0, 360, 90):
                rad = math.radians(angle)
                px = cx + r * math.cos(rad)
                py = cy + r * math.sin(rad)
                line = rhino3dm.Polyline(0)
                line.Add(px, py, 0)
                line.Add(px, py, d)
                model.Objects.AddCurve(line.ToPolylineCurve(), attr_h)
    else:
        # Default gradient porous pattern
        grid_n = 8
        for i in range(grid_n):
            for j in range(grid_n):
                cx = (i + 0.5) / grid_n * sx
                cy = (j + 0.5) / grid_n * sy
                dist = math.sqrt((cx - sx / 2) ** 2 + (cy - sy / 2) ** 2)
                max_dist = math.sqrt((sx / 2) ** 2 + (sy / 2) ** 2)
                r = (0.3 + 0.4 * (1 - dist / max_dist)) * sx / grid_n * 0.4

                circle = rhino3dm.Circle(rhino3dm.Point3d(cx, cy, d), r)
                attr_h = rhino3dm.ObjectAttributes()
                attr_h.LayerIndex = hole_idx
                model.Objects.AddCurve(circle.ToNurbsCurve(), attr_h)

    # Panel outline
    outline = rhino3dm.Polyline(0)
    outline.Add(0, 0, d)
    outline.Add(sx, 0, d)
    outline.Add(sx, sy, d)
    outline.Add(0, sy, d)
    outline.Add(0, 0, d)

    attr_o = rhino3dm.ObjectAttributes()
    attr_o.LayerIndex = outline_idx
    model.Objects.AddCurve(outline.ToPolylineCurve(), attr_o)

    return model
