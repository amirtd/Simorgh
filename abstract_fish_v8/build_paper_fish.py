from pathlib import Path
import hou,json
r=Path(__file__).resolve().parent;dest=r/'abstract_fish.hipnc'
if dest.exists():raise FileExistsError(dest)
hou.hipFile.load(str(r.parent/'abstract_fish_v7/abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
c=hou.node('/stage/FISH_CONTROLS');obj=hou.node('/obj/ABSTRACT_FISH');group=c.parmTemplateGroup();f=hou.FolderParmTemplate('paper_controls','Paper Ribbons')
for name,label,default,maximum in [('paper_length','Paper Length',1.45,3),('paper_flex','Wind Flexibility',3.,8),('paper_flutter','Paper Flutter Amount',.12,1),('paper_flutter_speed','Flutter Speed',1.4,5)]:f.addParmTemplate(hou.FloatParmTemplate(name,label,1,default_value=(default,),min=0,max=maximum,min_is_strict=True))
f.addParmTemplate(hou.ToggleParmTemplate('paper_colors','Use Colorful Paper Palette',True));group.insertBefore(group.entries()[0].name(),f);c.setParmTemplateGroup(group)
# Modify each procedural ribbon generator and corresponding guide generator together.
count=0
for node in obj.children():
 if node.type().name()!='python' or node.name() in ('BODY_BASE','EYES'):continue
 code=node.evalParm('python')
 if 'def create_ribbon(' not in code:continue
 code=code.replace("g=geo or hou.pwd().geometry();ctl=controls or {}", "g=geo or hou.pwd().geometry();ctl=dict(controls or {});paper=hou.node('/stage/FISH_CONTROLS');ctl['length']=ctl.get('length',1)*paper.evalParm('paper_length');ctl['ribbon_thickness']=0;ctl['ribbon_curl']=0;ctl['flat_ribbons']=False")
 code=code.replace("return direction*(strength*t**falloff*(1+ripple*math.sin(t*frequency*2*math.pi+phase)))", "flex=paper.evalParm('paper_flex');flutter=paper.evalParm('paper_flutter');speed=paper.evalParm('paper_flutter_speed');time=hou.time();envelope=t**falloff\n        return direction*(strength*flex*envelope*(1+ripple*math.sin(t*frequency*2*math.pi+phase)))+V((0,math.sin(t*9-time*speed*2*math.pi+phase),.55*math.cos(t*11-time*speed*2*math.pi+phase)))*(abs(strength)*flex*flutter*envelope)")
 node.parm('python').set(code);count+=1
assert count==18,count
# Keep body texture; switch decorative pieces back to their colorful materials.
uv=obj.node('PLANAR_TEXTURE_UV');code=uv.evalParm('python').replace("if system!='EYES' and c.evalParm('texture_enable'):","if system!='EYES' and c.evalParm('texture_enable') and (system=='BODY_BASE' or not c.evalParm('paper_colors')):")
uv.parm('python').set(code)
c.parm('wind_strength').set(.14);c.parm('ripple').set(.4);c.parm('twist_strength').set(.65)
for i in range(1,9):
 surface=hou.node('/mat/fish_%02d/mtlxstandard_surface'%i)
 surface.parm('specular_roughness').set(.65)
 if surface.parm('thin_walled'):surface.parm('thin_walled').set(1)
# Validate that ribbons are genuine single sheets and preserve UVs, rig and offsets.
counts={}
for system in ('HEAD_SURFACES','UPPER_RIBBONS','SIDE_RIBBONS','PECTORAL_FIN','PELVIC_FIN','ANAL_FIN','TAIL_UPPER','TAIL_MIDDLE','TAIL_LOWER'):
 g=obj.node(system).geometry();assert not obj.node(system).errors();counts[system]=len(g.prims());assert all(p.attribValue('ribbon_uv')[2]==1 for p in g.points())
assert obj.node('OUT_FISH').geometry().findPointAttrib('uv')
hou.setFrame(1);a=obj.node('UPPER_RIBBONS').geometry().pointFloatAttribValues('P');hou.setFrame(7);b=obj.node('UPPER_RIBBONS').geometry().pointFloatAttribValues('P');assert a!=b
hou.setFrame(1);assert hou.node('/stage/fish_render_settings').stage()
c.setCurrent(True,clear_all_selected=True);hou.hipFile.save(str(dest))
(r/'paper_validation.json').write_text(json.dumps({'single_surface_ribbons':True,'animated_wind_flutter':True,'length_multiplier':1.45,'wind_flexibility':3,'polygon_counts':counts},indent=2))
hou.node('/stage/fish_render_settings').parm('samplesperpixel').set(8);rop=hou.node('/stage/fish_render');rop.parm('res_user1').set(720);rop.parm('res_user2').set(405);rop.parm('outputimage').set(str(r/'paper_preview.png'));rop.render()
print('PAPER_READY_RENDERED',flush=True)
