"""Generate the BioForm Presentation Deck as a PowerPoint file.

Run this script to create/update docs/BioForm_Presentation.pptx.

Design: Biomimicry-themed, ~20 slides, professional architectural aesthetic.
Arc: Concept -> Ideation -> Resolution
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from datetime import datetime
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "BioForm_Presentation.pptx")

# ─── Brand palette (biomimicry / architectural) ───
BG_DARK = RGBColor(22, 27, 24)          # Deep green-black
BG_LIGHT = RGBColor(242, 240, 235)      # Warm off-white
BRAND_GREEN = RGBColor(45, 80, 56)      # Forest green
BRAND_SAGE = RGBColor(138, 164, 133)    # Sage
BRAND_ACCENT = RGBColor(108, 99, 255)   # Purple accent
BRAND_GOLD = RGBColor(198, 172, 120)    # Warm gold
TEXT_WHITE = RGBColor(245, 245, 240)
TEXT_DARK = RGBColor(30, 32, 30)
TEXT_MID = RGBColor(120, 125, 120)
PLACEHOLDER_BG = RGBColor(220, 218, 212)
PLACEHOLDER_BORDER = RGBColor(180, 178, 172)

# Slide dimensions (widescreen 16:9)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Font choices — clean architectural fonts
FONT_HEADING = "Century Gothic"
FONT_BODY = "Calibri Light"
FONT_ACCENT = "Calibri"


def _set_slide_bg(slide, color):
    """Set solid background colour for a slide."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_text_box(slide, left, top, width, height, text, font_name=FONT_BODY,
                  font_size=Pt(16), color=TEXT_WHITE, bold=False, alignment=PP_ALIGN.LEFT,
                  anchor=MSO_ANCHOR.TOP):
    """Add a text box with styled text."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    txBox.text_frame.word_wrap = True
    txBox.text_frame.auto_size = None

    p = txBox.text_frame.paragraphs[0]
    p.text = text
    p.font.name = font_name
    p.font.size = font_size
    p.font.color.rgb = color
    p.font.bold = bold
    p.alignment = alignment
    return txBox


def _add_multiline_box(slide, left, top, width, height, lines, font_name=FONT_BODY,
                       font_size=Pt(16), color=TEXT_WHITE, line_spacing=Pt(24),
                       alignment=PP_ALIGN.LEFT, bullet=False):
    """Add a text box with multiple paragraphs."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        if bullet:
            p.text = line
        else:
            p.text = line

        p.font.name = font_name
        p.font.size = font_size
        p.font.color.rgb = color
        p.alignment = alignment
        p.space_after = line_spacing

        if bullet:
            p.level = 0
            # Manual bullet prefix
            p.text = f"\u2022  {line}"

    return txBox


def _add_screenshot_placeholder(slide, left, top, width, height, label="Screenshot"):
    """Add a placeholder rectangle for a screenshot with label."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = PLACEHOLDER_BG
    shape.line.color.rgb = PLACEHOLDER_BORDER
    shape.line.width = Pt(1.5)
    shape.line.dash_style = 2  # Dash

    # Label inside
    tf = shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = f"\u25a3  {label}"
    p.font.name = FONT_ACCENT
    p.font.size = Pt(13)
    p.font.color.rgb = TEXT_MID
    p.alignment = PP_ALIGN.CENTER
    tf.paragraphs[0].space_before = Pt(4)

    return shape


def _add_section_divider(prs, section_title, section_subtitle, number):
    """Add a section divider slide (dark bg, large title)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    _set_slide_bg(slide, BG_DARK)

    # Section number — large faded
    _add_text_box(slide, Inches(0.8), Inches(1.0), Inches(3), Inches(1.5),
                  f"{number:02d}", FONT_HEADING, Pt(72), BRAND_SAGE, bold=True)

    # Decorative line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                   Inches(0.8), Inches(3.2), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = BRAND_GOLD
    line.line.fill.background()

    # Title
    _add_text_box(slide, Inches(0.8), Inches(3.6), Inches(10), Inches(1.2),
                  section_title, FONT_HEADING, Pt(40), TEXT_WHITE, bold=True)

    # Subtitle
    _add_text_box(slide, Inches(0.8), Inches(5.0), Inches(8), Inches(1),
                  section_subtitle, FONT_BODY, Pt(18), BRAND_SAGE)

    return slide


def _add_two_column_slide(prs, title, left_lines, right_lines, bg=BG_DARK,
                          title_color=TEXT_WHITE, body_color=TEXT_WHITE):
    """Slide with title and two text columns."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, bg)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  title, FONT_HEADING, Pt(28), title_color, bold=True)

    # Divider line under title
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                   Inches(0.8), Inches(1.5), Inches(11.5), Pt(1.5))
    line.fill.solid()
    line.fill.fore_color.rgb = BRAND_SAGE
    line.line.fill.background()

    _add_multiline_box(slide, Inches(0.8), Inches(1.9), Inches(5.2), Inches(5),
                       left_lines, FONT_BODY, Pt(15), body_color, Pt(20), bullet=True)

    _add_multiline_box(slide, Inches(6.8), Inches(1.9), Inches(5.2), Inches(5),
                       right_lines, FONT_BODY, Pt(15), body_color, Pt(20), bullet=True)

    return slide


def build_presentation():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # ═══════════════════════════════════════════════════
    # SLIDE 1 — TITLE
    # ═══════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    # Large title
    _add_text_box(slide, Inches(0.8), Inches(1.5), Inches(10), Inches(1.5),
                  "BioForm", FONT_HEADING, Pt(56), TEXT_WHITE, bold=True)

    # Subtitle
    _add_text_box(slide, Inches(0.8), Inches(3.2), Inches(8), Inches(0.8),
                  "Nature to Architecture", FONT_HEADING, Pt(28), BRAND_SAGE)

    # Tagline
    _add_text_box(slide, Inches(0.8), Inches(4.3), Inches(9), Inches(1.2),
                  "Translating biomimicry patterns from nature photographs\n"
                  "into parametric Rhino and Grasshopper files for architectural design.",
                  FONT_BODY, Pt(16), TEXT_MID)

    # Gold accent line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                   Inches(0.8), Inches(3.05), Inches(3.5), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = BRAND_GOLD
    line.line.fill.background()

    # Date
    _add_text_box(slide, Inches(0.8), Inches(6.3), Inches(5), Inches(0.5),
                  datetime.now().strftime("%B %Y"), FONT_BODY, Pt(14), TEXT_MID)

    # ═══════════════════════════════════════════════════
    # SECTION: CONCEPT
    # ═══════════════════════════════════════════════════
    _add_section_divider(prs, "Concept", "Why biomimicry needs better tools", 1)

    # ───────────────────────────────────────────────
    # SLIDE 3 — THE PROBLEM
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "The Problem", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    problems = [
        "Biomimicry is widely discussed in architecture, but rarely implemented in practice",
        "Translating a leaf vein or coral structure into parametric geometry is manual and slow",
        "Existing tools require deep scripting knowledge (Grasshopper C#/Python)",
        "Cloud-based generative AI services are expensive and output non-editable geometry",
        "No accessible pipeline exists from \"nature photograph\" to \"editable building file\"",
    ]
    _add_multiline_box(slide, Inches(0.8), Inches(1.8), Inches(11), Inches(4.5),
                       problems, FONT_BODY, Pt(18), TEXT_WHITE, Pt(28), bullet=True)

    # ───────────────────────────────────────────────
    # SLIDE 4 — WHAT IS BIOMIMICRY?
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "Biomimicry in Architecture", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    _add_text_box(slide, Inches(0.8), Inches(1.6), Inches(10), Inches(1.2),
                  "\"Innovation inspired by nature\" \u2014 Janine Benyus\n"
                  "Learning from 3.8 billion years of evolutionary problem-solving.",
                  FONT_BODY, Pt(17), BRAND_SAGE)

    categories = [
        ("Cellular", "Honeycombs, foam, cell tissue \u2192 Space-filling partitions"),
        ("Branching", "Tree veins, river networks \u2192 Structural hierarchies"),
        ("Lattice", "Crystal grids, spider webs \u2192 Regular structural patterns"),
        ("Porous", "Sponge, bone, coral \u2192 Filtered light and ventilation"),
        ("Spiral", "Nautilus, sunflower, vortex \u2192 Efficient circulation"),
        ("Shell", "Sea shells, seed pods \u2192 Curved load-bearing forms"),
    ]
    for i, (cat, desc) in enumerate(categories):
        row = i // 2
        col = i % 2
        x = Inches(0.8 + col * 6.0)
        y = Inches(3.2 + row * 1.2)
        _add_text_box(slide, x, y, Inches(5.5), Inches(0.4),
                      cat, FONT_HEADING, Pt(16), BRAND_GOLD, bold=True)
        _add_text_box(slide, x, y + Inches(0.35), Inches(5.5), Inches(0.5),
                      desc, FONT_BODY, Pt(14), TEXT_WHITE)

    # ───────────────────────────────────────────────
    # SLIDE 5 — THE VISION
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "The Vision", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    _add_text_box(slide, Inches(0.8), Inches(1.8), Inches(10), Inches(1.5),
                  "What if an architect could photograph a leaf, a coral, or a spider web \u2014\n"
                  "and receive an editable parametric building file within seconds?",
                  FONT_BODY, Pt(20), BRAND_SAGE)

    vision_points = [
        "No coding required \u2014 visual selection replaces scripting",
        "Runs locally \u2014 no cloud costs, no data leaving the machine",
        "Industry-standard output \u2014 .3dm + .ghx, ready for Rhino 8",
        "Three design variations from a single image",
        "Progressive detail \u2014 patterns evolve from ground to roof",
    ]
    _add_multiline_box(slide, Inches(0.8), Inches(3.8), Inches(10), Inches(3),
                       vision_points, FONT_BODY, Pt(17), TEXT_WHITE, Pt(24), bullet=True)

    # ═══════════════════════════════════════════════════
    # SECTION: IDEATION
    # ═══════════════════════════════════════════════════
    _add_section_divider(prs, "Ideation", "How it works \u2014 from image to architecture", 2)

    # ───────────────────────────────────────────────
    # SLIDE 7 — PIPELINE OVERVIEW
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "The Pipeline", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    steps = [
        ("01  Upload", "Nature image via drag-and-drop or Unsplash search"),
        ("02  Trace", "6 CV extractors run in parallel (~5 seconds)"),
        ("03  Select", "User picks preferred pattern interpretation from 3\u00d72 grid"),
        ("04  Brief", "Define building parameters: site, floors, facades"),
        ("05  Generate", "3 parametric variations: facade, structure, rooms"),
        ("06  Preview", "In-browser 3D viewer with layer controls"),
        ("07  Download", ".3dm + .ghx files for Rhino 8 / Grasshopper"),
    ]
    for i, (step, desc) in enumerate(steps):
        y = Inches(1.6 + i * 0.75)
        _add_text_box(slide, Inches(0.8), y, Inches(3), Inches(0.6),
                      step, FONT_HEADING, Pt(17), BRAND_GOLD, bold=True)
        _add_text_box(slide, Inches(4.0), y, Inches(8), Inches(0.6),
                      desc, FONT_BODY, Pt(16), TEXT_WHITE)

    # Connecting dots
    for i in range(6):
        y = Inches(2.1 + i * 0.75)
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(3.6), y, Pt(6), Pt(6))
        dot.fill.solid()
        dot.fill.fore_color.rgb = BRAND_SAGE
        dot.line.fill.background()

    # ───────────────────────────────────────────────
    # SLIDE 8 — IMAGE TRACE SYSTEM
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "Image Trace System", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    _add_text_box(slide, Inches(0.8), Inches(1.5), Inches(5.5), Inches(1.5),
                  "Six computer vision extraction approaches run\n"
                  "simultaneously on the uploaded image. Each maps\n"
                  "to a distinct biomimicry category.\n\n"
                  "The user sees all 6 results and picks visually \u2014\n"
                  "no algorithm configuration needed.",
                  FONT_BODY, Pt(15), TEXT_WHITE)

    # Screenshot placeholder for trace grid
    _add_screenshot_placeholder(slide, Inches(7.0), Inches(1.2), Inches(5.5), Inches(4.5),
                                 "Screenshot: Image Trace \u2014 6-option selection grid")

    # Method summary
    methods = [
        "Cellular \u2014 Canny edges + Voronoi seeds",
        "Branching \u2014 Skeleton path tracing",
        "Lattice \u2014 Hough line detection",
        "Porous \u2014 Otsu threshold + contours",
        "Spiral \u2014 Skeleton curves + radial FFT",
        "Shell \u2014 Height-mapped control grid",
    ]
    _add_multiline_box(slide, Inches(0.8), Inches(4.3), Inches(5.5), Inches(2.5),
                       methods, FONT_BODY, Pt(13), BRAND_SAGE, Pt(16), bullet=True)

    # ───────────────────────────────────────────────
    # SLIDE 9 — IMAGE TRACE SCREENSHOT
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_LIGHT)

    _add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
                  "Trace Selection", FONT_HEADING, Pt(28), TEXT_DARK, bold=True)

    _add_text_box(slide, Inches(0.8), Inches(1.1), Inches(10), Inches(0.6),
                  "The user selects the trace that best captures their design intent.",
                  FONT_BODY, Pt(15), TEXT_MID)

    _add_screenshot_placeholder(slide, Inches(1.2), Inches(1.9), Inches(10.9), Inches(5.0),
                                 "Screenshot: Full Image Trace UI with all 6 category previews")

    # ───────────────────────────────────────────────
    # SLIDE 10 — PROJECT BRIEF
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "Project Brief", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    brief_items = [
        "Site boundary \u2014 polygon with preset shapes or custom dimensions",
        "Floor count and floor height (default: 5 floors, 3m each)",
        "Dimension mode \u2014 static, taper, or setback per floor",
        "Active facades \u2014 north, south, east, west selection",
        "Optional \u2014 skip for sensible defaults (10\u00d710m, 5 floors)",
    ]
    _add_multiline_box(slide, Inches(0.8), Inches(1.8), Inches(5.5), Inches(4),
                       brief_items, FONT_BODY, Pt(16), TEXT_WHITE, Pt(24), bullet=True)

    _add_screenshot_placeholder(slide, Inches(7.0), Inches(1.2), Inches(5.5), Inches(5.0),
                                 "Screenshot: Project Brief form")

    # ───────────────────────────────────────────────
    # SLIDE 11 — THREE VARIATIONS
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "Three Design Variations", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    _add_text_box(slide, Inches(0.8), Inches(1.5), Inches(11), Inches(0.7),
                  "One natural pattern, three architectural applications:",
                  FONT_BODY, Pt(17), BRAND_SAGE)

    variations = [
        ("A \u2014 Facade Panel", "Pattern as external wall\ntreatment and screen",
         "Pattern size, repetitions,\nsimplicity"),
        ("B \u2014 Structure", "Columns and beams derived\nfrom pattern geometry",
         "Column spacing, beam depth,\npattern influence"),
        ("C \u2014 Room Layout", "Pattern shapes rooms,\ncorridors, and spaces",
         "Room count, corridor width,\nopenness"),
    ]
    for i, (name, desc, params) in enumerate(variations):
        x = Inches(0.8 + i * 4.1)
        # Card background
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                       x, Inches(2.5), Inches(3.7), Inches(4.2))
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(35, 42, 38)
        card.line.color.rgb = BRAND_SAGE
        card.line.width = Pt(0.75)

        _add_text_box(slide, x + Inches(0.3), Inches(2.7), Inches(3.1), Inches(0.6),
                      name, FONT_HEADING, Pt(18), BRAND_GOLD, bold=True)
        _add_text_box(slide, x + Inches(0.3), Inches(3.4), Inches(3.1), Inches(1.2),
                      desc, FONT_BODY, Pt(14), TEXT_WHITE)
        _add_text_box(slide, x + Inches(0.3), Inches(4.7), Inches(3.1), Inches(0.4),
                      "Editable:", FONT_ACCENT, Pt(12), BRAND_SAGE, bold=True)
        _add_text_box(slide, x + Inches(0.3), Inches(5.1), Inches(3.1), Inches(1.0),
                      params, FONT_BODY, Pt(13), TEXT_WHITE)

    # ───────────────────────────────────────────────
    # SLIDE 12 — 3D PREVIEW SYSTEM
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "3D Preview", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    # Two mode cards
    for i, (mode, desc, color_desc) in enumerate([
        ("Default Mode", "Dark background, purple materials\nwith wireframe overlay", "Dark, technical"),
        ("Arctic Mode", "White matte rendering with\nedge outlines \u2014 Rhino-style", "Clean, presentation-ready"),
    ]):
        x = Inches(0.8 + i * 6.2)
        _add_text_box(slide, x, Inches(1.6), Inches(5.5), Inches(0.5),
                      mode, FONT_HEADING, Pt(18), BRAND_GOLD, bold=True)
        _add_text_box(slide, x, Inches(2.1), Inches(5.5), Inches(0.8),
                      desc, FONT_BODY, Pt(14), TEXT_WHITE)

    # Two screenshot placeholders side by side
    _add_screenshot_placeholder(slide, Inches(0.8), Inches(3.2), Inches(5.5), Inches(3.5),
                                 "Screenshot: Default view mode")
    _add_screenshot_placeholder(slide, Inches(7.0), Inches(3.2), Inches(5.5), Inches(3.5),
                                 "Screenshot: Arctic view mode")

    # ───────────────────────────────────────────────
    # SLIDE 13 — LAYER CONTROLS & TWEAKING
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "Layer Controls & Parameter Tweaking", FONT_HEADING, Pt(28), TEXT_WHITE, bold=True)

    layer_items = [
        "Toggle visibility of individual building systems:",
        "   Floor Plates \u2022 Walls \u2022 Facade Pattern",
        "   Columns \u2022 Beams \u2022 Room Walls \u2022 Corridors",
        "",
        "Layer choices persist across variation switches",
        "Slider parameters persist across popup opens",
        "Regeneration takes 2\u20133 seconds per variation",
    ]
    _add_multiline_box(slide, Inches(0.8), Inches(1.6), Inches(5.5), Inches(4.5),
                       layer_items, FONT_BODY, Pt(15), TEXT_WHITE, Pt(18))

    _add_screenshot_placeholder(slide, Inches(7.0), Inches(1.2), Inches(5.5), Inches(5.0),
                                 "Screenshot: Layer panel + variation slider popup")

    # ───────────────────────────────────────────────
    # SLIDE 14 — TECH STACK
    # ───────────────────────────────────────────────
    _add_two_column_slide(prs,
        "Technology Stack",
        [
            "React 18 + Vite \u2014 Frontend SPA",
            "Three.js + rhino3dm.js \u2014 3D preview",
            "Python 3.11 / FastAPI \u2014 Backend API",
            "OpenCV + scikit-image \u2014 CV analysis",
        ],
        [
            "rhino3dm \u2014 .3dm file generation",
            "Programmatic XML \u2014 .ghx templates",
            "SSE streaming \u2014 Real-time progress",
            "Ollama (optional) \u2014 LLM classification",
        ],
    )

    # ═══════════════════════════════════════════════════
    # SECTION: RESOLUTION
    # ═══════════════════════════════════════════════════
    _add_section_divider(prs, "Resolution", "What was built, and what comes next", 3)

    # ───────────────────────────────────────────────
    # SLIDE 16 — DEVELOPMENT JOURNEY
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "Development Journey", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    milestones = [
        ("Phase 1", "Foundation \u2014 3-variation system, solid geometry, metres"),
        ("Phase 2", "Multi-scale extraction with 3-tier hierarchy"),
        ("Phase 3", "Image Trace UI \u2014 6-option visual selector, no LLM"),
        ("Phase 4", "Performance \u2014 server-side caching, feature caps, 50% faster extraction"),
        ("Phase 5", "Polish \u2014 timeouts, cancel buttons, curve smoothing"),
        ("Phase 6", "Stability \u2014 critical bug fixes, layer persistence, report generation"),
    ]
    for i, (phase, desc) in enumerate(milestones):
        y = Inches(1.7 + i * 0.85)
        # Phase badge
        badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                        Inches(0.8), y, Inches(1.8), Inches(0.55))
        badge.fill.solid()
        badge.fill.fore_color.rgb = BRAND_GREEN
        badge.line.fill.background()
        tf = badge.text_frame
        p = tf.paragraphs[0]
        p.text = phase
        p.font.name = FONT_HEADING
        p.font.size = Pt(14)
        p.font.color.rgb = TEXT_WHITE
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER

        _add_text_box(slide, Inches(3.0), y, Inches(9), Inches(0.55),
                      desc, FONT_BODY, Pt(16), TEXT_WHITE)

    # ───────────────────────────────────────────────
    # SLIDE 17 — KEY DECISIONS
    # ───────────────────────────────────────────────
    _add_two_column_slide(prs,
        "Key Design Decisions",
        [
            "Visual selection over algorithm configuration",
            "LLM removed from main flow \u2014 user picks pattern visually",
            "All geometry as solid meshes, not wireframe",
            "Progressive detail: ground \u2192 roof hierarchy",
        ],
        [
            "Local-first: no paid API dependencies",
            "Server-side trace caching (no large payloads)",
            "30-second timeout per generator",
            "Single building per brief (multi-building removed)",
        ],
    )

    # ───────────────────────────────────────────────
    # SLIDE 18 — PERFORMANCE
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "Performance", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    perf = [
        ("~5s", "Image Trace", "6 CV extractors in parallel"),
        ("~5\u201310s", "3D Generation", "3 variations with cached data"),
        ("~2\u20133s", "Regeneration", "Single variation, slider params"),
        ("89", "Tests Passing", "Full backend test suite"),
    ]
    for i, (metric, label, desc) in enumerate(perf):
        x = Inches(0.8 + i * 3.1)
        # Large metric
        _add_text_box(slide, x, Inches(2.0), Inches(2.8), Inches(1.2),
                      metric, FONT_HEADING, Pt(44), BRAND_GOLD, bold=True,
                      alignment=PP_ALIGN.CENTER)
        _add_text_box(slide, x, Inches(3.3), Inches(2.8), Inches(0.6),
                      label, FONT_HEADING, Pt(17), TEXT_WHITE, bold=True,
                      alignment=PP_ALIGN.CENTER)
        _add_text_box(slide, x, Inches(3.9), Inches(2.8), Inches(0.6),
                      desc, FONT_BODY, Pt(13), BRAND_SAGE,
                      alignment=PP_ALIGN.CENTER)

    _add_text_box(slide, Inches(0.8), Inches(5.2), Inches(11), Inches(0.8),
                  "All operations stream real-time progress via Server-Sent Events.\n"
                  "Cancel button available on every progress screen.",
                  FONT_BODY, Pt(15), TEXT_MID, alignment=PP_ALIGN.CENTER)

    # ───────────────────────────────────────────────
    # SLIDE 19 — DEMO SCREENSHOTS
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_LIGHT)

    _add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
                  "Full Workflow Demo", FONT_HEADING, Pt(28), TEXT_DARK, bold=True)

    # 4 screenshot placeholders in 2x2 grid
    labels = [
        "Screenshot: Image Upload",
        "Screenshot: Image Trace Selection",
        "Screenshot: 3D Preview (Default)",
        "Screenshot: 3D Preview (Arctic)",
    ]
    for i, label in enumerate(labels):
        row = i // 2
        col = i % 2
        x = Inches(0.8 + col * 6.2)
        y = Inches(1.5 + row * 2.85)
        _add_screenshot_placeholder(slide, x, y, Inches(5.7), Inches(2.6), label)

    # ───────────────────────────────────────────────
    # SLIDE 20 — FUTURE & NEXT STEPS
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    _add_text_box(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(0.9),
                  "Future Roadmap", FONT_HEADING, Pt(32), TEXT_WHITE, bold=True)

    future = [
        "End-to-end integration testing",
        "Deployment \u2014 Vercel (frontend) + Railway/Fly (backend)",
        "Additional biomimicry categories (fractal, tessellation)",
        "Multi-building site layouts",
        "Material and colour mapping from source image",
        "User documentation and onboarding guide",
        "Export to additional formats (IFC, FBX)",
    ]
    _add_multiline_box(slide, Inches(0.8), Inches(1.8), Inches(11), Inches(4.5),
                       future, FONT_BODY, Pt(18), TEXT_WHITE, Pt(28), bullet=True)

    # ───────────────────────────────────────────────
    # SLIDE 21 — THANK YOU
    # ───────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, BG_DARK)

    for _ in range(2):
        pass  # spacing handled by positioning

    _add_text_box(slide, Inches(0.8), Inches(2.0), Inches(11), Inches(1.2),
                  "Thank You", FONT_HEADING, Pt(48), TEXT_WHITE, bold=True,
                  alignment=PP_ALIGN.CENTER)

    # Gold line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                   Inches(5.0), Inches(3.4), Inches(3.3), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = BRAND_GOLD
    line.line.fill.background()

    _add_text_box(slide, Inches(0.8), Inches(3.8), Inches(11), Inches(0.8),
                  "BioForm \u2014 Nature to Architecture",
                  FONT_HEADING, Pt(20), BRAND_SAGE, alignment=PP_ALIGN.CENTER)

    _add_text_box(slide, Inches(0.8), Inches(4.8), Inches(11), Inches(0.6),
                  "Questions?", FONT_BODY, Pt(18), TEXT_MID, alignment=PP_ALIGN.CENTER)

    # ─── Save ───
    prs.save(OUTPUT_PATH)
    print(f"Presentation saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_presentation()
