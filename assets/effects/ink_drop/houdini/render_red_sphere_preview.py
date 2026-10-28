import hou

hou.hipFile.load(r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini\ink_drop_effect.hipnc")
hou.setFrame(24)
karma = hou.node('/stage/ink_drop_karma')
karma.parm('resolutionx').set(640)
karma.parm('samplesperpixel').set(4)
rop = hou.node('/stage/ink_drop_render')
rop.parm('outputimage').set(r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini\review\red_sphere_f24.exr")
rop.parm('trange').set(0)
rop.render()
