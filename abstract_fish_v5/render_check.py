from pathlib import Path
import hou
r=Path(__file__).resolve().parent
hou.hipFile.load(str(r/'abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
hou.node('/stage/FISH_CONTROLS').parm('presentation').set(2)
hou.node('/stage/fish_render_settings').parm('samplesperpixel').set(4)
rop=hou.node('/stage/fish_render');rop.parm('res_user1').set(480);rop.parm('res_user2').set(270);rop.parm('outputimage').set(str(r/'rig_render_check.png'));rop.render()
print('RENDER_OK',flush=True)
