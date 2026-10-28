r"""Create and assign the koi texture material in a Houdini OBJ/SOP network.

Usage:
    1. Open the koi .hipnc file.
    2. Select one or more Geometry objects in /obj (or select a SOP inside one).
    3. In a Python Shell or Python Source Editor, run:

       exec(open(r"E:\Wirling Worlds\Simorgh\assets\characters\koi+fish+3d+model\add_koi_material.py").read())

If nothing is selected, the script processes every Geometry object under /obj.
The operation is safe to run again: existing KOI_MATERIAL_ASSIGN nodes are reused.
"""

import os
import hou


KNOWN_ASSET_DIR = r"E:\Wirling Worlds\Simorgh\assets\characters\koi+fish+3d+model"


def find_asset_dir():
    """Resolve assets reliably when executed with exec() inside hou.session."""
    candidates = []

    # The koi HIP file lives beside its FBM texture folder, so this is the most
    # reliable location in Houdini's Python Source Editor.
    hip_path = hou.hipFile.path()
    if hip_path and hip_path not in ("untitled.hip", "untitled.hiplc", "untitled.hipnc"):
        candidates.append(os.path.dirname(os.path.abspath(hip_path)))

    # __file__ is useful when invoked as a normal script, but hou.session may
    # contain an unrelated __file__, so validate it before accepting it.
    script_path = globals().get("__file__")
    if script_path:
        candidates.append(os.path.dirname(os.path.abspath(script_path)))

    candidates.append(KNOWN_ASSET_DIR)

    for candidate in candidates:
        if os.path.isdir(candidate) and any(
            name.lower().endswith(".fbm")
            for name in os.listdir(candidate)
        ):
            return candidate

    return KNOWN_ASSET_DIR


ASSET_DIR = find_asset_dir()


def find_texture_dir():
    """Find the FBM folder matching the scene, or the newest valid export."""
    folders = [
        os.path.join(ASSET_DIR, name)
        for name in os.listdir(ASSET_DIR)
        if name.lower().endswith(".fbm")
        and os.path.isdir(os.path.join(ASSET_DIR, name))
    ]
    if not folders:
        raise RuntimeError("No .fbm texture folder found in " + ASSET_DIR)

    hip_name = os.path.basename(hou.hipFile.path()).lower()
    for folder in folders:
        export_name = os.path.basename(folder)[:-4].lower()
        if export_name in hip_name:
            return folder

    required = {
        "koi_fish_3d_model_basecolor.jpeg",
        "koi_fish_3d_model_metallic.jpeg",
        "koi_fish_3d_model_roughness.jpeg",
        "koi_fish_3d_model_normal.png",
    }
    valid = [
        folder
        for folder in folders
        if required.issubset({name.lower() for name in os.listdir(folder)})
    ]
    if not valid:
        raise RuntimeError("No .fbm folder contains the complete koi texture set")
    return max(valid, key=os.path.getmtime)


TEXTURE_DIR = find_texture_dir()

TEXTURES = {
    "basecolor": os.path.join(TEXTURE_DIR, "koi_fish_3d_model_basecolor.JPEG"),
    "metallic": os.path.join(TEXTURE_DIR, "koi_fish_3d_model_metallic.JPEG"),
    "roughness": os.path.join(TEXTURE_DIR, "koi_fish_3d_model_roughness.JPEG"),
    "normal": os.path.join(TEXTURE_DIR, "koi_fish_3d_model_normal.PNG"),
}


def set_first_parm(node, names, value):
    """Set the first parameter name that exists on this Houdini version."""
    for name in names:
        parm = node.parm(name)
        if parm is not None:
            parm.set(value)
            return True
    return False


def build_shader():
    """Create/reuse /obj/KOI_MATERIALS/koi_fish and return its path."""
    obj = hou.node("/obj")
    matnet = obj.node("KOI_MATERIALS")
    if matnet is None:
        matnet = obj.createNode("matnet", "KOI_MATERIALS")

    shader = matnet.node("koi_fish")
    if shader is None:
        try:
            shader = matnet.createNode("principledshader::2.0", "koi_fish")
        except hou.OperationFailed:
            shader = matnet.createNode("principledshader", "koi_fish")

    # These aliases cover the common Principled Shader parameter names across
    # recent Houdini versions. Missing optional parameters are simply skipped.
    set_first_parm(shader, ("basecolor_useTexture", "basecolor_use_texture"), 1)
    set_first_parm(shader, ("basecolor_texture", "basecolor_texture_file"), TEXTURES["basecolor"])

    set_first_parm(shader, ("metallic_useTexture", "metallic_use_texture"), 1)
    set_first_parm(shader, ("metallic_texture", "metallic_texture_file"), TEXTURES["metallic"])

    set_first_parm(shader, ("rough_useTexture", "rough_use_texture"), 1)
    set_first_parm(shader, ("rough_texture", "rough_texture_file"), TEXTURES["roughness"])

    set_first_parm(
        shader,
        ("baseBumpAndNormal_enable", "baseNormal_enable", "normal_enable"),
        1,
    )
    set_first_parm(
        shader,
        ("baseBumpAndNormal_type", "baseNormal_type", "normal_type"),
        "normal",  # normal map, rather than height/bump map
    )
    set_first_parm(
        shader,
        ("baseNormal_texture", "baseBumpAndNormal_texture", "normal_texture"),
        TEXTURES["normal"],
    )

    matnet.layoutChildren()
    return shader.path()


def selected_geo_objects():
    """Return unique Geometry OBJ nodes derived from the current selection."""
    result = []

    def add_geo(node):
        if (
            node.type().category() == hou.objNodeTypeCategory()
            and node.type().name() == "geo"
            and node not in result
        ):
            result.append(node)

    for node in hou.selectedNodes():
        # A selected SOP: walk upward until its containing Geometry OBJ.
        candidate = node
        while candidate is not None and candidate.path() != "/obj":
            add_geo(candidate)
            candidate = candidate.parent()

        # A selected FBX subnet: collect Geometry objects nested beneath it.
        if node.type().category() == hou.objNodeTypeCategory():
            for child in node.allSubChildren():
                add_geo(child)

    if result:
        return result

    # Convenient fallback for a freshly imported FBX scene. FBX imports commonly
    # place Geometry objects one level down inside an Object subnet.
    for node in hou.node("/obj").allSubChildren():
        add_geo(node)
    return result


def assign_material(geo_obj, material_path):
    """Insert/reuse a Material SOP after the object's current display SOP."""
    material = geo_obj.node("KOI_MATERIAL_ASSIGN")
    if material is None:
        source = geo_obj.displayNode()
        if source is None:
            raise RuntimeError("{} has no display SOP".format(geo_obj.path()))

        # Preserve downstream wiring if the display node already feeds other SOPs.
        consumers = [
            (output, index)
            for output in source.outputs()
            for index, input_node in enumerate(output.inputs())
            if input_node == source
        ]
        material = geo_obj.createNode("material", "KOI_MATERIAL_ASSIGN")
        material.setInput(0, source)
        for output, index in consumers:
            if output != material:
                output.setInput(index, material)

    set_first_parm(material, ("shop_materialpath1", "shop_materialpath"), material_path)
    material.setDisplayFlag(True)
    material.setRenderFlag(True)
    material.moveToGoodPosition()
    return material


def main():
    missing = [path for path in TEXTURES.values() if not os.path.isfile(path)]
    if missing:
        raise RuntimeError("Missing koi textures:\n" + "\n".join(missing))

    targets = selected_geo_objects()
    if not targets:
        raise RuntimeError("No Geometry objects found under /obj")

    with hou.undos.group("Create and assign koi material"):
        shader_path = build_shader()
        assigned = [assign_material(node, shader_path) for node in targets]
        hou.node("/obj").layoutChildren()

    print("Koi material: {}".format(shader_path))
    print("Assigned to: {}".format(", ".join(node.parent().path() for node in assigned)))
    return assigned


ASSIGNED_NODES = main()
