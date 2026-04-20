"""Tests for variation engine and scale system."""
import os
import rhino3dm


def _make_analysis_result():
    return {
        "category": "cellular",
        "confidence": 0.9,
        "rationale": "Test",
        "architectural_suggestions": [],
        "extraction_data": {
            "seed_points": [(50, 50), (120, 80), (80, 150), (160, 140)],
            "avg_cell_size": 500.0,
            "cell_count": 4,
        },
        "image_dimensions": [200, 200],
    }


class TestVariationEngine:
    def test_generates_multiple_variations(self):
        from app.variation_engine import generate_variations
        results = generate_variations(_make_analysis_result())
        assert len(results) >= 2
        assert len(results) <= 4

    def test_each_variation_has_required_fields(self):
        from app.variation_engine import generate_variations
        results = generate_variations(_make_analysis_result())
        for var in results:
            assert "name" in var
            assert "description" in var
            assert "model" in var
            assert isinstance(var["model"], rhino3dm.File3dm)

    def test_variation_names_are_distinct(self):
        from app.variation_engine import generate_variations
        results = generate_variations(_make_analysis_result())
        names = [v["name"] for v in results]
        assert len(names) == len(set(names))

    def test_variations_include_facade_and_structure(self):
        from app.variation_engine import generate_variations
        results = generate_variations(_make_analysis_result())
        names = [v["name"].lower() for v in results]
        has_facade = any("facade" in n or "panel" in n for n in names)
        has_structure = any("structure" in n or "structural" in n for n in names)
        assert has_facade
        assert has_structure


class TestScaleSystem:
    def test_apply_scale_module(self):
        from app.variation_engine import apply_scale
        analysis = _make_analysis_result()
        result = apply_scale(analysis, "module")
        assert result["scale_name"] == "module"
        assert 1.0 <= result["scale_factor"] <= 3.0

    def test_apply_scale_small(self):
        from app.variation_engine import apply_scale
        analysis = _make_analysis_result()
        result = apply_scale(analysis, "small")
        assert result["scale_name"] == "small"
        assert 5.0 <= result["scale_factor"] <= 15.0

    def test_apply_scale_large(self):
        from app.variation_engine import apply_scale
        analysis = _make_analysis_result()
        result = apply_scale(analysis, "large")
        assert result["scale_name"] == "large"
        assert result["scale_factor"] >= 15.0

    def test_invalid_scale_raises(self):
        import pytest
        from app.variation_engine import apply_scale
        with pytest.raises(ValueError):
            apply_scale(_make_analysis_result(), "huge")


class TestFullPipeline:
    def test_generate_and_save_all(self, tmp_path):
        from app.variation_engine import generate_variations
        results = generate_variations(_make_analysis_result())
        for i, var in enumerate(results):
            path = str(tmp_path / f"variation_{i}.3dm")
            var["model"].Write(path, 8)
            assert os.path.exists(path)

    def test_generate_with_ghx(self):
        from app.variation_engine import generate_output_bundle
        bundle = generate_output_bundle(_make_analysis_result())
        assert "variations" in bundle
        assert "ghx" in bundle
        assert len(bundle["variations"]) >= 2
        assert isinstance(bundle["ghx"], str)  # XML string
