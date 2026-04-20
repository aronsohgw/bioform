"""3D geometry generators for biomimicry patterns."""
import rhino3dm

from app.generators.cellular import generate_cellular
from app.generators.branching import generate_branching
from app.generators.shell import generate_shell
from app.generators.lattice import generate_lattice
from app.generators.spiral import generate_spiral
from app.generators.porous import generate_porous

GENERATORS = {
    "cellular": generate_cellular,
    "branching": generate_branching,
    "shell": generate_shell,
    "lattice": generate_lattice,
    "spiral": generate_spiral,
    "porous": generate_porous,
}


def generate_3dm(category: str, extraction_data: dict, **params) -> rhino3dm.File3dm:
    """Dispatch to the appropriate generator by category."""
    if category not in GENERATORS:
        raise ValueError(f"Unknown category: {category}. Must be one of {list(GENERATORS.keys())}")
    return GENERATORS[category](extraction_data, **params)
