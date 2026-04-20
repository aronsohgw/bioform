# BioForm — Project Plan

## Vision
Web app that converts nature images into parametric Rhino/Grasshopper files for architectural facades and structures, using biomimicry pattern analysis.

---

## Architecture Overview

```
┌─────────────┐     ┌──────────────────────────────────────┐     ┌──────────────┐
│  React +    │     │         Python / FastAPI              │     │   Output     │
│  Three.js   │────▶│                                      │────▶│   .3dm       │
│  Frontend   │     │  ┌─────────┐  ┌──────────┐  ┌─────┐ │     │   .ghx       │
│             │◀────│  │ OpenCV  │  │ Ollama   │  │rhino│ │     │   previews   │
│  - Upload   │     │  │ scikit  │  │ LLaMA3.2 │  │3dm  │ │     └──────────────┘
│  - Brief    │     │  │ image   │  │ Vision   │  │     │ │
│  - Preview  │     │  └─────────┘  └──────────┘  └─────┘ │
│  - Download │     └──────────────────────────────────────┘
└─────────────┘
```

## Pipeline

1. **Image Upload** → user submits nature photo (or searches Unsplash)
2. **Project Brief** → user fills site boundary (polygon), building, floors, dimensions, facades
3. **CV Extraction** → Multi-scale OpenCV/scikit-image: 3 hierarchy levels per category
4. **LLM Classification** → Ollama LLaMA 3.2 Vision: pattern category + rationale (runs parallel with CV)
5. **Parametric Generation** → rhino3dm: 3 variations (facade, structure, room layout) as solid geometry in meters
6. **Preview** → Three.js in-browser 3D preview with Default + Arctic view modes, layer toggles
7. **Export** → downloadable .3dm + .ghx per variation

---

## Phases

### Phase 1: Foundation
- [x] Project scaffolding (backend + frontend)
- [x] Python environment + dependencies (opencv, scikit-image, fastapi, httpx, scipy, python-dotenv)
- [x] Ollama integration (LLaMA 3.2 Vision) — classify_image + parse response
- [x] Basic image upload endpoint — POST /api/upload with validation
- [x] OpenCV pattern extraction pipeline — all 6 categories with multi-scale hierarchy
- [x] LLM classification prompt + few-shot templates
- [x] rhino3dm install — working on Python 3.11

### Phase 2: 3D Generation Core
- [x] rhino3dm geometry generators per biomimicry category
  - [x] Cellular (voronoi, honeycomb) — Voronoi mesh panels with extruded depth
  - [x] Branching (fractal, dendritic) — Traced skeleton paths with hierarchy
  - [x] Shell/Surface (curvature, folding) — NURBS surface from multi-scale height map
  - [x] Lattice/Grid (woven, tessellation) — Multi-scale HoughLines with progressive detail
  - [x] Spiral (fibonacci, helical) — Traced spiral paths + parametric fallback
  - [x] Porous (perforated, gradient density) — Multi-scale holes with boundary contours
- [x] .ghx parametric template generation — GHXBuilder + 6 category templates
- [x] Variation engine (3 outputs: facade, structure, room layout)
  - [x] Per-floor wall surfaces (replaces bounding-box approach)
  - [x] Adaptive pattern evolution per floor (density, depth, complexity increase with height)
  - [x] Structural beams via Delaunay triangulation + pattern-influenced column placement
  - [x] Room generation from pattern logic (Voronoi rooms, lattice grid rooms, branching corridor spine)
  - [x] Regeneration endpoint (POST /api/regenerate-variation) — no image re-upload needed
  - [x] Frontend VariationPopup with dynamic sliders per variation type
  - [x] Slider value persistence across popup opens (applied_params)
- [x] Scale system (module 1-3m, small 5-15m, large 15m+)
- [x] Solid geometry (200mm floor plates, 100mm walls, cylindrical columns, box beams)
- [x] Units set to meters (rhino3dm.UnitSystem.Meters)

### Phase 3: Project Brief Integration
- [x] Brief form UI (site polygon presets + custom, building, floors, dimensions, facades)
- [x] Static vs Varying floor dimension logic
  - [x] Manual per-floor input
  - [x] Rule-based (taper ratio, setback amount/interval)
- [x] Brief constraints → generation parameters mapping (polygon bounds, floor stack, facade selection)
- [x] Single building (multi-building removed)
- [x] Brief is optional — "Skip Brief" button generates with defaults

### Phase 4: Web App
- [x] React + Vite frontend scaffold (dark theme, responsive)
- [x] Image upload UI (drag-and-drop + click, file validation)
- [x] Brief form component
- [x] Three.js 3D preview viewer (OrbitControls, rhino3dm.js parsing, mesh + curve + point rendering)
- [x] Default + Arctic view modes
- [x] Layer visibility panel (toggle individual Rhino layers)
- [x] Download manager (.3dm per variation + .ghx)
- [x] Responsive layout (sidebar + viewer split)
- [x] Backend POST /api/generate endpoint (SSE progress streaming)
- [x] Backend GET /api/download/{file_id} endpoint
- [x] Progress bar with percentage during analysis
- [x] LLM + CV run in parallel for faster generation
- [x] Image downscaled for Ollama to speed up classification

### Phase 5: Polish & Deploy
- [x] Loading states + progress indicators (SSE progress bar)
- [ ] Error handling + validation (edge cases)
- [ ] Deploy frontend (Vercel)
- [ ] Deploy backend (Railway/Fly)
- [ ] End-to-end testing

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Frontend | React + Three.js |
| Backend | Python 3.11 / FastAPI |
| CV Analysis | OpenCV + scikit-image |
| LLM Analysis | Ollama + LLaMA 3.2 Vision 11B |
| 3D Generation | rhino3dm (Python) |
| Grasshopper | .ghx XML generation |
| 3D Preview | Three.js / rhino3dm.js |
| Hosting | Vercel + Railway/Fly |

## Dev Practices

- **TDD**: Tests first for all generation logic
- **SkillMD**: Document reusable skills as .md files
- **Plan-with-File**: This file — keep it current
- **Few-Shot Prompts**: Stored in `/skills/prompts/` for Ollama vision
- **Skill Creator**: New capabilities registered as skills

---

## Current Phase: Phase 5 (Polish & Deploy)
## Current Status: Phases 1-4 complete (89/89 backend tests). Image Trace phase with 6-option visual selector (no LLM needed). Server-side trace caching. 30s timeout per generator with cancel button. Solid geometry in meters. Default + Arctic view modes. Layer toggles. Slider persistence. building.py split into 4 focused modules. BioForm_Report.docx auto-generated on save. Next: error handling edge cases, deployment.
