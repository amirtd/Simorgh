from pathlib import Path
import hou,json,math
from install_swimming import install_swimming
root=Path(__file__).resolve().parent;dest=root/'abstract_fish.hipnc'
if dest.exists():raise FileExistsError('Existing scene protected')
hou.hipFile.load(str(root.parent/'abstract_fish_v3/abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
obj=hou.node('/obj/ABSTRACT_FISH')
original=[tuple(p.position()) for p in obj.node('FINAL_MERGE').geometry().points()]
control=install_swimming();out=obj.node('SWIM_DEFORM')
control.parm('swim_enable').set(0)
assert [tuple(p.position()) for p in out.geometry().points()]==original
control.parm('swim_enable').set(1)
frames={}
for frame in (1,7,13,19,25):
 hou.setFrame(frame);g=out.geometry()
 frames[frame]=[tuple(p.position()) for p in g.points()]
 assert len(g.points())==len(original)
 assert all(math.isfinite(x) for p in g.points() for x in p.position())
assert frames[1]!=frames[7],'No automatic timeline motion'
hou.setFrame(7);g=out.geometry();weights=g.pointFloatAttribValues('swim_weight')
head=[w for p,w in zip(g.points(),weights) if p.attribValue('rest')[0]<-1.8]
tail=[w for p,w in zip(g.points(),weights) if p.attribValue('rest')[0]>2]
assert sum(head)/len(head)<.12
assert sum(tail)/len(tail)>sum(head)/len(head)*5
# Speed is in real seconds; doubling speed reproduces half-speed's pose twice as fast.
control.parm('swim_speed').set(.8);hou.setFrame(13);pose_a=[tuple(p.position()) for p in out.geometry().points()]
control.parm('swim_speed').set(1.6);hou.setFrame(7);pose_b=[tuple(p.position()) for p in out.geometry().points()]
assert max(abs(a-b) for p,q in zip(pose_a,pose_b) for a,b in zip(p,q))<1e-6
control.parm('swim_speed').set(.8)
control.parm('swim_strength').set(0);g=out.geometry()
assert max(abs(a-b) for p,q in zip([tuple(p.position()) for p in g.points()],original) for a,b in zip(p,q))<1e-8
control.parm('swim_strength').set(.22)
hou.setFrame(1)
stage=hou.node('/stage/fish_render_settings').stage();assert stage is not None
hou.hipFile.save(str(dest))
(root/'swim_validation.json').write_text(json.dumps({'timeline_motion':True,'head_damped_tail_amplified':True,'speed_cycles_per_second_verified':True,'disable_restores_geometry':True,'zero_strength_restores_geometry':True,'topology_preserved':True,'finite_positions':True,'solaris_cooks':True,'frames_checked':list(frames)},indent=2))
print('SWIM_VALIDATED',dest,flush=True)
