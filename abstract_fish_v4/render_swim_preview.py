from pathlib import Path
import hou
r=Path(__file__).resolve().parent
hou.hipFile.load(str(r/'abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
ctrl=hou.node('/stage/FISH_CONTROLS');ctrl.parm('presentation').set(2)
settings=hou.node('/stage/fish_render_settings');settings.parm('samplesperpixel').set(4)
rop=hou.node('/stage/fish_render');rop.parm('res_user1').set(480);rop.parm('res_user2').set(270)
out=r/'previews'/'swimming_frames';out.mkdir(parents=True,exist_ok=False)
for index,frame in enumerate(range(1,31,2)):
 hou.setFrame(frame);dest=out/('swim.%04d.png'%index)
 rop.parm('outputimage').set(str(dest));rop.render()
 assert dest.exists() and dest.stat().st_size>0
 print('RENDERED',frame,str(dest),flush=True)
print('SWIM_PREVIEW_COMPLETE',flush=True)
