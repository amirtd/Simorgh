import hou
UV_CODE='''import hou,math
geo=hou.pwd().geometry();c=hou.node('/stage/FISH_CONTROLS')
uv=geo.findPointAttrib('uv') or geo.addAttrib(hou.attribType.Point,'uv',(0.,0.,0.))
axes=[(0,2),(0,1),(1,2)][c.evalParm('texture_plane')];groups={}
for prim in geo.prims():groups.setdefault(prim.attribValue('name'),[]).append(prim)
angle=math.radians(c.evalParm('texture_rotation'));co=math.cos(angle);si=math.sin(angle)
for name,prims in groups.items():
 points={p.number():p for prim in prims for p in prim.points()};positions={i:p.attribValue('rest') for i,p in points.items()}
 lo=[min(v[a] for v in positions.values()) for a in axes];hi=[max(v[a] for v in positions.values()) for a in axes]
 for i,p in points.items():
  v=positions[i];u=(v[axes[0]]-lo[0])/max(hi[0]-lo[0],1e-6)-.5;w=(v[axes[1]]-lo[1])/max(hi[1]-lo[1],1e-6)-.5
  p.setAttribValue(uv,((u*co-w*si)*c.evalParm('texture_tileu')+.5+c.evalParm('texture_offsetu'),(u*si+w*co)*c.evalParm('texture_tilev')+.5+c.evalParm('texture_offsetv'),0.))
 for prim in prims:
  system=prim.attribValue('system')
  if system!='EYES' and c.evalParm('texture_enable'):
   body=system=='BODY_BASE';prefix='texbody_' if body else 'texparts_'
   prim.setAttribValue('name',prefix+name);prim.setAttribValue('shop_materialpath','/mat/fish_texture_body' if body else '/mat/fish_texture_parts')
'''
def install_texture(texture_path):
 obj=hou.node('/obj/ABSTRACT_FISH');c=hou.node('/stage/FISH_CONTROLS')
 if obj.node('PLANAR_TEXTURE_UV'):raise RuntimeError('Existing texture setup protected')
 group=c.parmTemplateGroup();f=hou.FolderParmTemplate('texture_controls','Texture and Color')
 file=hou.StringParmTemplate('texture_file','Texture Image',1,default_value=(texture_path,),string_type=hou.stringParmType.FileReference)
 f.addParmTemplate(hou.ToggleParmTemplate('texture_enable','Enable Image Texture',True));f.addParmTemplate(file)
 f.addParmTemplate(hou.MenuParmTemplate('texture_plane','Planar UV Plane',['xz','xy','yz'],['XZ — Side','XY — Top','YZ — Front']))
 for name,label,default in [('tileu','UV Tile U',1.),('tilev','UV Tile V',1.),('offsetu','UV Offset U',0.),('offsetv','UV Offset V',0.),('rotation','UV Rotation',0.)]:f.addParmTemplate(hou.FloatParmTemplate('texture_'+name,label,1,default_value=(default,)))
 for name,label,default in [('body','Body Color',(1.,1.,1.)),('parts','Other Parts — Dark Blue Tint',(.08,.20,.48))]:
  f.addParmTemplate(hou.FloatParmTemplate('texture_'+name+'_color',label,3,default_value=default,naming_scheme=hou.parmNamingScheme.RGBA,look=hou.parmLook.ColorSquare))
  f.addParmTemplate(hou.FloatParmTemplate('texture_'+name+'_tint','%s Tint Strength'%('Body' if name=='body' else 'Other Parts'),1,default_value=(1.,),min=0,max=1,min_is_strict=True,max_is_strict=True))
  f.addParmTemplate(hou.FloatParmTemplate('texture_'+name+'_brightness','%s Brightness'%('Body' if name=='body' else 'Other Parts'),1,default_value=(1.,),min=0,max=3,min_is_strict=True))
 group.insertBefore(group.entries()[0].name(),f);c.setParmTemplateGroup(group)
 merge=obj.node('FINAL_MERGE');consumers=[(n,idx) for n in merge.outputs() for idx,inp in enumerate(n.inputs()) if inp==merge]
 uv=obj.createNode('python','PLANAR_TEXTURE_UV');uv.parm('python').set(UV_CODE);uv.setInput(0,merge)
 for n,idx in consumers:n.setInput(idx,uv)
 for part in ('body','parts'):
  net=hou.node('/mat/fish_04').copyTo(hou.node('/mat'));net.setName('fish_texture_'+part,unique_name=False)
  surface=net.node('mtlxstandard_surface');image=net.createNode('mtlximage','PATTERN_IMAGE');image.parm('file').setExpression('chs("/stage/FISH_CONTROLS/texture_file")',hou.exprLanguage.Hscript)
  image.parm('filecolorspace').set('srgb_texture')
  coord=net.createNode('mtlxtexcoord','PLANAR_UV');image.setNamedInput('texcoord',coord,0)
  tint=net.createNode('mtlxmultiply','COLOR_TINT');tint.parm('signature').set('color3');tint.setNamedInput('in1',image,0)
  for comp,parm in zip('rgb',tint.parmTuple('in2_color3')):
   base='/stage/FISH_CONTROLS/texture_'+part
   parm.setExpression('(1-ch("'+base+'_tint")+ch("'+base+'_tint")*ch("'+base+'_color'+comp+'"))*ch("'+base+'_brightness")')
  surface.setNamedInput('base_color',tint,0);surface.setNamedInput('emission_color',tint,0);net.layoutChildren()
 mats=hou.node('/stage/fish_materials');mats.parm('materials').set(10)
 for i,part in [(9,'body'),(10,'parts')]:
  for key,value in [('matflag',True),('matnode','/mat/fish_texture_'+part),('matpath','/materials/fish_texture_'+part),('assign',True),('geopath','/fish/tex'+part+'_*')]:mats.parm(key+str(i)).set(value)
 c.parm('presentation').set(2);c.setCurrent(True,clear_all_selected=True);obj.layoutChildren()
 return c
