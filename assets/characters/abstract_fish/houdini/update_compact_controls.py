from pathlib import Path
import hou,json
from install_compact_controls import install
r=Path(__file__).resolve().parent;scene=r/'abstract_fish.hipnc'
hou.hipFile.load(str(r/'abstract_fish_before_compact_controls.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
backup=r/'abstract_fish_before_compact_controls.hipnc'
if not backup.exists():hou.hipFile.save(str(backup))
c=hou.node('/stage/FISH_CONTROLS')
def snapshot():
 return {p.name():(p.evalAsString(),tuple(k.asCode() for k in p.keyframes())) for p in c.parms() if not isinstance(p.parmTemplate(),(hou.FolderParmTemplate,hou.FolderSetParmTemplate,hou.ButtonParmTemplate))}
before=snapshot();install();after=snapshot()
for name,value in before.items():assert after[name]==value,'Changed parameter '+name
assert hou.node('/stage/fish_render_settings').stage()
hou.hipFile.save(str(scene));hou.hipFile.load(str(scene),ignore_load_warnings=True,suppress_save_prompt=True)
(r/'compact_controls_validation.json').write_text(json.dumps({'parameters_preserved':len(before),'values_and_keyframes_preserved':True,'top_level_tabs':[f.label() for f in hou.node('/stage/FISH_CONTROLS').parmTemplateGroup().entries()],'reload_verified':True},indent=2))
print('COMPACT_CONTROLS_VERIFIED',flush=True)
