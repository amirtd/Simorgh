"""Run in the open fish scene. Preserves current transforms and unsaved edits."""
import hou

def install():
 obj=hou.node('/obj/ABSTRACT_FISH');imp=hou.node('/stage/fish_geometry')
 if obj is None or imp is None:raise RuntimeError('Open the fish scene first')
 out=obj.node('OUT_STAGE_FISH')
 if out is None:
  bake=obj.createNode('python','OBJ_TRANSFORM_TO_STAGE')
  bake.parm('python').set("import hou\nnode=hou.pwd()\nnode.geometry().transform(node.parent().worldTransform())\n")
  bake.setInput(0,obj.node('OUT_FISH'))
  out=obj.createNode('null','OUT_STAGE_FISH');out.setInput(0,bake)
  bake.setPosition(obj.node('OUT_FISH').position()+hou.Vector2((2,-1)))
  out.setPosition(bake.position()+hou.Vector2((0,-1)))
  bake.setComment('Bake live OBJ world transform for Solaris only. OBJ viewport output remains OUT_FISH.')
 # Keep local OBJ output displayed; transformed output is used only by Solaris.
 obj.node('OUT_FISH').setDisplayFlag(True);obj.node('OUT_FISH').setRenderFlag(True)
 imp.parm('soppath').set(out.path())
 return out
if __name__=='__main__':
 install()
 print('Stage now follows the fish OBJ transform. Save your scene to keep the fix.')
