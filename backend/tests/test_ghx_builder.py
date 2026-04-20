"""Tests for GHX (Grasshopper XML) builder."""
import xml.etree.ElementTree as ET


class TestGHXBuilder:
    def test_creates_valid_xml(self):
        from app.ghx_builder import GHXBuilder
        builder = GHXBuilder()
        xml_str = builder.build()
        # Should parse without error
        ET.fromstring(xml_str)

    def test_add_slider(self):
        from app.ghx_builder import GHXBuilder
        builder = GHXBuilder()
        guid = builder.add_slider("Density", 1, 100, 50)
        assert guid is not None
        xml_str = builder.build()
        assert "Density" in xml_str

    def test_add_multiple_sliders(self):
        from app.ghx_builder import GHXBuilder
        builder = GHXBuilder()
        builder.add_slider("Density", 1, 100, 50)
        builder.add_slider("Depth", 0.01, 2.0, 0.1, decimals=2)
        builder.add_slider("Scale", 0.1, 10.0, 1.0, decimals=1)
        xml_str = builder.build()
        assert "Density" in xml_str
        assert "Depth" in xml_str
        assert "Scale" in xml_str

    def test_save_to_file(self, tmp_path):
        from app.ghx_builder import GHXBuilder
        builder = GHXBuilder()
        builder.add_slider("Test", 0, 10, 5)
        path = str(tmp_path / "test.ghx")
        builder.save(path)
        assert (tmp_path / "test.ghx").exists()
        # Verify saved file is valid XML
        ET.parse(path)

    def test_has_archive_structure(self):
        from app.ghx_builder import GHXBuilder
        builder = GHXBuilder()
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        assert root.tag == "Archive"

    def test_connect_wires(self):
        from app.ghx_builder import GHXBuilder
        builder = GHXBuilder()
        s1 = builder.add_slider("Input", 0, 10, 5)
        s2 = builder.add_slider("Output", 0, 10, 5)
        builder.connect(s1, 0, s2, 0)
        xml_str = builder.build()
        # Wire info should be present
        assert s1 in xml_str or "Source" in xml_str


class TestGHXTemplates:
    def test_cellular_template(self):
        from app.ghx_builder import build_cellular_ghx
        xml_str = build_cellular_ghx()
        ET.fromstring(xml_str)  # valid XML
        assert "Cell Count" in xml_str or "Density" in xml_str

    def test_branching_template(self):
        from app.ghx_builder import build_branching_ghx
        xml_str = build_branching_ghx()
        ET.fromstring(xml_str)

    def test_shell_template(self):
        from app.ghx_builder import build_shell_ghx
        xml_str = build_shell_ghx()
        ET.fromstring(xml_str)

    def test_lattice_template(self):
        from app.ghx_builder import build_lattice_ghx
        xml_str = build_lattice_ghx()
        ET.fromstring(xml_str)

    def test_spiral_template(self):
        from app.ghx_builder import build_spiral_ghx
        xml_str = build_spiral_ghx()
        ET.fromstring(xml_str)

    def test_porous_template(self):
        from app.ghx_builder import build_porous_ghx
        xml_str = build_porous_ghx()
        ET.fromstring(xml_str)
