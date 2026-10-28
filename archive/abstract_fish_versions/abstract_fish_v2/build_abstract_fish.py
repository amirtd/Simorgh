"""Houdini 22 abstract ribbon fish builder. Run with hython; see README."""
import argparse,json,math,sys
from pathlib import Path
import hou
# BEGIN_RIBBON_RUNTIME
"""Self-contained geometry runtime embedded in every Python SOP by the builder."""
import math,json
import hou
V=hou.Vector3
COLORS=['C72D38','EF745F','E9A64B','F1E3C8','3E9FAD','A5CBD4','236A76','D66B39']

def linear_color(mid, variation=0, seed=0):
    rgb=[int(COLORS[mid-1][i:i+2],16)/255 for i in (0,2,4)]
    rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    factor=1+variation*.15*math.sin(seed*2.39)
    return tuple(min(1,max(0,v*factor)) for v in rgb)

def interp(values,t):
    if isinstance(values,(float,int)):return values
    u=max(0,min(1,t))*(len(values)-1);i=min(int(u),len(values)-2);f=u-i
    return values[i]*(1-f)+values[i+1]*f

def curve(cps,t):
    u=max(0,min(1,t))*(len(cps)-1);i=min(int(u),len(cps)-2);f=u-i
    p0=V(cps[max(0,i-1)]);p1=V(cps[i]);p2=V(cps[i+1]);p3=V(cps[min(len(cps)-1,i+2)])
    return .5*((2*p1)+(-p0+p2)*f+(2*p0-5*p1+4*p2-p3)*f*f+(-p0+3*p1-3*p2+p3)*f*f*f)

def attrs(g):
    for n,d in [('name',''),('shop_materialpath',''),('system',''),('control_points','')]:g.addAttrib(hou.attribType.Prim,n,d)
    g.addAttrib(hou.attribType.Prim,'material_id',0)
    g.addAttrib(hou.attribType.Prim,'attachment',(0.,0.,0.))
    g.addAttrib(hou.attribType.Point,'Cd',(1.,1.,1.))
    g.addAttrib(hou.attribType.Point,'ribbon_uv',(0.,0.,0.))
    g.addAttrib(hou.attribType.Point,'rest',(0.,0.,0.))
    g.addAttrib(hou.attribType.Point,'width',0.)
    g.addAttrib(hou.attribType.Point,'twist',0.)
    g.addAttrib(hou.attribType.Point,'guide_normal',(0.,1.,0.))

def metadata(prim,name,mid,system,cps):
    prim.setAttribValue('name','m%02d_%s'%(mid,name));prim.setAttribValue('shop_materialpath','/mat/fish_%02d'%mid)
    prim.setAttribValue('system',system);prim.setAttribValue('material_id',mid)
    prim.setAttribValue('attachment',tuple(cps[0]));prim.setAttribValue('control_points',json.dumps(cps))

def point(g,pos,mid,uv=(0,0,0),width=0,variation=0,seed=0):
    p=g.createPoint();p.setPosition(pos);p.setAttribValue('rest',tuple(pos));p.setAttribValue('Cd',linear_color(mid,variation,seed));p.setAttribValue('ribbon_uv',tuple(float(x) for x in uv));p.setAttribValue('width',float(width));return p

def face(g,points,name,mid,system,cps):
    f=g.createPolygon()
    for p in points:f.addVertex(p)
    metadata(f,name,mid,system,cps)
    group=g.findPrimGroup(name) or g.createPrimGroup(name);group.add(f)
    return f

def body_radius(x):
    knots=[(-2.5,.025),(-2.3,.37),(-1.85,.63),(-1.25,.76),(-.3,.73),(.45,.48),(.95,.22),(1.2,.07)]
    for i in range(len(knots)-1):
        a,ra=knots[i];b,rb=knots[i+1]
        if x<=b:
            t=max(0,(x-a)/(b-a));t=t*t*(3-2*t);return ra*(1-t)+rb*t
    return .07

def spine(x):return .045*math.sin((x+2.5)*1.4)

def project_side(x,z,offset):
    radius=body_radius(x)
    return .325*math.sqrt(max(.02,1-((z-spine(x))/max(.1,radius))**2))*min(1,radius/.55)+offset

def create_ribbon(name,control_points,width_profile,thickness,twist,material_id,depth_offset,geo=None,system='ribbon',controls=None,guides=False,edge_curl=.05,conform=False,surface_normal=(0,1,0)):
    g=geo or hou.pwd().geometry();ctl=controls or {}
    flat=bool(ctl.get('flat_ribbons',0))
    thickness_scale=0 if flat else ctl.get('ribbon_thickness',1)
    curl_scale=0 if flat else ctl.get('ribbon_curl',1)
    twist_scale=0 if flat else ctl.get('twist_strength',1)
    force_node=hou.node('/obj/ABSTRACT_FISH/RIBBON_FORCE_CONTROLS')
    strength=force_node.evalParm('wind_strength') if force_node else 0.
    direction=V(force_node.parmTuple('wind_direction').eval()) if force_node else V((0,1,0))
    if direction.length()>1e-8:direction=direction.normalized()
    ripple=force_node.evalParm('ripple') if force_node else 0.
    frequency=force_node.evalParm('frequency') if force_node else 1.
    seed=force_node.evalParm('seed') if force_node else 0.
    falloff=force_node.evalParm('root_falloff') if force_node else 2.
    phase=sum(map(ord,name))*.173+seed
    def wind(t):
        return direction*(strength*t**falloff*(1+ripple*math.sin(t*frequency*2*math.pi+phase)))
    cps=[tuple(p) for p in control_points];root=V(cps[0]);processed=[]
    for p in cps:
        p=V(p);p=root+(p-root)*ctl.get('length',1)
        if system.startswith('TAIL'):p[2]=root[2]+(p[2]-root[2])*ctl.get('tailspread',1)
        if 'FIN' in system:p[2]=root[2]+(p[2]-root[2])*ctl.get('finspread',1)
        p[0]=-2.5+(p[0]+2.5)*ctl.get('bodylength',1)
        processed.append(tuple(p))
    cps=processed;n=48;m=8
    centers=[];widths=[];sides=[];normals=[]
    for i in range(n):
        t=i/(n-1);c=curve(cps,t)
        base=V(cps[0])*(1-t)+V(cps[-1])*t
        c=base+(c-base)*ctl.get('curvature',1)
        c[1]*=ctl.get('bodythickness',1)
        if conform:c[1]=project_side(c[0],c[2],depth_offset)*ctl.get('bodythickness',1)
        else:
            c[1]+=depth_offset
            blend=min(1,t*5);blend=blend*blend*(3-2*blend)
            anchor=.025 if system.startswith('TAIL') else project_side(cps[0][0],cps[0][2],-.004)*ctl.get('bodythickness',1)
            c[1]=anchor*(1-blend)+c[1]*blend
        c+=wind(t)
        tangent=(curve(cps,min(1,t+.001))+wind(min(1,t+.001))-curve(cps,max(0,t-.001))-wind(max(0,t-.001))).normalized()
        side=V(surface_normal).cross(tangent).normalized()
        normal=tangent.cross(side).normalized()
        theta=math.radians((interp(twist,t)+ctl.get('twist',0)*math.sin(math.pi*t))*twist_scale)
        side2=side*math.cos(theta)+normal*math.sin(theta)
        normal2=tangent.cross(side2).normalized()
        width=max(.004,interp(width_profile,t)*ctl.get('width',1))
        centers.append(c);widths.append(width);sides.append(side2);normals.append(normal2)
    cps_meta=list(cps);cps_meta[0]=tuple(centers[0])
    if guides:
        prim=g.createPolygon(is_closed=False)
        for i,c in enumerate(centers):
            pt=point(g,c,3,(i/(n-1),.5,0),widths[i]);pt.setAttribValue('twist',float((interp(twist,i/(n-1))+ctl.get('twist',0)*math.sin(math.pi*i/(n-1)))*twist_scale));pt.setAttribValue('guide_normal',tuple(normals[i]));prim.addVertex(pt)
        metadata(prim,name,material_id,system,cps_meta)
        return
    grids=[]
    for shell in ((1,) if thickness_scale==0 else (1,-1)):
        rows=[]
        for i,c in enumerate(centers):
            t=i/(n-1);row=[]
            thick=thickness*thickness_scale*(.38+.62*math.sin(math.pi*t)**.7)
            for j in range(m+1):
                v=j/m*2-1
                pos=c+sides[i]*(v*widths[i]*.5)+normals[i]*(curl_scale*(.055*(1-v*v)*math.sin(math.pi*t)+edge_curl*v*v*math.sin(math.pi*t)*math.sin(2*math.pi*t))+shell*thick*.5)
                row.append(point(g,pos,material_id,(t,j/m,shell),widths[i],ctl.get('colorvariation',0),sum(map(ord,name))))
            rows.append(row)
        grids.append(rows)
    if thickness_scale==0:
        top=grids[0]
        for i in range(n-1):
            for j in range(m):face(g,[top[i][j],top[i+1][j],top[i+1][j+1],top[i][j+1]],name,material_id,system,cps_meta)
        return
    top,bottom=grids
    for i in range(n-1):
        for j in range(m):
            face(g,[top[i][j],top[i+1][j],top[i+1][j+1],top[i][j+1]],name,material_id,system,cps_meta)
            face(g,[bottom[i][j+1],bottom[i+1][j+1],bottom[i+1][j],bottom[i][j]],name,material_id,system,cps_meta)
        face(g,[bottom[i][0],bottom[i+1][0],top[i+1][0],top[i][0]],name,material_id,system,cps_meta)
        face(g,[top[i][-1],top[i+1][-1],bottom[i+1][-1],bottom[i][-1]],name,material_id,system,cps_meta)
    for j in range(m):
        face(g,[top[0][j+1],bottom[0][j+1],bottom[0][j],top[0][j]],name,material_id,system,cps_meta)
        face(g,[top[-1][j],bottom[-1][j],bottom[-1][j+1],top[-1][j+1]],name,material_id,system,cps_meta)

def build_body(g,ctl):
    n=84;m=40;rows=[]
    for i in range(n):
        t=i/(n-1);x=-2.5+3.7*t;r=body_radius(x);row=[]
        for j in range(m):
            a=2*math.pi*j/m;pos=V((-2.5+(x+2.5)*ctl['bodylength'],.325*min(1,r/.55)*math.sin(a)*ctl['bodythickness'],spine(x)+r*math.cos(a)))
            row.append(point(g,pos,4,(t,j/m,0)))
        rows.append(row)
    cps=[(-2.5,0,.05),(1.2,0,0)]
    for i in range(n-1):
        for j in range(m):face(g,[rows[i][j],rows[i+1][j],rows[i+1][(j+1)%m],rows[i][(j+1)%m]],'BODY_BASE',4,'BODY_BASE',cps)
    face(g,rows[0],'BODY_BASE',4,'BODY_BASE',cps);face(g,list(reversed(rows[-1])),'BODY_BASE',4,'BODY_BASE',cps)

def sphere(g,center,radii,name,mid):
    obj=hou.node('/obj/ABSTRACT_FISH');length=obj.evalParm('bodylength');depth=obj.evalParm('bodythickness')
    center=(-2.5+(center[0]+2.5)*length,center[1]*depth,center[2]);radii=(radii[0]*length,radii[1]*depth,radii[2])
    n=12;m=24;rows=[]
    for i in range(1,n):
        phi=math.pi*i/n
        rows.append([point(g,V(center)+V((radii[0]*math.sin(phi)*math.cos(2*math.pi*j/m),radii[1]*math.cos(phi),radii[2]*math.sin(phi)*math.sin(2*math.pi*j/m))),mid) for j in range(m)])
    north=point(g,V(center)+V((0,radii[1],0)),mid);south=point(g,V(center)-V((0,radii[1],0)),mid)
    cps=[center,center]
    for j in range(m):
        k=(j+1)%m
        face(g,[north,rows[0][k],rows[0][j]],name,mid,'EYES',cps)
        face(g,[south,rows[-1][j],rows[-1][k]],name,mid,'EYES',cps)
        for i in range(len(rows)-1):face(g,[rows[i][j],rows[i][k],rows[i+1][k],rows[i+1][j]],name,mid,'EYES',cps)

def execute(system,specs,guides=False):
    g=hou.pwd().geometry();attrs(g)
    obj=hou.node('/obj/ABSTRACT_FISH')
    ctl={k:obj.evalParm(k) for k in ('width','length','curvature','twist','tailspread','finspread','bodylength','bodythickness','colorvariation','flat_ribbons','ribbon_thickness','ribbon_curl','twist_strength')}
    local=obj.node(system)
    if local and local.parm('local_thickness'):
        ctl['flat_ribbons']=ctl['flat_ribbons'] or local.evalParm('local_flat')
        for key,parm in [('ribbon_thickness','local_thickness'),('ribbon_curl','local_curl'),('twist_strength','local_twist')]:ctl[key]*=local.evalParm(parm)
    if system=='BODY_BASE':build_body(g,ctl)
    elif system=='EYES':
        for sign in (1,-1):
            sphere(g,(-2.15,sign*.295,.25),(.105,.042,.105),'EYE_GOLD_'+('FRONT' if sign>0 else 'BACK'),3)
            sphere(g,(-2.17,sign*.332,.25),(.054,.025,.062),'EYE_PUPIL_'+('FRONT' if sign>0 else 'BACK'),7)
            sphere(g,(-2.19,sign*.355,.276),(.015,.01,.015),'EYE_GLINT_'+('FRONT' if sign>0 else 'BACK'),4)
    else:
        for d in specs:create_ribbon(geo=g,system=system,controls=ctl,guides=guides,**d)

# END_RIBBON_RUNTIME
HERE=Path(__file__).resolve().parent
SYSTEMS={k:[] for k in ('HEAD_SURFACES','UPPER_RIBBONS','SIDE_RIBBONS','PECTORAL_FIN','PELVIC_FIN','ANAL_FIN','TAIL_UPPER','TAIL_MIDDLE','TAIL_LOWER')}

def ribbon(system,name,xz,width,mid,depth=.02,y=.18,twist=(0,12,-8,0),conform=False):
    SYSTEMS[system].append(dict(name=name,control_points=[(x,y,z) for x,z in xz],width_profile=[.018,width*.75,width,width*.62,.006],thickness=.018,twist=list(twist),material_id=mid,depth_offset=depth,edge_curl=.045,conform=conform))

# Six overlapping head plates. The pupil at (-2.15,+Y,.25) remains uncovered.
ribbon('HEAD_SURFACES','H01',[(-2.48,.14),(-2.28,.48),(-1.95,.57),(-1.48,.48),(-1.12,.38)],.25,1,.035,conform=True)
ribbon('HEAD_SURFACES','H02',[(-2.02,.20),(-1.8,.19),(-1.5,.04),(-1.24,-.23)],.29,5,.065,conform=True)
ribbon('HEAD_SURFACES','H03',[(-2.48,-.08),(-2.16,-.24),(-1.8,-.42),(-1.22,-.42)],.25,4,.045,conform=True)
ribbon('HEAD_SURFACES','H04',[(-1.5,.45),(-1.32,.22),(-1.26,-.05),(-1.25,-.45)],.19,8,.095,conform=True)
ribbon('HEAD_SURFACES','H05',[(-1.9,.45),(-1.62,.71),(-1.19,.84),(-.9,.9)],.19,3,.08,y=.25)
ribbon('HEAD_SURFACES','H06',[(-2.48,-.1),(-2.37,-.29),(-2.05,-.36),(-1.78,-.39)],.14,2,.06,conform=True)
# Dorsal feathers emerge from meaningful locations along the back.
upper=[('U01',[(-1.3,.48),(-.8,.94),(-.2,1.18),(.68,.89)],.30,1),('U02',[(-1.05,.63),(-.5,1.18),(.23,1.32),(1.22,.73)],.27,2),('U03',[(-.35,.53),(.19,1.13),(.85,1.37),(1.72,1.0)],.27,3),('U04',[(-1.18,.38),(-.38,.63),(.58,.69),(1.45,.37)],.25,4),('U05',[(.67,.22),(1.02,.81),(1.57,1.14),(1.7,.88)],.22,5),('U06',[(-.78,.57),(-.2,.98),(.52,1.08),(1.34,.82)],.21,6),('U07',[(-.22,.57),(.38,.87),(1.04,1.22),(1.76,1.08)],.13,1),('U08',[(.5,.29),(1.11,.66),(1.62,.59),(1.82,.88)],.13,4)]
for i,(name,cps,width,mid) in enumerate(upper):ribbon('UPPER_RIBBONS',name,cps,width,mid,.02,y=.12+i*.022)
side=[('S01',[(-1.3,.38),(-.92,.53),(-.4,.28),(.28,-.05),(1.05,.1)],.34,1),('S02',[(-1.3,.37),(-.92,.23),(-.4,-.26),(.3,-.49),(1.18,-.04)],.39,4),('S03',[(-1.22,.08),(-.8,.08),(-.25,-.08),(.53,-.19),(1.3,.03)],.26,5),('S04',[(-1.24,-.18),(-.73,-.43),(-.03,-.53),(.65,-.31),(1.08,-.06)],.29,2),('S05',[(-.6,.43),(-.12,.23),(.42,-.17),(.97,.05)],.26,3),('S06',[(-.8,-.34),(-.28,-.55),(.4,-.4),(1.44,0)],.21,6)]
for i,(name,cps,width,mid) in enumerate(side):ribbon('SIDE_RIBBONS',name,cps,width,mid,.05+i*.018,conform=True)
for i,mid in enumerate((5,4,2,3)):
    ribbon('PECTORAL_FIN','F01_%02d'%(i+1),[(-1.3+i*.035,-.2),(-1.11+i*.08,-.52),(-.76+i*.11,-.9),(-.48+i*.08,-1.04+i*.09)],.23-i*.024,mid,.02,y=.43+i*.018)
for i,mid in enumerate((2,4,5)):
    ribbon('PELVIC_FIN','F02_%02d'%(i+1),[(-.6+i*.035,-.45),(-.44+i*.1,-.84),(-.05+i*.14,-1.18),(.3+i*.11,-1.08+i*.12)],.23-i*.027,mid,.01,y=.22+i*.03)
for i,mid in enumerate((3,1,4)):
    ribbon('ANAL_FIN','F03_%02d'%(i+1),[(.5+i*.025,-.3),(.8+i*.06,-.58),(1.35+i*.05,-.91),(1.8-i*.14,-.85+i*.12)],.21-i*.025,mid,.02,y=.14+i*.035)
for i,mid in enumerate((1,8,4,3)):
    ribbon('TAIL_UPPER','T%02d'%(i+1),[(1.16,.035),(1.53,.34+i*.07),(2.13,1.02+i*.13),(2.85+i*.16,1.42-i*.13),(3.35-i*.12,.94-i*.08)],.34-i*.029,mid,.01,y=.06+i*.035,twist=(0,-15,18,32,-10))
for i,mid in enumerate((5,6,4,2)):
    ribbon('TAIL_MIDDLE','T%02d'%(i+5),[(1.17,.01-i*.015),(1.72,.18-i*.16),(2.37,.38-i*.2),(2.99,.05-i*.13),(3.5-i*.12,.22-i*.16)],.25-i*.023,mid,.015,y=.16+i*.025,twist=(0,8,-20,14,0))
for i,mid in enumerate((1,3,5,4)):
    ribbon('TAIL_LOWER','T%02d'%(i+9),[(1.16,-.035),(1.57,-.35-i*.035),(2.16,-1.02-i*.1),(2.93+i*.12,-1.33+i*.10),(3.34-i*.12,-.85+i*.12)],.32-i*.026,mid,.015,y=.06+i*.04,twist=(0,16,-12,-28,8))


def setp(n,k,v):
    p=n.parm(k)
    if p is None:raise RuntimeError('Missing parameter '+n.path()+'/'+k)
    p.set(v)

def look_rotation(pos,target):
    # Camera local -Z looks toward target; local +Y points toward world +Z.
    backward=(hou.Vector3(pos)-hou.Vector3(target)).normalized()
    right=hou.Vector3((0,0,1)).cross(backward).normalized()
    up=backward.cross(right).normalized()
    return hou.Matrix3(tuple(right)+tuple(up)+tuple(backward)).extractRotates()

def python_sop(parent,name,code):
    n=parent.createNode('python',name);setp(n,'python',code);return n

def build(output):
    if hou.applicationVersion()[0]!=22:raise RuntimeError('Requires Houdini 22')
    if output.exists():raise FileExistsError('Refusing to overwrite '+str(output))
    if hou.isUIAvailable() and hou.hipFile.hasUnsavedChanges():raise RuntimeError('Run in a fresh hython session; existing unsaved scenes are protected')
    if hou.node('/obj/ABSTRACT_FISH'):raise RuntimeError('Existing ABSTRACT_FISH is protected')
    runtime=Path(__file__).read_text().split('# BEGIN_RIBBON_RUNTIME\n',1)[1].split('# END_RIBBON_RUNTIME',1)[0]
    obj=hou.node('/obj').createNode('geo','ABSTRACT_FISH')
    for n in obj.children():n.destroy()
    ptg=obj.parmTemplateGroup();folder=hou.FolderParmTemplate('fish_controls','Ribbon Fish Controls')
    for key,label,value,lo,hi in [('ribbon_thickness','Ribbon Thickness',1,0,3),('ribbon_curl','Ribbon Curl',1,0,2),('twist_strength','Ribbon Twist Strength',1,0,2),('width','Ribbon Width Multiplier',1,.25,2),('length','Ribbon Length Multiplier',1,.5,1.5),('curvature','Ribbon Curvature',1,.2,1.8),('twist','Additional Ribbon Twist (degrees)',0,-60,60),('tailspread','Tail Spread',1,.4,1.5),('finspread','Fin Spread',1,.4,1.5),('bodylength','Body Length Multiplier',1,.7,1.3),('bodythickness','Body Thickness Multiplier',1,.5,1.8),('colorvariation','Color Variation',0,0,1)]:
        folder.addParmTemplate(hou.FloatParmTemplate(key,label,1,default_value=(value,),min=lo,max=hi,min_is_strict=True,max_is_strict=True))
    flat=hou.ToggleParmTemplate('flat_ribbons','Flat Ribbons',default_value=False);flat.setHelp('Makes ribbons zero-thickness open surfaces, removes cross-section curl and authored twist; flowing guide paths remain.');folder.setParmTemplates((flat,)+folder.parmTemplates())
    ptg.append(folder);obj.setParmTemplateGroup(ptg)
    force=obj.createNode('null','RIBBON_FORCE_CONTROLS')
    force.setColor(hou.Color((.2,.55,.8)));force.setComment('Wind-style static ribbon deformation. Strength is a displacement in scene units, not a physical Newton force. Roots stay pinned. Select this node to edit wind strength, direction and ripple.')
    fg=force.parmTemplateGroup();ff=hou.FolderParmTemplate('wind','Wind Force Controls')
    for key,label,default,lo,hi in [('wind_strength','Wind Force / Deflection',0,0,3),('ripple','Ripple Amount',.2,0,1),('frequency','Ripple Frequency',1,0,6),('root_falloff','Root Pin Falloff',2,1,6),('seed','Ripple Seed',0,0,100)]:ff.addParmTemplate(hou.FloatParmTemplate(key,label,1,default_value=(default,),min=lo,max=hi,min_is_strict=True,max_is_strict=True))
    ff.addParmTemplate(hou.FloatParmTemplate('wind_direction','Wind Direction XYZ',3,default_value=(0,1,0)))
    fg.append(ff)
    surface=hou.FolderParmTemplate('surface_shape','Ribbon Surface Shape')
    for key in ('flat_ribbons','ribbon_thickness','ribbon_curl','twist_strength'):surface.addParmTemplate(obj.parm(key).parmTemplate())
    fg.append(surface);force.setParmTemplateGroup(fg)
    for key in ('flat_ribbons','ribbon_thickness','ribbon_curl','twist_strength'):obj.parm(key).setExpression('ch("RIBBON_FORCE_CONTROLS/'+key+'")')
    force.setUserData('nodegraph_showcomment','1')
    group_nodes=[];guide_nodes=[]
    for i,system in enumerate(['BODY_BASE']+list(SYSTEMS)+['EYES']):
        data=repr(SYSTEMS.get(system,[]))
        code=runtime+'\nexecute('+repr(system)+','+data+')\n'
        n=python_sop(obj,system,code)
        if system in SYSTEMS:
            group=n.parmTemplateGroup();f=hou.FolderParmTemplate('surface_controls','Surface Shape Overrides');f.addParmTemplate(hou.ToggleParmTemplate('local_flat','Flatten This System',default_value=False))
            for key,label in [('local_thickness','Thickness Multiplier'),('local_curl','Curl Multiplier'),('local_twist','Twist Multiplier')]:f.addParmTemplate(hou.FloatParmTemplate(key,label,1,default_value=(1,),min=0,max=3,min_is_strict=True,max_is_strict=True))
            group.append(f);n.setParmTemplateGroup(group)
        n.setInput(0,force)
        normal=obj.createNode('normal',system+'_NORMALS');normal.setInput(0,n)
        group_nodes.append(normal)
        n.setComment('Curve-swept closed polygon ribbons. Primitive groups, rest, control_points, attachment and material_id are preserved.')
        if system in SYSTEMS:
            guides=python_sop(obj,system+'_GUIDES',runtime+'\nexecute('+repr(system)+','+data+',guides=True)\n')
            guides.setInput(0,force);guide_nodes.append(guides)
    final=obj.createNode('merge','FINAL_MERGE')
    for i,n in enumerate(group_nodes):final.setInput(i,n)
    guides=obj.createNode('merge','ALL_GUIDE_CURVES')
    for i,n in enumerate(guide_nodes):guides.setInput(i,n)
    wire_code='''import hou
n=hou.pwd();g=n.geometry();source=n.inputs()[0].geometry();g.clear()
attr=g.addAttrib(hou.attribType.Prim,'name','m07_WIREFRAME')
seen=set()
for prim in source.prims():
    ids=[v.point().number() for v in prim.vertices()]
    for a,b in zip(ids,ids[1:]+ids[:1]):
        key=tuple(sorted((a,b)))
        if key in seen:continue
        seen.add(key)
        uv_a=source.point(a).attribValue('ribbon_uv');uv_b=source.point(b).attribValue('ribbon_uv')
        if uv_a[2]<0 or uv_b[2]<0:continue
        along=abs(uv_a[1]-uv_b[1])<1e-6 and abs(uv_a[0]-uv_b[0])>1e-6 and round(uv_a[1]*8)%2==0
        across=abs(uv_a[0]-uv_b[0])<1e-6 and round(uv_a[0]*47)%6==0
        if not (along or across):continue
        line=g.createPolygon(is_closed=False);line.setAttribValue('name','m07_WIREFRAME')
        for idx in (a,b):
            p=g.createPoint();p.setPosition(source.point(idx).position());line.addVertex(p)
'''
    wire=python_sop(obj,'WIREFRAME_LINES',wire_code);wire.setInput(0,final)
    tubes=obj.createNode('polywire','WIREFRAME_TUBES');tubes.setInput(0,wire)
    setp(tubes,'radius',.0035)
    if tubes.parm('div'):setp(tubes,'div',3)
    guidetubes=obj.createNode('polywire','GUIDE_CURVES_TUBES');guidetubes.setInput(0,guides);setp(guidetubes,'radius',.008)
    if guidetubes.parm('div'):setp(guidetubes,'div',4)
    wiremerge=obj.createNode('merge','WIREFRAME_AND_GUIDES');wiremerge.setInput(0,tubes);wiremerge.setInput(1,guidetubes)
    switch=obj.createNode('switch','PRESENTATION_VIEW');switch.setInput(0,final);switch.setInput(1,wiremerge);switch.setInput(2,final)
    group=obj.parmTemplateGroup();group.append(hou.MenuParmTemplate('presentation','Presentation',['0','1','2'],['Material ID','Wireframe + Guides','Shaded'],default_value=0));obj.setParmTemplateGroup(group)
    switch.parm('input').setExpression('ch("../presentation")')
    out=obj.createNode('null','OUT_FISH');out.setInput(0,switch);out.setDisplayFlag(True);out.setRenderFlag(True)
    obj.layoutChildren();force.setCurrent(True,clear_all_selected=True)
    # MaterialX builders provide both unlit ID and diffuse shaded configurations.
    import voptoolutils
    palette=['C72D38','EF745F','E9A64B','F1E3C8','3E9FAD','A5CBD4','236A76','D66B39']
    for i,hexcolor in enumerate(palette,1):
        name='fish_%02d'%i
        voptoolutils._setupMtlXBuilderSubnet(destination_node=hou.node('/mat'),name=name,mask=voptoolutils.KARMAMTLX_TAB_MASK,folder_label='Karma Material Builder',render_context='kma')
        net=hou.node('/mat/'+name);surface=net.node('mtlxstandard_surface')
        rgb=[int(hexcolor[j:j+2],16)/255 for j in (0,2,4)];linear=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)
        surface.parmTuple('base_color').set(linear);surface.parmTuple('emission_color').set(linear)
        for channel in ('base_color','emission_color'):
            for component,parm in enumerate(surface.parmTuple(channel)):
                parm.setExpression(str(linear[component])+'*(1+0.12*'+str(math.sin(i*2.39))+'*ch("/obj/ABSTRACT_FISH/colorvariation"))')
        setp(surface,'specular_roughness',.48)
        surface.parm('base').setExpression('if(ch("/obj/ABSTRACT_FISH/presentation")==2,1,0)')
        surface.parm('emission').setExpression('if(ch("/obj/ABSTRACT_FISH/presentation")==2,0,1)')
        surface.parm('specular').setExpression('if(ch("/obj/ABSTRACT_FISH/presentation")==2,0.25,0)')
        net.layoutChildren()
    for name,pos,ortho in [('FISH_SIDE',(0,12,0),True),('FISH_THREE_QUARTER',(-9,17,5),False)]:
        cam=hou.node('/obj').createNode('cam',name);cam.parmTuple('t').set(pos);cam.parmTuple('r').set(look_rotation(pos,(0,0,0)));cam.parmTuple('s').set((-1,1,1) if ortho else (1,1,1))
        setp(cam,'projection',1 if ortho else 0);setp(cam,'orthowidth',7.6);setp(cam,'resx',960);setp(cam,'resy',540)
    stage=hou.node('/stage') or hou.node('/').createNode('lopnet','stage')
    imp=stage.createNode('sopimport','fish_geometry');setp(imp,'soppath',out.path());setp(imp,'enable_pathprefix',1);setp(imp,'pathprefix','/fish');setp(imp,'bindmaterials','nobind')
    mats=stage.createNode('materiallibrary','fish_materials');mats.setInput(0,imp);setp(mats,'matnet','/mat');setp(mats,'materials',8)
    for i in range(1,9):
        for k,v in [('matflag',True),('matnode','/mat/fish_%02d'%i),('matpath','/materials/fish_%02d'%i),('assign',True),('geopath','/fish/m%02d_*'%i)]:setp(mats,k+str(i),v)
    prev=mats
    for name,pos,ortho in [('fish_side_camera',(0,12,0),True),('fish_threequarter_camera',(-9,17,5),False)]:
        cam=stage.createNode('camera',name);cam.setInput(0,prev);prev=cam
        setp(cam,'primpath','/cameras/'+name);cam.parmTuple('t').set(pos);cam.parmTuple('r').set(look_rotation(pos,(0,0,0)));cam.parmTuple('s').set((-1,1,1) if ortho else (1,1,1))
        setp(cam,'projection','orthographic' if ortho else 'perspective')
        if cam.parm('orthowidth'):setp(cam,'orthowidth',7.6)
        if cam.parm('horizontalAperture') and ortho:setp(cam,'horizontalAperture',7600);setp(cam,'horizontalApertureOffset',500)
    dome=stage.createNode('domelight::3.0','fish_fill');dome.setInput(0,prev);setp(dome,'xn__inputsintensity_i0a',.35)
    light=stage.createNode('distantlight::2.0','fish_key');light.setInput(0,dome);light.parmTuple('r').set((-35,25,-20));setp(light,'xn__inputsintensity_i0a',2)
    settings=stage.createNode('karmarenderproperties','fish_render_settings');settings.setInput(0,light);setp(settings,'camera','/cameras/fish_side_camera');setp(settings,'engine','cpu');setp(settings,'resolutionx',960);setp(settings,'samplesperpixel',32);setp(settings,'picture','$HIP/previews/material_id.png')
    rop=stage.createNode('usdrender_rop','fish_render');rop.setInput(0,settings);setp(rop,'renderer','BRAY_HdKarma');setp(rop,'trange',0);setp(rop,'override_res','specific');setp(rop,'res_user1',960);setp(rop,'res_user2',540)
    settings.setDisplayFlag(True);stage.layoutChildren();hou.node('/obj').layoutChildren()
    return obj,final,rop


def validate(obj,final,directory=HERE):
    reports={};total=0
    for system in ['BODY_BASE']+list(SYSTEMS)+['EYES']:
        node=obj.node(system);node.cook(force=True);g=node.geometry()
        if g is None or not g.prims():raise AssertionError('Empty geometry '+system+' '+str(node.errors()))
        if system in SYSTEMS:
            guides=obj.node(system+'_GUIDES').geometry()
            if guides is None or len(guides.prims())!=len(SYSTEMS[system]):raise AssertionError('Guide count mismatch '+system)
            if any(len(p.vertices())<24 for p in guides.prims()):raise AssertionError('Insufficient guide samples')
            for a in ('width','twist','guide_normal'):
                if not guides.findPointAttrib(a):raise AssertionError('Missing guide attribute '+a)
        expected=[d['name'] for d in SYSTEMS.get(system,[])]
        for name in expected:
            group=g.findPrimGroup(name)
            if group is None or len(group.prims())<24:raise AssertionError('Missing ribbon '+name)
        from collections import defaultdict
        edges=defaultdict(list);volumes=defaultdict(float)
        for prim in g.prims():
            points=[v.point() for v in prim.vertices()];ids=[p.number() for p in points]
            for a,b in zip(ids,ids[1:]+ids[:1]):edges[tuple(sorted((a,b)))].append(1 if a<b else -1)
            v0=points[0].position()
            for j in range(1,len(points)-1):volumes[prim.stringAttribValue('name')]+=v0.dot(points[j].position().cross(points[j+1].position()))/6
        local=obj.node(system)
        open_surface=system in SYSTEMS and (obj.evalParm('flat_ribbons') or obj.evalParm('ribbon_thickness')==0 or local.evalParm('local_flat') or local.evalParm('local_thickness')==0)
        if any(len(v)>2 or (not open_surface and len(v)!=2) for v in edges.values()):raise AssertionError('Invalid shell topology '+system)
        if any(len(v)==2 and sum(v)!=0 for v in edges.values()):raise AssertionError('Inconsistent polygon winding '+system)
        if not open_surface and any(v<=0 for v in volumes.values()):raise AssertionError('Inward shell normals '+system+' '+str(volumes))
        bad=[]
        for prim in g.prims():
            if prim.intrinsicValue('measuredarea')<1e-10:bad.append(prim.number())
        if bad:raise AssertionError('Degenerate polygons '+system+' '+str(bad[:8]))
        normal_geo=obj.node(system+'_NORMALS').geometry()
        if not (normal_geo.findVertexAttrib('N') or normal_geo.findPointAttrib('N')):raise AssertionError('Missing smooth normals '+system)
        ids=set(g.primIntAttribValues('material_id'))
        if not ids<=set(range(1,9)):raise AssertionError('Bad material IDs')
        reports[system]={'polygons':len(g.prims()),'points':len(g.points()),'ribbons':len(expected),'closed_manifold':not open_surface,'consistent_winding':True,'material_ids':sorted(ids),'bbox':str(g.boundingBox())}
        total+=len(expected)
    if total!=42:raise AssertionError('Expected 42 ribbons')
    from pxr import UsdGeom,UsdShade
    stage=hou.node('/stage/fish_materials').stage()
    meshes=[p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)]
    if not meshes:raise AssertionError('No USD meshes imported')
    unbound=[str(p.GetPath()) for p in meshes if not UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0]]
    if unbound:raise AssertionError('Unbound USD materials: '+str(unbound[:5]))
    result={'usd_meshes':len(meshes),'all_usd_materials_bound':True,'houdini':hou.applicationVersionString(),'license':str(hou.licenseCategory()),'ribbon_count':total,'systems':reports,'bounds':str(final.geometry().boundingBox()),'reference_image':'/home/amir/Pictures/Screenshots/Screenshot from 2026-10-22 17-11-44.png','visual_validation':'pending rendered review'}
    (directory/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--render',action='store_true');p.add_argument('--output-dir',type=Path,default=HERE);a=p.parse_args();directory=a.output_dir.resolve();directory.mkdir(parents=True,exist_ok=True)
    apprentice='apprentice' in str(hou.licenseCategory()).lower()
    output=directory/('abstract_fish.hipnc' if apprentice else 'abstract_fish.hip')
    obj,final,rop=build(output);validate(obj,final,directory);hou.hipFile.save(str(output))
    if a.render:
        previews=directory/'previews';previews.mkdir(exist_ok=True)
        for mode,name in [(0,'material_id'),(1,'wireframe'),(2,'shaded'),(2,'three_quarter')]:
            dest=previews/(name+'.png')
            if dest.exists():raise FileExistsError('Refusing to overwrite '+str(dest))
            obj.parm('presentation').set(mode);hou.node('/stage/fish_render_settings').parm('camera').set('/cameras/fish_threequarter_camera' if name=='three_quarter' else '/cameras/fish_side_camera');rop.parm('outputimage').set(str(dest));print('RENDER_BEGIN',name,flush=True);rop.render()
            if not dest.is_file() or not dest.stat().st_size:raise RuntimeError('Missing preview '+str(dest))
            print('RENDER_COMPLETE',name,dest,flush=True)
        obj.parm('presentation').set(0);hou.node('/stage/fish_render_settings').parm('camera').set('/cameras/fish_side_camera');hou.hipFile.save(str(output))
    print('SCENE_SAVED',output,flush=True)

if __name__=='__main__':main()
