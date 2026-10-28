"""Promote Phoenix animation controls onto the BodyRig HDA interface."""

from __future__ import annotations

import os

try:
    hou  # type: ignore[name-defined]
except NameError:
    import hou  # type: ignore


ROOT = os.path.dirname(os.path.abspath(__file__))
HDA_PATH = os.path.join(ROOT, "BodyRig.hdanc")
TYPE_NAME = "tamadon::wings::1.0"
GUIDE_TOGGLE = "show_feather_flow_guides"

CONTROL_NAMES = (
    "feather_growth",
    "wind_physics_strength",
    "roots_only_preview",
    "auto_flap",
    "flap_angle",
    "flap_amplitude",
    "flap_period",
    "shoulder_sweep",
    "elbow_fold",
    "wrist_curl",
    "wing_twist",
    "feather_flex",
    "body_pitch",
    "neck_pitch",
    "head_pitch",
    "body_center_t",
    "body_center_r",
    "foot_l_t",
    "foot_l_r",
    "leg_pin_l",
    "toe_l_curl",
    "toe_l_spread",
    "hallux_l_curl",
    "foot_r_t",
    "foot_r_r",
    "leg_pin_r",
    "toe_r_curl",
    "toe_r_spread",
    "hallux_r_curl",
    "show_wing_boundary",
    "wing_boundary_offset",
    "wing_boundary_thickness",
    "wing_boundary_bevel_radius",
    "show_body_proxy",
    "show_skeleton",
)


def definition() -> hou.HDADefinition:
    hou.hda.installFile(HDA_PATH)
    for item in hou.hda.definitionsInFile(HDA_PATH):
        if item.nodeTypeName() == TYPE_NAME:
            return item
    raise RuntimeError(f"Definition {TYPE_NAME!r} not found in {HDA_PATH}")


def main() -> None:
    hda_def = definition()
    instance = hou.node("/obj").createNode(TYPE_NAME, "__bodyrig_promote_controls", exact_type_name=True)
    instance.allowEditingOfContents()
    internal = instance.node("phoenix_character_rig")
    if internal is None:
        raise RuntimeError("Internal phoenix_character_rig node was not found")

    templates = []
    for name in CONTROL_NAMES:
        parm_tuple = internal.parmTuple(name)
        if parm_tuple is None:
            raise RuntimeError(f"Missing internal control: {name}")
        templates.append(parm_tuple.parmTemplate())

        # Link every scalar component to the identically named HDA parameter.
        for parm in parm_tuple:
            parm.deleteAllKeyframes()
            parm.setExpression(
                f'ch("../{parm.name()}")',
                language=hou.exprLanguage.Hscript,
            )

    guide_toggle_template = hou.ToggleParmTemplate(
        GUIDE_TOGGLE,
        "Show Feather Flow Guides",
        default_value=False,
    )
    guide_toggle_template.setScriptCallback(
        'node = kwargs["node"]; '
        'node.parm("visibleobjects").set('
        '"phoenix_character_rig feather_flow_guides" '
        'if kwargs["parm"].eval() else "phoenix_character_rig")'
    )
    guide_toggle_template.setScriptCallbackLanguage(hou.scriptLanguage.Python)
    templates.append(guide_toggle_template)
    guide_switch = instance.node("feather_flow_guides/show_guides")
    if guide_switch is None or guide_switch.parm("input") is None:
        raise RuntimeError("Internal feather flow guide switch was not found")
    guide_switch.parm("input").deleteAllKeyframes()
    guide_switch.parm("input").setExpression(
        f'ch("../../{GUIDE_TOGGLE}")',
        language=hou.exprLanguage.Hscript,
    )
    guide_object = instance.node("feather_flow_guides")
    if guide_object is None or guide_object.parm("display") is None:
        raise RuntimeError("Internal feather flow guide object display parameter was not found")
    guide_object.parm("display").deleteAllKeyframes()
    guide_object.parm("display").setExpression(
        f'ch("../{GUIDE_TOGGLE}")',
        language=hou.exprLanguage.Hscript,
    )

    # Save the relative internal channel links into the master definition.
    hda_def.updateFromNode(instance)

    interface = hda_def.parmTemplateGroup()
    visible_children = interface.find("visibleobjects")
    if visible_children is None:
        raise RuntimeError("HDA Visible Children parameter template was not found")
    visible_children.setDefaultValue(("phoenix_character_rig",))
    interface.replace("visibleobjects", visible_children)
    # Houdini may normalize an appended folder's internal token (for example,
    # to stdswitcher3_2), so use its stable user-facing label for replacement.
    for entry in interface.entries():
        if isinstance(entry, hou.FolderParmTemplate) and entry.label() == "Phoenix Animation Controls":
            interface.remove(entry.name())
    folder = hou.FolderParmTemplate(
        "phoenix_animation_controls",
        "Phoenix Animation Controls",
        parm_templates=templates,
    )
    interface.append(folder)
    hda_def.setParmTemplateGroup(interface)

    visibility_event = '''node = kwargs.get("node")
if node is not None:
    show = bool(node.evalParm("show_feather_flow_guides"))
    pattern = "phoenix_character_rig feather_flow_guides" if show else "phoenix_character_rig"
    parm = node.parm("visibleobjects")
    if parm is not None:
        parm.set(pattern)
'''
    for section_name in ("OnCreated", "OnLoaded", "OnUpdated"):
        hda_def.addSection(section_name, visibility_event)
        hda_def.setExtraFileOption(f"{section_name}/IsPython", True)

    instance.destroy()
    hou.hda.reloadFile(HDA_PATH)

    # Create a clean locked instance to verify the published definition.
    check = hou.node("/obj").createNode(TYPE_NAME, "__bodyrig_verify", exact_type_name=True)
    missing = [name for name in CONTROL_NAMES + (GUIDE_TOGGLE,) if check.parmTuple(name) is None]
    if missing:
        raise RuntimeError(f"Promoted controls missing after reload: {missing}")
    if check.parm("visibleobjects").eval() != "phoenix_character_rig":
        raise RuntimeError(
            "New asset did not initialize hidden guides: " + check.parm("visibleobjects").eval())
    check.parm("shoulder_sweep").set(23.0)
    linked = check.node("phoenix_character_rig").parm("shoulder_sweep").eval()
    if abs(linked - 23.0) > 1e-6:
        raise RuntimeError(f"Promoted shoulder control did not drive the rig: {linked}")
    check.parm(GUIDE_TOGGLE).set(True)
    callback = check.parm(GUIDE_TOGGLE).parmTemplate().scriptCallback()
    exec(callback, {"kwargs": {"node": check, "parm": check.parm(GUIDE_TOGGLE)}})
    guide_value = check.node("feather_flow_guides/show_guides").parm("input").eval()
    if guide_value != 1:
        raise RuntimeError(f"Promoted guide toggle did not drive the guide switch: {guide_value}")
    object_visibility = check.node("feather_flow_guides").parm("display").eval()
    if object_visibility != 1:
        raise RuntimeError(f"Promoted guide toggle did not drive object visibility: {object_visibility}")
    visible_pattern = check.parm("visibleobjects").eval()
    if "feather_flow_guides" not in visible_pattern:
        raise RuntimeError(f"Visible Children did not include guides: {visible_pattern}")
    output = check.node("phoenix_character_rig/OUT_PHOENIX_CHARACTER")
    output.geometry()
    errors = output.errors()
    if errors:
        raise RuntimeError("Rig output cook errors: " + "\n".join(errors))
    check.destroy()

    print("Updated:", HDA_PATH)
    print("Definition:", TYPE_NAME)
    print("Promoted controls:", len(CONTROL_NAMES) + 1)


if __name__ == "__main__":
    main()
