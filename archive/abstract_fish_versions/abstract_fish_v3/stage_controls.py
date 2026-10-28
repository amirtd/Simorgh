"""Run in Houdini's Python Source Editor to add Stage controls to the open fish.
Does not load, save, or clear the open scene. Existing unsaved edits are retained.
"""
import hou

def install_stage_controls():
    obj=hou.node('/obj/ABSTRACT_FISH');stage=hou.node('/stage')
    if obj is None or stage is None:raise RuntimeError('Open the abstract fish scene first')
    force=obj.node('RIBBON_FORCE_CONTROLS');imp=stage.node('fish_geometry')
    if force is None or imp is None:raise RuntimeError('Fish control/import nodes missing')
    existing=stage.node('FISH_CONTROLS')
    if existing:
        if existing.userData('phoenix_controls')=='stage_v3':return existing
        raise RuntimeError('Existing FISH_CONTROLS is protected')
    control=stage.createNode('null','FISH_CONTROLS')
    control.setUserData('phoenix_controls','stage_v3')
    control.setColor(hou.Color((.18,.62,.8)))
    control.setComment('MASTER FISH CONTROLS: wind, flat mode, ribbon shape, body proportions and individual fin/tail systems. OBJ controls remain linked.')
    control.setUserData('nodegraph_showcomment','1')
    group=control.parmTemplateGroup();bindings=[]
    def folder(name,label,items):
        f=hou.FolderParmTemplate(name,label)
        for source,newname,label_override in items:
            template=source.parmTemplate().clone()
            template.setName(newname)
            if label_override:template.setLabel(label_override)
            f.addParmTemplate(template);bindings.append((source,newname))
        group.append(f)
    folder('wind_controls','Wind Force',[(force.parmTuple(n),n,None) for n in ('wind_strength','wind_direction','ripple','frequency','root_falloff','seed')])
    folder('surface_controls','Ribbon Surface',[(force.parmTuple(n),n,None) for n in ('flat_ribbons','ribbon_thickness','ribbon_curl','twist_strength')]+[(obj.parmTuple(n),n,None) for n in ('width','length','curvature','twist')])
    folder('body_fin_controls','Body and Fin Shape',[(obj.parmTuple(n),n,None) for n in ('tailspread','finspread','bodylength','bodythickness','colorvariation')])
    folder('presentation_controls','Presentation',[(obj.parmTuple('presentation'),'presentation',None)])
    for system in ('HEAD_SURFACES','UPPER_RIBBONS','SIDE_RIBBONS','PECTORAL_FIN','PELVIC_FIN','ANAL_FIN','TAIL_UPPER','TAIL_MIDDLE','TAIL_LOWER'):
        node=obj.node(system)
        folder(system.lower()+'_overrides',system.replace('_',' ').title(),[(node.parmTuple(n),system.lower()+'_'+n,None) for n in ('local_flat','local_thickness','local_curl','local_twist')])
    control.setParmTemplateGroup(group)
    # Resolve the existing object/force links before assigning the Stage master.
    # Keep current values and keyframes instead of resetting to template defaults.
    for source_tuple,name in bindings:
        dest_tuple=control.parmTuple(name)
        for source,dest in zip(source_tuple,dest_tuple):
            master=source.getReferencedParm()
            dest.setFromParm(master)
            master.deleteAllKeyframes()
            master.setExpression('ch("'+dest.path()+'")',hou.exprLanguage.Hscript)
    previous=imp.input(0)
    if previous:control.setInput(0,previous)
    imp.setInput(0,control)
    control.setPosition(imp.position()+hou.Vector2((0,2)))
    control.setCurrent(True,clear_all_selected=True)
    return control

if __name__=='__main__':
    node=install_stage_controls()
    print('Stage controls ready:',node.path())
