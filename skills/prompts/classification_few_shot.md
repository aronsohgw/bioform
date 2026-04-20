# Few-Shot Classification Prompt Templates

Templates for Ollama LLaMA 3.2 Vision biomimicry classification.

## Base System Context

```
You are a biomimicry pattern analyst for architectural applications. You analyze nature photographs and classify the dominant geometric pattern for use in parametric building design.
```

## Few-Shot Examples

### Cellular
**Image description**: Close-up of dragonfly wing membrane
**Expected output**:
```json
{
    "category": "cellular",
    "confidence": 0.92,
    "rationale": "The image shows a clear network of irregular polygonal cells formed by the wing veins, resembling a Voronoi tessellation. Cell sizes vary from small near the wing edge to larger in the center, creating a natural density gradient.",
    "architectural_suggestions": [
        "Voronoi-based facade panels with varying cell density for graduated shading",
        "Load-distributing partition walls using irregular cell geometry",
        "Acoustic ceiling panels with voronoi cell pattern for sound scattering"
    ]
}
```

### Branching
**Image description**: Bare tree silhouette against sky
**Expected output**:
```json
{
    "category": "branching",
    "confidence": 0.95,
    "rationale": "The image displays a hierarchical branching network radiating from a central trunk. Each branch subdivides into progressively thinner members, following a fractal-like pattern with consistent branching angles.",
    "architectural_suggestions": [
        "Tree-column structural system distributing roof loads from point to area",
        "Branching canopy structure for large-span pavilion coverage",
        "Dendritic facade relief pattern creating organic depth variation"
    ]
}
```

### Shell/Surface
**Image description**: Curled autumn leaf with visible curvature
**Expected output**:
```json
{
    "category": "shell",
    "confidence": 0.88,
    "rationale": "The leaf exhibits compound curvature — a primary curl along its length axis with secondary rippling along the edges. This double-curvature creates structural rigidity in an extremely thin material.",
    "architectural_suggestions": [
        "Folded-plate facade panels that gain rigidity from curvature rather than material thickness",
        "Self-shading roof shell with undulating surface geometry",
        "Curved wall partitions that resist lateral loads through form rather than mass"
    ]
}
```

### Lattice/Grid
**Image description**: Spider web with morning dew
**Expected output**:
```json
{
    "category": "lattice",
    "confidence": 0.91,
    "rationale": "The web shows a highly regular radial-and-spiral grid structure. Primary radial threads provide tension framework while spiral threads create a regular mesh with consistent spacing that decreases toward the center.",
    "architectural_suggestions": [
        "Diagrid structural system with radial and circumferential members",
        "Woven facade screen with interlocking strips creating variable transparency",
        "Cable-net roof structure inspired by web tension geometry"
    ]
}
```

### Spiral
**Image description**: Sunflower seed head viewed from above
**Expected output**:
```json
{
    "category": "spiral",
    "confidence": 0.93,
    "rationale": "The seed head displays classic Fibonacci phyllotaxis — two families of spirals (clockwise and counter-clockwise) with counts following the Fibonacci sequence. Seeds are packed at golden-angle intervals for optimal density.",
    "architectural_suggestions": [
        "Facade panel arrangement using Fibonacci spiral for non-repeating organic distribution",
        "Sunshade fin layout with spiral positioning for all-day varying shade angles",
        "Floor plan circulation organized around golden-ratio spiral paths"
    ]
}
```

### Porous
**Image description**: Cross-section of bone (trabecular/spongy bone)
**Expected output**:
```json
{
    "category": "porous",
    "confidence": 0.89,
    "rationale": "The bone cross-section shows a gradient porosity pattern — dense cortical bone on the exterior transitioning to highly porous trabecular structure in the interior. Pore sizes and density respond to structural load paths.",
    "architectural_suggestions": [
        "Perforated facade screen with load-responsive porosity gradient (dense at supports, open at midspan)",
        "Ventilation panel with variable pore size controlling airflow rate by zone",
        "Structural optimization panel — material only where loads demand it, voids elsewhere"
    ]
}
```

## Usage Notes

- Always respond with exactly ONE category
- Confidence should reflect how clearly the pattern matches (>0.8 = strong match, 0.5-0.8 = partial, <0.5 = ambiguous)
- Architectural suggestions should be specific and practical, referencing scale (facade, structure, panel, etc.)
- If multiple patterns are present, classify by the DOMINANT one
