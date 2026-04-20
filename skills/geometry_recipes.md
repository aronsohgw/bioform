# Skill: Geometry Recipes

Reusable rhino3dm patterns for generating 3D geometry in BioForm.

## When to Use
Any time you create or modify 3D output in the generation pipeline. Reference this before writing rhino3dm code.

## Core Primitives (rhino3dm Python)

### Point
```python
import rhino3dm

point = rhino3dm.Point3d(x, y, z)
```

### Line / Polyline
```python
polyline = rhino3dm.Polyline(point_count)
for i, pt in enumerate(points):
    polyline[i] = rhino3dm.Point3d(pt[0], pt[1], pt[2])

curve = polyline.ToPolylineCurve()
```

### Circle / Arc
```python
plane = rhino3dm.Plane.WorldXY()
circle = rhino3dm.Circle(plane, radius)
arc_curve = rhino3dm.ArcCurve(circle)
```

### NURBS Curve
```python
curve = rhino3dm.NurbsCurve(degree, point_count)
for i, pt in enumerate(control_points):
    curve.Points[i] = rhino3dm.Point4d(pt[0], pt[1], pt[2], 1.0)  # weight=1.0
```

### NURBS Surface
```python
surface = rhino3dm.NurbsSurface.Create(
    3,              # dimension
    False,          # is_rational
    degree_u + 1,   # order_u
    degree_v + 1,   # order_v
    count_u,        # control point count u
    count_v         # control point count v
)
for i in range(count_u):
    for j in range(count_v):
        surface.Points[i, j] = rhino3dm.Point4d(x, y, z, 1.0)
```

### Mesh
```python
mesh = rhino3dm.Mesh()
for pt in vertices:
    mesh.Vertices.Add(pt[0], pt[1], pt[2])
for face in faces:
    if len(face) == 3:
        mesh.Faces.AddFace(face[0], face[1], face[2])
    elif len(face) == 4:
        mesh.Faces.AddFace(face[0], face[1], face[2], face[3])
mesh.Normals.ComputeNormals()
mesh.Compact()
```

### Extrusion (panel/facade thickness)
```python
# Extrude a curve along a direction
extrusion = rhino3dm.Extrusion()
extrusion.SetPathAndUp(
    rhino3dm.Point3d(0, 0, 0),      # start
    rhino3dm.Point3d(0, 0, depth),   # end
    rhino3dm.Vector3d(0, 1, 0)       # up
)
```

## Writing to .3dm File
```python
model = rhino3dm.File3dm()
model.Objects.AddMesh(mesh)
model.Objects.AddCurve(curve)
model.Objects.AddSurface(surface)

# Add to named layer
layer = rhino3dm.Layer()
layer.Name = "Facade_Panel"
layer.Color = (200, 100, 50, 255)
model.Layers.Add(layer)
layer_index = model.Layers.Count - 1

attr = rhino3dm.ObjectAttributes()
attr.LayerIndex = layer_index
model.Objects.AddMesh(mesh, attr)

model.Write("output.3dm", version=8)
```

## Common Patterns for BioForm

### Voronoi → Mesh Panels
Generate voronoi cells from seed points → create mesh face per cell → optional depth extrusion for 3D panels.

### Branching → Curve Network
Start from root point → recursive subdivision with angle/length rules → NurbsCurve per branch segment.

### Surface Curvature → NURBS Surface
Sample height/curvature values from CV analysis → map to control point Z values → create NURBS surface.

### Grid/Lattice → Polyline Grid + Mesh Infill
Create regular or irregular grid of polylines → optionally mesh between grid lines → extrude for depth.

### Spiral → Helix Curve
Parametric curve: x=r*cos(t), y=r*sin(t), z=pitch*t → sample points → NurbsCurve fit.

### Porous → Mesh with Holes
Start with solid mesh surface → boolean subtract circles/polygons based on density map from CV.
