"""Cellular (Voronoi/Honeycomb) geometry generator.

Converts cell seed points from CV extraction into voronoi mesh panels.
"""
import rhino3dm
import numpy as np
from scipy.spatial import Voronoi


def generate_cellular(extraction_data: dict, panel_depth: float = 0.1,
                       scale: float = 1.0, bounds: tuple = (10.0, 10.0),
                       **kwargs) -> rhino3dm.File3dm:
    """Generate voronoi mesh panels from cellular extraction data."""
    model = rhino3dm.File3dm()

    cell_layer = rhino3dm.Layer()
    cell_layer.Name = "Voronoi_Cells"
    cell_layer.Color = (200, 100, 50, 255)
    model.Layers.Add(cell_layer)
    cell_layer_idx = len(model.Layers) - 1

    frame_layer = rhino3dm.Layer()
    frame_layer.Name = "Cell_Frames"
    frame_layer.Color = (80, 80, 80, 255)
    model.Layers.Add(frame_layer)
    frame_layer_idx = len(model.Layers) - 1

    seed_points = extraction_data.get("seed_points", [])
    if len(seed_points) < 4:
        seed_points = [(i * 2, j * 2) for i in range(5) for j in range(5)]

    # Normalize seed points to target bounds
    pts = np.array(seed_points, dtype=float)
    if pts.max() > 0:
        pts[:, 0] = pts[:, 0] / pts[:, 0].max() * bounds[0] * scale
        pts[:, 1] = pts[:, 1] / pts[:, 1].max() * bounds[1] * scale

    # Add boundary points to contain voronoi
    margin = max(bounds) * scale * 2
    boundary = np.array([
        [-margin, -margin], [bounds[0] * scale + margin, -margin],
        [-margin, bounds[1] * scale + margin],
        [bounds[0] * scale + margin, bounds[1] * scale + margin],
    ])
    all_pts = np.vstack([pts, boundary])

    vor = Voronoi(all_pts)

    for region_idx in vor.point_region[:len(pts)]:
        region = vor.regions[region_idx]
        if not region or -1 in region:
            continue

        vertices = [vor.vertices[i] for i in region]
        if len(vertices) < 3:
            continue

        clipped = _clip_polygon(vertices, bounds[0] * scale, bounds[1] * scale)
        if len(clipped) < 3:
            continue

        # Create mesh for this cell
        mesh = rhino3dm.Mesh()
        for v in clipped:
            mesh.Vertices.Add(v[0], v[1], 0.0)
        for v in clipped:
            mesh.Vertices.Add(v[0], v[1], panel_depth * scale)

        n = len(clipped)
        for i in range(1, n - 1):
            mesh.Faces.AddFace(0, i, i + 1)
        for i in range(1, n - 1):
            mesh.Faces.AddFace(n, n + i + 1, n + i)
        for i in range(n):
            j = (i + 1) % n
            mesh.Faces.AddFace(i, j, n + j, n + i)

        mesh.Normals.ComputeNormals()
        mesh.Compact()

        attr = rhino3dm.ObjectAttributes()
        attr.LayerIndex = cell_layer_idx
        model.Objects.AddMesh(mesh, attr)

        # Cell outline as polyline
        polyline = rhino3dm.Polyline(0)
        for v in clipped:
            polyline.Add(v[0], v[1], panel_depth * scale)
        polyline.Add(clipped[0][0], clipped[0][1], panel_depth * scale)
        curve = polyline.ToPolylineCurve()

        attr2 = rhino3dm.ObjectAttributes()
        attr2.LayerIndex = frame_layer_idx
        model.Objects.AddCurve(curve, attr2)

    return model


def _clip_polygon(vertices, max_x, max_y):
    """Clip polygon vertices to bounding box [0, max_x] x [0, max_y]."""
    clipped = []
    for v in vertices:
        x = max(0.0, min(float(v[0]), max_x))
        y = max(0.0, min(float(v[1]), max_y))
        clipped.append((x, y))
    result = [clipped[0]]
    for v in clipped[1:]:
        if abs(v[0] - result[-1][0]) > 1e-6 or abs(v[1] - result[-1][1]) > 1e-6:
            result.append(v)
    return result
