from pathlib import Path
import hou,json
from stage_controls import install_stage_controls
root=Path(__file__).resolve().parent
source=root.parent/'abstract_fish_v2/abstract_fish.hipnc';dest=root/'abstract_fish.hipnc'
if dest.exists():raise FileExistsError('Existing output protected')
hou.hipFile.load(str(source),ignore_load_warnings=True,suppress_save_prompt=True)
obj=hou.node('/obj/ABSTRACT_FISH');guide=obj.node('TAIL_UPPER_GUIDES')
before=[tuple(p.position()) for p in guide.geometry().points()]
control=install_stage_controls()
after=[tuple(p.position()) for p in guide.geometry().points()]
assert before==after,'Promoting controls changed saved shape'
value=control.evalParm('wind_strength');control.parm('wind_strength').set(value+.15)
moved=[tuple(p.position()) for p in guide.geometry().points()]
assert moved!=after,'Stage wind control not connected'
assert moved[0]==after[0],'Root moved'
control.parm('wind_strength').set(value)
flat=control.evalParm('flat_ribbons');control.parm('flat_ribbons').set(1)
assert len(obj.node('TAIL_UPPER').geometry().prims())==1504
control.parm('flat_ribbons').set(flat)
for parm in control.parms():
 try:
  if parm.parmTemplate().type() in (hou.parmTemplateType.Float,hou.parmTemplateType.Int,hou.parmTemplateType.Toggle,hou.parmTemplateType.Menu):parm.eval()
 except hou.Error:raise AssertionError('Invalid control '+parm.path())
hou.hipFile.save(str(dest))
# Roundtrip to verify the master links survive saving.
hou.hipFile.load(str(dest),ignore_load_warnings=True,suppress_save_prompt=True)
control=hou.node('/stage/FISH_CONTROLS')
assert control is not None
assert hou.node('/obj/ABSTRACT_FISH/RIBBON_FORCE_CONTROLS').parm('wind_strength').getReferencedParm().path()==control.parm('wind_strength').path()
assert hou.node('/stage/fish_geometry').input(0)==control
stage=hou.node('/stage/fish_render_settings').stage()
assert stage is not None,'Solaris chain failed to cook'
(root/'stage_controls_validation.json').write_text(json.dumps({'saved_source_shape_preserved':True,'stage_wind_updates_geometry':True,'roots_stay_pinned':True,'stage_flat_mode_updates_geometry':True,'parameter_links_survive_reload':True,'solaris_stage_cooks':True,'controller':'/stage/FISH_CONTROLS'},indent=2))
print('STAGE_CONTROLS_VALIDATED',dest,flush=True)
