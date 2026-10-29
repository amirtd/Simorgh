"""Make Solaris follow the OBJ koi without driving its animation controls."""

import hou

FISH_PATH = "/obj/koi_fish_hero"
IMPORT_PATH = "/stage/koi_fish_sopimport"
CONTROL_PATH = "/stage/koi_fish_controls"
GEOMETRY_TRANSFORM_PATH = "/stage/koi_fish_geometry_transform"
PRIM_PATH = "/world/koi_fish_hero"


def copy_animation(source, target):
    """Copy animation itself, rather than creating a channel reference."""
    keys = source.keyframes()
    value = source.eval()
    target.deleteAllKeyframes()
    if keys:
        for key in keys:
            target.setKeyframe(key)
        target.setKeyframeExtrapolation(True, source.keyframeExtrapolation(True))
        target.setKeyframeExtrapolation(False, source.keyframeExtrapolation(False))
    else:
        target.set(value)


def main():
    fish = hou.node(FISH_PATH)
    sop_import = hou.node(IMPORT_PATH)
    if fish is None or sop_import is None:
        raise RuntimeError("Missing koi OBJ or SOP Import")

    old = hou.node(CONTROL_PATH)
    moved = []
    if old is not None:
        # Migrate only parameters still driven by the old Stage panel.
        # Existing independent OBJ animation is authoritative and untouched.
        for target in fish.parms():
            if CONTROL_PATH + "/" not in target.rawValue():
                continue
            source = target.getReferencedParm()
            if source == target or source.node() != old:
                raise RuntimeError("Cannot safely migrate " + target.path())
            if FISH_PATH + "/" in source.rawValue():
                raise RuntimeError("Circular animation reference: " + source.path())
            copy_animation(source, target)
            moved.append(target.name())

    # Reuse only the standard transform node. Remove its old rig controls and
    # callbacks so there is no second animation panel that can drive the OBJ.
    controls = old or hou.node("/stage").createNode("xform", "koi_fish_controls")
    if controls.type().name() != "xform":
        raise RuntimeError("Expected a Transform LOP at " + CONTROL_PATH)
    controls.removeSpareParms()
    controls.parm("primpattern").set(PRIM_PATH)
    for name in (
        "tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "scale",
        "px", "py", "pz", "prx", "pry", "prz", "xOrd", "rOrd",
    ):
        source = fish.parm(name)
        target = controls.parm(name)
        if source is None or target is None:
            continue
        target.deleteAllKeyframes()
        function = "chs" if target.parmTemplate().type() == hou.parmTemplateType.String else "ch"
        target.setExpression('{}("{}/{}")'.format(function, FISH_PATH, name), hou.exprLanguage.Hscript)
    for parm in controls.parmTuple("shear") or ():
        parm.deleteAllKeyframes()
        parm.set(0)
    controls.parm("setabsolutexform").set(1)
    controls.setComment("Animate /obj/koi_fish_hero. This node only imports its transforms; it does not drive OBJ controls.")
    controls.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    controls.setColor(hou.Color((0.3, 0.6, 0.35)))

    # SOP Import reads raw SOP points. The FBX geometry object's local
    # transform (including its pre-transform) is separate from the outer HDA.
    # Restore that inner transform on the imported mesh before applying the
    # outer rig transform. Decomposition includes shear and ancestor transforms.
    source_sop = sop_import.parm("soppath").evalAsNode()
    if source_sop is None:
        raise RuntimeError("Missing source SOP")
    source_object = source_sop.parent()
    while source_object and not isinstance(source_object, hou.ObjNode):
        source_object = source_object.parent()
    if source_object is None:
        raise RuntimeError("Source SOP has no geometry object")
    geometry_transform = hou.node(GEOMETRY_TRANSFORM_PATH)
    if geometry_transform is None:
        geometry_transform = hou.node("/stage").createNode("xform", "koi_fish_geometry_transform")
        geometry_transform.setPosition((sop_import.position() + controls.position()) * 0.5)
    geometry_transform.parm("primpattern").set(PRIM_PATH + "/*")
    geometry_transform.parm("xforminworldspace").set(0)
    geometry_transform.parm("setabsolutexform").set(1)
    geometry_transform.parm("xOrd").set("srt")
    geometry_transform.parm("rOrd").set("xyz")
    matrix_expression = '(hou.node({!r}).worldTransform() * hou.node({!r}).worldTransform().inverted())'.format(source_object.path(), FISH_PATH)
    for tuple_name, component in (("t", "translate"), ("r", "rotate"), ("s", "scale"), ("shear", "shear")):
        for index, parm in enumerate(geometry_transform.parmTuple(tuple_name)):
            parm.deleteAllKeyframes()
            parm.setExpression(matrix_expression + ".explode()[{!r}][{}]".format(component, index), hou.exprLanguage.Python)
    geometry_transform.setComment("Preserves the inner geometry object's full transform. Animation remains in /obj.")
    geometry_transform.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    consumers = [
        (node, index)
        for node in sop_import.outputs()
        for index, input_node in enumerate(node.inputs())
        if input_node == sop_import and node not in (controls, geometry_transform)
    ]
    geometry_transform.setInput(0, sop_import)
    controls.setInput(0, geometry_transform)
    for node, index in consumers:
        node.setInput(index, controls)
    sop_import.parm("authortimesamples").set("always")
    print("Migrated controls to OBJ:", moved)
    print("Stage now follows:", FISH_PATH)
    return controls


if __name__ == "__main__":
    STAGE_KOI_CONTROLS = main()
