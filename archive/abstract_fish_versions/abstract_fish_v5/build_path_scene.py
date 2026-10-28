from pathlib import Path
import hou,json,math
from install_path_rig import install_path_rig
r=Path(__file__).resolve().parent;dest=r/'abstract_fish.hipnc'
if dest.exists():raise FileExistsError(dest)
hou.hipFile.load(str(r.parent/'abstract_fish_v4/abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
c=install_path_rig();out=hou.node('/obj/ABSTRACT_FISH/OUT_FISH');base=out.input(0).input(0)
c.parm('path_enable').set(0);a=base.geometry();b=out.geometry()
assert a.pointFloatAttribValues('P')==b.pointFloatAttribValues('P')
count=len(b.points());c.parm('path_enable').set(1)
poses=[]
for progress in (0,.25,.5,.75,1):
 c.parm('path_progress').set(progress);g=out.geometry();assert len(g.points())==count
 assert all(math.isfinite(v) for v in g.pointFloatAttribValues('P'))
 poses.append(tuple(g.boundingBox().center()))
assert (hou.Vector3(poses[0])-hou.Vector3(poses[-1])).length()>15
# Editing a visible waypoint updates the sampled path and fish placement.
c.parm('path_progress').set(.5);point=hou.node('/obj/FISH_PATH_POINT_03');orig=point.parmTuple('t').eval();before=out.geometry().boundingBox().center();point.parm('tz').set(3)
after=out.geometry().boundingBox().center();assert (after-before).length()>.1
point.parmTuple('t').set(orig)
c.parm('path_progress').set(0)
stage=hou.node('/stage/fish_render_settings').stage();assert stage
from pxr import UsdGeom
assert UsdGeom.Imageable(stage.GetPrimAtPath('/FishRig')).ComputePurpose()=='guide'
# Keep swimming active and path progress ready for user keys.
hou.setFrame(1);hou.hipFile.save(str(dest))
hou.hipFile.load(str(dest),ignore_load_warnings=True,suppress_save_prompt=True)
assert hou.node('/obj/ABSTRACT_FISH/OUT_FISH').geometry().points()
(r/'rig_validation.json').write_text(json.dumps({'path_positions':poses,'topology_preserved':True,'finite_geometry':True,'disabled_matches_source':True,'waypoint_edit_updates_fish':True,'usd_rig_guide_purpose':True,'reload_verified':True},indent=2))
print('RIG_VALIDATED',dest,flush=True)
