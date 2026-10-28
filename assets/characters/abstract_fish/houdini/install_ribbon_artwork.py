import hou,json
from pathlib import Path

def install(asset_root):
 obj=hou.node('/obj/ABSTRACT_FISH');c=hou.node('/stage/FISH_CONTROLS')
 if obj.node('RIBBON_ARTWORK'):return
 report=json.loads((Path(asset_root)/'ribbon_offset_validation.json').read_text());mapping=report['controls']
 group=c.parmTemplateGroup()
 # Add source/flip controls beside each ribbon's existing mesh offset.
 for name,prefix in mapping.items():
  indices=group.findIndices(prefix+'_position');parent=indices[:-1];folder=group.entryAtIndices(parent).clone()
  folder.addParmTemplate(hou.MenuParmTemplate(prefix+'_art','Ribbon Artwork',['auto','red','blue'],['Match Original Color','Red / Gold','Blue / Gold']))
  folder.addParmTemplate(hou.ToggleParmTemplate(prefix+'_flip','Flip Artwork Horizontally',False));group.replace(parent,folder)
 color=next(f for f in group.entries() if f.label()=='Color').clone()
 f=hou.FolderParmTemplate('ribbon_artwork_controls','Ribbon Artwork',folder_type=hou.folderType.Collapsible)
 f.addParmTemplate(hou.ToggleParmTemplate('ribbon_art_enable','Use Supplied Ribbon Artwork',True))
 f.addParmTemplate(hou.ToggleParmTemplate('ribbon_art_flip','Flip All Ribbon Artwork Horizontally',False))
 color.addParmTemplate(f);group.replace(group.findIndices(color.name()),color);c.setParmTemplateGroup(group)
 bounds=json.loads((Path(asset_root)/'textures/ribbon_alpha_bounds.json').read_text())
 code='''import hou
geo=hou.pwd().geometry();c=hou.node('/stage/FISH_CONTROLS')
mapping=MAPPING
bounds=BOUNDS
if c.evalParm('ribbon_art_enable') and c.evalParm('preview_textures') and not c.evalParm('preview_fast'):
 uv=geo.findPointAttrib('uv') or geo.addAttrib(hou.attribType.Point,'uv',(0.,0.,0.));seen=set();settings={}
 for name,prefix in mapping.items():
  choice=c.evalParm(prefix+'_art');mid=int(name[1:3]);kind='red' if mid in (1,2,3,4,8) else 'blue'
  if choice:kind='red' if choice==1 else 'blue'
  settings[name]=(kind,bool(c.evalParm(prefix+'_flip'))!=bool(c.evalParm('ribbon_art_flip')))
 for prim in geo.prims():
  name=prim.attribValue('name')
  if name.startswith('texparts_'):name=name[9:]
  if name not in settings:continue
  kind,flip=settings[name];table=bounds[kind]
  for p in prim.points():
   if p.number() in seen:continue
   seen.add(p.number());t,v,shell=p.attribValue('ribbon_uv');u=1-t if flip else t;i=max(0,min(len(table)-1,int(u*(len(table)-1))));lo,hi=table[i]
   p.setAttribValue(uv,(u,lo+v*(hi-lo),0.))
  prim.setAttribValue('name','art'+kind+'_'+name);prim.setAttribValue('shop_materialpath','/mat/fish_art_'+kind)
'''.replace('MAPPING',repr(mapping)).replace('BOUNDS',repr(bounds))
 source=obj.node('SWIM_DEFORM').input(0);consumers=[(n,i) for n in source.outputs() for i,v in enumerate(n.inputs()) if v==source]
 node=obj.createNode('python','RIBBON_ARTWORK');node.parm('python').set(code);node.setInput(0,source)
 for n,i in consumers:n.setInput(i,node)
 for kind in ('red','blue'):
  net=hou.node('/mat/fish_04').copyTo(hou.node('/mat'));net.setName('fish_art_'+kind,unique_name=False);surface=net.node('mtlxstandard_surface')
  coord=net.createNode('mtlxtexcoord','RIBBON_UV')
  image=net.createNode('mtlximage','ARTWORK');image.parm('file').set('$HIP/textures/ribbon_'+kind+'.png');image.parm('filecolorspace').set('srgb_texture');image.setNamedInput('texcoord',coord,0)
  alpha=net.createNode('mtlximage','ALPHA');alpha.parm('signature').set('color4');alpha.parm('file').set('$HIP/textures/ribbon_'+kind+'.png');alpha.parm('filecolorspace').set('raw');alpha.setNamedInput('texcoord',coord,0)
  extract=net.createNode('mtlxextract','CUTOUT');extract.parm('signature').set('color4');extract.parm('index').set(3);extract.setNamedInput('in',alpha,0)
  surface.setNamedInput('base_color',image,0);surface.setNamedInput('emission_color',image,0);surface.setNamedInput('opacity',extract,0);surface.parm('thin_walled').set(1);surface.parm('specular_roughness').set(.65);net.layoutChildren()
 mats=hou.node('/stage/fish_materials');start=mats.evalParm('materials')+1;mats.parm('materials').set(start+1)
 for i,kind in enumerate(('red','blue'),start):
  for key,value in [('matflag',True),('matnode','/mat/fish_art_'+kind),('matpath','/materials/fish_art_'+kind),('assign',True),('geopath','/fish/art'+kind+'_*')]:mats.parm(key+str(i)).set(value)
 node.setPosition(source.position()+hou.Vector2((2,-1)))

if __name__=='__main__':
 install(Path(hou.expandString('$HIP')))
 print('Ribbon artwork installed in the open scene. Save manually to retain it.')
