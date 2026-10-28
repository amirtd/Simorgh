r"""Create animator-facing koi controls in /stage for an existing fish HDA."""

import hou


FISH_PATH = "/obj/koi_fish_hero"
IMPORT_PATH = "/stage/koi_fish_sopimport"
CONTROL_PATH = "/stage/koi_fish_controls"
PRIM_PATH = "/world/koi_fish_hero"

SWIM_PARMS = (
    "enabled",
    "swim_speed",
    "body_amplitude",
    "tail_amplitude",
    "wavelength",
    "body_stiffness",
    "phase",
    "turn",
    "fish_bank",
    "auto_bank",
    "tail_flutter",
    "flutter_speed",
    "vertical_bob",
    "bob_speed",
    "curl_enable",
    "curl_start_frame",
    "curl_end_frame",
    "curl_amount",
    "curl_turns",
    "curl_tightness",
    "curl_spin_speed",
    "curl_spin_phase",
)


def copy_animation(source, target):
    """Copy keys/expression/value from one scalar parameter to another."""
    target.deleteAllKeyframes()
    keys = source.keyframes()
    if keys:
        for key in keys:
            target.setKeyframe(key)
    else:
        try:
            target.setExpression(source.expression(), source.expressionLanguage())
        except hou.OperationFailed:
            target.set(source.eval())


def main():
    stage = hou.node("/stage")
    fish = hou.node(FISH_PATH)
    sop_import = hou.node(IMPORT_PATH)
    if fish is None:
        raise RuntimeError("Missing " + FISH_PATH)
    if sop_import is None:
        raise RuntimeError("Missing " + IMPORT_PATH)

    controls = hou.node(CONTROL_PATH)
    if controls is None:
        controls = stage.createNode("xform", "koi_fish_controls")

    controls.parm("primpattern").set(PRIM_PATH)
    controls.setColor(hou.Color((0.1, 0.65, 1.0)))
    controls.setUserData("nodeshape", "trapezoid_up")

    # Add the HDA's authored animator folders to the Stage control node.
    group = controls.parmTemplateGroup()
    for folder_name in ("Koi Swim Rig", "Curl Ball Release"):
        old_folder = group.findFolder(folder_name)
        if old_folder:
            group.remove(old_folder.name())
        source_folder = fish.parmTemplateGroup().findFolder(folder_name)
        if source_folder is None:
            raise RuntimeError("The fish HDA has no {} parameter folder".format(folder_name))
        group.append(source_folder)
    controls.setParmTemplateGroup(group)

    # Preserve the current rig settings, then make the HDA follow Stage controls.
    for name in SWIM_PARMS:
        fish_parm = fish.parm(name)
        stage_parm = controls.parm(name)
        if fish_parm is None or stage_parm is None:
            continue
        copy_animation(fish_parm, stage_parm)
        fish_parm.deleteAllKeyframes()
        fish_parm.setExpression(
            'ch("{}/{}")'.format(CONTROL_PATH, name),
            hou.exprLanguage.Hscript,
        )

    # Transfer OBJ transform animation to the Transform LOP. SOP Import ignores
    # object transforms, whereas these LOP parameters author USD xform samples.
    for name in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        copy_animation(fish.parm(name), controls.parm(name))

    # Insert controls immediately after the fish SOP Import, preserving its
    # existing downstream connection (for example, directly into a camera LOP).
    consumers = [
        (output, index)
        for output in sop_import.outputs()
        for index, input_node in enumerate(output.inputs())
        if input_node == sop_import
    ]
    controls.setInput(0, sop_import)
    for output, index in consumers:
        if output != controls:
            output.setInput(index, controls)

    sop_import.parm("authortimesamples").set("always")
    controls.moveToGoodPosition()
    controls.setCurrent(True, clear_all_selected=True)
    controls.setDisplayFlag(True)
    print("Stage koi controls: " + controls.path())
    return controls


STAGE_KOI_CONTROLS = main()
