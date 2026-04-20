"""Generate the BioForm Project Report as a Word document.

Run this script to update docs/BioForm_Report.docx with current project state.
Called automatically during "saving now" sessions.
"""
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from datetime import datetime
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "BioForm_Report.docx")

# ─── Brand colours ───
BRAND_PRIMARY = RGBColor(45, 80, 56)      # Deep forest green
BRAND_ACCENT = RGBColor(108, 99, 255)     # Purple accent
BRAND_DARK = RGBColor(30, 30, 35)         # Near-black
BRAND_MID = RGBColor(100, 100, 110)       # Grey
BRAND_LIGHT = RGBColor(180, 180, 180)     # Light grey


def _set_cell_shading(cell, hex_color):
    """Apply background shading to a table cell."""
    shading = cell._element.get_or_add_tcPr()
    shading_elem = shading.makeelement(qn("w:shd"), {
        qn("w:fill"): hex_color,
        qn("w:val"): "clear",
    })
    shading.append(shading_elem)


def _add_styled_table(doc, headers, rows, col_widths=None):
    """Add a clean table with header row shading."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(255, 255, 255)
        _set_cell_shading(cell, "2D5038")

    # Data rows
    for row_data in rows:
        row = table.add_row()
        for i, val in enumerate(row_data):
            row.cells[i].text = val
            for p in row.cells[i].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(10)

    # Column widths
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Cm(w)

    doc.add_paragraph()
    return table


def _heading(doc, text, level=1):
    """Add heading with brand colour."""
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = BRAND_PRIMARY
    return h


def build_report():
    doc = Document()

    # ─── Default font ───
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style.font.color.rgb = BRAND_DARK

    # ─── Margins ───
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # ═══════════════════════════════════════════════
    # TITLE PAGE
    # ═══════════════════════════════════════════════
    for _ in range(6):
        doc.add_paragraph()

    title = doc.add_heading("BioForm", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.size = Pt(36)
        run.font.color.rgb = BRAND_PRIMARY

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Nature-to-Architecture Generator")
    run.font.size = Pt(18)
    run.font.color.rgb = BRAND_ACCENT

    doc.add_paragraph()

    tagline = doc.add_paragraph()
    tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = tagline.add_run(
        "Bridging biomimicry pattern analysis with parametric architectural design.\n"
        "A web application that converts nature images into Rhino (.3dm)\n"
        "and Grasshopper (.ghx) files for facades, structures, and spaces."
    )
    run.font.size = Pt(11)
    run.font.color.rgb = BRAND_MID

    for _ in range(6):
        doc.add_paragraph()

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run("Project Report")
    run.font.size = Pt(12)
    run.bold = True
    run.font.color.rgb = BRAND_DARK
    meta.add_run("\n")
    run = meta.add_run(f"Last updated: {datetime.now().strftime('%d %B %Y')}")
    run.font.size = Pt(10)
    run.font.color.rgb = BRAND_MID

    doc.add_page_break()

    # ═══════════════════════════════════════════════
    # TABLE OF CONTENTS (manual)
    # ═══════════════════════════════════════════════
    _heading(doc, "Contents", level=1)
    toc_items = [
        "1. Executive Summary",
        "2. Project Overview",
        "3. User Workflow",
        "4. Biomimicry Categories & Image Trace System",
        "5. Output Variations",
        "6. 3D Model Specification",
        "7. Preview System",
        "8. Technology Stack",
        "9. Architecture & Pipeline",
        "10. Performance Benchmarks",
        "11. Development Timeline",
        "12. Current Status & Next Steps",
    ]
    for item in toc_items:
        p = doc.add_paragraph(item)
        p.paragraph_format.space_after = Pt(2)
        for run in p.runs:
            run.font.color.rgb = BRAND_DARK

    doc.add_page_break()

    # ═══════════════════════════════════════════════
    # 1. EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════
    _heading(doc, "1. Executive Summary", level=1)
    doc.add_paragraph(
        "BioForm is a web-based tool that translates nature photographs into parametric "
        "architectural geometry. It addresses a persistent gap in computational design: "
        "while biomimicry is widely discussed in architecture, there are few tools that "
        "directly convert natural pattern observations into editable 3D building files."
    )
    doc.add_paragraph(
        "The application analyses uploaded images using six computer vision extraction "
        "approaches, each mapping onto a distinct biomimicry category (cellular, branching, "
        "lattice, porous, spiral, and shell). The user selects their preferred interpretation, "
        "defines building parameters through a project brief, and receives three parametric "
        "variations: a facade panel system, a structural column-and-beam layout, and a "
        "room/corridor plan \u2014 all derived from the same natural pattern."
    )
    doc.add_paragraph(
        "All processing runs locally with no paid API dependencies. Outputs are industry-standard "
        "Rhino (.3dm) and Grasshopper (.ghx) files, ready for further design development."
    )

    # ═══════════════════════════════════════════════
    # 2. PROJECT OVERVIEW
    # ═══════════════════════════════════════════════
    _heading(doc, "2. Project Overview", level=1)

    _heading(doc, "Problem Statement", level=2)
    doc.add_paragraph(
        "Architects inspired by natural forms face a manual, time-consuming process to "
        "translate biological patterns into parametric geometry. Existing tools require "
        "deep scripting knowledge (Grasshopper C#/Python, Rhino scripting) or expensive "
        "cloud-based generative AI services. There is no accessible pipeline from "
        "\"photograph of a leaf\" to \"editable building facade.\""
    )

    _heading(doc, "Solution", level=2)
    doc.add_paragraph(
        "BioForm provides an end-to-end web pipeline: upload a nature image, pick a "
        "pattern interpretation, define building parameters, and download parametric "
        "3D files \u2014 all within a browser, with no Rhino license required on the server."
    )

    _heading(doc, "Design Principles", level=2)
    principles = [
        ("Visual selection over algorithm", "The user picks the trace that looks right, "
         "rather than configuring extraction parameters."),
        ("Local-first", "All CV and generation runs on the user's machine. No cloud API costs."),
        ("Solid geometry", "Every output element is a proper solid mesh \u2014 not wireframe \u2014 "
         "ready for fabrication workflows."),
        ("Progressive detail", "Pattern complexity increases from ground floor to roof, "
         "reflecting natural growth hierarchies."),
    ]
    for name, desc in principles:
        p = doc.add_paragraph()
        run = p.add_run(f"{name}: ")
        run.bold = True
        run.font.color.rgb = BRAND_PRIMARY
        p.add_run(desc)

    # ═══════════════════════════════════════════════
    # 3. USER WORKFLOW
    # ═══════════════════════════════════════════════
    _heading(doc, "3. User Workflow", level=1)
    doc.add_paragraph(
        "The application follows a linear seven-step workflow. Each step produces "
        "a visible artefact that the user can review before proceeding."
    )
    steps = [
        ("Upload", "User uploads a nature image via drag-and-drop or searches Unsplash for reference "
         "photographs. The image is the sole creative input to the system."),
        ("Image Trace", "The backend runs all six CV extractors in parallel (~5 seconds). The frontend "
         "displays a 3\u00d72 grid of trace results. The user selects the interpretation that best "
         "captures the pattern they want to apply architecturally."),
        ("Project Brief", "An optional form where the user defines site polygon shape, floor count, "
         "floor height, dimension mode (static, taper, setback), and which facades receive the pattern. "
         "Skipping the brief applies sensible defaults (10\u00d710 m, 5 floors, 3 m height)."),
        ("3D Generation", "The system generates three parametric variations using the cached trace data "
         "and brief parameters. Each generator runs with a 30-second timeout. Progress streams via SSE."),
        ("3D Preview", "An in-browser Three.js viewer renders the .3dm file with orbit controls. "
         "Two display modes are available: Default (dark, purple materials) and Arctic (white matte "
         "with edge outlines). A layer panel allows toggling visibility of individual building systems."),
        ("Tweak", "Each variation has a slider popup for parameter adjustment (e.g. pattern size, "
         "column spacing, room count). Adjusted values persist across popup opens and variation switches."),
        ("Download", "The user downloads .3dm files per variation and a .ghx Grasshopper definition "
         "for the detected category. Files open directly in Rhino 8 and Grasshopper."),
    ]
    for i, (name, desc) in enumerate(steps, 1):
        p = doc.add_paragraph()
        run = p.add_run(f"Step {i}: {name}")
        run.bold = True
        run.font.color.rgb = BRAND_PRIMARY
        doc.add_paragraph(desc)

    # ═══════════════════════════════════════════════
    # 4. BIOMIMICRY CATEGORIES & IMAGE TRACE
    # ═══════════════════════════════════════════════
    _heading(doc, "4. Biomimicry Categories & Image Trace System", level=1)
    doc.add_paragraph(
        "Six extraction approaches run in parallel on the uploaded image, each tuned "
        "for a distinct class of natural pattern. Images are downscaled to 1024px for "
        "consistent processing. Each extractor produces multi-scale features tagged "
        "with a hierarchy level (primary, secondary, tertiary) for progressive "
        "architectural application."
    )

    _add_styled_table(doc,
        ["Category", "Extraction Method", "Architectural Application"],
        [
            ["Cellular", "Canny edge detection at 2 scales, smooth contour\napproximation, Voronoi seed points",
             "Facade panels, partition walls,\nfloor tiling patterns"],
            ["Branching", "Adaptive threshold, skeleton path tracing,\npaths tagged primary/secondary by length",
             "Structural tree columns, corridor\nspine networks, facade veins"],
            ["Lattice / Grid", "HoughLinesP line detection at 2 sensitivity\nscales with hierarchy tagging",
             "Structural grids, mullion patterns,\nregular facade subdivisions"],
            ["Porous", "Otsu threshold, hole boundary contours,\nsize-based hierarchy classification",
             "Perforated facades, ventilation\npatterns, light-filtering screens"],
            ["Spiral", "Skeleton-traced curved paths, radial profile\nanalysis, FFT arm count detection",
             "Ramp/stair layouts, facade\nswirl patterns, organic room flow"],
            ["Shell / Surface", "Height-mapped control point grid from\nblurred grayscale, curvature analysis",
             "Curved roof forms, undulating\nfacades, terrain-responsive floors"],
        ],
        col_widths=[3.5, 6.0, 5.0],
    )

    doc.add_paragraph(
        "Feature caps prevent excessive geometry: 100 contours, 60 paths, 150 lines, "
        "100 holes. Polygon approximation uses a low epsilon (0.005) to maintain smooth "
        "curves rather than angular segments."
    )

    # ═══════════════════════════════════════════════
    # 5. OUTPUT VARIATIONS
    # ═══════════════════════════════════════════════
    _heading(doc, "5. Output Variations", level=1)
    doc.add_paragraph(
        "Each generation produces three design variations, all derived from the same "
        "extracted pattern but applied to different architectural systems:"
    )

    variations = [
        ("A \u2014 Facade Panel",
         "The natural pattern is applied as an external wall treatment or screen. "
         "Pattern density and complexity evolve per floor (ground = bold primary features, "
         "upper floors = finer tertiary detail). Each facade face (N/S/E/W) can be "
         "independently activated in the brief.",
         "Pattern size, repetitions, simplicity"),
        ("B \u2014 Structure",
         "Columns and beams are derived from the pattern geometry. Cellular patterns "
         "produce Voronoi-based column grids; branching patterns create tree-like column "
         "layouts; lattice patterns generate regular structural grids. Beams connect "
         "columns via Delaunay triangulation.",
         "Column spacing, beam depth, pattern influence"),
        ("C \u2014 Room Layout",
         "The pattern shapes rooms, corridors, and open spaces on each floor plate. "
         "Cellular patterns create Voronoi room subdivisions; branching patterns generate "
         "spine corridors with rooms branching off; lattice patterns produce grid-based "
         "room arrangements.",
         "Target room count, corridor width, openness"),
    ]
    for name, desc, params in variations:
        _heading(doc, name, level=2)
        doc.add_paragraph(desc)
        p = doc.add_paragraph()
        run = p.add_run("Editable parameters: ")
        run.bold = True
        p.add_run(params)

    # ═══════════════════════════════════════════════
    # 6. 3D MODEL SPECIFICATION
    # ═══════════════════════════════════════════════
    _heading(doc, "6. 3D Model Specification", level=1)
    doc.add_paragraph(
        "All generated geometry follows consistent specifications for downstream "
        "compatibility with Rhino 8 and fabrication workflows:"
    )

    _add_styled_table(doc,
        ["Element", "Geometry Type", "Dimensions"],
        [
            ["Floor plates", "Solid box mesh (6-face)", "200 mm thick"],
            ["Walls (envelope)", "Solid box mesh", "100 mm thick"],
            ["Walls (rooms)", "Solid box mesh", "100 mm thick"],
            ["Columns", "Cylindrical mesh (12 segments)", "150 mm radius"],
            ["Beams", "Rectangular box mesh", "200 mm wide"],
            ["Facade panels", "Extruded solid mesh", "Variable depth per hierarchy"],
            ["Corridors", "Solid box mesh", "100 mm walls, variable width"],
        ],
        col_widths=[4.0, 5.0, 5.0],
    )

    props = [
        "Units: metres (rhino3dm.UnitSystem.Meters)",
        "All geometry is filled solid meshes \u2014 no wireframe or surface-only elements",
        "Rhino file version: 8 (.3dm v8)",
        "Layers: Site Boundary, Floor Plates, Walls, Facade Pattern, Structural Columns, "
        "Structural Beams, Room Walls, Room Floors, Corridors",
        "Voronoi subdivision capped at 60 seed points to prevent O(n\u00b2) computation",
        "Pattern applicator caps: 120 seed points, 200 lines, 150 holes, 80 paths",
    ]
    for prop in props:
        doc.add_paragraph(prop, style="List Bullet")

    # ═══════════════════════════════════════════════
    # 7. PREVIEW SYSTEM
    # ═══════════════════════════════════════════════
    _heading(doc, "7. Preview System", level=1)
    doc.add_paragraph(
        "The in-browser 3D preview uses Three.js with rhino3dm.js for native .3dm "
        "file parsing. Two display modes are available:"
    )

    _add_styled_table(doc,
        ["Mode", "Background", "Materials", "Special Features"],
        [
            ["Default", "Dark (#0a0a0f)", "Purple standard material,\nwireframe overlay",
             "Ambient + directional + fill lights"],
            ["Arctic", "Light (#f5f5f5)", "White matte (roughness 0.95),\nno wireframe",
             "Edge outlines, mimics Rhino\u2019s\nArctic display mode"],
        ],
        col_widths=[2.5, 3.0, 4.5, 4.5],
    )

    doc.add_paragraph(
        "A collapsible layer panel allows toggling visibility of individual building "
        "systems (floors, walls, facade, columns, beams, rooms, corridors). Layer "
        "visibility persists across variation switches and parameter regenerations, "
        "resetting only when a new image is uploaded."
    )

    # ═══════════════════════════════════════════════
    # 8. TECHNOLOGY STACK
    # ═══════════════════════════════════════════════
    _heading(doc, "8. Technology Stack", level=1)

    _add_styled_table(doc,
        ["Layer", "Technology", "Role"],
        [
            ["Frontend", "React 18 + Vite", "Single-page app, state management, UI"],
            ["3D Preview", "Three.js + rhino3dm.js", "In-browser .3dm parsing and rendering"],
            ["Backend", "Python 3.11 / FastAPI", "API endpoints, generation orchestration"],
            ["CV Analysis", "OpenCV + scikit-image", "6 biomimicry pattern extractors"],
            ["LLM (local-only)", "Ollama + LLaMA 3.2 Vision 11B", "Optional local classification; disabled in cloud build"],
            ["3D Generation", "rhino3dm (Python)", "Parametric .3dm file creation"],
            ["Grasshopper", "Programmatic XML", ".ghx definition generation"],
            ["Streaming", "Server-Sent Events (SSE)", "Real-time progress updates"],
        ],
        col_widths=[3.0, 5.0, 5.5],
    )

    doc.add_paragraph(
        "The stack runs locally for development and has also been deployed to a free-tier "
        "cloud environment (frontend on Vercel, backend on Render) for public access at "
        "https://bioform.vercel.app. The cloud build omits the optional local LLM so no "
        "paid AI services are required. The optional Unsplash integration (image search) "
        "uses a free API key."
    )

    # ═══════════════════════════════════════════════
    # 9. ARCHITECTURE & PIPELINE
    # ═══════════════════════════════════════════════
    _heading(doc, "9. Architecture & Pipeline", level=1)

    _heading(doc, "Request Flow", level=2)
    flow_steps = [
        "POST /api/trace \u2014 Upload image, run 6 CV extractors in parallel, return trace_id + all results",
        "User selects preferred trace category from 3\u00d72 grid",
        "User fills project brief (or skips for defaults)",
        "POST /api/generate \u2014 Send image + trace_id + trace_category + brief_json",
        "Backend retrieves cached trace data (no re-extraction), generates 3 variations",
        "Each variation runs in executor with 30s timeout, progress streamed via SSE",
        "Frontend receives session_id + file_ids, loads .3dm in Three.js viewer",
        "POST /api/regenerate-variation \u2014 Adjust single variation with custom slider params",
        "GET /api/download/{file_id} \u2014 Download .3dm or .ghx file",
    ]
    for i, step in enumerate(flow_steps, 1):
        doc.add_paragraph(f"{i}. {step}")

    _heading(doc, "Backend Module Structure", level=2)
    modules = [
        ("main.py", "API endpoints, SSE streaming, session/trace/file stores"),
        ("cv_extraction.py", "6 CV extractors with feature caps and 1024px downscaling"),
        ("variation_engine.py", "Variation configs, generation orchestration, scale system"),
        ("brief.py", "Brief validation and parameter conversion"),
        ("ghx_builder.py", "Grasshopper XML template generation"),
        ("generators/building.py", "3 variation generators (facade, structure, room)"),
        ("generators/building_core.py", "Building envelope, floors, walls, solid geometry helpers"),
        ("generators/pattern_applicators.py", "6 pattern-to-wall-surface mapping functions"),
        ("generators/room_generator.py", "Room layout and corridor generation"),
    ]
    for mod, desc in modules:
        p = doc.add_paragraph()
        run = p.add_run(f"{mod}")
        run.bold = True
        run.font.name = "Consolas"
        run.font.size = Pt(10)
        p.add_run(f" \u2014 {desc}")

    # ═══════════════════════════════════════════════
    # 10. PERFORMANCE BENCHMARKS
    # ═══════════════════════════════════════════════
    _heading(doc, "10. Performance Benchmarks", level=1)

    _add_styled_table(doc,
        ["Operation", "Duration", "Notes"],
        [
            ["Image Trace (6 extractors)", "~5 seconds", "Parallel execution on 1024px image"],
            ["3D Generation (3 variations)", "~5\u201310 seconds", "Cached trace data, 30s timeout each"],
            ["Single Variation Regeneration", "~2\u20133 seconds", "No re-analysis, slider params only"],
            ["3dm File Load (browser)", "~1\u20132 seconds", "rhino3dm.js WASM parsing"],
            ["Full Pipeline (trace \u2192 download)", "~15\u201325 seconds", "Including user selection time"],
        ],
        col_widths=[5.0, 3.5, 5.5],
    )

    doc.add_paragraph(
        "All long-running operations stream progress via Server-Sent Events with "
        "percentage indicators. A cancel button is available on all progress screens."
    )

    # ═══════════════════════════════════════════════
    # 11. DEVELOPMENT TIMELINE
    # ═══════════════════════════════════════════════
    _heading(doc, "11. Development Timeline", level=1)
    doc.add_paragraph(
        "Development followed an iterative approach, with each session building on "
        "the previous and validated by a comprehensive test suite (89 tests)."
    )

    timeline = [
        ("7 Apr 2026 \u2014 Session 1", "Variation System Foundation",
         "Built the 3-variation system (facade, structure, room layout) with per-floor "
         "facade application. Added regeneration endpoint and VariationPopup slider UI."),
        ("7 Apr 2026 \u2014 Session 2", "Solid Geometry & Arctic View",
         "Converted all geometry from wireframe to solid meshes. Set units to metres. "
         "Added Arctic preview mode with white matte rendering and edge outlines."),
        ("7 Apr 2026 \u2014 Session 3", "Multi-scale Extraction & Layers",
         "Rewrote all 6 CV extractors with 3-tier hierarchy (primary/secondary/tertiary). "
         "Added layer visibility panel. Implemented slider value persistence."),
        ("7 Apr 2026 \u2014 Session 4", "SSE Progress & Code Health",
         "Added real-time progress streaming. Made LLM + CV run concurrently. "
         "Split monolithic building.py (1959 lines) into 4 focused modules."),
        ("7 Apr 2026 \u2014 Session 5", "Pattern Preview Step",
         "Added a pattern preview canvas between analysis and 3D generation, "
         "letting users verify CV extraction before committing to generation."),
        ("7 Apr 2026 \u2014 Session 6", "Image Trace UI",
         "Replaced single-category preview with 6-option visual selector grid. "
         "New /api/trace endpoint runs all extractors in parallel. Users pick visually."),
        ("7 Apr 2026 \u2014 Session 7", "Performance Optimisation",
         "Fixed payload size issues by moving trace data server-side. Added feature caps. "
         "Simplified extraction by ~50%. Capped Voronoi at 60 points."),
        ("7 Apr 2026 \u2014 Session 8", "LLM Removal & Timeouts",
         "Removed Ollama from trace flow (was adding 30\u201340s for a badge). Added 30s "
         "timeout per generator and cancel buttons. Trace dropped from ~40s to ~5s."),
        ("7 Apr 2026 \u2014 Session 9", "Critical Bug Fix & Trace Quality",
         "Fixed asyncio event loop NameError that broke the fast generation path. "
         "Increased trace resolution to 1024px and made curves 3\u20136\u00d7 smoother."),
        ("7 Apr 2026 \u2014 Session 10", "Report Auto-generation",
         "Created automated Word document report generation (this document)."),
        ("14 Apr 2026 \u2014 Session 11", "Fast-path Fix & Layer Persistence",
         "Fixed NameError where /api/generate referenced undefined \u2018classification\u2019 on "
         "the fast path. Lifted layer visibility state to App.jsx for persistence "
         "across variation switches and regenerations."),
        ("20 Apr 2026 \u2014 Session 12", "Cloud Deployment",
         "Deployed BioForm to public URLs: frontend on Vercel (bioform.vercel.app), "
         "backend on Render. Switched to CV-only classification path for the cloud build "
         "(Ollama remains available for local use). Introduced a guarded upload-to-live "
         "workflow (tests + frontend build + git push) so non-developer edits stay safe."),
        ("21 Apr 2026 \u2014 Session 13", "Pattern Fidelity Fix",
         "3D output was too linear / appeared random because pattern features were "
         "normalised by per-feature max rather than source-image dimensions, stretching "
         "clustered features to fill each wall. Threaded image_dimensions through the "
         "pipeline so spatial relationships are preserved. Raised structural pattern "
         "influence default from 0.7 to 1.0, removed the beam max-span cap, and added "
         "shell + spiral cases to the column-position extractor."),
    ]

    for date, title, desc in timeline:
        p = doc.add_paragraph()
        run = p.add_run(f"{date}: {title}")
        run.bold = True
        run.font.color.rgb = BRAND_PRIMARY
        doc.add_paragraph(desc)

    # ═══════════════════════════════════════════════
    # 12. CURRENT STATUS & NEXT STEPS
    # ═══════════════════════════════════════════════
    _heading(doc, "12. Current Status & Next Steps", level=1)

    _heading(doc, "Completed", level=2)
    completed = [
        "Full 7-step workflow: upload \u2192 trace \u2192 brief \u2192 generate \u2192 preview \u2192 tweak \u2192 download",
        "6 biomimicry CV extractors with multi-scale hierarchy and feature caps",
        "Image Trace UI \u2014 6-option visual selector with parallel extraction",
        "3 variation generators (facade panel, structural, room layout)",
        "Solid geometry in metres with proper architectural dimensions",
        ".ghx Grasshopper template generation per category",
        "Project Brief form with polygon site boundary and dimension modes",
        "Three.js preview with Default and Arctic display modes",
        "Layer visibility toggles with persistence across variations",
        "Per-variation slider popups with value persistence",
        "SSE progress streaming with cancel button on all long operations",
        "Server-side trace caching (no large data round-trips to frontend)",
        "Automated project report generation",
        "Public cloud deployment on free tiers (Vercel + Render) at bioform.vercel.app",
        "Guarded non-developer deploy workflow (upload-to-live.bat) with test + build gates",
        "Pattern-fidelity fix: 3D output now preserves spatial relationships from the trace",
        "93/93 backend tests passing",
    ]
    for item in completed:
        doc.add_paragraph(item, style="List Bullet")

    _heading(doc, "Remaining Work", level=2)
    remaining = [
        "End-to-end integration testing (frontend \u2192 backend \u2192 file output)",
        "Error handling for edge cases (corrupt images, empty extractions)",
        "User documentation and onboarding guide",
        "Additional biomimicry categories (fractal, tessellation)",
        "Multi-building site layouts",
        "Material and colour mapping from source image",
    ]
    for item in remaining:
        doc.add_paragraph(item, style="List Bullet")

    # ─── Footer ───
    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run(f"Generated {datetime.now().strftime('%d %B %Y at %H:%M')}")
    run.font.size = Pt(9)
    run.font.color.rgb = BRAND_LIGHT
    run.font.italic = True

    # ─── Save ───
    doc.save(OUTPUT_PATH)
    print(f"Report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_report()
