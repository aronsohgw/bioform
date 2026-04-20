"""Stub module — Ollama disabled for cloud deployment (Path B: CV-only).

The `/api/trace` endpoint runs all 6 CV extractors and lets the user pick a
category, so AI classification is not needed for the main user flow. This stub
keeps the `/api/upload` and `/api/generate` full-path endpoints working by
returning a neutral default instead of calling a local Ollama server.
"""


async def classify_image(image_path: str) -> dict:
    return {
        "category": "cellular",
        "confidence": 0.0,
        "rationale": "AI classification disabled in cloud deployment. Use Image Trace to pick a pattern.",
        "architectural_suggestions": [],
    }
