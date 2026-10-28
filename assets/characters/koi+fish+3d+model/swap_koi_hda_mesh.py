r"""Swap the reusable koi HDA to the new colorful fish mesh and textures."""

import os
import hou


HDA_PATH = r"E:\Wirling Worlds\Simorgh\assets\characters\koi+fish+3d+model\simorgh_koi_fish_rig.hdalc"
TYPE_NAME = "simorgh::koi_fish_rig::1.0"
TEXTURE_DIR = os.path.join(
    r"E:\Wirling Worlds\Simorgh\assets\characters",
    "tripo_convert_4a0a7924-94fc-45d5-89e3-c8a918e2d2fa.fbm",
)
FBX_PATH = os.path.join(
    TEXTURE_DIR,
    "tripo_convert_4a0a7924-94fc-45d5-89e3-c8a918e2d2fa.fbx",
)
TEXTURES = {
    "base": os.path.join(TEXTURE_DIR, "colorful_fish_3d_model_basecolor.JPEG"),
    "rough": os.path.join(TEXTURE_DIR, "colorful_fish_3d_model_roughness.JPEG"),
    "metal": os.path.join(TEXTURE_DIR, "colorful_fish_3d_model_metallic.JPEG"),
    "normal": os.path.join(TEXTURE_DIR, "colorful_fish_3d_model_normal.PNG"),
}


def main():
    missing = [path for path in [HDA_PATH, FBX_PATH] + list(TEXTURES.values()) if not os.path.isfile(path)]
    if missing:
        raise RuntimeError("Missing files:\n" + "\n".join(missing))

    hou.hda.installFile(HDA_PATH)
    obj = hou.node("/obj")
    old = obj.node("KOI_HDA_UPDATE_TEST")
    if old is not None:
        old.destroy()
    asset = obj.createNode(TYPE_NAME, "KOI_HDA_UPDATE_TEST")
    asset.allowEditingOfContents()

    file_nodes = [
        node for node in asset.allSubChildren()
        if node.type().category() == hou.sopNodeTypeCategory() and node.type().name() == "file"
    ]
    if not file_nodes:
        raise RuntimeError("No File SOP found inside koi HDA")
    source = file_nodes[0]
    if source.isHardLocked():
        source.setHardLocked(False)
    # Force Houdini to discard any cooked geometry embedded in the HDA from a
    # previous mesh. Setting an identical path does not dirty a locked File SOP.
    source.parm("file").set("")
    source.parm("file").set(FBX_PATH)
    source.parm("reload").pressButton()
    source.cook(force=True)
    source_count = source.geometry().intrinsicValue("pointcount")
    if source_count != 990649:
        raise RuntimeError("New FBX did not reload; got {} points".format(source_count))

    geo = source.parent()
    normalize = geo.node("NEW_MESH_AXIS_NORMALIZE")
    if normalize is None:
        consumers = [
            (output, index)
            for output in source.outputs()
            for index, input_node in enumerate(output.inputs())
            if input_node == source
        ]
        normalize = geo.createNode("xform", "NEW_MESH_AXIS_NORMALIZE")
        normalize.setInput(0, source)
        for output, index in consumers:
            if output != normalize:
                output.setInput(index, normalize)
    normalize.parmTuple("r").set((90.0, 0.0, 0.0))
    normalize.setColor(hou.Color((0.15, 0.65, 1.0)))
    normalize.moveToGoodPosition()

    shaders = [
        node for node in asset.allSubChildren()
        if node.type().name().startswith("principledshader")
    ]
    for shader in shaders:
        for parm_name, path in (
            ("basecolor_texture", TEXTURES["base"]),
            ("rough_texture", TEXTURES["rough"]),
            ("metallic_texture", TEXTURES["metal"]),
            ("baseNormal_texture", TEXTURES["normal"]),
        ):
            parm = shader.parm(parm_name)
            if parm is not None:
                parm.set(path)

    rig_nodes = [node for node in asset.allSubChildren() if node.name() == "KOI_PROCEDURAL_SWIM_RIG"]
    if not rig_nodes:
        raise RuntimeError("Koi rig node not found")
    rig = rig_nodes[0]
    rig.cook(force=True)
    if rig.errors():
        raise RuntimeError("Rig cook failed: " + "\n".join(rig.errors()))

    definition = asset.type().definition()
    definition.updateFromNode(asset)
    asset.matchCurrentDefinition()

    print("Updated HDA: " + HDA_PATH)
    print("New FBX: " + FBX_PATH)
    print("Points: {}".format(rig.geometry().intrinsicValue("pointcount")))
    print("Bounds: {}".format(rig.geometry().boundingBox().sizevec()))
    return asset, rig


UPDATED_ASSET, UPDATED_RIG = main()
