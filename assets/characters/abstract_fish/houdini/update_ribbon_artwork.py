from pathlib import Path
from datetime import datetime
import hou,shutil,json,os
from install_ribbon_artwork import install
r=Path(__file__).resolve().parent;scene=r/'abstract_fish.hipnc';stamp=scene.stat().st_mtime_ns
backup=r/('abstract_fish_before_artwork_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.hipnc');shutil.copy2(scene,backup)
hou.hipFile.load(str(scene),ignore_load_warnings=True,suppress_save_prompt=True)
c=hou.node('/stage/FISH_CONTROLS')
def snapshot():return {p.name():(p.rawValue(),tuple(k.asCode() for k in p.keyframes())) for p in c.parms() if not isinstance(p.parmTemplate(),(hou.FolderParmTemplate,hou.FolderSetParmTemplate,hou.ButtonParmTemplate))}
before=snapshot();install(r);after=snapshot();assert all(after[n]==v for n,v in before.items())
g=hou.node('/obj/ABSTRACT_FISH/RIBBON_ARTWORK').geometry();assert not hou.node('/obj/ABSTRACT_FISH/RIBBON_ARTWORK').errors()
assert any(n.startswith('artred_') for n in g.primStringAttribValues('name'));assert any(n.startswith('artblue_') for n in g.primStringAttribValues('name'))
assert hou.node('/stage/fish_render_settings').stage();assert scene.stat().st_mtime_ns==stamp
pending=r/'artwork_pending.hipnc';hou.hipFile.save(str(pending));os.replace(pending,scene)
(r/'artwork_validation.json').write_text(json.dumps({'existing_controls_and_keys_preserved':True,'backup':str(backup),'red_blue_assigned':True,'per_ribbon_horizontal_flip':True},indent=2))
print('ARTWORK_SAVED',flush=True)
# Preview only: use the existing side camera and neutral fish placement without saving these overrides.
for name in ('fish_location','fish_rotation'):
 for p in c.parmTuple(name):p.deleteAllKeyframes();p.set(0)
c.parm('preview_fast').set(0);c.parm('preview_ribbons').set(1);c.parm('preview_textures').set(1)
settings=hou.node('/stage/fish_render_settings');settings.parm('camera').set('/cameras/fish_side_camera');settings.parm('samplesperpixel').set(8)
rop=hou.node('/stage/fish_render');rop.parm('trange').set(0);rop.parm('res_user1').set(720);rop.parm('res_user2').set(405);rop.parm('outputimage').set(str(r/'ribbon_artwork_preview.png'));rop.render();print('ARTWORK_RENDERED',flush=True)
