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

def create_ribbon(name,control_points,width_profile,thickness,twist,material_id,depth_offset,geo=None,system='ribbon',controls=None,guides=False,edge_curl=.05,conform=False):
    g=geo or hou.pwd().geometry();ctl=controls or {}
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
        else:c[1]+=depth_offset
        tangent=(curve(cps,min(1,t+.001))-curve(cps,max(0,t-.001))).normalized()
        side=V((0,1,0)).cross(tangent).normalized()
        normal=tangent.cross(side).normalized()
        theta=math.radians(interp(twist,t)+ctl.get('twist',0)*math.sin(math.pi*t))
        side2=side*math.cos(theta)+normal*math.sin(theta)
        normal2=tangent.cross(side2).normalized()
        width=max(.004,interp(width_profile,t)*ctl.get('width',1))
        centers.append(c);widths.append(width);sides.append(side2);normals.append(normal2)
    if guides:
        prim=g.createPolygon(is_closed=False)
        for i,c in enumerate(centers):prim.addVertex(point(g,c,3,(i/(n-1),.5,0),widths[i]))
        metadata(prim,name,material_id,system,cps)
        return
    grids=[]
    for shell in (1,-1):
        rows=[]
        for i,c in enumerate(centers):
            t=i/(n-1);row=[]
            thick=thickness*(.38+.62*math.sin(math.pi*t)**.7)
            for j in range(m+1):
                v=j/m*2-1
                pos=c+sides[i]*(v*widths[i]*.5)+normals[i]*(.055*(1-v*v)*math.sin(math.pi*t)+edge_curl*v*v*math.sin(math.pi*t)*math.sin(2*math.pi*t)+shell*thick*.5)
                row.append(point(g,pos,material_id,(t,j/m,shell),widths[i],ctl.get('colorvariation',0),sum(map(ord,name))))
            rows.append(row)
        grids.append(rows)
    top,bottom=grids
    for i in range(n-1):
        for j in range(m):
            face(g,[top[i][j],top[i+1][j],top[i+1][j+1],top[i][j+1]],name,material_id,system,cps)
            face(g,[bottom[i][j+1],bottom[i+1][j+1],bottom[i+1][j],bottom[i][j]],name,material_id,system,cps)
        face(g,[bottom[i][0],bottom[i+1][0],top[i+1][0],top[i][0]],name,material_id,system,cps)
        face(g,[top[i][-1],top[i+1][-1],bottom[i+1][-1],bottom[i][-1]],name,material_id,system,cps)
    for j in range(m):
        face(g,[top[0][j+1],bottom[0][j+1],bottom[0][j],top[0][j]],name,material_id,system,cps)
        face(g,[top[-1][j],bottom[-1][j],bottom[-1][j+1],top[-1][j+1]],name,material_id,system,cps)

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
    ctl={k:obj.evalParm(k) for k in ('width','length','curvature','twist','tailspread','finspread','bodylength','bodythickness','colorvariation')}
    if system=='BODY_BASE':build_body(g,ctl)
    elif system=='EYES':
        for sign in (1,-1):
            sphere(g,(-2.15,sign*.295,.25),(.105,.042,.105),'EYE_GOLD_'+('FRONT' if sign>0 else 'BACK'),3)
            sphere(g,(-2.17,sign*.332,.25),(.054,.025,.062),'EYE_PUPIL_'+('FRONT' if sign>0 else 'BACK'),7)
            sphere(g,(-2.19,sign*.355,.276),(.015,.01,.015),'EYE_GLINT_'+('FRONT' if sign>0 else 'BACK'),4)
    else:
        for d in specs:create_ribbon(geo=g,system=system,controls=ctl,guides=guides,**d)
