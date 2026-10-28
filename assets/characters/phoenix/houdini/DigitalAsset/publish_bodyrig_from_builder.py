"""Publish the current scripted Phoenix skeleton/pose network into BodyRig."""

from __future__ import annotations

import os
import sys

try:
    hou  # type: ignore[name-defined]
except NameError:
    import hou  # type: ignore


HERE = os.path.dirname(os.path.abspath(__file__))
PHOENIX_ROOT = os.path.dirname(HERE)
if PHOENIX_ROOT not in sys.path:
    sys.path.insert(0, PHOENIX_ROOT)

import build_phoenix_character_rig as base


HDA_PATH = os.path.join(HERE, "BodyRig.hdanc")
TYPE_NAME = "tamadon::wings::1.0"


def main() -> None:
    hou.hda.installFile(HDA_PATH)
    definitions = [
        item for item in hou.hda.definitionsInFile(HDA_PATH)
        if item.nodeTypeName() == TYPE_NAME
    ]
    if not definitions:
        raise RuntimeError(f"Definition {TYPE_NAME} not found")
    definition = definitions[0]

    instance = hou.node("/obj").createNode(TYPE_NAME, "__bodyrig_publish", exact_type_name=True)
    instance.allowEditingOfContents()
    internal = instance.node("phoenix_character_rig")
    if internal is None:
        raise RuntimeError("phoenix_character_rig is missing inside BodyRig")

    # Rebuild the internal rig-control parameter folder from the authoritative
    # builder without disturbing the standard Geometry object parameters.
    template_node = hou.node("/obj").createNode("geo", "__bodyrig_control_template")
    base.add_controls(template_node)
    source_folder = next(
        entry for entry in template_node.parmTemplateGroup().entries()
        if isinstance(entry, hou.FolderParmTemplate) and entry.label() == "Phoenix Rig Controls"
    )
    internal_group = internal.parmTemplateGroup()
    for entry in internal_group.entries():
        if isinstance(entry, hou.FolderParmTemplate) and entry.label() == "Phoenix Rig Controls":
            internal_group.remove(entry.name())
    internal_group.append(source_folder)
    internal.setParmTemplateGroup(internal_group)
    template_node.destroy()

    # Synchronize the procedural skeleton and pose/deformation code used by the
    # standalone original rig.  Node wiring and HDA-relative paths are retained.
    snippets = {
        "REST_SKELETON": base.REST_SKELETON_VEX,
        "POSE_SKELETON": base.POSE_SKELETON_VEX,
        "WING_SKELETAL_DEFORM": base.WING_DEFORM_VEX,
        "BODY_PROXY": base.BODY_PROXY_VEX,
        "BODY_PROXY_POSE": base.BODY_POSE_VEX,
        "BODY_CENTER_WINGS": base.CENTER_TRANSFORM_VEX,
    }
    for node_name, code in snippets.items():
        node = internal.node(node_name)
        if node is None or node.parm("snippet") is None:
            raise RuntimeError(f"Missing wrangle {node_name} in BodyRig")
        node.parm("snippet").set(code)

    # Rebuild the static weighted wing-boundary proxy. This topology was added
    # after the original HDA was authored, so it must be created as well as
    # having its snippets synchronized.
    boundary_nodes = (
        "SHOW_WING_BOUNDARY", "OUT_WING_BOUNDARY", "BODY_CENTER_WING_BOUNDARY",
        "WING_BOUNDARY_POSITION_OFFSET", "MERGE_WING_BOUNDARIES", "RIGHT_WING_BOUNDARY_MIRROR",
        "LEFT_WING_BOUNDARY_OFFSET", "WING_BOUNDARY_NORMALS", "WING_BOUNDARY_SKIN",
        "WING_BOUNDARY_BEVEL", "WING_BOUNDARY_CENTER_THICKNESS",
        "WING_BOUNDARY_EXTRUDE", "WING_BOUNDARY_REST",
    )
    for node_name in boundary_nodes:
        node = internal.node(node_name)
        if node is not None:
            node.destroy()
    empty = internal.node("EMPTY")
    final = internal.node("MERGE_CHARACTER")
    if empty is None or final is None:
        raise RuntimeError("BodyRig is missing EMPTY or MERGE_CHARACTER")
    boundary_switch, boundary_out = base.build_wing_boundary_network(internal, empty)
    final.setInput(3, boundary_switch)

    definition.updateFromNode(instance)
    instance.destroy()
    hou.hda.reloadFile(HDA_PATH)
    print("Published builder rig into:", HDA_PATH)


if __name__ == "__main__":
    main()
