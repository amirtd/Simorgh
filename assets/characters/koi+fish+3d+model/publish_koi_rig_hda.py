r"""Publish the rigged koi as a reusable OBJ-level Houdini Digital Asset."""

import os
import hou


ASSET_DIR = r"E:\Wirling Worlds\Simorgh\assets\characters\koi+fish+3d+model"
HDA_PATH = os.path.join(ASSET_DIR, "simorgh_koi_fish_rig.hdalc")
TYPE_NAME = "simorgh::koi_fish_rig::1.0"
SOURCE_SUBNET = "/obj/tripo_convert_19f40ccf_6c7c_40f8_af02_f33d6490f453_fbx"
SOURCE_CONTROLS = "/obj/KOI_RIG_CONTROLS"
SOURCE_MATERIALS = "/obj/KOI_MATERIALS"
PUBLISH_NODE_NAME = "KOI_FISH_RIG_ASSET"

CONTROL_NAMES = (
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
)


def add_asset_controls(asset, source_controls):
    group = asset.parmTemplateGroup()
    existing = group.findFolder("Koi Swim Rig")
    if existing:
        group.remove(existing.name())
    folder = source_controls.parmTemplateGroup().findFolder("Koi Swim Rig")
    if folder is None:
        raise RuntimeError("Koi Swim Rig control folder was not found")
    group.append(folder)
    asset.setParmTemplateGroup(group)
    for name in CONTROL_NAMES:
        source = source_controls.parm(name)
        target = asset.parm(name)
        if source is not None and target is not None:
            target.set(source.eval())


def internalize_material(asset):
    source = hou.node(SOURCE_MATERIALS)
    if source is None:
        raise RuntimeError("Missing " + SOURCE_MATERIALS)
    old = asset.node("KOI_MATERIALS")
    if old is not None:
        old.destroy()
    material_net = source.copyTo(asset)
    material_net.setName("KOI_MATERIALS", unique_name=False)

    for node in asset.allSubChildren():
        if node.type().category() == hou.sopNodeTypeCategory() and node.type().name() == "material":
            parm = node.parm("shop_materialpath1") or node.parm("shop_materialpath")
            if parm is not None and "koi_fish" in parm.eval():
                parm.set("../../KOI_MATERIALS/koi_fish")


def retarget_rig_controls(asset):
    for node in asset.allSubChildren():
        if node.type().category() != hou.sopNodeTypeCategory():
            continue
        snippet = node.parm("snippet")
        if snippet is None:
            continue
        code = snippet.rawValue()
        if "/obj/KOI_RIG_CONTROLS/" in code:
            snippet.set(code.replace("/obj/KOI_RIG_CONTROLS/", "../../"))


def publish():
    obj = hou.node("/obj")
    source = hou.node(SOURCE_SUBNET)
    controls = hou.node(SOURCE_CONTROLS)
    if source is None or controls is None:
        raise RuntimeError("The rigged koi source nodes were not found")

    old = obj.node(PUBLISH_NODE_NAME)
    if old is not None:
        old.destroy()

    asset = source.copyTo(obj)
    asset.setName(PUBLISH_NODE_NAME, unique_name=False)
    add_asset_controls(asset, controls)
    internalize_material(asset)
    retarget_rig_controls(asset)
    asset.setColor(hou.Color((0.12, 0.55, 0.9)))
    asset.setUserData("nodeshape", "trapezoid_up")

    if os.path.isfile(HDA_PATH):
        os.remove(HDA_PATH)

    asset = asset.createDigitalAsset(
        name=TYPE_NAME,
        hda_file_name=HDA_PATH,
        description="Simorgh Koi Fish Rig",
        min_num_inputs=0,
        max_num_inputs=0,
        create_backup=False,
    )
    definition = asset.type().definition()
    # createDigitalAsset does not automatically promote spare parameters into
    # the saved type definition, so explicitly add the animator control folder.
    definition_group = definition.parmTemplateGroup()
    definition_group.append(controls.parmTemplateGroup().findFolder("Koi Swim Rig"))
    definition.setParmTemplateGroup(definition_group)
    definition.setIcon("OBJ_character")
    definition.updateFromNode(asset)
    asset.matchCurrentDefinition()
    # Preserve the artist's current pose/settings on the published source-scene
    # instance. Fresh instances use the control templates' authored defaults.
    for name in CONTROL_NAMES:
        source_parm = controls.parm(name)
        target_parm = asset.parm(name)
        if source_parm is not None and target_parm is not None:
            target_parm.set(source_parm.eval())
    asset.setDisplayFlag(False)
    asset.moveToGoodPosition()
    hou.hda.installFile(HDA_PATH)
    print("Published HDA: " + HDA_PATH)
    print("Asset type: " + asset.type().nameWithCategory())
    return asset


if __name__ == "__main__":
    PUBLISHED_ASSET = publish()
