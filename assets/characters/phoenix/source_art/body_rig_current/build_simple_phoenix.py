# -*- coding: utf-8 -*-
"""Build a deliberately simple 2D Phoenix card rig for Houdini 22."""
import os
import struct
import hou

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
RIG_NAME = "PHOENIX_SIMPLE_RIG"

# name, image, pivot UV, default XY, rotation, scale, layer, horizontal flip.
# body.png already contains the complete body and neck.
PARTS = (
    ("body_neck", "body.png",    (0.50, 0.50), (0.00, 0.00),   0.0, 1.00, 0, False),
    ("tail",      "tail.png",    (0.88, 0.08), (2.15, -1.45), -8.0, 0.78, -1, False),
    ("wing_l",    "wing_L.png",  (0.91, 0.82), (-0.25, 1.05),  0.0, 0.92, 1, False),
    ("wing_r",    "wing_R.png",  (0.10, 0.80), (0.45, 1.00),   0.0, 0.92, 2, False),
    ("head",      "head_01.png", (0.52, 0.08), (-2.42, 2.22),  4.0, 0.72, 3, False),
    ("feet",      "foot_R.png",  (0.50, 0.92), (0.00, -2.05),  0.0, 0.62, 2, False),
)


def _png_size(path):
    with open(path, "rb") as stream:
        data = stream.read(26)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Not a PNG: %s" % path)
    return struct.unpack(">II", data[16:24])


def _float(name, label, default, lo, hi, help_text=""):
    return hou.FloatParmTemplate(name, label, 1, default_value=(default,), min=lo, max=hi, help=help_text)


def _expr(parm, text):
    parm.setExpression(text, hou.exprLanguage.Hscript)


CARD_VEX = r"""
vector q = set(@P.x + 0.5, @P.y + 0.5, 0);
float h = chf("../../card_height") * chf("../../%s_scale");
float a = chf("../../%s_aspect");
float px = chf("../../%s_pivotx");
float py = chf("../../%s_pivoty");
int flip = chi("../../%s_flip");
v@uv = set(flip ? 1-q.x : q.x, q.y, 0);
vector p = set((q.x-px)*h*a, (q.y-py)*h, 0);
float r = radians(chf("../../%s_rot"));
p = set(p.x*cos(r)-p.y*sin(r), p.x*sin(r)+p.y*cos(r), 0);
float cs = chf("/obj/%s/scale");
float cr = radians(chf("/obj/%s/rz"));
p *= cs;
p = set(p.x*cos(cr)-p.y*sin(cr), p.x*sin(cr)+p.y*cos(cr), 0);
p.x += chf("../../%s_tx") + chf("/obj/%s/tx");
p.y += chf("../../%s_ty") + chf("/obj/%s/ty");
float ms = chf("/obj/PHX_BODY_CTRL/scale");
float mr = radians(chf("/obj/PHX_BODY_CTRL/rz"));
p *= ms;
p = set(p.x*cos(mr)-p.y*sin(mr), p.x*sin(mr)+p.y*cos(mr), 0);
p.x += chf("/obj/PHX_BODY_CTRL/tx");
p.y += chf("/obj/PHX_BODY_CTRL/ty");
p.z = chf("../../base_depth") + chf("../../%s_layer") * chf("../../layer_spacing");
@P = p;
s@piece = "%s";
v@Cd = {1,1,1};
"""


def build(save_to=None):
    hou.hipFile.clear(suppress_save_prompt=True)
    obj = hou.node("/obj")
    rig = obj.createNode("geo", RIG_NAME)
    for node in list(rig.children()):
        node.destroy()

    ptg = rig.parmTemplateGroup()
    main = hou.FolderParmTemplate("simple_rig", "Simple Phoenix", folder_type=hou.folderType.Tabs)
    main.addParmTemplate(hou.LabelParmTemplate(
        "info", "", column_labels=("Six clear cards: body+neck, head, two wings, tail, and feet.",)))
    main.addParmTemplate(_float("card_height", "Base Card Height", 4.5, 0.1, 20.0))
    main.addParmTemplate(_float("base_depth", "Base Depth", -0.5, -10.0, 1.0))
    main.addParmTemplate(_float("layer_spacing", "Layer Spacing", 0.01, 0.0001, 0.1))
    main.addParmTemplate(_float("alpha_cutoff", "Alpha Clip Threshold", 0.01, 0.0, 0.25))
    main.addParmTemplate(hou.ToggleParmTemplate("show_controls", "Show Visual Rig Controls", default_value=True))
    ptg.append(main)

    for name, image, pivot, xy, rot, scale, layer, flip in PARTS:
        label = name.replace("_", " ").title()
        folder = hou.FolderParmTemplate("f_%s" % name, label, folder_type=hou.folderType.Tabs)
        folder.addParmTemplate(_float("%s_tx" % name, "Offset X", xy[0], -15, 15))
        folder.addParmTemplate(_float("%s_ty" % name, "Offset Y", xy[1], -15, 15))
        folder.addParmTemplate(_float("%s_rot" % name, "Rotation Offset", rot, -180, 180))
        folder.addParmTemplate(_float("%s_scale" % name, "Scale", scale, 0.01, 10))
        folder.addParmTemplate(_float("%s_layer" % name, "Layer Depth", layer, -16, 16))
        folder.addParmTemplate(_float("%s_pivotx" % name, "Pivot X", pivot[0], 0, 1))
        folder.addParmTemplate(_float("%s_pivoty" % name, "Pivot Y", pivot[1], 0, 1))
        folder.addParmTemplate(hou.ToggleParmTemplate("%s_flip" % name, "Flip Horizontally", default_value=flip))
        ptg.append(folder)
    rig.setParmTemplateGroup(ptg)

    cards = []
    for index, (name, image_name, pivot, xy, rot, scale, layer, flip) in enumerate(PARTS):
        image_path = "%s/%s" % (HERE, image_name)
        width, height = _png_size(image_path)
        rig.addSpareParmTuple(_float("%s_aspect" % name, "%s Aspect" % name, float(width)/height, 0.01, 20.0))
        rig.parm("%s_aspect" % name).hide(True)

        subnet = rig.createNode("subnet", "CARD_%s" % name.upper())
        grid = subnet.createNode("grid", "PLANE")
        grid.parm("orient").set("xy")
        grid.parmTuple("size").set((1, 1))
        grid.parm("rows").set(2)
        grid.parm("cols").set(2)

        setup = subnet.createNode("attribwrangle", "CARD_SETUP")
        setup.setInput(0, grid)
        setup.parm("class").set("point")
        ctrl_name = "PHX_%s_CTRL" % name.upper()
        args = (name, name, name, name, name, name, ctrl_name, ctrl_name,
                name, ctrl_name, name, ctrl_name, name, name)
        setup.parm("snippet").set(CARD_VEX % args)

        matnet = subnet.createNode("matnet", "MATNET")
        shader = matnet.createNode("principledshader::2.0", "MAT")
        shader.parm("basecolor_useTexture").set(1)
        shader.parm("basecolor_texture").set(image_path)
        shader.parm("basecolor_useTextureAlpha").set(1)
        shader.parm("alphablendmode").set("mask")
        _expr(shader.parm("alphacutoff"), 'ch("../../../alpha_cutoff")')
        shader.parm("rough").set(1.0)
        shader.parm("reflect").set(0.0)

        assign = subnet.createNode("material", "MATERIAL")
        assign.setInput(0, setup)
        assign.parm("num_materials").set(1)
        assign.parm("shop_materialpath1").set(shader.path())
        out_card = subnet.createNode("null", "OUT")
        out_card.setInput(0, assign)
        out_card.setDisplayFlag(True)
        out_card.setRenderFlag(True)
        subnet.setPosition(hou.Vector2(((index % 4) * 3, -(index // 4) * 2)))
        cards.append(subnet)

    merge = rig.createNode("merge", "MERGE_CARDS")
    for card in cards:
        merge.setNextInput(card)
    output = rig.createNode("null", "OUT_SIMPLE_PHOENIX")
    output.setInput(0, merge)
    output.setDisplayFlag(True)
    output.setRenderFlag(True)
    merge.setPosition(hou.Vector2((4.5, -5)))
    output.setPosition(hou.Vector2((4.5, -6.5)))

    # Visible OBJ-level animator controls. Part controls have their display position in
    # a pre-transform, so their translate/rotate/scale channels remain zero/zero/one.
    body_ctrl = obj.createNode("null", "PHX_BODY_CTRL")
    body_ctrl.parm("controltype").set("circles")
    body_ctrl.parm("orientation").set("xy")
    body_ctrl.parm("geoscale").set(3.3)
    body_ctrl.parm("use_dcolor").set(1)
    body_ctrl.parmTuple("dcolor").set((1.0, 0.75, 0.1))
    _expr(body_ctrl.parm("display"), 'ch("../PHOENIX_SIMPLE_RIG/show_controls")')

    control_colors = {
        "body_neck": (1.0, 0.75, 0.1), "head": (1.0, 0.25, 0.65),
        "wing_l": (0.2, 0.65, 1.0), "wing_r": (1.0, 0.3, 0.25),
        "tail": (0.65, 0.3, 1.0), "feet": (0.3, 1.0, 0.45),
    }
    for name, image_name, pivot, xy, rot, scale, layer, flip in PARTS:
        ctrl = obj.createNode("null", "PHX_%s_CTRL" % name.upper())
        ctrl.setFirstInput(body_ctrl)
        pre = hou.hmath.buildTranslate((xy[0], xy[1], 0.25))
        ctrl.setPreTransform(pre)
        ctrl.parm("controltype").set("circles" if name not in ("wing_l", "wing_r") else "planes")
        ctrl.parm("orientation").set("xy")
        ctrl.parm("geoscale").set(0.6 if name != "body_neck" else 1.0)
        ctrl.parm("use_dcolor").set(1)
        ctrl.parmTuple("dcolor").set(control_colors[name])
        _expr(ctrl.parm("display"), 'ch("../PHOENIX_SIMPLE_RIG/show_controls")')

    cam = obj.createNode("cam", "PHOENIX_SIMPLE_CAM")
    cam.parmTuple("t").set((0, 0, 30))
    cam.parm("projection").set("ortho")
    cam.parm("orthowidth").set(14)

    output.cook(force=True)
    if save_to:
        hou.hipFile.save(save_to)
        print("[simple phoenix] saved", save_to)
    print("[simple phoenix] built %d cards from %s" % (len(cards), HERE))
    return rig


if __name__ == "__main__":
    build(os.path.join(HERE, "phoenix_simple.hipnc"))
