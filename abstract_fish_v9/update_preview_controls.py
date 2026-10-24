from pathlib import Path
import hou,json
from install_preview_controls import install
r=Path(__file__).resolve().parent;scene=r/'abstract_fish.hipnc'
hou.hipFile.load(str(scene),ignore_load_warnings=True,suppress_save_prompt=True)
backup=r/'abstract_fish_before_preview_controls.hipnc'
if not backup.exists():hou.hipFile.save(str(backup))
obj=hou.node('/obj/ABSTRACT_FISH');before=len(obj.node('OUT_FISH').geometry().prims());c=install();assert len(obj.node('OUT_FISH').geometry().prims())==before
c.parm('preview_fast').set(1);quick=obj.node('OUT_FISH').geometry();assert set(quick.primStringAttribValues('system'))<=set(('BODY_BASE','EYES'));assert len(quick.prims())<before
c.parm('preview_fast').set(0);c.parm('preview_ribbons').set(0);assert set(obj.node('OUT_FISH').geometry().primStringAttribValues('system'))<=set(('BODY_BASE','EYES'))
c.parm('preview_ribbons').set(1);c.parm('preview_effects').set(0);assert not obj.node('OUT_FISH').errors();c.parm('preview_effects').set(1)
c.parm('preview_low').set(1);low=len(obj.node('OUT_FISH').geometry().prims());assert low<before;c.parm('preview_low').set(0)
assert hou.node('/stage/fish_render_settings').stage();hou.hipFile.save(str(scene))
(r/'preview_controls_validation.json').write_text(json.dumps({'default_polygons':before,'low_polygons':low,'fast_preview_body_eyes_only':True,'ribbon_toggle_verified':True,'default_geometry_preserved':True,'stage_cooks':True},indent=2))
print('PREVIEW_CONTROLS_VERIFIED',flush=True)
