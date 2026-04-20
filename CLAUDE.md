# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: BioForm

Nature-to-architecture generator. Converts nature images into parametric Rhino (.3dm) and Grasshopper (.ghx) files for architectural facades and structures using biomimicry pattern analysis.

## Important: User Context

The user is a **complete beginner at coding** — an architect/designer who vibe codes with Claude Code. Be extra careful about breaking things, run tests after every change, and proactively flag if a requested change could cause problems. Explain plainly.

## Architecture

- **Frontend**: React + Three.js (web app with 3D preview, Default + Arctic view modes, layer visibility toggles)
- **Backend**: Python 3.11 / FastAPI (generation logic + API, SSE progress streaming)
- **Image Analysis**: Hybrid — OpenCV/scikit-image multi-scale extraction (3 hierarchy levels) + Ollama LLaMA 3.2 Vision for classification/rationale (run in parallel)
- **3D Generation**: `rhino3dm` Python library for .3dm (meters, solid geometry), programmatic XML for .ghx
- **Preview**: Three.js with rhino3dm.js in-browser parsing

Pipeline: Image upload → Project brief form → CV extraction + LLM classification (parallel) → Parametric generation (3 variations: facade, structure, room layout) → 3D preview → Download .3dm + .ghx

## Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install
npm run dev

# Tests (TDD — write tests first)
cd backend && pytest
cd frontend && npm test

# Run single test
pytest tests/test_cv_extraction.py -k "test_extract_cellular"
pytest tests/test_building_generator.py -k "test_facade"

# Ollama (must be running for LLM classification)
ollama serve
ollama run llama3.2-vision

# Lint
cd backend && ruff check .
cd frontend && npm run lint
```

## Dev Practices

- **TDD**: Write tests before implementation for all generation logic
- **Run tests after every change**: 89 tests must stay green
- **SkillMD**: Reusable skills documented in `/skills/` as .md files — read these before implementing related features
- **Plan-with-File**: `PLAN.md` tracks phases, decisions, and status — keep it current
- **Few-Shot Prompts**: Stored in `/skills/prompts/` — curated examples for Ollama vision classification
- **Skill Creator**: New biomimicry categories or output types get registered as skills

## Key Design Decisions

- All image analysis runs locally (Ollama + OpenCV) — no paid API calls
- .ghx files are XML-based Grasshopper definitions generated programmatically (no Rhino needed server-side)
- `rhino3dm` is open-source and creates .3dm without a Rhino license
- User's local Rhino 8 is for opening/editing downloaded files only
- Each generation produces 3 variations: facade panel, structure, room layout
- All geometry is solid (200mm floor plates, 100mm walls, cylindrical columns, box beams) in meters
- Multi-scale CV extraction with hierarchy (0=primary, 1=secondary, 2=tertiary) — progressive detail per floor
- Variation slider values persist across popup opens (applied_params)
- Single building per project brief with polygon site boundary

## Biomimicry Categories

Cellular, Branching, Shell/Surface, Lattice/Grid, Spiral, Porous — auto-detected from image, tool provides rationale and architectural application suggestions to user.
