from pathlib import Path
import hou
r=Path(__file__).resolve().parent;hou.hipFile.load(str(r/'abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
c=hou.node('/stage/FISH_CONTROLS')
for name in ('preview_fast','preview_low'):c.parm(name).set(0)
for name in ('preview_ribbons','preview_textures'):c.parm(name).set(1)
settings=hou.node('/stage/fish_render_settings');settings.parm('samplesperpixel').set(8)
rop=hou.node('/stage/fish_render');rop.parm('trange').set(0);rop.parm('res_user1').set(720);rop.parm('res_user2').set(405);rop.parm('outputimage').set(str(r/'ribbon_artwork_preview.png'));rop.render();print('REVIEW_RENDERED',flush=True)
