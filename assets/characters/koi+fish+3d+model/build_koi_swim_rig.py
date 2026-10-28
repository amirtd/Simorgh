r"""Install a procedural animation rig into the current koi Houdini scene."""

import math
import hou


CONTROL_PATH = "/obj/KOI_RIG_CONTROLS"
RIG_NODE_NAME = "KOI_PROCEDURAL_SWIM_RIG"


VEX = r'''
int enabled = chi("/obj/KOI_RIG_CONTROLS/enabled");
if (!enabled) return;

vector rest = @P;
float xmin = detail(0, "koi_xmin", 0);
float xmax = detail(0, "koi_xmax", 0);
float length = max(xmax - xmin, 1e-5);

// This model faces -X: u=0 at the head and u=1 at the tail.
float u = clamp((rest.x - xmin) / length, 0.0, 1.0);
float bodymask = smooth(0.08, 1.0, u);
float tailmask = smooth(0.55, 1.0, u);

float speed = chf("/obj/KOI_RIG_CONTROLS/swim_speed");
float cycles = chf("/obj/KOI_RIG_CONTROLS/wavelength");
float phase = radians(chf("/obj/KOI_RIG_CONTROLS/phase"));
float t = @Time * speed * M_TWO_PI + phase;
float wavephase = t - u * cycles * M_TWO_PI;

float bodyamp = chf("/obj/KOI_RIG_CONTROLS/body_amplitude");
float tailamp = chf("/obj/KOI_RIG_CONTROLS/tail_amplitude");
float stiffness = chf("/obj/KOI_RIG_CONTROLS/body_stiffness");
float flexible = pow(bodymask, max(stiffness, 0.05));
float amp = lerp(bodyamp, tailamp, tailmask) * flexible;

float turn = radians(chf("/obj/KOI_RIG_CONTROLS/turn"));
float turn_offset = tan(turn) * length * u * u * 0.35;
float center_y = sin(wavephase) * amp + turn_offset;

// Rotate each cross-section to follow the centerline tangent. This produces a
// bend instead of merely sliding slices sideways.
float dydx_wave = -cos(wavephase) * amp * cycles * M_TWO_PI / length;
float dydx_turn = tan(turn) * 0.7 * u;
float theta = atan(dydx_wave + dydx_turn);
float local_y = rest.y;
@P.x = rest.x - local_y * sin(theta);
@P.y = center_y + local_y * cos(theta);

// Small high-frequency follow-through near the caudal fin.
float flutter = chf("/obj/KOI_RIG_CONTROLS/tail_flutter");
float flutter_speed = chf("/obj/KOI_RIG_CONTROLS/flutter_speed");
@P.y += sin(@Time * flutter_speed * M_TWO_PI - u * M_TWO_PI) * flutter * tailmask;

// Whole-body vertical drift, faded slightly toward the head for softness.
float bob = chf("/obj/KOI_RIG_CONTROLS/vertical_bob");
float bob_speed = chf("/obj/KOI_RIG_CONTROLS/bob_speed");
@P.z += sin(@Time * bob_speed * M_TWO_PI + phase * 0.5) * bob;

// Bank around the fish's long axis. Auto-bank responds to the swim and turn.
float bank = radians(chf("/obj/KOI_RIG_CONTROLS/fish_bank"));
float auto_bank = chf("/obj/KOI_RIG_CONTROLS/auto_bank");
bank += (-sin(wavephase) * amp / max(length, 1e-5) + turn) * auto_bank;
float cy = cos(bank);
float sy = sin(bank);
float yy = @P.y;
float zz = @P.z;
float zcenter = detail(0, "koi_zcenter", 0);
@P.y = yy * cy - (zz - zcenter) * sy;
@P.z = zcenter + yy * sy + (zz - zcenter) * cy;
'''


def add_float(folder, name, label, default, minimum, maximum):
    parm = hou.FloatParmTemplate(
        name,
        label,
        1,
        default_value=(default,),
        min=minimum,
        max=maximum,
        min_is_strict=False,
        max_is_strict=False,
    )
    folder.addParmTemplate(parm)


def create_controls():
    obj = hou.node("/obj")
    controls = obj.node("KOI_RIG_CONTROLS")
    if controls is None:
        controls = obj.createNode("null", "KOI_RIG_CONTROLS")
    controls.setColor(hou.Color((0.15, 0.65, 1.0)))
    controls.setUserData("nodeshape", "circle")

    group = controls.parmTemplateGroup()
    old = group.findFolder("Koi Swim Rig")
    if old:
        group.remove(old.name())

    folder = hou.FolderParmTemplate("koi_swim_rig", "Koi Swim Rig")
    folder.addParmTemplate(hou.ToggleParmTemplate("enabled", "Enable Swim Rig", True))
    add_float(folder, "swim_speed", "Swim Speed", 0.8, 0.0, 5.0)
    add_float(folder, "body_amplitude", "Body Amplitude", 0.012, 0.0, 0.15)
    add_float(folder, "tail_amplitude", "Tail Amplitude", 0.055, 0.0, 0.25)
    add_float(folder, "wavelength", "Waves Along Body", 0.85, 0.1, 3.0)
    add_float(folder, "body_stiffness", "Body Stiffness", 1.8, 0.1, 5.0)
    add_float(folder, "phase", "Phase (Degrees)", 0.0, -360.0, 360.0)

    add_float(folder, "turn", "Turn", 0.0, -45.0, 45.0)
    add_float(folder, "fish_bank", "Manual Bank", 0.0, -45.0, 45.0)
    add_float(folder, "auto_bank", "Automatic Bank", 0.35, 0.0, 2.0)

    add_float(folder, "tail_flutter", "Tail Flutter", 0.004, 0.0, 0.05)
    add_float(folder, "flutter_speed", "Flutter Speed", 2.2, 0.0, 10.0)
    add_float(folder, "vertical_bob", "Vertical Bob", 0.008, 0.0, 0.1)
    add_float(folder, "bob_speed", "Bob Speed", 0.22, 0.0, 3.0)

    folder.addParmTemplate(
        hou.ButtonParmTemplate(
            "reset_pose",
            "Reset Pose Controls",
            script_callback=(
                "n=hou.pwd(); "
                "[n.parm(p).revertToDefaults() for p in "
                "('turn','fish_bank','phase') if n.parm(p)]"
            ),
            script_callback_language=hou.scriptLanguage.Python,
        )
    )
    group.append(folder)
    controls.setParmTemplateGroup(group)
    return controls


def find_fish_geo():
    candidates = []
    for node in hou.node("/obj").allSubChildren():
        if node.type().category() != hou.objNodeTypeCategory():
            continue
        if node.type().name() != "geo" or node.displayNode() is None:
            continue
        try:
            count = node.displayNode().geometry().intrinsicValue("pointcount")
        except hou.Error:
            continue
        if count:
            candidates.append((count, node))
    if not candidates:
        raise RuntimeError("No fish Geometry object found")
    return max(candidates, key=lambda item: item[0])[1]


def install_rig(geo_obj):
    existing = geo_obj.node(RIG_NODE_NAME)
    source = existing.input(0) if existing is not None else geo_obj.displayNode()
    if source is None:
        raise RuntimeError("Fish Geometry object has no display SOP")

    if existing is None:
        consumers = [
            (output, index)
            for output in source.outputs()
            for index, input_node in enumerate(output.inputs())
            if input_node == source
        ]
        bounds = source.geometry().boundingBox()
        rig = geo_obj.createNode("attribwrangle", RIG_NODE_NAME)
        rig.setInput(0, source)
        for output, index in consumers:
            if output != rig:
                output.setInput(index, rig)
    else:
        rig = existing
        bounds = source.geometry().boundingBox()

    # Cache stable rest bounds as detail attributes upstream of the deformation.
    metadata = geo_obj.node("KOI_RIG_REST_BOUNDS")
    if metadata is None:
        metadata = geo_obj.createNode("attribwrangle", "KOI_RIG_REST_BOUNDS")
        metadata.setInput(0, source)
        rig.setInput(0, metadata)
    metadata.parm("class").set(0)  # detail mode
    metadata.parm("snippet").set(
        'setdetailattrib(0, "koi_xmin", getbbox_min(0).x, "set");\n'
        'setdetailattrib(0, "koi_xmax", getbbox_max(0).x, "set");\n'
        'setdetailattrib(0, "koi_zcenter", getbbox_center(0).z, "set");'
    )

    rig.parm("class").set(2)  # point mode
    rig.parm("snippet").set(VEX)
    rig.setColor(hou.Color((0.15, 0.65, 1.0)))
    rig.setDisplayFlag(True)
    rig.setRenderFlag(True)
    metadata.moveToGoodPosition()
    rig.moveToGoodPosition()
    return rig, bounds


def clear_stale_session_script():
    """Remove the accidentally persisted one-line material installer, if present."""
    try:
        source = hou.sessionModuleSource()
        if "add_koi_material.py" in source or "No Geometry objects found under /obj" in source:
            hou.setSessionModuleSource("")
    except (AttributeError, hou.Error):
        pass


def main():
    with hou.undos.group("Build koi procedural swim rig"):
        controls = create_controls()
        fish = find_fish_geo()
        rig, bounds = install_rig(fish)
        controls.setPosition(fish.position() + hou.Vector2(0.0, -2.0))
        hou.node("/obj").layoutChildren(items=(controls,))
        clear_stale_session_script()

    print("Koi controls: {}".format(controls.path()))
    print("Koi rig: {}".format(rig.path()))
    print("Fish bounds: {}".format(bounds.sizevec()))
    return controls, rig


if __name__ == "__main__":
    CONTROLS, RIG = main()
