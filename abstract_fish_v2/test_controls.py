from pathlib import Path
import json,math
import hou
import build_abstract_fish as fish
root=Path(__file__).resolve().parent
hou.hipFile.load(str(root/'abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
obj=hou.node('/obj/ABSTRACT_FISH');force=obj.node('RIBBON_FORCE_CONTROLS');guide=obj.node('TAIL_UPPER_GUIDES')
def positions():
 g=guide.geometry();return [tuple(p.position()) for p in g.points()]
before=positions();force.parm('wind_strength').set(.75);after=positions()
assert abs(after[47][1]-before[47][1])>.5,'Wind did not update ribbon tips'
assert max(abs(a-b) for a,b in zip(after[0],before[0]))<1e-8,'Attachment root moved'
force.parm('wind_strength').set(0)
assert max(abs(a-b) for p,q in zip(positions(),before) for a,b in zip(p,q))<1e-8,'Zero force did not restore baseline'
obj.parm('flat_ribbons').set(1)
fish.validate(obj,obj.node('FINAL_MERGE'),root)
for system in fish.SYSTEMS:
 g=obj.node(system).geometry()
 assert len(g.prims())==376*len(fish.SYSTEMS[system]),'Not a single-surface ribbon'
obj.parm('flat_ribbons').set(0)
obj.node('TAIL_UPPER').parm('local_flat').set(1)
assert len(obj.node('TAIL_UPPER').geometry().prims())==4*376
assert len(obj.node('TAIL_LOWER').geometry().prims())==4*862
obj.node('TAIL_UPPER').parm('local_flat').set(0)
fish.validate(obj,obj.node('FINAL_MERGE'),root)
(root/'controls_validation.json').write_text(json.dumps({'wind_updates_without_forced_recook':True,'roots_pinned':True,'zero_force_restores_shape':True,'flat_single_surface_all_42_ribbons':True,'per_system_flat_override':True,'baseline_restored':True},indent=2))
print('CONTROL_TESTS_PASSED',flush=True)
# Save a flat, wind-deflected shaded preview, leaving the delivered scene defaults unchanged.
previews=root/'previews';previews.mkdir(exist_ok=True)
obj.parm('flat_ribbons').set(1);obj.parm('presentation').set(2);force.parm('wind_strength').set(.35);force.parmTuple('wind_direction').set((0,1,.3))
rop=hou.node('/stage/fish_render');dest=previews/'flat_wind_preview.png'
if dest.exists():raise RuntimeError('Existing preview protected')
rop.parm('outputimage').set(str(dest));rop.render()
assert dest.is_file() and dest.stat().st_size>0
print('PREVIEW_COMPLETE',dest,flush=True)
