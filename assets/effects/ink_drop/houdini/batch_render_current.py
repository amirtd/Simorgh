import os
import hou

scene = r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini\ink_drop_effect.hipnc"
review = r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini\review"
hou.hipFile.load(scene)
frame = int(round(hou.frame()))
os.makedirs(review, exist_ok=True)
output = os.path.join(review, "current_frame_%04d.exr" % frame)
rop = hou.node('/stage/ink_drop_render')
rop.parm('outputimage').set(output)
rop.parm('trange').set(0)
print('Rendering saved current frame', frame, 'to', output)
rop.render()
print('Finished', output)
