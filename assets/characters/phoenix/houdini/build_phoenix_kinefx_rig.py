"""Build a native KineFX joint-selectable Phoenix rig in a new scene.

The resulting Rig Pose SOP exposes every named joint for direct viewport
selection, rotation, translation, and keyframing.  Feathers and the body proxy
are captured to the skeleton and follow arbitrary joint edits.
"""

from __future__ import annotations

import os
import sys

try:
    hou  # type: ignore[name-defined]
except NameError:
    import hou  # type: ignore


ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import build_phoenix_character_rig as base


OUTPUT = os.path.join(ROOT, "phoenix_kinefx_joint_rig.hipnc")
RIG_OBJECT = "/obj/phoenix_kinefx_rig"
JOINT_NAMES = (
    "root", "pelvis", "spine_01", "chest", "neck_01", "neck_02", "head", "beak",
    "tail_01", "tail_02", "tail_03",
    "clavicle_L", "shoulder_L", "elbow_L", "wrist_L", "wingtip_L",
    "clavicle_R", "shoulder_R", "elbow_R", "wrist_R", "wingtip_R",
    "hip_L", "knee_L", "ankle_L", "foot_L", "toe_L",
    "hip_R", "knee_R", "ankle_R", "foot_R", "toe_R",
)
WING_JOINTS = (
    "clavicle_L", "shoulder_L", "elbow_L", "wrist_L", "wingtip_L",
    "clavicle_R", "shoulder_R", "elbow_R", "wrist_R", "wingtip_R",
)


def wrangle(parent: hou.Node, name: str, code: str, source: hou.Node,
            run_over: int) -> hou.Node:
    node = parent.createNode("attribwrangle", name)
    node.setInput(0, source)
    node.parm("class").set(run_over)
    node.parm("snippet").set(code)
    return node


def add_rig_parameters(geo: hou.Node) -> None:
    group = geo.parmTemplateGroup()
    controls = hou.FolderParmTemplate(
        "kinefx_rig_settings",
        "KineFX Rig Settings",
        parm_templates=[
            base.float_parm("feather_growth", "Feather Growth Completion", 1.0, 0.0, 1.0),
            base.toggle_parm("roots_only_preview", "Roots Only Preview", True),
            base.toggle_parm("show_body_proxy", "Show Body Proxy", True),
            base.toggle_parm("show_skeleton", "Show Skeleton", True),
        ],
    )
    group.append(controls)
    geo.setParmTemplateGroup(group)


def source_space_xform(parent: hou.Node, source: hou.Node, name: str) -> hou.Node:
    node = parent.createNode("xform", name)
    node.setInput(0, source)
    for axis in "xyz":
        node.parm("t" + axis).setExpression(
            f'ch("/obj/feather_flow_guides/t{axis}")', language=hou.exprLanguage.Hscript)
        node.parm("r" + axis).setExpression(
            f'ch("/obj/feather_flow_guides/r{axis}")', language=hou.exprLanguage.Hscript)
        node.parm("s" + axis).setExpression(
            f'ch("/obj/feather_flow_guides/s{axis}")', language=hou.exprLanguage.Hscript)
    return node


def configure_rig_pose(rig_pose: hou.Node) -> None:
    """Create a keyable transform multiparm for every skeleton joint."""
    rig_pose.parm("transformations").set(len(JOINT_NAMES))
    for index, joint in enumerate(JOINT_NAMES):
        rig_pose.parm(f"enable{index}").set(True)
        rig_pose.parm(f"group{index}").set(f'@name="{joint}"')
        rig_pose.parm(f"mode{index}").set("pre")
        rig_pose.parm(f"rOrd{index}").set("xyz")
    rig_pose.setColor(hou.Color(0.95, 0.38, 0.05))
    rig_pose.setComment(
        "Select this node and press Enter in the viewport. Select joints, rotate/translate, and key the generated channels.")


def build_source_wings(geo: hou.Node) -> hou.Node:
    feather_import = geo.createNode("object_merge", "SOURCE_FEATHER_WING")
    feather_import.parm("objpath1").set("/obj/feather_flow_guides/OUT_FEATHER_SHAPES")
    if feather_import.parm("xformtype"):
        feather_import.parm("xformtype").set(0)
    feather_space = source_space_xform(geo, feather_import, "FEATHER_SOURCE_SPACE")

    root_sources = []
    source_geo = hou.node("/obj/feather_flow_guides")
    if source_geo is not None:
        for layer in source_geo.children():
            roots = layer.node("OUT_ROOTS")
            if roots is None:
                continue
            root_import = geo.createNode("object_merge", f"ROOTS_{layer.name().upper()}")
            root_import.parm("objpath1").set(roots.path())
            if root_import.parm("xformtype"):
                root_import.parm("xformtype").set(0)
            root_sources.append(source_space_xform(
                geo, root_import, f"{root_import.name()}_SOURCE_SPACE"))

    roots_merge = geo.createNode("merge", "MERGE_FEATHER_ROOTS")
    for index, source in enumerate(root_sources):
        roots_merge.setInput(index, source)

    preview = geo.createNode("switch", "FULL_FEATHERS_OR_ROOTS")
    preview.setInput(0, feather_space)
    preview.setInput(1, roots_merge)
    preview.parm("input").setExpression('ch("../roots_only_preview")')

    left = geo.createNode("xform", "REST_LEFT_WING")
    left.setInput(0, preview)
    left.parm("tz").set(0.28)
    right = geo.createNode("xform", "REST_RIGHT_WING")
    right.setInput(0, preview)
    right.parm("sz").set(-1.0)
    right.parm("tz").set(-0.28)

    merge = geo.createNode("merge", "REST_WINGS")
    merge.setInput(0, left)
    merge.setInput(1, right)
    return merge


def capture_and_deform(parent: hou.Node, name: str, rest_geo: hou.Node,
                       rest_skeleton: hou.Node, posed_skeleton: hou.Node,
                       capture_group: str = "") -> hou.Node:
    capture = parent.createNode("kinefx::jointcaptureproximity", f"CAPTURE_{name}")
    capture.setInput(0, rest_geo)
    capture.setInput(1, rest_skeleton)
    if capture.parm("capturegroup") and capture_group:
        capture.parm("capturegroup").set(capture_group)
    if capture.parm("maxinfluences"):
        capture.parm("maxinfluences").set(3)
    if capture.parm("dropoff"):
        capture.parm("dropoff").set(4.0)
    if capture.parm("ignoreskeletonconnectivity"):
        capture.parm("ignoreskeletonconnectivity").set(False)

    deform = parent.createNode("kinefx::jointdeform", f"DEFORM_{name}")
    deform.setInput(0, capture)
    deform.setInput(1, rest_skeleton)
    deform.setInput(2, posed_skeleton)
    deform.setComment(f"Native KineFX deformation for {name.lower()}")
    return deform


def build_kinefx_rig() -> tuple[hou.Node, hou.Node]:
    obj = hou.node("/obj")
    for name in ("phoenix_character_rig", "phoenix_kinefx_rig"):
        old = obj.node(name)
        if old is not None:
            old.destroy()

    geo = obj.createNode("geo", "phoenix_kinefx_rig")
    for child in geo.children():
        child.destroy()
    add_rig_parameters(geo)
    geo.setColor(hou.Color(0.85, 0.22, 0.04))
    geo.setComment("Native KineFX Phoenix: viewport-selectable and keyable joints")

    empty = geo.createNode("null", "EMPTY")
    rest = wrangle(geo, "REST_SKELETON", base.REST_SKELETON_VEX, empty, run_over=0)
    rest.setComment("Capture/rest pose skeleton")

    rig_pose = geo.createNode("kinefx::rigpose", "RIG_POSE_SELECT_AND_KEY")
    rig_pose.setInput(0, rest)
    configure_rig_pose(rig_pose)

    rest_wings = build_source_wings(geo)
    wing_group = " ".join(f'@name="{name}"' for name in WING_JOINTS)
    deformed_wings = capture_and_deform(
        geo, "WINGS", rest_wings, rest, rig_pose, capture_group=wing_group)
    wings_out = geo.createNode("null", "OUT_DEFORMED_WINGS")
    wings_out.setInput(0, deformed_wings)

    body = wrangle(geo, "REST_BODY_PROXY", base.BODY_PROXY_VEX, empty, run_over=0)
    deformed_body = capture_and_deform(geo, "BODY", body, rest, rig_pose)
    body_switch = geo.createNode("switch", "SHOW_BODY_PROXY")
    body_switch.setInput(0, empty)
    body_switch.setInput(1, deformed_body)
    body_switch.parm("input").setExpression('ch("../show_body_proxy")')

    wire = geo.createNode("polywire", "POSED_SKELETON_BONES")
    wire.setInput(0, rig_pose)
    if wire.parm("radius"):
        wire.parm("radius").set(0.025)
    skeleton_switch = geo.createNode("switch", "SHOW_SKELETON")
    skeleton_switch.setInput(0, empty)
    skeleton_switch.setInput(1, wire)
    skeleton_switch.parm("input").setExpression('ch("../show_skeleton")')

    final = geo.createNode("merge", "MERGE_KINEFX_CHARACTER")
    final.setInput(0, wings_out)
    final.setInput(1, body_switch)
    final.setInput(2, skeleton_switch)
    out = geo.createNode("null", "OUT_KINEFX_PHOENIX")
    out.setInput(0, final)
    out.setDisplayFlag(True)
    out.setRenderFlag(True)

    for node in geo.children():
        node.moveToGoodPosition()
    geo.layoutChildren()
    return geo, rig_pose


def configure_source(geo: hou.Node) -> None:
    growth = hou.node("/obj/feather_flow_guides/oil_growth")
    if growth is not None and growth.parm("progress") is not None:
        growth.parm("progress").deleteAllKeyframes()
        growth.parm("progress").setExpression(
            f'ch("{geo.path()}/feather_growth")', language=hou.exprLanguage.Hscript)

    controls = hou.node("/obj/feather_flow_guides/WING_CONTROLS")
    if controls is not None and controls.parm("flap_amp") is not None:
        controls.parm("flap_amp").set(0.0)

    wind = hou.node("/obj/feather_flow_guides/wing_wind")
    if wind is not None:
        wind.bypass(True)
        wind.setComment("Bypassed: native joint rig has no procedural wind physics")


def main() -> None:
    hou.hipFile.load(base.latest_source(), suppress_save_prompt=True)
    geo, rig_pose = build_kinefx_rig()
    configure_source(geo)
    hou.playbar.setFrameRange(1, 240)
    hou.setFrame(1)
    rig_pose.setCurrent(True, clear_all_selected=True)
    hou.hipFile.save(OUTPUT)
    print("Rig Pose:", rig_pose.path())
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
