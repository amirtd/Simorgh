r"""Add curl controls to the existing Stage controller without rebuilding it."""

import hou


FISH_PATH = "/obj/koi_fish_hero"
CONTROL_PATH = "/stage/koi_fish_controls"
CURL_NAMES = (
    "curl_enable", "curl_start_frame", "curl_end_frame", "curl_amount",
    "curl_turns", "curl_tightness", "curl_spin_speed", "curl_spin_phase",
)


def main():
    fish = hou.node(FISH_PATH)
    controls = hou.node(CONTROL_PATH)
    if fish is None:
        raise RuntimeError("Missing " + FISH_PATH)
    if controls is None:
        raise RuntimeError("Missing " + CONTROL_PATH)

    source_folder = fish.parmTemplateGroup().findFolder("Curl Ball Release")
    if source_folder is None:
        raise RuntimeError("Reload the updated koi HDA before adding Stage curl controls")

    group = controls.parmTemplateGroup()
    if group.findFolder("Curl Ball Release") is None:
        group.append(source_folder)
        controls.setParmTemplateGroup(group)

    for name in CURL_NAMES:
        fish_parm = fish.parm(name)
        stage_parm = controls.parm(name)
        if fish_parm is None or stage_parm is None:
            raise RuntimeError("Missing curl parameter: " + name)
        # On first install, preserve the HDA default on the Stage controller.
        if not stage_parm.keyframes():
            stage_parm.set(fish_parm.eval())
        fish_parm.deleteAllKeyframes()
        fish_parm.setExpression(
            'ch("{}/{}")'.format(CONTROL_PATH, name),
            hou.exprLanguage.Hscript,
        )

    controls.setCurrent(True, clear_all_selected=True)
    print("Added Curl Ball Release controls to " + CONTROL_PATH)
    return controls


STAGE_CURL_CONTROLS = main()
