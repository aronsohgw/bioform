"""Project brief model — site polygon, building definitions, floor dimensions.

Converts architectural brief constraints into generator parameters so
the biomimicry patterns map onto real building geometry.
"""


def validate_brief(brief: dict) -> dict:
    """Validate a project brief and return normalized result."""
    errors = []

    # Validate site polygon
    polygon = brief.get("site_polygon", [])
    if len(polygon) < 3:
        errors.append("Site polygon must have at least 3 points")

    # Validate buildings
    buildings = brief.get("buildings", [])
    if not buildings:
        errors.append("At least one building is required")

    validated_buildings = []
    for i, bldg in enumerate(buildings):
        bldg_errors = []
        name = bldg.get("name", f"Building {i + 1}")
        floor_count = bldg.get("floor_count", 1)
        floor_height = bldg.get("floor_height", 3.0)
        dimension_mode = bldg.get("dimension_mode", "static")
        footprint_inset = bldg.get("footprint_inset", 0)
        facades = bldg.get("facades", ["all"])

        if floor_count < 1:
            bldg_errors.append(f"{name}: floor count must be at least 1")
        if floor_height <= 0:
            bldg_errors.append(f"{name}: floor height must be positive")

        errors.extend(bldg_errors)
        validated_buildings.append({
            "name": name,
            "floor_count": floor_count,
            "floor_height": floor_height,
            "dimension_mode": dimension_mode,
            "footprint_inset": footprint_inset,
            "facades": facades,
            "taper_ratio": bldg.get("taper_ratio", 0.9),
            "setback_amount": bldg.get("setback_amount", 1.0),
            "setback_every": bldg.get("setback_every", 3),
            "manual_floors": bldg.get("manual_floors", []),
        })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "site_polygon": polygon,
        "buildings": validated_buildings,
    }


def compute_floor_dimensions(
    mode: str,
    floor_count: int,
    floor_height: float,
    base_width: float,
    base_depth: float,
    taper_ratio: float = 0.9,
    setback_amount: float = 1.0,
    setback_every: int = 3,
    manual_floors: list = None,
) -> list[dict]:
    """Compute per-floor width, depth, height based on dimension mode."""

    if mode == "manual" and manual_floors:
        return [
            {
                "width": f.get("width", base_width),
                "depth": f.get("depth", base_depth),
                "height": f.get("height", floor_height),
                "z_offset": sum(
                    manual_floors[j].get("height", floor_height)
                    for j in range(i)
                ),
            }
            for i, f in enumerate(manual_floors[:floor_count])
        ]

    floors = []
    current_width = base_width
    current_depth = base_depth
    z = 0.0

    for i in range(floor_count):
        if mode == "taper" and i > 0:
            current_width *= taper_ratio
            current_depth *= taper_ratio
        elif mode == "setback" and i > 0 and i % setback_every == 0:
            current_width = max(current_width - setback_amount * 2, base_width * 0.3)
            current_depth = max(current_depth - setback_amount * 2, base_depth * 0.3)

        floors.append({
            "width": round(current_width, 3),
            "depth": round(current_depth, 3),
            "height": floor_height,
            "z_offset": round(z, 3),
        })
        z += floor_height

    return floors


def polygon_area(polygon: list[tuple]) -> float:
    """Compute area of a polygon using the shoelace formula."""
    n = len(polygon)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += polygon[i][0] * polygon[j][1]
        area -= polygon[j][0] * polygon[i][1]
    return abs(area) / 2.0


def polygon_bounds(polygon: list[tuple]) -> dict:
    """Compute bounding box of a polygon."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return {
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "width": max_x - min_x,
        "depth": max_y - min_y,
    }


def brief_to_gen_params(brief: dict, building_index: int = 0) -> dict:
    """Convert a validated brief into parameters for the 3D generators."""
    validated = validate_brief(brief)
    if not validated["valid"]:
        raise ValueError(f"Invalid brief: {validated['errors']}")

    polygon = validated["site_polygon"]
    bounds = polygon_bounds(polygon)
    area = polygon_area(polygon)

    bldg = validated["buildings"][building_index]
    inset = bldg["footprint_inset"]

    # Compute building footprint (inset from site bounds)
    bldg_width = max(bounds["width"] - inset * 2, 2.0)
    bldg_depth = max(bounds["depth"] - inset * 2, 2.0)

    # Compute floor stack
    floors = compute_floor_dimensions(
        mode=bldg["dimension_mode"],
        floor_count=bldg["floor_count"],
        floor_height=bldg["floor_height"],
        base_width=bldg_width,
        base_depth=bldg_depth,
        taper_ratio=bldg.get("taper_ratio", 0.9),
        setback_amount=bldg.get("setback_amount", 1.0),
        setback_every=bldg.get("setback_every", 3),
        manual_floors=bldg.get("manual_floors", []),
    )

    total_height = bldg["floor_count"] * bldg["floor_height"]

    # Facade selection
    facades = bldg.get("facades", ["all"])
    if "all" in facades:
        active_facades = ["north", "south", "east", "west"]
    else:
        active_facades = facades

    return {
        "site_polygon": polygon,
        "site_area": area,
        "site_bounds": bounds,
        "bounds": (bldg_width, bldg_depth),
        "total_height": total_height,
        "floor_count": bldg["floor_count"],
        "floor_height": bldg["floor_height"],
        "floors": floors,
        "active_facades": active_facades,
        "building_name": bldg["name"],
        "dimension_mode": bldg["dimension_mode"],
    }
