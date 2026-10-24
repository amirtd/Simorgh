"""Install a visible, editable motion-path rig without loading or saving a scene."""
import hou
PATH_CODE = '''import hou, math
node=hou.pwd();geo=node.geometry();geo.clear()
points=[hou.node('/obj/FISH_PATH_POINT_%02d'%i).worldTransform().extractTranslates() for i in range(1,7)]
curve=geo.createPolygon();curve.setIsClosed(False)
for seg in range(len(points)-1):
 p0=points[max(0,seg-1)];p1=points[seg];p2=points[seg+1];p3=points[min(len(points)-1,seg+2)]
 for j in range(40):
  t=j/40.;pos=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
  point=geo.createPoint();point.setPosition(pos);curve.addVertex(point)
point=geo.createPoint();point.setPosition(points[-1]);curve.addVertex(point)
'''
MOVE_CODE = '''import hou,bisect
geo=hou.pwd().geometry();c=hou.node('/stage/FISH_CONTROLS')
matrix=hou.hmath.identityTransform()
if c.evalParm('path_enable'):
 points=[p.position() for p in hou.node('/obj/FISH_PATH/OUT_PATH').geometry().points()]
 distances=[0.]
 for a,b in zip(points,points[1:]):distances.append(distances[-1]+(b-a).length())
 target=max(0.,min(1.,c.evalParm('path_progress')))*distances[-1]
 i=max(0,min(len(points)-2,bisect.bisect_right(distances,target)-1))
 span=distances[i+1]-distances[i];f=(target-distances[i])/span if span>1e-9 else 0
 pos=points[i]*(1-f)+points[i+1]*f
 if c.evalParm('path_orient'):
  tangent=points[i+1]-points[i]
  if tangent.length()<1e-8:tangent=hou.Vector3((-1,0,0))
  x=-tangent.normalized();reference=hou.Vector3((0,0,1))
  if abs(x.dot(reference))>.98:reference=hou.Vector3((0,1,0))
  y=reference.cross(x).normalized();z=x.cross(y).normalized()
  matrix=hou.Matrix4((x[0],x[1],x[2],0,y[0],y[1],y[2],0,z[0],z[1],z[2],0,0,0,0,1))
 matrix=matrix*hou.hmath.buildTranslate(pos)
# Manual offset/rotation/scale is local to the fish, then carried along the path.
geo.transform(hou.node('/obj/FISH_MOTION_CTRL').worldTransform()*matrix)
'''
GUIDE_CODE = '''import hou,math
geo=hou.pwd().geometry();geo.clear()
if hou.node('/stage/FISH_CONTROLS').evalParm('path_show'):
 geo.merge(hou.node('/obj/FISH_PATH/OUT_PATH').geometry())
 for i in range(1,7):
  center=hou.node('/obj/FISH_PATH_POINT_%02d'%i).worldTransform().extractTranslates()
  for axis in range(3):
   line=geo.createPolygon();line.setIsClosed(True)
   for j in range(24):
    angle=2*math.pi*j/24.;v=[0.,0.,0.];v[(axis+1)%3]=.25*math.cos(angle);v[(axis+2)%3]=.25*math.sin(angle)
    p=geo.createPoint();p.setPosition(center+hou.Vector3(v));line.addVertex(p)
 geo.addAttrib(hou.attribType.Point,'Cd',(0.,.8,1.))
'''
def install_path_rig():
 obj=hou.node('/obj/ABSTRACT_FISH');stage=hou.node('/stage');c=stage.node('FISH_CONTROLS')
 if obj is None or c is None:raise RuntimeError('Open the swimming fish scene first')
 if hou.node('/obj/FISH_PATH'):raise RuntimeError('Existing path rig protected')
 group=c.parmTemplateGroup();folder=hou.FolderParmTemplate('motion_path','Motion Path Rig')
 for p in [hou.ToggleParmTemplate('path_enable','Follow Motion Path',True),hou.FloatParmTemplate('path_progress','Path Progress',1,default_value=(0.,),min=0,max=1,min_is_strict=True,max_is_strict=True),hou.ToggleParmTemplate('path_orient','Face Along Path',True),hou.ToggleParmTemplate('path_show','Show Visual Rig',True)]:folder.addParmTemplate(p)
 button=hou.ButtonParmTemplate('edit_path','Edit Visual Path Controls')
 button.setScriptCallback("import hou; nodes=[hou.node('/obj/FISH_PATH_POINT_%02d'%i) for i in range(1,7)]; pane=hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor); pane.setPwd(hou.node('/obj')) if pane else None; hou.clearAllSelected(); [n.setSelected(True) for n in nodes]; pane.homeToSelection() if pane else None")
 button.setScriptCallbackLanguage(hou.scriptLanguage.Python);folder.addParmTemplate(button)
 group.insertBefore(group.entries()[0].name(),folder);c.setParmTemplateGroup(group)
 root=hou.node('/obj')
 for i,pos in enumerate([(0,0,0),(-4,0,0),(-8,2,.5),(-12,4,1),(-16,2,1),(-20,0,0)],1):
  n=root.createNode('null','FISH_PATH_POINT_%02d'%i);n.parmTuple('t').set(pos);n.setColor(hou.Color((0,.8,1)));n.setComment('Move with viewport translate handle to shape the swim path.');n.setUserData('nodeshape','circle')
  if n.parm('geoscale'):n.parm('geoscale').set(.4)
 manual=root.createNode('null','FISH_MOTION_CTRL');manual.setColor(hou.Color((1,.65,.1)));manual.setComment('Animate local fish translation, rotation and scale. Applied before path placement.')
 path=root.createNode('geo','FISH_PATH');path.setColor(hou.Color((0,.8,1)))
 for n in path.children():n.destroy()
 code=path.createNode('python','PATH_FROM_HANDLES');code.parm('python').set(PATH_CODE)
 out=path.createNode('null','OUT_PATH');out.setInput(0,code);out.setDisplayFlag(True);out.setRenderFlag(True)
 guides=path.createNode('python','VISUAL_RIG');guides.parm('python').set(GUIDE_CODE)
 path.setDisplayFlag(True);path.layoutChildren()
 output=obj.node('OUT_FISH');upstream=output.input(0)
 move=obj.createNode('python','FOLLOW_MOTION_PATH');move.parm('python').set(MOVE_CODE);move.setInput(0,upstream);output.setInput(0,move);obj.layoutChildren()
 imp=stage.createNode('sopimport','fish_path_visual_rig');imp.parm('soppath').set(guides.path());imp.parm('primpath').set('/FishRig');imp.parm('pathprefix').set('/FishRig')
 # Import rig before the fish; USD guide purpose keeps it out of final renders.
 imp.setInput(0,c);guide=stage.createNode('pythonscript','rig_viewport_only');guide.setInput(0,imp)
 guide.parm('python').set("from pxr import UsdGeom\nstage=hou.pwd().editableStage()\np=stage.GetPrimAtPath('/FishRig')\nif p: UsdGeom.Imageable(p).CreatePurposeAttr().Set(UsdGeom.Tokens.guide)")
 stage.node('fish_geometry').setInput(0,guide)
 imp.setPosition(c.position()+hou.Vector2((0,-1.2)));guide.setPosition(c.position()+hou.Vector2((0,-2.4)))
 c.setPosition(c.position()+hou.Vector2((0,2)))
 for i in range(1,7):root.node('FISH_PATH_POINT_%02d'%i).setPosition(hou.Vector2((i*2,-4)))
 manual.setPosition(hou.Vector2((2,-1)));path.setPosition(hou.Vector2((5,-1)))
 c.setCurrent(True,clear_all_selected=True)
 return c
if __name__=='__main__':install_path_rig()
