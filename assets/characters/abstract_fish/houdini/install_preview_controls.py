"""Install preview performance switches in the open scene without loading/saving."""
import hou

def install():
 obj=hou.node('/obj/ABSTRACT_FISH');c=hou.node('/stage/FISH_CONTROLS')
 if obj is None or c is None:raise RuntimeError('Open the fish scene first')
 if c.parm('preview_fast'):return c
 systems=('HEAD_SURFACES','UPPER_RIBBONS','SIDE_RIBBONS','PECTORAL_FIN','PELVIC_FIN','ANAL_FIN','TAIL_UPPER','TAIL_MIDDLE','TAIL_LOWER')
 group=c.parmTemplateGroup();folder=hou.FolderParmTemplate('preview_performance','Preview Performance')
 for name,label,default in [('preview_fast','Fast Preview — Body Only',False),('preview_low','Low Resolution Geometry',False),('preview_ribbons','Ribbons On',True),('preview_effects','Effects On',True),('preview_wind','Wind On',True),('preview_flutter','Paper Flutter On',True),('preview_swim','Swimming Ripple On',True),('preview_textures','Image Texture On',True),('preview_offsets','Ribbon Mesh Offsets On',True)]:folder.addParmTemplate(hou.ToggleParmTemplate(name,label,default))
 for system in systems:folder.addParmTemplate(hou.ToggleParmTemplate('preview_'+system.lower(),system.replace('_',' ').title()+' On',True))
 group.insertBefore(group.entries()[0].name(),folder);c.setParmTemplateGroup(group)
 empty=obj.createNode('null','PREVIEW_EMPTY')
 def gate(source,name,expression):
  consumers=[(n,i) for n in source.outputs() for i,v in enumerate(n.inputs()) if v==source]
  switch=obj.createNode('switch',name);switch.setInput(0,empty);switch.setInput(1,source);switch.parm('input').setExpression(expression)
  for node,i in consumers:node.setInput(i,switch)
  return switch
 base='ch("/stage/FISH_CONTROLS/'
 def ch(n):return base+n+'")'
 for system in systems:
  expr=ch('preview_ribbons')+' && !'+ch('preview_fast')+' && '+ch('preview_'+system.lower())
  gate(obj.node(system+'_NORMALS'),'PREVIEW_'+system,expr)
  gate(obj.node(system+'_GUIDES'),'PREVIEW_'+system+'_GUIDES',expr)
 # Bypass costly UV and mesh-offset SOPs entirely when disabled.
 for name,control in [('PLANAR_TEXTURE_UV','preview_textures'),('INDIVIDUAL_RIBBON_OFFSETS','preview_offsets'),('INDIVIDUAL_GUIDE_OFFSETS','preview_offsets')]:
  source=obj.node(name)
  if not source:continue
  consumers=[(n,i) for n in source.outputs() for i,v in enumerate(n.inputs()) if v==source]
  switch=obj.createNode('switch','PREVIEW_'+name);switch.setInput(0,source.input(0));switch.setInput(1,source)
  switch.parm('input').setExpression(ch(control)+' && !'+ch('preview_fast'))
  for n,i in consumers:n.setInput(i,switch)
 for node in obj.children():
  if node.type().name()!='python':continue
  code=node.evalParm('python')
  if 'def create_ribbon(' in code:
   code=code.replace('def wind(t):','def wind(t):\n        if not paper.evalParm("preview_effects") or not paper.evalParm("preview_wind") or paper.evalParm("preview_fast"):return V((0,0,0))')
   code=code.replace('time=hou.time();','time=hou.time() if paper.evalParm("preview_flutter") else 0.;flutter=flutter if paper.evalParm("preview_flutter") else 0.;')
   code=code.replace('cps=processed;n=48;m=8','cps=processed;n=20 if paper.evalParm("preview_low") else 48;m=2 if paper.evalParm("preview_low") else 8')
   code=code.replace('n=84;m=40;rows=[]','low=hou.node("/stage/FISH_CONTROLS").evalParm("preview_low");n=32 if low else 84;m=16 if low else 40;rows=[]')
  if node.name() in ('SWIM_DEFORM','SWIM_GUIDES'):
   code=code.replace("if ctrl.evalParm('swim_enable'):","if ctrl.evalParm('swim_enable') and ctrl.evalParm('preview_effects') and ctrl.evalParm('preview_swim') and not ctrl.evalParm('preview_fast'):")
  node.parm('python').set(code)
 # Existing guide visibility remains under the user's Show Visual Rig switch.
 guide=hou.node('/stage/fish_path_visual_rig')
 if guide:
  gate_lop=hou.node('/stage').createNode('switch','PREVIEW_PATH_GUIDES');consumers=list(guide.outputs());gate_lop.setInput(0,guide.input(0));gate_lop.setInput(1,guide);gate_lop.parm('input').setExpression('!'+ch('preview_fast'))
  for n in consumers:
   for i,v in enumerate(n.inputs()):
    if v==guide:n.setInput(i,gate_lop)
 obj.layoutChildren();c.setCurrent(True,clear_all_selected=True)
 return c
if __name__=='__main__':install()
