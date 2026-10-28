from pathlib import Path
import hou,json,re
r=Path(__file__).resolve().parent;dest=r/'abstract_fish.hipnc'
if dest.exists():raise FileExistsError(dest)
hou.hipFile.load(str(r.parent/'abstract_fish_v6/abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
obj=hou.node('/obj/ABSTRACT_FISH');c=hou.node('/stage/FISH_CONTROLS')
g=obj.node('FINAL_MERGE').geometry();entries={}
for p in g.prims():
 system=p.attribValue('system');name=p.attribValue('name')
 if system not in ('BODY_BASE','EYES'):entries[name]=system
mapping={name:'ribbon_'+re.sub('[^a-zA-Z0-9_]','_',name).lower() for name in entries}
group=c.parmTemplateGroup();folder=hou.FolderParmTemplate('ribbon_offsets','Individual Ribbon Offsets')
for system in sorted(set(entries.values())):
 sub=hou.FolderParmTemplate('offset_'+system.lower(),system.replace('_',' ').title())
 for name in sorted(n for n in entries if entries[n]==system):
  prefix=mapping[name];f=hou.FolderParmTemplate(prefix+'_folder',name.split('_',1)[1].replace('_',' ').title())
  f.addParmTemplate(hou.FloatParmTemplate(prefix+'_uv','Texture UV Offset',2,default_value=(0.,0.),naming_scheme=hou.parmNamingScheme.XYZW))
  f.addParmTemplate(hou.FloatParmTemplate(prefix+'_tile','Texture UV Scale',2,default_value=(1.,1.),naming_scheme=hou.parmNamingScheme.XYZW))
  f.addParmTemplate(hou.FloatParmTemplate(prefix+'_rotate','Texture UV Rotation',1,default_value=(0.,)))
  f.addParmTemplate(hou.FloatParmTemplate(prefix+'_position','Ribbon Position Offset',3,default_value=(0.,0.,0.),naming_scheme=hou.parmNamingScheme.XYZW))
  sub.addParmTemplate(f)
 folder.addParmTemplate(sub)
group.insertBefore(group.entries()[0].name(),folder);c.setParmTemplateGroup(group)
code='''import hou,math
geo=hou.pwd().geometry();c=hou.node('/stage/FISH_CONTROLS')
mapping=MAPPING
seen=set()
for prim in geo.prims():
 name=prim.attribValue('name')
 if name.startswith('texparts_'):name=name[len('texparts_'):]
 prefix=mapping.get(name)
 if not prefix:continue
 offset=hou.Vector3(c.parmTuple(prefix+'_position').eval());uvshift=c.parmTuple(prefix+'_uv').eval();scale=c.parmTuple(prefix+'_tile').eval();angle=math.radians(c.evalParm(prefix+'_rotate'));co=math.cos(angle);si=math.sin(angle)
 for point in prim.points():
  if point.number() in seen:continue
  seen.add(point.number());point.setPosition(point.position()+offset)
  if geo.findPointAttrib('rest'):point.setAttribValue('rest',tuple(hou.Vector3(point.attribValue('rest'))+offset))
  if geo.findPointAttrib('uv'):
   uv=point.attribValue('uv');u=(uv[0]-.5)*scale[0];v=(uv[1]-.5)*scale[1];point.setAttribValue('uv',(u*co-v*si+.5+uvshift[0],u*si+v*co+.5+uvshift[1],uv[2]))
 if geo.findPrimAttrib('attachment'):prim.setAttribValue('attachment',tuple(hou.Vector3(prim.attribValue('attachment'))+offset))
'''.replace('MAPPING',repr(mapping))
for source,name in [(obj.node('PLANAR_TEXTURE_UV'),'INDIVIDUAL_RIBBON_OFFSETS'),(obj.node('ALL_GUIDE_CURVES'),'INDIVIDUAL_GUIDE_OFFSETS')]:
 consumers=[(n,i) for n in source.outputs() for i,v in enumerate(n.inputs()) if v==source]
 node=obj.createNode('python',name);node.parm('python').set(code);node.setInput(0,source)
 for n,i in consumers:n.setInput(i,node)
 node.setColor(hou.Color((.2,.65,.85)))
# Zero offsets must preserve all existing geometry and UVs.
uv=obj.node('PLANAR_TEXTURE_UV').geometry();out=obj.node('INDIVIDUAL_RIBBON_OFFSETS');baseline=out.geometry().freeze()
assert baseline.pointFloatAttribValues('P')==uv.pointFloatAttribValues('P')
assert baseline.pointFloatAttribValues('uv')==uv.pointFloatAttribValues('uv')
name=sorted(mapping)[0];prefix=mapping[name];c.parmTuple(prefix+'_uv').set((.2,-.1));c.parmTuple(prefix+'_position').set((0,.12,.08))
changed=out.geometry();ids={p.number() for prim in baseline.prims() if prim.attribValue('name')=='texparts_'+name for p in prim.points()};assert ids
for a,b in zip(baseline.points(),changed.points()):
 if a.number() in ids:
  assert (b.position()-a.position()-hou.Vector3((0,.12,.08))).length()<1e-5
  assert abs(b.attribValue('uv')[0]-a.attribValue('uv')[0]-.2)<1e-5
 else:assert (a.position()-b.position()).length()<1e-8
c.parmTuple(prefix+'_uv').set((0,0));c.parmTuple(prefix+'_position').set((0,0,0))
assert hou.node('/stage/fish_render_settings').stage()
obj.layoutChildren();c.setCurrent(True,clear_all_selected=True);hou.hipFile.save(str(dest))
(r/'ribbon_offset_validation.json').write_text(json.dumps({'ribbons':len(mapping),'zero_defaults_preserve_geometry_uv':True,'individual_uv_offset_verified':True,'individual_position_verified':True,'other_ribbons_unchanged':True,'stage_cooks':True,'controls':mapping},indent=2))
print('RIBBON_OFFSETS_READY',len(mapping),dest,flush=True)
