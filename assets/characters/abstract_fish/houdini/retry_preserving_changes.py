from pathlib import Path
from datetime import datetime
import hou,json,shutil,os
from install_preview_controls import install as preview
from install_compact_controls import install as compact
r=Path(__file__).resolve().parent;scene=r/'abstract_fish.hipnc';stamp=scene.stat().st_mtime_ns
backup=r/('abstract_fish_user_changes_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.hipnc');shutil.copy2(scene,backup)
hou.hipFile.load(str(scene),ignore_load_warnings=True,suppress_save_prompt=True)
def snapshot():
 result={}
 for n in hou.node('/').allSubChildren():
  for p in n.parms():
   template=p.parmTemplate()
   if isinstance(template,(hou.FolderParmTemplate,hou.FolderSetParmTemplate,hou.ButtonParmTemplate)):continue
   if p.name()=='python':continue
   try:result[p.path()]=(p.rawValue(),tuple(k.asCode() for k in p.keyframes()))
   except hou.Error:pass
 return result
before=snapshot();preview();compact();after=snapshot()
changed={path for path,value in before.items() if after.get(path)!=value}
assert not changed,'Unexpected parameter changes: '+repr(sorted(changed))
c=hou.node('/stage/FISH_CONTROLS');assert c.parmTuple('fish_location').eval()==(-43.3,.1,0.);assert c.parmTuple('fish_rotation').eval()==(-91.,-20.,4.)
assert [f.label() for f in c.parmTemplateGroup().entries()]==['Preview','Motion','Ribbons','Color','Individual Ribbons']
assert hou.node('/stage/fish_render_settings').stage()
assert scene.stat().st_mtime_ns==stamp,'Scene changed during update; original protected'
temp=r/'abstract_fish_preview_update_pending.hipnc';hou.hipFile.save(str(temp));os.replace(temp,scene)
(r/'preserved_changes_validation.json').write_text(json.dumps({'source_backup':str(backup),'existing_parameters_verified':len(before),'existing_values_expressions_keyframes_unchanged':True,'location':list(c.parmTuple('fish_location').eval()),'rotation':list(c.parmTuple('fish_rotation').eval()),'tabs':[f.label() for f in c.parmTemplateGroup().entries()]},indent=2))
print('USER_CHANGES_PRESERVED',flush=True)
