import os
import hou

HIP = r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini\ink_drop_effect.hipnc"
OUTPUT_DIR = r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini\render"

os.makedirs(OUTPUT_DIR, exist_ok=True)
hou.hipFile.load(HIP)
karma = hou.node('/stage/ink_drop_karma')
rop = hou.node('/stage/ink_drop_render')
if karma is None or rop is None:
    raise RuntimeError('Could not find the Karma render nodes in the saved scene.')

# Keep the scene's current quality settings; only make the output destination explicit.
karma.parm('picture').set(r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini\render\ink_drop.$F4.png")
print('Rendering frames 3-23')
print('Output:', karma.parm('picture').unexpandedString())
rop.render(frame_range=(3, 23, 1))
print('Batch render complete.')
