"""Tests for project brief model, floor dimensions, and parameter mapping."""
import pytest
import math


# --- Brief model validation ---

class TestBriefModel:
    def test_valid_rectangular_brief(self):
        from app.brief import validate_brief
        brief = {
            "site_polygon": [(0, 0), (20, 0), (20, 30), (0, 30)],
            "buildings": [
                {
                    "name": "Tower A",
                    "floor_count": 10,
                    "floor_height": 3.5,
                    "dimension_mode": "static",
                    "footprint_inset": 0,
                    "facades": ["north", "south", "east", "west"],
                }
            ],
        }
        result = validate_brief(brief)
        assert result["valid"] is True

    def test_triangular_site(self):
        from app.brief import validate_brief
        brief = {
            "site_polygon": [(0, 0), (30, 0), (15, 25)],
            "buildings": [
                {
                    "name": "Pavilion",
                    "floor_count": 1,
                    "floor_height": 5.0,
                    "dimension_mode": "static",
                    "footprint_inset": 0,
                    "facades": ["all"],
                }
            ],
        }
        result = validate_brief(brief)
        assert result["valid"] is True

    def test_rejects_polygon_with_fewer_than_3_points(self):
        from app.brief import validate_brief
        brief = {
            "site_polygon": [(0, 0), (10, 0)],
            "buildings": [{"name": "X", "floor_count": 1, "floor_height": 3.0,
                           "dimension_mode": "static", "footprint_inset": 0, "facades": ["all"]}],
        }
        result = validate_brief(brief)
        assert result["valid"] is False

    def test_rejects_zero_floors(self):
        from app.brief import validate_brief
        brief = {
            "site_polygon": [(0, 0), (10, 0), (10, 10), (0, 10)],
            "buildings": [{"name": "X", "floor_count": 0, "floor_height": 3.0,
                           "dimension_mode": "static", "footprint_inset": 0, "facades": ["all"]}],
        }
        result = validate_brief(brief)
        assert result["valid"] is False

    def test_multi_building(self):
        from app.brief import validate_brief
        brief = {
            "site_polygon": [(0, 0), (50, 0), (50, 50), (0, 50)],
            "buildings": [
                {"name": "A", "floor_count": 5, "floor_height": 3.0,
                 "dimension_mode": "static", "footprint_inset": 0, "facades": ["all"]},
                {"name": "B", "floor_count": 3, "floor_height": 4.0,
                 "dimension_mode": "static", "footprint_inset": 5, "facades": ["north", "south"]},
            ],
        }
        result = validate_brief(brief)
        assert result["valid"] is True
        assert len(result["buildings"]) == 2


# --- Floor dimension logic ---

class TestFloorDimensions:
    def test_static_floors_all_same(self):
        from app.brief import compute_floor_dimensions
        floors = compute_floor_dimensions(
            mode="static",
            floor_count=5,
            floor_height=3.5,
            base_width=20.0,
            base_depth=15.0,
        )
        assert len(floors) == 5
        for f in floors:
            assert f["width"] == 20.0
            assert f["depth"] == 15.0
            assert f["height"] == 3.5

    def test_taper_floors_shrink_upward(self):
        from app.brief import compute_floor_dimensions
        floors = compute_floor_dimensions(
            mode="taper",
            floor_count=5,
            floor_height=3.5,
            base_width=20.0,
            base_depth=15.0,
            taper_ratio=0.8,
        )
        assert len(floors) == 5
        assert floors[0]["width"] == 20.0
        assert floors[-1]["width"] < floors[0]["width"]
        # Each floor should be smaller than the one below
        for i in range(1, len(floors)):
            assert floors[i]["width"] <= floors[i - 1]["width"]

    def test_setback_floors(self):
        from app.brief import compute_floor_dimensions
        floors = compute_floor_dimensions(
            mode="setback",
            floor_count=10,
            floor_height=3.0,
            base_width=30.0,
            base_depth=20.0,
            setback_amount=1.0,
            setback_every=3,
        )
        assert len(floors) == 10
        # After floor 3, width should decrease
        assert floors[3]["width"] < floors[0]["width"]

    def test_manual_floors(self):
        from app.brief import compute_floor_dimensions
        manual = [
            {"width": 20.0, "depth": 15.0, "height": 4.0},
            {"width": 18.0, "depth": 14.0, "height": 3.5},
            {"width": 16.0, "depth": 13.0, "height": 3.5},
        ]
        floors = compute_floor_dimensions(
            mode="manual",
            floor_count=3,
            floor_height=3.5,
            base_width=20.0,
            base_depth=15.0,
            manual_floors=manual,
        )
        assert len(floors) == 3
        assert floors[0]["width"] == 20.0
        assert floors[2]["width"] == 16.0


# --- Brief to generation parameters ---

class TestBriefToParams:
    def test_maps_rectangular_brief(self):
        from app.brief import brief_to_gen_params
        brief = {
            "site_polygon": [(0, 0), (20, 0), (20, 30), (0, 30)],
            "buildings": [
                {
                    "name": "Tower",
                    "floor_count": 8,
                    "floor_height": 3.5,
                    "dimension_mode": "static",
                    "footprint_inset": 0,
                    "facades": ["all"],
                }
            ],
        }
        params = brief_to_gen_params(brief, building_index=0)
        assert "bounds" in params
        assert "total_height" in params
        assert "floors" in params
        assert params["total_height"] == pytest.approx(8 * 3.5)
        assert params["bounds"][0] == pytest.approx(20.0)
        assert params["bounds"][1] == pytest.approx(30.0)

    def test_maps_with_taper(self):
        from app.brief import brief_to_gen_params
        brief = {
            "site_polygon": [(0, 0), (25, 0), (25, 25), (0, 25)],
            "buildings": [
                {
                    "name": "Tapered",
                    "floor_count": 6,
                    "floor_height": 3.0,
                    "dimension_mode": "taper",
                    "taper_ratio": 0.85,
                    "footprint_inset": 0,
                    "facades": ["all"],
                }
            ],
        }
        params = brief_to_gen_params(brief, building_index=0)
        assert len(params["floors"]) == 6
        assert params["floors"][-1]["width"] < params["floors"][0]["width"]

    def test_polygon_area_computed(self):
        from app.brief import polygon_area
        # 10x10 square
        area = polygon_area([(0, 0), (10, 0), (10, 10), (0, 10)])
        assert area == pytest.approx(100.0)
        # Triangle
        area = polygon_area([(0, 0), (10, 0), (5, 8)])
        assert area == pytest.approx(40.0)

    def test_polygon_bounds(self):
        from app.brief import polygon_bounds
        b = polygon_bounds([(5, 10), (25, 10), (25, 40), (5, 40)])
        assert b["min_x"] == 5
        assert b["max_x"] == 25
        assert b["min_y"] == 10
        assert b["max_y"] == 40
        assert b["width"] == 20
        assert b["depth"] == 30
