from pathlib import Path
import hou,json
from install_transform_controls import install
r=Path(__file__).resolve().parent;scene=r/'abstract_fish.hipnc'
hou.hipFile.load(str(scene),ignore_load_warnings=True,suppress_save_prompt=True)
# Preserve the existing version before updating it in place.
backup=r/'abstract_fish_before_transform_controls.hipnc'
if not backup.exists():hou.hipFile.save(str(backup))
c=install();obj=hou.node('/obj/ABSTRACT_FISH');location=c.parmTuple('fish_location').eval();rotation=c.parmTuple('fish_rotation').eval()
c.parmTuple('fish_location').set((1,2,3));c.parmTuple('fish_rotation').set((-90,15,20))
assert obj.parmTuple('t').eval()==(1,2,3);assert obj.parmTuple('r').eval()==(-90,15,20)
# Verify that keys on the Stage node evaluate through the OBJ link.
p=c.parm('fish_rotationx');p.deleteAllKeyframes()
for frame,value in [(1,-90),(25,0)]:
 k=hou.Keyframe();k.setFrame(frame);k.setValue(value);k.setExpression('linear()',hou.exprLanguage.Hscript);p.setKeyframe(k)
hou.setFrame(13);assert abs(obj.evalParm('rx')+45)<1e-5
assert hou.node('/stage/fish_render_settings').stage()
p.deleteAllKeyframes();c.parmTuple('fish_location').set(location);c.parmTuple('fish_rotation').set(rotation);hou.setFrame(1)
hou.hipFile.save(str(scene))
(r/'transform_controls_validation.json').write_text(json.dumps({'location_link_verified':True,'rotation_link_verified':True,'keyframes_evaluate_through_obj':True,'stage_cooks':True,'original_transform_restored':True},indent=2))
print('TRANSFORM_CONTROLS_VERIFIED',flush=True)
