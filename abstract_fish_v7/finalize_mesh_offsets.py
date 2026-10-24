from pathlib import Path
import hou,json
r=Path(__file__).resolve().parent
hou.hipFile.load(str(r/'abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
c=hou.node('/stage/FISH_CONTROLS');group=c.parmTemplateGroup();report=json.loads((r/'ribbon_offset_validation.json').read_text());mapping=report['controls']
for prefix in mapping.values():
 for suffix in ('_uv','_tile','_rotate'):group.remove(prefix+suffix)
c.setParmTemplateGroup(group)
code='''import hou
geo=hou.pwd().geometry();c=hou.node('/stage/FISH_CONTROLS');mapping=MAPPING
seen=set();offsets={name:hou.Vector3(c.parmTuple(prefix+'_position').eval()) for name,prefix in mapping.items()}
for prim in geo.prims():
 name=prim.attribValue('name')
 if name.startswith('texparts_'):name=name[len('texparts_'):]
 offset=offsets.get(name)
 if offset is None or offset.lengthSquared()==0:continue
 for point in prim.points():
  if point.number() in seen:continue
  seen.add(point.number());point.setPosition(point.position()+offset)
  if geo.findPointAttrib('rest'):point.setAttribValue('rest',tuple(hou.Vector3(point.attribValue('rest'))+offset))
 if geo.findPrimAttrib('attachment'):prim.setAttribValue('attachment',tuple(hou.Vector3(prim.attribValue('attachment'))+offset))
'''.replace('MAPPING',repr(mapping))
obj=hou.node('/obj/ABSTRACT_FISH')
for name in ('INDIVIDUAL_RIBBON_OFFSETS','INDIVIDUAL_GUIDE_OFFSETS'):obj.node(name).parm('python').set(code)
out=obj.node('INDIVIDUAL_RIBBON_OFFSETS');baseline=out.geometry().freeze();name=sorted(mapping)[0];prefix=mapping[name]
c.parmTuple(prefix+'_position').set((0,.12,.08));changed=out.geometry();ids={p.number() for prim in baseline.prims() if prim.attribValue('name')=='texparts_'+name for p in prim.points()}
for a,b in zip(baseline.points(),changed.points()):
 assert (b.position()-a.position()-(hou.Vector3((0,.12,.08)) if a.number() in ids else hou.Vector3())).length()<1e-5
assert baseline.pointFloatAttribValues('uv')==changed.pointFloatAttribValues('uv')
c.parmTuple(prefix+'_position').set((0,0,0));assert hou.node('/stage/fish_render_settings').stage()
hou.hipFile.save(str(r/'abstract_fish.hipnc'))
(r/'ribbon_offset_validation.json').write_text(json.dumps({'ribbons':42,'mesh_offsets_only':True,'individual_position_verified':True,'other_ribbons_unchanged':True,'uv_unchanged':True,'stage_cooks':True,'controls':mapping},indent=2))
print('MESH_OFFSETS_VERIFIED',flush=True)
