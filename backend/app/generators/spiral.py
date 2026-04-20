"""Spiral (Fibonacci/Helical) geometry generator.

Converts spiral center and arm data into helical curves.
"""
import math
import rhino3dm


def generate_spiral(extraction_data: dict, pitch: float = 1.0,
                     growth_rate: float = 1.618, scale: float = 1.0,
                     height: float = 10.0, **kwargs) -> rhino3dm.File3dm:
    """Generate spiral/helical curves from extraction data."""
    model = rhino3dm.File3dm()

    spiral_layer = rhino3dm.Layer()
    spiral_layer.Name = "Spiral_Curves"
    spiral_layer.Color = (180, 120, 60, 255)
    model.Layers.Add(spiral_layer)
    spiral_idx = len(model.Layers) - 1

    ring_layer = rhino3dm.Layer()
    ring_layer.Name = "Spiral_Rings"
    ring_layer.Color = (120, 160, 80, 255)
    model.Layers.Add(ring_layer)
    ring_idx = len(model.Layers) - 1

    point_layer = rhino3dm.Layer()
    point_layer.Name = "Spiral_Points"
    point_layer.Color = (200, 80, 80, 255)
    model.Layers.Add(point_layer)
    point_idx = len(model.Layers) - 1

    arm_count = max(1, extraction_data.get("arm_count", 3))
    max_radius = extraction_data.get("max_radius", 50) * scale * 0.1
    golden_angle = 2 * math.pi / growth_rate

    # Generate helical spiral arms
    for arm in range(arm_count):
        arm_offset = arm * (2 * math.pi / arm_count)
        num_samples = 100

        polyline = rhino3dm.Polyline(0)
        for i in range(num_samples):
            t = i / num_samples
            theta = t * 4 * math.pi + arm_offset
            r = 0.5 * scale + max_radius * t
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            z = t * height * scale * pitch
            polyline.Add(x, y, z)

        if polyline.Count >= 2:
            attr = rhino3dm.ObjectAttributes()
            attr.LayerIndex = spiral_idx
            model.Objects.AddCurve(polyline.ToPolylineCurve(), attr)

    # Reference rings at intervals
    num_rings = 8
    for i in range(1, num_rings + 1):
        z = (i / num_rings) * height * scale * pitch
        r = 0.5 * scale + max_radius * (i / num_rings)
        circle = rhino3dm.Circle(rhino3dm.Point3d(0, 0, z), r)
        attr = rhino3dm.ObjectAttributes()
        attr.LayerIndex = ring_idx
        model.Objects.AddCurve(circle.ToNurbsCurve(), attr)

    # Fibonacci-distributed points on a disc
    num_fib_points = 50
    for i in range(num_fib_points):
        theta = i * golden_angle
        r = max_radius * math.sqrt(i / num_fib_points)
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        attr = rhino3dm.ObjectAttributes()
        attr.LayerIndex = point_idx
        model.Objects.AddPoint(rhino3dm.Point3d(x, y, 0), attr)

    return model
