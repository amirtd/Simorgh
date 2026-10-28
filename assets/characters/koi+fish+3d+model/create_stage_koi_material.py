r"""Build and assign a Karma MaterialX material to the Stage koi."""

import os
import hou


TEXTURE_DIR = os.path.join(
    r"E:\Wirling Worlds\Simorgh\assets\characters",
    "tripo_convert_4a0a7924-94fc-45d5-89e3-c8a918e2d2fa.fbm",
)
TEXTURES = {
    "base": os.path.join(TEXTURE_DIR, "colorful_fish_3d_model_basecolor.JPEG"),
    "rough": os.path.join(TEXTURE_DIR, "colorful_fish_3d_model_roughness.JPEG"),
    "metal": os.path.join(TEXTURE_DIR, "colorful_fish_3d_model_metallic.JPEG"),
    "normal": os.path.join(TEXTURE_DIR, "colorful_fish_3d_model_normal.PNG"),
}


def create_image(parent, name, path, signature, colorspace):
    node = parent.createNode("mtlximage", name)
    node.parm("signature").set(signature)
    node.parm("file").set(path)
    node.parm("filecolorspace").set(colorspace)
    return node


def build_material():
    mat = hou.node("/mat")
    existing = mat.node("koi_fish_mtl")
    if existing is not None:
        existing.allowEditingOfContents()
        surface = existing.node("mtlxstandard_surface")
        if surface is None:
            raise RuntimeError("Existing koi material has no standard surface")
        # Repair older installs copied from the emissive red-sphere template.
        for name, value in (
            ("base", 1.0),
            ("specular", 0.38),
            ("transmission", 0.0),
            ("subsurface", 0.0),
            ("emission", 0.0),
            ("coat", 0.08),
            ("coat_roughness", 0.28),
            ("thin_walled", 0),
        ):
            parm = surface.parm(name)
            if parm is not None:
                parm.set(value)
        opacity = surface.parmTuple("opacity")
        if opacity is not None:
            opacity.set((1.0, 1.0, 1.0))
        for node_name, texture_key in (
            ("koi_basecolor", "base"),
            ("koi_roughness", "rough"),
            ("koi_metallic", "metal"),
            ("koi_normal_texture", "normal"),
        ):
            image = existing.node(node_name)
            if image is not None and image.parm("file") is not None:
                image.parm("file").set(TEXTURES[texture_key])
        return existing

    # Copy an existing MaterialX builder so all Karma output connectors and
    # builder metadata match this project's established material setup.
    template = mat.node("red_sphere_mtl") or mat.node("ink_drop_mtl")
    if template is None:
        raise RuntimeError("No project MaterialX builder found in /mat")
    material = template.copyTo(mat)
    material.setName("koi_fish_mtl", unique_name=False)
    material.setMaterialFlag(True)

    surface = material.node("mtlxstandard_surface")
    if surface is None:
        raise RuntimeError("Copied MaterialX builder has no standard surface")

    # Remove the copied template's surface inputs, but preserve its connection
    # to the builder's material output.
    for index in range(len(surface.inputs())):
        surface.setInput(index, None)

    base = create_image(material, "koi_basecolor", TEXTURES["base"], "color3", "srgb_texture")
    rough = create_image(material, "koi_roughness", TEXTURES["rough"], "float", "raw")
    metal = create_image(material, "koi_metallic", TEXTURES["metal"], "float", "raw")
    normal_image = create_image(material, "koi_normal_texture", TEXTURES["normal"], "color3", "raw")
    normal_map = material.createNode("mtlxnormalmap", "koi_normal_map")
    normal_map.setNamedInput("in", normal_image, 0)

    surface.setNamedInput("base_color", base, 0)
    surface.setNamedInput("specular_roughness", rough, 0)
    surface.setNamedInput("metalness", metal, 0)
    surface.setNamedInput("normal", normal_map, 0)

    # A subtle dielectric coat helps the wet scales respond to lights.
    for name, value in (
        ("base", 1.0),
        ("specular", 0.38),
        ("transmission", 0.0),
        ("subsurface", 0.0),
        ("emission", 0.0),
        ("coat", 0.08),
        ("coat_roughness", 0.28),
        ("thin_walled", 0),
    ):
        parm = surface.parm(name)
        if parm is not None:
            parm.set(value)
    opacity = surface.parmTuple("opacity")
    if opacity is not None:
        opacity.set((1.0, 1.0, 1.0))

    material.layoutChildren()
    return material


def install_lop(material):
    stage = hou.node("/stage")
    controls = stage.node("koi_fish_controls")
    if controls is None:
        raise RuntimeError("Missing /stage/koi_fish_controls")

    library = stage.node("koi_fish_materials")
    if library is None:
        library = stage.createNode("materiallibrary", "koi_fish_materials")

    library.parm("matnet").set("/mat")
    library.parm("materials").set(1)
    library.parm("enable1").set(1)
    library.parm("matflag1").set(1)
    library.parm("matnode1").set(material.path())
    library.parm("matpath1").set("/materials/koi_fish_mtl")
    library.parm("assign1").set(1)
    library.parm("geopath1").set("/world/koi_fish_hero/**")

    consumers = [
        (output, index)
        for output in controls.outputs()
        for index, input_node in enumerate(output.inputs())
        if input_node == controls
    ]
    library.setInput(0, controls)
    for output, index in consumers:
        if output != library:
            output.setInput(index, library)

    library.moveToGoodPosition()
    library.setCurrent(True, clear_all_selected=True)
    library.setDisplayFlag(True)
    return library


def main():
    missing = [path for path in TEXTURES.values() if not os.path.isfile(path)]
    if missing:
        raise RuntimeError("Missing koi textures:\n" + "\n".join(missing))
    material = build_material()
    library = install_lop(material)
    print("Koi MaterialX: " + material.path())
    print("Koi Material Library: " + library.path())
    print("Assigned to: /world/koi_fish_hero/**")
    return material, library


KOI_MATERIAL, KOI_MATERIAL_LIBRARY = main()
