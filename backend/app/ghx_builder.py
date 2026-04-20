"""GHX (Grasshopper XML) parametric definition builder.

Generates .ghx files with sliders and components tailored to each biomimicry category.
"""
import uuid
import xml.etree.ElementTree as ET


class GHXBuilder:
    def __init__(self):
        self.components = []
        self.wires = []

    def add_slider(self, name: str, min_val: float, max_val: float,
                   default: float, decimals: int = 0,
                   position: tuple = (0, 0)) -> str:
        guid = str(uuid.uuid4())
        self.components.append({
            "type": "slider",
            "guid": guid,
            "name": name,
            "min": min_val,
            "max": max_val,
            "value": default,
            "decimals": decimals,
            "position": position,
        })
        return guid

    def add_panel(self, name: str, text: str, position: tuple = (0, 0)) -> str:
        guid = str(uuid.uuid4())
        self.components.append({
            "type": "panel",
            "guid": guid,
            "name": name,
            "text": text,
            "position": position,
        })
        return guid

    def connect(self, source_guid: str, output_index: int,
                target_guid: str, input_index: int):
        self.wires.append({
            "source": source_guid,
            "output": output_index,
            "target": target_guid,
            "input": input_index,
        })

    def build(self) -> str:
        """Generate .ghx XML string."""
        root = ET.Element("Archive", name="Root")
        items = ET.SubElement(root, "items", count="1")
        version_item = ET.SubElement(items, "item", name="ArchiveVersion",
                                      type_name="gh_version", type_code="80")
        ET.SubElement(version_item, "Major").text = "0"
        ET.SubElement(version_item, "Minor").text = "2"
        ET.SubElement(version_item, "Revision").text = "0"

        chunks = ET.SubElement(root, "chunks", count="1")
        definition = ET.SubElement(chunks, "chunk", name="Definition")

        def_items = ET.SubElement(definition, "items", count="1")
        plugin_ver = ET.SubElement(def_items, "item", name="plugin_version",
                                    type_name="gh_version", type_code="80")
        ET.SubElement(plugin_ver, "Major").text = "1"
        ET.SubElement(plugin_ver, "Minor").text = "0"
        ET.SubElement(plugin_ver, "Revision").text = "7"

        def_chunks = ET.SubElement(definition, "chunks", count="2")

        # Properties chunk
        ET.SubElement(def_chunks, "chunk", name="DefinitionProperties")

        # Objects chunk
        objects_chunk = ET.SubElement(def_chunks, "chunk", name="DefinitionObjects")
        obj_items = ET.SubElement(objects_chunk, "items", count="1")
        ET.SubElement(obj_items, "item", name="ObjectCount",
                      type_name="gh_int32", type_code="3").text = str(len(self.components))

        obj_chunks = ET.SubElement(objects_chunk, "chunks",
                                    count=str(len(self.components)))

        for idx, comp in enumerate(self.components):
            obj = ET.SubElement(obj_chunks, "chunk", name="Object", index=str(idx))
            obj_items = ET.SubElement(obj, "items", count="2")
            ET.SubElement(obj_items, "item", name="GUID",
                          type_name="gh_guid", type_code="9").text = "{" + comp["guid"] + "}"
            ET.SubElement(obj_items, "item", name="Name",
                          type_name="gh_string", type_code="10").text = comp.get("name", "")

            container_chunks = ET.SubElement(obj, "chunks", count="1")
            container = ET.SubElement(container_chunks, "chunk", name="Container")
            cont_items = ET.SubElement(container, "items")

            if comp["type"] == "slider":
                self._build_slider(cont_items, comp)
            elif comp["type"] == "panel":
                self._build_panel(cont_items, comp)

            # Pivot position
            pivot = ET.SubElement(cont_items, "item", name="Pivot",
                                   type_name="gh_drawing_pointf", type_code="31")
            ET.SubElement(pivot, "X").text = str(comp["position"][0])
            ET.SubElement(pivot, "Y").text = str(comp["position"][1])

            # Instance GUID
            ET.SubElement(cont_items, "item", name="InstanceGuid",
                          type_name="gh_guid", type_code="9").text = "{" + comp["guid"] + "}"

            # Add wire sources if this component is a target
            for wire in self.wires:
                if wire["target"] == comp["guid"]:
                    source_el = ET.SubElement(cont_items, "item", name="Source",
                                              type_name="gh_guid", type_code="9")
                    source_el.text = "{" + wire["source"] + "}"

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def _build_slider(self, parent, comp):
        slider = ET.SubElement(parent, "item", name="Slider",
                                type_name="gh_slider", type_code="75")
        ET.SubElement(slider, "Name").text = comp["name"]
        ET.SubElement(slider, "Min").text = str(comp["min"])
        ET.SubElement(slider, "Max").text = str(comp["max"])
        ET.SubElement(slider, "Value").text = str(comp["value"])
        ET.SubElement(slider, "Decimals").text = str(comp["decimals"])

    def _build_panel(self, parent, comp):
        panel = ET.SubElement(parent, "item", name="Panel",
                               type_name="gh_panel", type_code="59")
        ET.SubElement(panel, "Name").text = comp["name"]
        ET.SubElement(panel, "Text").text = comp.get("text", "")

    def save(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.build())


# --- Category-specific GHX templates ---

def _common_sliders(builder: GHXBuilder, y_offset: int = 0):
    """Add standard BioForm sliders."""
    builder.add_slider("Pattern Density", 1, 100, 50, position=(100, y_offset))
    builder.add_slider("Panel Depth", 0.01, 2.0, 0.1, decimals=2, position=(100, y_offset + 40))
    builder.add_slider("Scale Factor", 0.1, 10.0, 1.0, decimals=1, position=(100, y_offset + 80))
    builder.add_slider("Randomness", 0.0, 1.0, 0.2, decimals=2, position=(100, y_offset + 120))
    builder.add_slider("Module Size X", 0.5, 10.0, 2.0, decimals=1, position=(100, y_offset + 160))
    builder.add_slider("Module Size Y", 0.5, 10.0, 2.0, decimals=1, position=(100, y_offset + 200))


def build_cellular_ghx() -> str:
    builder = GHXBuilder()
    _common_sliders(builder)
    builder.add_slider("Cell Count", 5, 200, 30, position=(100, 280))
    builder.add_slider("Cell Size Variation", 0.0, 1.0, 0.3, decimals=2, position=(100, 320))
    builder.add_slider("Wall Thickness", 0.005, 0.1, 0.02, decimals=3, position=(100, 360))
    builder.add_panel("Category", "Cellular / Voronoi", position=(400, 100))
    return builder.build()


def build_branching_ghx() -> str:
    builder = GHXBuilder()
    _common_sliders(builder)
    builder.add_slider("Branch Angle", 10, 60, 30, position=(100, 280))
    builder.add_slider("Subdivision Levels", 1, 6, 4, position=(100, 320))
    builder.add_slider("Taper Ratio", 0.3, 0.9, 0.7, decimals=2, position=(100, 360))
    builder.add_slider("Trunk Diameter", 0.1, 1.0, 0.3, decimals=2, position=(100, 400))
    builder.add_panel("Category", "Branching / Dendritic", position=(400, 100))
    return builder.build()


def build_shell_ghx() -> str:
    builder = GHXBuilder()
    _common_sliders(builder)
    builder.add_slider("Curvature Intensity", 0.0, 5.0, 2.0, decimals=1, position=(100, 280))
    builder.add_slider("Fold Frequency", 1, 20, 5, position=(100, 320))
    builder.add_slider("Surface Thickness", 0.01, 0.5, 0.05, decimals=2, position=(100, 360))
    builder.add_panel("Category", "Shell / Surface", position=(400, 100))
    return builder.build()


def build_lattice_ghx() -> str:
    builder = GHXBuilder()
    _common_sliders(builder)
    builder.add_slider("Grid Angle", 0, 90, 45, position=(100, 280))
    builder.add_slider("Grid Spacing", 0.1, 5.0, 0.5, decimals=1, position=(100, 320))
    builder.add_slider("Member Thickness", 0.01, 0.2, 0.05, decimals=2, position=(100, 360))
    builder.add_panel("Category", "Lattice / Grid", position=(400, 100))
    return builder.build()


def build_spiral_ghx() -> str:
    builder = GHXBuilder()
    _common_sliders(builder)
    builder.add_slider("Arm Count", 1, 8, 3, position=(100, 280))
    builder.add_slider("Growth Rate", 1.0, 3.0, 1.618, decimals=3, position=(100, 320))
    builder.add_slider("Pitch", 0.1, 5.0, 1.0, decimals=1, position=(100, 360))
    builder.add_panel("Category", "Spiral / Fibonacci", position=(400, 100))
    return builder.build()


def build_porous_ghx() -> str:
    builder = GHXBuilder()
    _common_sliders(builder)
    builder.add_slider("Hole Size Range", 0.05, 2.0, 0.3, decimals=2, position=(100, 280))
    builder.add_slider("Solid-to-Void Ratio", 0.2, 0.9, 0.6, decimals=2, position=(100, 320))
    builder.add_slider("Gradient Curve", 0.0, 1.0, 0.5, decimals=2, position=(100, 360))
    builder.add_panel("Category", "Porous / Perforated", position=(400, 100))
    return builder.build()


GHX_BUILDERS = {
    "cellular": build_cellular_ghx,
    "branching": build_branching_ghx,
    "shell": build_shell_ghx,
    "lattice": build_lattice_ghx,
    "spiral": build_spiral_ghx,
    "porous": build_porous_ghx,
}


def build_ghx_for_category(category: str) -> str:
    """Build a .ghx template for the given category."""
    if category not in GHX_BUILDERS:
        raise ValueError(f"Unknown category: {category}")
    return GHX_BUILDERS[category]()
