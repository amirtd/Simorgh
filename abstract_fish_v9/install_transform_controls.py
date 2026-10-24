"""Expose the current fish OBJ location and rotation on the Stage master.
Run in an open scene; preserves existing values, animation and unsaved edits.
"""
import hou

def install():
 obj=hou.node('/obj/ABSTRACT_FISH');c=hou.node('/stage/FISH_CONTROLS')
 if obj is None or c is None:raise RuntimeError('Open the fish scene first')
 group=c.parmTemplateGroup()
 if group.find('fish_location') is None:
  f=hou.FolderParmTemplate('fish_transform','Fish Location and Rotation')
  f.addParmTemplate(hou.FloatParmTemplate('fish_location','Location',3,default_value=tuple(obj.parmTuple('t').eval()),naming_scheme=hou.parmNamingScheme.XYZW))
  f.addParmTemplate(hou.FloatParmTemplate('fish_rotation','Rotation',3,default_value=tuple(obj.parmTuple('r').eval()),naming_scheme=hou.parmNamingScheme.XYZW))
  group.insertBefore(group.entries()[0].name(),f);c.setParmTemplateGroup(group)
  for source,dest in [('t','fish_location'),('r','fish_rotation')]:
   for src,dst in zip(obj.parmTuple(source),c.parmTuple(dest)):
    # Copy animation before linking the OBJ parameter to its Stage master.
    dst.setFromParm(src)
    src.deleteAllKeyframes();src.setExpression('ch("'+dst.path()+'")',hou.exprLanguage.Hscript)
 # Ensure Stage receives the live object transform even on an older open scene.
 out=obj.node('OUT_STAGE_FISH')
 if out is None:
  bake=obj.createNode('python','OBJ_TRANSFORM_TO_STAGE');bake.parm('python').set("import hou\nnode=hou.pwd()\nnode.geometry().transform(node.parent().worldTransform())\n");bake.setInput(0,obj.node('OUT_FISH'))
  out=obj.createNode('null','OUT_STAGE_FISH');out.setInput(0,bake)
 hou.node('/stage/fish_geometry').parm('soppath').set(out.path())
 c.setCurrent(True,clear_all_selected=True)
 return c
if __name__=='__main__':
 install();print('Fish Location and Rotation controls are ready on /stage/FISH_CONTROLS.')
