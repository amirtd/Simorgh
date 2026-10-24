from pathlib import Path
import hou,json
from install_obj_stage_transform import install
from pxr import UsdGeom,Gf
r=Path(__file__).resolve().parent;dest=r/'abstract_fish.hipnc'
if dest.exists():raise FileExistsError(dest)
hou.hipFile.load(str(r.parent/'abstract_fish_v8/abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
out=install();obj=hou.node('/obj/ABSTRACT_FISH');rotation=obj.parmTuple('r').eval();translation=obj.parmTuple('t').eval()
base=obj.node('OUT_FISH').geometry().freeze()
obj.parmTuple('r').set((-90,0,0));obj.parmTuple('t').set((1,2,3))
expected=base.freeze();expected.transform(obj.worldTransform())
actual=out.geometry();assert max(abs(a-b) for a,b in zip(expected.pointFloatAttribValues('P'),actual.pointFloatAttribValues('P')))<1e-5
stage=hou.node('/stage/fish_render_settings').stage();cache=UsdGeom.BBoxCache(hou.time()*hou.fps()+1,[UsdGeom.Tokens.default_,UsdGeom.Tokens.render]);bbox=cache.ComputeWorldBound(stage.GetPrimAtPath('/fish')).ComputeAlignedRange()
# Actual USD bounds must match the world-transformed SOP geometry.
box=actual.boundingBox()
assert max(abs(a-b) for a,b in zip(tuple(bbox.GetMin()),tuple(box.minvec())))<1e-4
assert max(abs(a-b) for a,b in zip(tuple(bbox.GetMax()),tuple(box.maxvec())))<1e-4
obj.parmTuple('r').set(rotation);obj.parmTuple('t').set(translation)
hou.hipFile.save(str(dest))
(r/'transform_validation.json').write_text(json.dumps({'obj_rotation_translation_baked_once':True,'usd_world_bounds_match_obj':True,'original_obj_transform_preserved':True},indent=2))
print('OBJ_STAGE_TRANSFORM_VERIFIED',flush=True)
