"""Variation engine — generates 3 design variations per analysis result.

Each variation applies the detected pattern differently onto the building:
- A: Facade Panel — pattern as external wall treatment/screen
- B: Structure — columns + beams derived from the natural pattern
- C: Room Layout — pattern shapes rooms, corridors, and spaces on floor plates
"""
import rhino3dm

from app.generators import generate_3dm
from app.generators.building import (
    generate_facade_variation,
    generate_structural_variation,
    generate_room_variation,
)
from app.ghx_builder import build_ghx_for_category


VARIATION_CONFIGS = [
    {
        "name": "Facade Panel",
        "description": "Pattern applied as facade skin on building walls.",
        "generator": generate_facade_variation,
        "editable_params": {
            "pattern_size": {"min": 0.2, "max": 3.0, "default": 1.0, "step": 0.1,
                             "label": "Pattern Size"},
            "pattern_repetitions": {"min": 1, "max": 10, "default": 3, "step": 1,
                                    "label": "Repetitions"},
            "pattern_simplicity": {"min": 0.0, "max": 1.0, "default": 0.5, "step": 0.05,
                                   "label": "Simplicity"},
        },
    },
    {
        "name": "Structure",
        "description": "Columns and beams derived from the natural pattern.",
        "generator": generate_structural_variation,
        "editable_params": {
            "column_spacing": {"min": 2.0, "max": 12.0, "default": 6.0, "step": 0.5,
                               "label": "Column Spacing (m)"},
            "beam_depth": {"min": 0.2, "max": 1.0, "default": 0.4, "step": 0.05,
                           "label": "Beam Depth (m)"},
            "pattern_influence": {"min": 0.0, "max": 1.0, "default": 0.7, "step": 0.05,
                                  "label": "Pattern Influence"},
        },
    },
    {
        "name": "Room Layout",
        "description": "Pattern shapes rooms, corridors, and spaces on each floor plate.",
        "generator": generate_room_variation,
        "editable_params": {
            "room_count": {"min": 3, "max": 20, "default": 8, "step": 1,
                           "label": "Target Room Count"},
            "corridor_width": {"min": 1.0, "max": 4.0, "default": 2.0, "step": 0.25,
                               "label": "Corridor Width (m)"},
            "openness": {"min": 0.0, "max": 1.0, "default": 0.3, "step": 0.05,
                         "label": "Openness"},
        },
    },
]

# Default brief when none is provided
DEFAULT_BRIEF = {
    "bounds": (10.0, 10.0),
    "total_height": 15.0,
    "floor_count": 5,
    "floor_height": 3.0,
    "floors": [
        {"width": 10.0, "depth": 10.0, "height": 3.0, "z_offset": i * 3.0}
        for i in range(5)
    ],
    "active_facades": ["north", "south", "east", "west"],
    "site_polygon": [(0, 0), (10, 0), (10, 10), (0, 10)],
}

SCALE_CONFIG = {
    "module": {"scale_factor": 2.0, "bounds": (3.0, 3.0), "description": "Single repeating unit, ~1-3m"},
    "small": {"scale_factor": 8.0, "bounds": (10.0, 10.0), "description": "3-5 modules assembled, ~5-15m"},
    "large": {"scale_factor": 25.0, "bounds": (30.0, 20.0), "description": "Full facade/building envelope"},
}


def generate_variations(analysis: dict, num_variations: int = 3,
                         brief_params: dict = None,
                         custom_params: dict = None) -> list[dict]:
    """Generate 3 model variations from analysis + brief."""
    category = analysis.get("category", "cellular")
    extraction_data = analysis.get("extraction_data", {})
    brief = brief_params or DEFAULT_BRIEF

    num_variations = max(2, min(num_variations, len(VARIATION_CONFIGS)))
    results = []

    for config in VARIATION_CONFIGS[:num_variations]:
        model = config["generator"](brief, extraction_data, category,
                                     custom_params=custom_params)
        results.append({
            "name": config["name"],
            "description": config["description"],
            "model": model,
        })

    return results


def generate_single_variation(variation_index: int, extraction_data: dict,
                               brief_params: dict, category: str,
                               custom_params: dict = None) -> dict:
    """Regenerate a single variation with custom parameters."""
    config = VARIATION_CONFIGS[variation_index]
    model = config["generator"](brief_params, extraction_data, category,
                                 custom_params=custom_params)
    return {
        "name": config["name"],
        "description": config["description"],
        "model": model,
    }


def apply_scale(analysis: dict, scale_name: str) -> dict:
    """Return scale parameters for the given scale level."""
    if scale_name not in SCALE_CONFIG:
        raise ValueError(f"Unknown scale: {scale_name}. Must be one of {list(SCALE_CONFIG.keys())}")

    config = SCALE_CONFIG[scale_name]
    return {
        "scale_name": scale_name,
        "scale_factor": config["scale_factor"],
        "bounds": config["bounds"],
        "description": config["description"],
    }


def generate_output_bundle(analysis: dict) -> dict:
    """Generate the complete output bundle: variations + GHX template."""
    category = analysis.get("category", "cellular")

    variations = generate_variations(analysis)
    ghx_xml = build_ghx_for_category(category)

    return {
        "variations": variations,
        "ghx": ghx_xml,
        "category": category,
    }
