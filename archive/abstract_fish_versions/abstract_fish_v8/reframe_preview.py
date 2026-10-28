from pathlib import Path
import hou
r=Path(__file__).resolve().parent
hou.hipFile.load(str(r/'abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
cam=hou.node('/stage/fish_side_camera');print([(p.name(),p.evalAsString()) for p in cam.parms() if 'ortho' in p.name()],flush=True)
cam.parm('horizontalAperture').set(11800)
hou.hipFile.save(str(r/'abstract_fish.hipnc'))
hou.node('/stage/fish_render_settings').parm('samplesperpixel').set(8);rop=hou.node('/stage/fish_render');rop.parm('res_user1').set(720);rop.parm('res_user2').set(405);rop.parm('outputimage').set(str(r/'paper_preview.png'));rop.render()
print('REFRAMED',flush=True)
