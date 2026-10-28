import hou
hou.hipFile.load('/home/amir/Documents/ChatGPT/Phoenix/abstract_fish/abstract_fish_build3_debug.hipnc',ignore_load_warnings=True)
for path in ['/stage/fish_render_settings','/stage/fish_side_camera','/stage/fish_render']:
 n=hou.node(path)
 for p in n.parms():
  if any(k in p.name().lower() for k in ['aspect','res','aperture','ortho']):
   try:print(path,p.name(),repr(p.eval()),'menu',p.menuItems() if p.parmTemplate().type()==hou.parmTemplateType.Menu else '',flush=True)
   except:pass
