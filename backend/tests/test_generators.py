"""Tests for rhino3dm 3D geometry generators."""
import pytest
import rhino3dm


def _make_cellular_data():
    return {
        "seed_points": [(50, 50), (120, 80), (80, 150), (160, 140), (30, 120)],
        "avg_cell_size": 500.0,
        "cell_count": 5,
    }


def _make_branching_data():
    return {
        "branch_points": [[100, 100], [60, 50], [140, 50]],
        "endpoints": [[100, 180], [40, 20], [70, 20], [130, 20], [160, 20]],
        "branch_count": 3,
    }


def _make_shell_data():
    return {
        "control_points": [
            [(0, 0, 0.1), (50, 0, 0.3), (100, 0, 0.2)],
            [(0, 50, 0.4), (50, 50, 0.8), (100, 50, 0.5)],
            [(0, 100, 0.2), (50, 100, 0.6), (100, 100, 0.3)],
        ],
        "height_map": None,
        "curvature_map": None,
        "gradient_magnitude": None,
    }


def _make_lattice_data():
    return {
        "lines": [
            [[0, 0, 200, 0]], [[0, 50, 200, 50]], [[0, 100, 200, 100]],
            [[0, 0, 0, 200]], [[50, 0, 50, 200]], [[100, 0, 100, 200]],
        ],
        "dominant_angles": [0.0, 1.5707],
        "intersections": [(0, 0), (50, 0), (100, 0), (0, 50), (50, 50), (100, 50)],
        "line_count": 6,
    }


def _make_spiral_data():
    return {
        "center": (100, 100),
        "arm_count": 3,
        "radial_profile": [(i, 10 + i // 3) for i in range(0, 360, 10)],
        "max_radius": 90,
    }


def _make_porous_data():
    return {
        "holes": [
            {"center": (30, 30), "radius": 8.0, "area": 201.0},
            {"center": (80, 50), "radius": 12.0, "area": 452.0},
            {"center": (140, 90), "radius": 6.0, "area": 113.0},
            {"center": (50, 150), "radius": 10.0, "area": 314.0},
        ],
        "hole_count": 4,
        "density_map": [[1, 0, 0, 0], [0, 1, 1, 0], [0, 0, 0, 0], [1, 0, 0, 0]],
        "avg_hole_radius": 9.0,
    }


# --- Cellular Generator ---

class TestCellularGenerator:
    def test_generates_3dm_model(self):
        from app.generators.cellular import generate_cellular
        model = generate_cellular(_make_cellular_data())
        assert isinstance(model, rhino3dm.File3dm)

    def test_model_has_geometry(self):
        from app.generators.cellular import generate_cellular
        model = generate_cellular(_make_cellular_data())
        assert len(model.Objects) > 0

    def test_model_has_layers(self):
        from app.generators.cellular import generate_cellular
        model = generate_cellular(_make_cellular_data())
        layer_names = [model.Layers[i].Name for i in range(len(model.Layers))]
        assert any("Voronoi" in n or "Cell" in n for n in layer_names)

    def test_can_write_to_file(self, tmp_path):
        from app.generators.cellular import generate_cellular
        model = generate_cellular(_make_cellular_data())
        path = str(tmp_path / "cellular.3dm")
        model.Write(path, 8)
        assert (tmp_path / "cellular.3dm").exists()


# --- Branching Generator ---

class TestBranchingGenerator:
    def test_generates_3dm_model(self):
        from app.generators.branching import generate_branching
        model = generate_branching(_make_branching_data())
        assert isinstance(model, rhino3dm.File3dm)

    def test_model_has_curves(self):
        from app.generators.branching import generate_branching
        model = generate_branching(_make_branching_data())
        assert len(model.Objects) > 0

    def test_can_write_to_file(self, tmp_path):
        from app.generators.branching import generate_branching
        model = generate_branching(_make_branching_data())
        path = str(tmp_path / "branching.3dm")
        model.Write(path, 8)
        assert (tmp_path / "branching.3dm").exists()


# --- Shell Generator ---

class TestShellGenerator:
    def test_generates_3dm_model(self):
        from app.generators.shell import generate_shell
        model = generate_shell(_make_shell_data())
        assert isinstance(model, rhino3dm.File3dm)

    def test_model_has_surface(self):
        from app.generators.shell import generate_shell
        model = generate_shell(_make_shell_data())
        assert len(model.Objects) > 0

    def test_can_write_to_file(self, tmp_path):
        from app.generators.shell import generate_shell
        model = generate_shell(_make_shell_data())
        path = str(tmp_path / "shell.3dm")
        model.Write(path, 8)
        assert (tmp_path / "shell.3dm").exists()


# --- Lattice Generator ---

class TestLatticeGenerator:
    def test_generates_3dm_model(self):
        from app.generators.lattice import generate_lattice
        model = generate_lattice(_make_lattice_data())
        assert isinstance(model, rhino3dm.File3dm)

    def test_model_has_geometry(self):
        from app.generators.lattice import generate_lattice
        model = generate_lattice(_make_lattice_data())
        assert len(model.Objects) > 0

    def test_can_write_to_file(self, tmp_path):
        from app.generators.lattice import generate_lattice
        model = generate_lattice(_make_lattice_data())
        path = str(tmp_path / "lattice.3dm")
        model.Write(path, 8)
        assert (tmp_path / "lattice.3dm").exists()


# --- Spiral Generator ---

class TestSpiralGenerator:
    def test_generates_3dm_model(self):
        from app.generators.spiral import generate_spiral
        model = generate_spiral(_make_spiral_data())
        assert isinstance(model, rhino3dm.File3dm)

    def test_model_has_curves(self):
        from app.generators.spiral import generate_spiral
        model = generate_spiral(_make_spiral_data())
        assert len(model.Objects) > 0

    def test_can_write_to_file(self, tmp_path):
        from app.generators.spiral import generate_spiral
        model = generate_spiral(_make_spiral_data())
        path = str(tmp_path / "spiral.3dm")
        model.Write(path, 8)
        assert (tmp_path / "spiral.3dm").exists()


# --- Porous Generator ---

class TestPorousGenerator:
    def test_generates_3dm_model(self):
        from app.generators.porous import generate_porous
        model = generate_porous(_make_porous_data())
        assert isinstance(model, rhino3dm.File3dm)

    def test_model_has_geometry(self):
        from app.generators.porous import generate_porous
        model = generate_porous(_make_porous_data())
        assert len(model.Objects) > 0

    def test_can_write_to_file(self, tmp_path):
        from app.generators.porous import generate_porous
        model = generate_porous(_make_porous_data())
        path = str(tmp_path / "porous.3dm")
        model.Write(path, 8)
        assert (tmp_path / "porous.3dm").exists()


# --- Generate dispatch ---

class TestGenerateDispatch:
    def test_dispatch_cellular(self):
        from app.generators import generate_3dm
        model = generate_3dm("cellular", _make_cellular_data())
        assert isinstance(model, rhino3dm.File3dm)

    def test_dispatch_unknown_raises(self):
        from app.generators import generate_3dm
        with pytest.raises(ValueError):
            generate_3dm("unknown", {})
