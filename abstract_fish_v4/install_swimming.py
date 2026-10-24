"""Adds time-driven swimming to an open v3 fish without loading or saving it."""
import hou

SWIM_CODE=r'''
import math
import hou
node=hou.pwd();geo=node.geometry();ctrl=hou.node('/stage/FISH_CONTROLS')
if ctrl.evalParm('swim_enable'):
    speed=ctrl.evalParm('swim_speed');amplitude=ctrl.evalParm('swim_strength')
    waves=ctrl.evalParm('swim_waves');head=ctrl.evalParm('swim_head_motion')
    tail=ctrl.evalParm('swim_tail_gain');falloff=ctrl.evalParm('swim_falloff')
    vertical=ctrl.evalParm('swim_vertical');phase=math.radians(ctrl.evalParm('swim_phase'))
    elapsed=hou.time()  # Frame 1 is time zero; speed is independent of scene FPS.
    length=hou.node('/obj/ABSTRACT_FISH').evalParm('bodylength')
    span=6.0*length
    def wave(x):
        u=max(0.,min(1.,(x+2.5)/span))
        q=max(0.,min(1.,(u-.16)/.84));smooth=q*q*(3.-2.*q)
        weight=head+(1.-head)*smooth**falloff
        tailboost=1+(tail-1)*max(0.,(u-.6)/.4)
        angle=2*math.pi*(waves*u-speed*elapsed)+phase
        return hou.Vector3((0,amplitude*weight*tailboost*math.sin(angle),amplitude*vertical*weight*tailboost*math.sin(angle+math.pi*.5))),weight
    def deform(pos):
        x,y,z=pos
        shift,weight=wave(x)
        eps=.001
        a=wave(x-eps)[0];b=wave(x+eps)[0]
        tangent=hou.Vector3((1,(b[1]-a[1])/(2*eps),(b[2]-a[2])/(2*eps))).normalized()
        side=(hou.Vector3((0,1,0))-tangent*tangent.dot(hou.Vector3((0,1,0)))).normalized()
        up=tangent.cross(side).normalized()
        return hou.Vector3((x,0,0))+shift+side*y+up*z,weight,tangent,side,up
    geo.addAttrib(hou.attribType.Point,'swim_weight',0.)
    geo.addAttrib(hou.attribType.Point,'swim_offset',(0.,0.,0.))
    for p in geo.points():
        old=p.position();new,weight,tangent,side,up=deform(old)
        p.setPosition(new);p.setAttribValue('swim_weight',float(weight));p.setAttribValue('swim_offset',tuple(new-old))
        if geo.findPointAttrib('guide_normal'):
            n=hou.Vector3(p.attribValue('guide_normal'));p.setAttribValue('guide_normal',tuple(tangent*n[0]+side*n[1]+up*n[2]))
    if geo.findPrimAttrib('attachment'):
        for prim in geo.prims():prim.setAttribValue('attachment',tuple(deform(hou.Vector3(prim.attribValue('attachment')))[0]))
'''

def install_swimming():
    obj=hou.node('/obj/ABSTRACT_FISH');control=hou.node('/stage/FISH_CONTROLS')
    if obj is None or control is None:raise RuntimeError('Open the v3 fish with Stage controls first')
    if obj.node('SWIM_DEFORM'):
        if obj.node('SWIM_DEFORM').userData('phoenix_swim')=='v4':return control
        raise RuntimeError('Existing SWIM_DEFORM is protected')
    group=control.parmTemplateGroup();folder=hou.FolderParmTemplate('swimming','Swimming Motion')
    folder.addParmTemplate(hou.ToggleParmTemplate('swim_enable','Enable Swimming',default_value=True))
    for key,label,default,lo,hi in [('swim_speed','Swim Speed (cycles / second)',.8,0,4),('swim_strength','Body Ripple Strength',.22,0,1),('swim_waves','Ripples Along Fish',1.25,.25,3),('swim_head_motion','Head Motion Fraction',.04,0,1),('swim_tail_gain','Tail Motion Multiplier',1.8,0,3),('swim_falloff','Head-to-Tail Falloff',1.2,.3,4),('swim_vertical','Vertical Ripple Amount',.2,0,1),('swim_phase','Swim Phase (degrees)',0,-360,360)]:
        folder.addParmTemplate(hou.FloatParmTemplate(key,label,1,default_value=(default,),min=lo,max=hi,min_is_strict=True,max_is_strict=True))
    group.insertBefore('wind_controls',folder);control.setParmTemplateGroup(group)
    def deform_node(name,source):
        n=obj.createNode('python',name);n.setInput(0,source);n.parm('python').set(SWIM_CODE);n.setUserData('phoenix_swim','v4');n.setColor(hou.Color((.15,.5,.8)));return n
    swim=deform_node('SWIM_DEFORM',obj.node('FINAL_MERGE'))
    normal=obj.createNode('normal','SWIM_NORMALS');normal.setInput(0,swim)
    guides=deform_node('SWIM_GUIDES',obj.node('ALL_GUIDE_CURVES'))
    switch=obj.node('PRESENTATION_VIEW');switch.setInput(0,normal);switch.setInput(2,normal)
    obj.node('WIREFRAME_LINES').setInput(0,swim)
    obj.node('GUIDE_CURVES_TUBES').setInput(0,guides)
    swim.setComment('Head-to-tail traveling body wave, driven by /stage/FISH_CONTROLS. Body, eyes, ribbons and guides share the same deformation.')
    normal.setPosition(swim.position()+hou.Vector2((0,-1)))
    obj.layoutChildren()
    control.setComment('FISH CONTROLS: Swimming Motion, wind, ribbon surfaces, body proportions and fins. Play the timeline to preview swimming.')
    control.setCurrent(True,clear_all_selected=True)
    hou.playbar.setFrameRange(1,120);hou.playbar.setPlaybackRange(1,120)
    return control

if __name__=='__main__':
    print('Swimming installed:',install_swimming().path())
