import hou

hou.hipFile.load(r"E:\Wirling Worlds\Houdini Ink Drop\ink_drop_effect.hipnc")
hou.setFrame(30)
rop = hou.node('/stage/ink_drop_render')
rop.parm('outputimage').set(r"E:\Wirling Worlds\Houdini Ink Drop\review\tear_satellite_f30.exr")
rop.parm('override_res').set('640 640')
rop.parm('trange').set(0)
rop.render()
