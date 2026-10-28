r"""Add curl-ball release animation controls to the reusable koi HDA."""

import os
import hou


HDA_PATH = r"E:\Wirling Worlds\Simorgh\assets\characters\koi+fish+3d+model\simorgh_koi_fish_rig.hdalc"
TYPE_NAME = "simorgh::koi_fish_rig::1.0"
MARKER = "// KOI_CURL_BALL_RELEASE_V1"

CURL_VEX = r'''

// KOI_CURL_BALL_RELEASE_V1
// Before curl_start_frame the fish is fully curled and spinning. Between the
// start and end frames it blends smoothly back to the normal swim deformation.
if (chi("../../curl_enable")) {
    float curl_start = chf("../../curl_start_frame");
    float curl_end = max(curl_start + 0.001, chf("../../curl_end_frame"));
    float release = 1.0 - smooth(curl_start, curl_end, @Frame);
    float curl_weight = clamp(chf("../../curl_amount") * release, 0.0, 1.0);

    if (curl_weight > 1e-5) {
        vector swimP = @P;
        float turns = max(0.1, chf("../../curl_turns"));
        float tightness = max(0.1, chf("../../curl_tightness"));
        float arc = u * turns * M_TWO_PI;
        float radius = length / (turns * M_TWO_PI * tightness);

        // Circle tangent begins along +X at the head, keeping the release pose
        // stable while the body and tail wrap into a compact ball.
        vector curlP;
        curlP.x = xmin + radius * sin(arc);
        curlP.y = radius * (1.0 - cos(arc));
        curlP.z = rest.z;

        // Rotate each body cross-section along the curled centerline.
        curlP.x -= rest.y * sin(arc);
        curlP.y += rest.y * cos(arc);

        // Spin the curled target around its approximate ball center. The spin
        // continues during release, while its visible influence fades smoothly.
        float spin = @Time * chf("../../curl_spin_speed") * M_TWO_PI
                   + radians(chf("../../curl_spin_phase"));
        vector center = set(xmin, radius, detail(0, "koi_zcenter", 0));
        vector q = curlP - center;
        float cs = cos(spin);
        float sn = sin(spin);
        curlP.x = center.x + q.x * cs - q.y * sn;
        curlP.y = center.y + q.x * sn + q.y * cs;

        @P = lerp(swimP, curlP, curl_weight);
    }
}
'''


def float_parm(name, label, default, minimum, maximum):
    return hou.FloatParmTemplate(
        name, label, 1, default_value=(default,), min=minimum, max=maximum,
        min_is_strict=False, max_is_strict=False,
    )


def curl_folder():
    folder = hou.FolderParmTemplate("koi_curl_release", "Curl Ball Release")
    folder.addParmTemplate(hou.ToggleParmTemplate("curl_enable", "Enable Curl Ball", False))
    folder.addParmTemplate(float_parm("curl_start_frame", "Curl Start Frame", 24.0, -1000.0, 4000.0))
    folder.addParmTemplate(float_parm("curl_end_frame", "Curl End Frame", 48.0, -999.0, 4001.0))
    folder.addParmTemplate(float_parm("curl_amount", "Curl Amount", 1.0, 0.0, 1.0))
    folder.addParmTemplate(float_parm("curl_turns", "Curl Turns", 1.15, 0.1, 3.0))
    folder.addParmTemplate(float_parm("curl_tightness", "Ball Tightness", 1.0, 0.25, 4.0))
    folder.addParmTemplate(float_parm("curl_spin_speed", "Spin Cycles / Second", 0.65, -5.0, 5.0))
    folder.addParmTemplate(float_parm("curl_spin_phase", "Spin Phase", 0.0, -360.0, 360.0))
    return folder


def main():
    if not os.path.isfile(HDA_PATH):
        raise RuntimeError("Missing HDA: " + HDA_PATH)
    hou.hda.installFile(HDA_PATH)
    definition = hou.nodeType(hou.objNodeTypeCategory(), TYPE_NAME).definition()

    # Add the controls to the type definition without replacing existing folders.
    group = definition.parmTemplateGroup()
    old = group.findFolder("Curl Ball Release")
    if old is not None:
        group.remove(old.name())
    group.append(curl_folder())
    definition.setParmTemplateGroup(group)

    obj = hou.node("/obj")
    old_test = obj.node("KOI_CURL_UPDATE_TEST")
    if old_test is not None:
        old_test.destroy()
    asset = obj.createNode(TYPE_NAME, "KOI_CURL_UPDATE_TEST")
    asset.allowEditingOfContents()
    rigs = [node for node in asset.allSubChildren() if node.name() == "KOI_PROCEDURAL_SWIM_RIG"]
    if not rigs:
        raise RuntimeError("Koi procedural rig node not found")
    rig = rigs[0]
    snippet = rig.parm("snippet")
    code = snippet.rawValue()
    if MARKER in code:
        code = code.split(MARKER)[0].rstrip()
    snippet.set(code + CURL_VEX)

    # Validate both curled and released frames before publishing the definition.
    asset.parm("curl_enable").set(1)
    hou.setFrame(1)
    rig.cook(force=True)
    if rig.errors():
        raise RuntimeError("Curl cook failed: " + "\n".join(rig.errors()))
    curled_bounds = rig.geometry().boundingBox().sizevec()
    hou.setFrame(60)
    rig.cook(force=True)
    if rig.errors():
        raise RuntimeError("Released cook failed: " + "\n".join(rig.errors()))
    released_bounds = rig.geometry().boundingBox().sizevec()

    definition.updateFromNode(asset)
    asset.matchCurrentDefinition()
    print("Updated HDA: " + HDA_PATH)
    print("Curl controls added to: " + TYPE_NAME)
    print("Curled bounds: {}".format(curled_bounds))
    print("Released bounds: {}".format(released_bounds))
    return asset, rig


UPDATED_CURL_ASSET, UPDATED_CURL_RIG = main()
