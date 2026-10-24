from pathlib import Path
from datetime import datetime
import hou,json,time
r=Path(__file__).resolve().parent
hou.hipFile.load(str(r/'abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
rop=hou.node('/stage/fish_render');settings=hou.node('/stage/fish_render_settings')
first=int(rop.evalParm('f1'));last=int(rop.evalParm('f2'));step=int(rop.evalParm('f3'))
out=r/'renders'/datetime.now().strftime('batch_%Y%m%d_%H%M%S');out.mkdir(parents=True,exist_ok=False)
status={'state':'running','output':str(out),'first':first,'last':last,'completed':[],'camera':settings.evalParm('camera'),'resolution':[rop.evalParm('res_user1'),rop.evalParm('res_user2')]}
statusfile=r/'renders'/'batch_status.json'
def update():statusfile.write_text(json.dumps(status,indent=2))
update();print('OUTPUT',out,flush=True)
try:
 rop.parm('trange').set(0)
 for frame in range(first,last+1,step):
  dest=out/('fish_v9.%04d.png'%frame);hou.setFrame(frame);rop.parm('outputimage').set(str(dest));print('BEGIN',frame,flush=True);rop.render()
  assert dest.exists() and dest.stat().st_size>0
  status['completed'].append(frame);update();print('DONE',frame,flush=True)
 status['state']='complete';update();print('BATCH_COMPLETE',flush=True)
except Exception as error:
 status['state']='failed';status['error']=str(error);update();raise
