"""Patch the current ink-drop scene without rebuilding or resetting user values."""

from __future__ import annotations

import os
import shutil

import hou

import build_ink_drop


HERE = os.path.dirname(os.path.abspath(__file__))
SCENE = os.path.join(HERE, "ink_drop_effect.hipnc")
BACKUP = os.path.join(HERE, "ink_drop_effect_before_bubble_tooltips_no_spin_20261025.hipnc")


def add_tooltips(node):
    group = node.parmTemplateGroup()
    changed = []
    for name, help_text in build_ink_drop.CONTROL_HELP.items():
        template = group.find(name)
        if template is None:
            continue
        template.setHelp(help_text)
        if name == "satellite_orbit":
            template.setLabel("Depth Offset")
        group.replace(name, template)
        changed.append(name)
    node.setParmTemplateGroup(group)
    return changed


def main():
    if not os.path.exists(BACKUP):
        shutil.copy2(SCENE, BACKUP)
    hou.hipFile.load(SCENE, suppress_save_prompt=True)

    stage_control = hou.node(build_ink_drop.HERO_CTL_NODE)
    geo = hou.node(build_ink_drop.GEO_PATH)
    points = hou.node(build_ink_drop.GEO_PATH + "/satellite_bubble_points")
    assert stage_control is not None and geo is not None and points is not None

    preserved = {name: stage_control.parm(name).rawValue()
                 for name in build_ink_drop.CONTROL_HELP
                 if stage_control.parm(name) is not None}
    stage_changed = add_tooltips(stage_control)
    add_tooltips(geo)
    points.parm("snippet").set(build_ink_drop.SATELLITE_POINTS_VEX)

    for name, old_value in preserved.items():
        assert stage_control.parm(name).rawValue() == old_value, "Changed user value: " + name
    assert len(stage_changed) == len(build_ink_drop.CONTROL_HELP)
    assert "p.z += cos(w)" not in points.parm("snippet").eval()
    assert "Depth Offset" == stage_control.parm("satellite_orbit").parmTemplate().label()
    assert all(stage_control.parm(name).parmTemplate().help().strip()
               for name in build_ink_drop.CONTROL_HELP)

    hou.hipFile.save(SCENE)
    print("Patched controls:", len(stage_changed))
    print("Preserved user values:", len(preserved))
    print("Backup:", BACKUP)
    print("Saved:", SCENE)


if __name__ == "__main__":
    main()
