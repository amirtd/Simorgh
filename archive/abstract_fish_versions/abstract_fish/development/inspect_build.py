import hou
hou.hipFile.load('/home/amir/Documents/ChatGPT/Phoenix/abstract_fish/abstract_fish.hipnc',ignore_load_warnings=True)
for name in ['BODY_BASE','HEAD_SURFACES','EYES','OUT_FISH']:
 n=hou.node('/obj/ABSTRACT_FISH/'+name)
 try:n.cook(force=True)
 except hou.Error:pass
 print(name,n.errors(),flush=True)
for name in ['fish_side_camera','fish_render_settings']:
 n=hou.node('/stage/'+name)
 for p in n.parms():
  if any(k in p.name() for k in ['Aperture','ortho','resolution','projection']):
   try:print(p.name(),p.eval(),flush=True)
   except:pass
