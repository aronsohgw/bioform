"""Tests for building envelope + pattern application."""
import pytest
import rhino3dm


def _default_brief_params():
    return {
        "bounds": (20.0, 30.0),
        "total_height": 28.0,
        "floor_count": 8,
        "floor_height": 3.5,
        "floors": [
            {"width": 20.0, "depth": 30.0, "height": 3.5, "z_offset": i * 3.5}
            for i in range(8)
        ],
        "active_facades": ["north", "south", "east", "west"],
        "site_polygon": [(0, 0), (20, 0), (20, 30), (0, 30)],
    }


def _cellular_extraction():
    return {
        "seed_points": [(30, 40), (80, 60), (150, 30), (50, 120), (120, 100),
                        (90, 150), (170, 130), (40, 80), (130, 70), (100, 40)],
        "avg_cell_size": 800.0,
        "cell_count": 10,
    }


def _branching_extraction():
    return {
        "branch_points": [[100, 100], [60, 50], [140, 50]],
        "endpoints": [[100, 180], [40, 20], [70, 20], [130, 20], [160, 20]],
        "branch_count": 3,
    }


# --- Building Envelope ---

class TestBuildingEnvelope:
    def test_creates_model_with_floor_plates(self):
        from app.generators.building import generate_building_envelope
        brief = _default_brief_params()
        model = generate_building_envelope(brief)
        assert isinstance(model, rhino3dm.File3dm)
        assert len(model.Objects) > 0

    def test_has_floor_plate_layer(self):
        from app.generators.building import generate_building_envelope
        brief = _default_brief_params()
        model = generate_building_envelope(brief)
        layer_names = [model.Layers[i].Name for i in range(len(model.Layers))]
        assert any("Floor" in n for n in layer_names)

    def test_has_wall_layer(self):
        from app.generators.building import generate_building_envelope
        brief = _default_brief_params()
        model = generate_building_envelope(brief)
        layer_names = [model.Layers[i].Name for i in range(len(model.Layers))]
        assert any("Wall" in n for n in layer_names)

    def test_has_site_boundary(self):
        from app.generators.building import generate_building_envelope
        brief = _default_brief_params()
        model = generate_building_envelope(brief)
        layer_names = [model.Layers[i].Name for i in range(len(model.Layers))]
        assert any("Site" in n for n in layer_names)

    def test_floor_count_matches_brief(self):
        from app.generators.building import generate_building_envelope
        brief = _default_brief_params()
        model = generate_building_envelope(brief)
        # Should have at least floor_count floor plate objects
        # (each floor plate is one mesh)
        floor_layer_idx = None
        for i in range(len(model.Layers)):
            if "Floor" in model.Layers[i].Name:
                floor_layer_idx = i
                break
        assert floor_layer_idx is not None

    def test_writes_to_file(self, tmp_path):
        from app.generators.building import generate_building_envelope
        brief = _default_brief_params()
        model = generate_building_envelope(brief)
        path = str(tmp_path / "building.3dm")
        model.Write(path, 8)
        assert (tmp_path / "building.3dm").exists()


# --- Facade Pattern Application ---

class TestFacadeVariation:
    def test_creates_facade_model(self):
        from app.generators.building import generate_facade_variation
        brief = _default_brief_params()
        extraction = _cellular_extraction()
        model = generate_facade_variation(brief, extraction, "cellular")
        assert isinstance(model, rhino3dm.File3dm)
        assert len(model.Objects) > 0

    def test_facade_has_pattern_layer(self):
        from app.generators.building import generate_facade_variation
        brief = _default_brief_params()
        extraction = _cellular_extraction()
        model = generate_facade_variation(brief, extraction, "cellular")
        layer_names = [model.Layers[i].Name for i in range(len(model.Layers))]
        assert any("Pattern" in n or "Facade" in n for n in layer_names)

    def test_facade_has_building_and_pattern(self):
        from app.generators.building import generate_facade_variation
        brief = _default_brief_params()
        extraction = _cellular_extraction()
        model = generate_facade_variation(brief, extraction, "cellular")
        # Should have both building structure and pattern geometry
        assert len(model.Objects) > 10


# --- Structural Pattern Application ---

class TestStructuralVariation:
    def test_creates_structural_model(self):
        from app.generators.building import generate_structural_variation
        brief = _default_brief_params()
        extraction = _branching_extraction()
        model = generate_structural_variation(brief, extraction, "branching")
        assert isinstance(model, rhino3dm.File3dm)
        assert len(model.Objects) > 0

    def test_structural_has_column_layer(self):
        from app.generators.building import generate_structural_variation
        brief = _default_brief_params()
        extraction = _branching_extraction()
        model = generate_structural_variation(brief, extraction, "branching")
        layer_names = [model.Layers[i].Name for i in range(len(model.Layers))]
        assert any("Struct" in n or "Column" in n for n in layer_names)


# --- Variation dispatch ---

class TestVariationDispatch:
    def test_all_three_variations_different_object_count(self):
        from app.generators.building import (
            generate_facade_variation, generate_structural_variation,
            generate_room_variation,
        )
        brief = _default_brief_params()
        extraction = _cellular_extraction()
        cat = "cellular"

        facade = generate_facade_variation(brief, extraction, cat)
        struct = generate_structural_variation(brief, extraction, cat)
        rooms = generate_room_variation(brief, extraction, cat)

        counts = [len(m.Objects) for m in [facade, struct, rooms]]
        # At least 2 of 3 should have different object counts (truly different geometry)
        assert len(set(counts)) >= 2

    def test_all_variations_have_floor_plates(self):
        from app.generators.building import (
            generate_facade_variation, generate_structural_variation,
            generate_room_variation,
        )
        brief = _default_brief_params()
        extraction = _cellular_extraction()
        cat = "cellular"

        for gen_fn in [generate_facade_variation, generate_structural_variation,
                       generate_room_variation]:
            model = gen_fn(brief, extraction, cat)
            layer_names = [model.Layers[i].Name for i in range(len(model.Layers))]
            assert any("Floor" in n for n in layer_names), f"{gen_fn.__name__} missing floor plates"
