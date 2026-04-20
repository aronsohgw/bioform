"""Shell/Surface (Curvature/Folding) geometry generator.

Converts height map control points into NURBS surface with Z-displacement.
"""
import rhino3dm
import numpy as np


def generate_shell(extraction_data: dict, curvature_intensity: float = 2.0,
                    scale: float = 1.0, bounds: tuple = (10.0, 10.0),
                    **kwargs) -> rhino3dm.File3dm:
    """Generate NURBS surface from shell extraction data."""
    model = rhino3dm.File3dm()

    surface_layer = rhino3dm.Layer()
    surface_layer.Name = "Shell_Surface"
    surface_layer.Color = (180, 180, 220, 255)
    model.Layers.Add(surface_layer)
    surface_idx = len(model.Layers) - 1

    contour_layer = rhino3dm.Layer()
    contour_layer.Name = "Shell_Contours"
    contour_layer.Color = (100, 100, 160, 255)
    model.Layers.Add(contour_layer)
    contour_idx = len(model.Layers) - 1

    control_points = extraction_data.get("control_points", [])

    if not control_points or len(control_points) < 3:
        control_points = []
        for i in range(8):
            row = []
            for j in range(8):
                z = 0.5 + 0.3 * np.sin(i * 0.8) * np.cos(j * 0.8)
                row.append((j, i, z))
            control_points.append(row)

    count_v = len(control_points)
    count_u = len(control_points[0])

    while count_u < 4:
        for row in control_points:
            row.append(row[-1])
        count_u = len(control_points[0])
    while count_v < 4:
        control_points.append(list(control_points[-1]))
        count_v = len(control_points)

    degree_u = min(3, count_u - 1)
    degree_v = min(3, count_v - 1)

    surface = rhino3dm.NurbsSurface.Create(
        3, False,
        degree_u + 1, degree_v + 1,
        count_u, count_v,
    )

    for i in range(count_u + degree_u - 1):
        surface.KnotsU[i] = float(i)
    for j in range(count_v + degree_v - 1):
        surface.KnotsV[j] = float(j)

    span_x = bounds[0] * scale
    span_y = bounds[1] * scale

    for i in range(count_u):
        for j in range(count_v):
            pt = control_points[j][i]
            x = (i / max(count_u - 1, 1)) * span_x
            y = (j / max(count_v - 1, 1)) * span_y
            z = float(pt[2]) * curvature_intensity * scale
            surface.Points[i, j] = rhino3dm.Point4d(x, y, z, 1.0)

    attr = rhino3dm.ObjectAttributes()
    attr.LayerIndex = surface_idx
    model.Objects.AddSurface(surface, attr)

    # Add contour polylines at Z intervals
    num_contours = 5
    z_values = np.linspace(0, curvature_intensity * scale, num_contours + 2)[1:-1]
    for z_val in z_values:
        pts_at_z = []
        for i in range(count_u):
            for j in range(count_v):
                pt = control_points[j][i]
                pz = float(pt[2]) * curvature_intensity * scale
                if abs(pz - z_val) < curvature_intensity * scale * 0.15:
                    x = (i / max(count_u - 1, 1)) * span_x
                    y = (j / max(count_v - 1, 1)) * span_y
                    pts_at_z.append((x, y, z_val))

        if len(pts_at_z) >= 2:
            polyline = rhino3dm.Polyline(0)
            for p in pts_at_z:
                polyline.Add(p[0], p[1], p[2])
            attr2 = rhino3dm.ObjectAttributes()
            attr2.LayerIndex = contour_idx
            model.Objects.AddCurve(polyline.ToPolylineCurve(), attr2)

    return model
