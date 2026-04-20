# Skill: GHX Builder

How to programmatically generate Grasshopper .ghx files (XML format) for parametric definitions.

## When to Use
Any time you generate .ghx output files. This skill documents the XML structure so you don't have to reverse-engineer it each time.

## GHX File Structure

A .ghx file is XML with this skeleton:

```xml
<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<Archive name="Root">
  <items count="1">
    <item name="ArchiveVersion" type_name="gh_version" type_code="80">
      <Major>0</Major>
      <Minor>2</Minor>
      <Revision>0</Revision>
    </item>
  </items>
  <chunks count="1">
    <chunk name="Definition">
      <items count="1">
        <item name="plugin_version" type_name="gh_version" type_code="80">
          <Major>1</Major><Minor>0</Minor><Revision>7</Revision>
        </item>
      </items>
      <chunks count="2">
        <chunk name="DefinitionProperties">
          <!-- Document properties -->
        </chunk>
        <chunk name="DefinitionObjects">
          <!-- All components and parameters live here -->
        </chunk>
      </chunks>
    </chunk>
  </chunks>
</Archive>
```

## Key Concepts

### Components (nodes)
Each Grasshopper component is an object with:
- **InstanceGuid**: Unique UUID
- **Name**: Component name (e.g., "Number Slider", "Merge", "Mesh")
- **Pivot**: Canvas position (x, y)
- **Inputs/Outputs**: Parameter ports with their own GUIDs

### Wires (connections)
Connections between components are defined by referencing source output GUID → target input GUID.

### Number Slider (most common parametric input)
```xml
<chunk name="Object" index="0">
  <items count="2">
    <item name="GUID" type_name="gh_guid" type_code="9">{57da07bd-ecab-415d-9d86-af36d7073abc}</item>
    <item name="Name" type_name="gh_string" type_code="10">Number Slider</item>
  </items>
  <chunks count="1">
    <chunk name="Container">
      <items count="10">
        <item name="Slider" type_name="gh_slider" type_code="75">
          <Name>Density</Name>
          <Min>1</Min>
          <Max>100</Max>
          <Value>50</Value>
          <Decimals>0</Decimals>
        </item>
        <item name="Pivot" type_name="gh_drawing_pointf" type_code="31">
          <X>100</X><Y>100</Y>
        </item>
        <item name="InstanceGuid" type_name="gh_guid" type_code="9">{57da07bd-ecab-415d-9d86-af36d7073abc}</item>
      </items>
    </chunk>
  </chunks>
</chunk>
```

## BioForm Parametric Sliders

Every .ghx file should include these adjustable parameters:

| Slider | Range | Default | Purpose |
|--------|-------|---------|---------|
| Pattern Density | 1–100 | 50 | How dense/fine the biomimicry pattern is |
| Panel Depth | 0.01–2.0m | 0.1 | Extrusion depth for facade panels |
| Scale Factor | 0.1–10.0 | 1.0 | Overall scale multiplier |
| Curvature | 0.0–1.0 | 0.5 | Surface curvature intensity |
| Randomness | 0.0–1.0 | 0.2 | Organic variation amount |
| Module Size X | 0.5–10.0m | 2.0 | Module width |
| Module Size Y | 0.5–10.0m | 2.0 | Module height |

## Python Generation Strategy

Rather than constructing raw XML (error-prone), use a builder class:

```python
import uuid
import xml.etree.ElementTree as ET

class GHXBuilder:
    def __init__(self):
        self.components = []
        self.wires = []

    def add_slider(self, name, min_val, max_val, default, decimals=2, position=(0, 0)):
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

    def add_component(self, name, component_guid, position=(0, 0), inputs=None, outputs=None):
        guid = str(uuid.uuid4())
        self.components.append({
            "type": "component",
            "guid": guid,
            "component_guid": component_guid,
            "name": name,
            "position": position,
            "inputs": inputs or [],
            "outputs": outputs or [],
        })
        return guid

    def connect(self, source_guid, output_index, target_guid, input_index):
        self.wires.append({
            "source": source_guid,
            "output": output_index,
            "target": target_guid,
            "input": input_index,
        })

    def build(self) -> str:
        """Generate .ghx XML string."""
        # Build XML tree from self.components and self.wires
        # Return as formatted XML string
        ...

    def save(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.build())
```

## Common Grasshopper Component GUIDs

These are stable across Grasshopper versions:
- `{59e0b89a-e487-49f8-bab8-b5bab16be14c}` — Panel (text display)
- `{3581f42a-9592-4549-bd6b-1c0fc39d190b}` — Merge
- `{a0d62394-a118-422d-abb3-6af115c75b25}` — Mesh from Points
- `{b6d01011-2565-4025-8bba-71c42773caab}` — Voronoi 3D

> **Note**: Verify GUIDs against Rhino 8 Grasshopper. These may shift between versions. When in doubt, create a reference .ghx in Grasshopper manually and inspect the XML.

## Validation
Always validate generated .ghx by:
1. Checking XML is well-formed (`xml.etree.ElementTree.parse()`)
2. Ensuring all wire references point to existing component GUIDs
3. Opening in Grasshopper to verify (manual step — user's Rhino 8)
