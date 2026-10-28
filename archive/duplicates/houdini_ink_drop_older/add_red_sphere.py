import hou
import voptoolutils

HIP = r"E:\Wirling Worlds\Houdini Ink Drop\ink_drop_effect.hipnc"
TEXTURE = r"E:\Wirling Worlds\Houdini Ink Drop\textures\red_sphere_persian_pattern.png"
OBJ_PATH = '/obj/RED_TEXTURED_SPHERE'
CTL_PATH = '/stage/red_sphere_controls'
MAT_PATH = '/mat/red_sphere_mtl'

hou.hipFile.load(HIP)

def fparm(name, label, value, lo, hi, folder):
    folder.addParmTemplate(hou.FloatParmTemplate(name, label, 1, default_value=(value,), min=lo, max=hi))

def make_controls(node):
    group = node.parmTemplateGroup()
    folder = hou.FolderParmTemplate('red_sphere_settings', 'Red Sphere Controls')
    fparm('red_start', 'Growth Start Frame', 8.0, -1000, 2000, folder)
    fparm('red_end', 'Growth End Frame', 32.0, -999, 4000, folder)
    fparm('red_radius', 'Final Radius', 0.72, 0.001, 5.0, folder)
    fparm('red_overshoot', 'Growth Overshoot', 0.08, 0.0, 1.0, folder)
    fparm('red_posx', 'Position X', 0.0, -10, 10, folder)
    fparm('red_posy', 'Position Y', -0.72, -10, 10, folder)
    fparm('red_posz', 'Position Z', 0.0, -10, 10, folder)
    fparm('red_rotx', 'Rotation X', 0.0, -360, 360, folder)
    fparm('red_roty', 'Rotation Y', 0.0, -360, 360, folder)
    fparm('red_rotz', 'Rotation Z', 0.0, -360, 360, folder)
    fparm('red_spin', 'Spin Speed', 18.0, -360, 360, folder)
    fparm('red_scale_x', 'Scale X', 1.0, 0.01, 5.0, folder)
    fparm('red_scale_y', 'Scale Y', 1.0, 0.01, 5.0, folder)
    fparm('red_scale_z', 'Scale Z', 1.0, 0.01, 5.0, folder)
    folder.addParmTemplate(hou.StringParmTemplate('red_texture', 'Texture', 1, default_value=(TEXTURE,), string_type=hou.stringParmType.FileReference))
    folder.addParmTemplate(hou.FloatParmTemplate('red_tint', 'Red Tint', 3, default_value=(1.0, 0.24, 0.18), min=0, max=1, look=hou.parmLook.ColorSquare, naming_scheme=hou.parmNamingScheme.RGBA))
    fparm('red_texture_mix', 'Texture Amount', 0.82, 0, 1, folder)
    fparm('red_roughness', 'Roughness', 0.24, 0, 1, folder)
    fparm('red_specular', 'Reflection', 0.55, 0, 1, folder)
    fparm('red_emission', 'Emission', 0.08, 0, 5, folder)
    group.append(folder)
    node.setParmTemplateGroup(group)

# Additive object creation: only replace this tool's own object if rerun.
obj = hou.node('/obj')
old = hou.node(OBJ_PATH)
if old:
    old.destroy()
geo = obj.createNode('geo', 'RED_TEXTURED_SPHERE')
geo.setComment('Additive textured red sphere; controls are mirrored on /stage/red_sphere_controls.')
for child in geo.children():
    child.destroy()
make_controls(geo)

sphere = geo.createNode('sphere', 'red_sphere_source')
sphere.parm('type').set(2)
sphere.parm('freq').set(6)
sphere.parmTuple('rad').set((1, 1, 1))
uv = geo.createNode('texture', 'spherical_texture_coordinates')
uv.setInput(0, sphere)
uv.parm('type').set('polar')
uv.parm('axis').set('y')
uv.parm('fixseams').set(True)

animate = geo.createNode('attribwrangle', 'grow_position_rotate')
animate.setInput(0, uv)
animate.parm('class').set(2)
animate.parm('snippet').set(r'''
float start=chf("../red_start");
float end=max(start+0.001,chf("../red_end"));
float u=clamp((@Frame-start)/(end-start),0,1);
float grow=u*u*(3-2*u)+sin(PI*u)*chf("../red_overshoot");
float r=chf("../red_radius")*max(grow,0.0001);
vector p=@P*set(chf("../red_scale_x"),chf("../red_scale_y"),chf("../red_scale_z"))*r;
float seconds=max(0,@Frame-start)/24.0;
vector rot=radians(set(chf("../red_rotx"),chf("../red_roty")+seconds*chf("../red_spin"),chf("../red_rotz")));
matrix3 m=ident(); rotate(m,rot.x,{1,0,0}); rotate(m,rot.y,{0,1,0}); rotate(m,rot.z,{0,0,1});
@P=p*m+set(chf("../red_posx"),chf("../red_posy"),chf("../red_posz"));
f@red_growth=grow;
''')
normal = geo.createNode('normal', 'red_sphere_normals')
normal.setInput(0, animate)
tag = geo.createNode('attribwrangle', 'red_sphere_material_tag')
tag.setInput(0, normal)
tag.parm('class').set(1)
tag.parm('snippet').set('s@name="red_textured_sphere"; s@shop_materialpath="/mat/red_sphere_mtl";')
out = geo.createNode('null', 'OUT_RED_TEXTURED_SPHERE')
out.setInput(0, tag)
out.setDisplayFlag(True)
out.setRenderFlag(True)
geo.layoutChildren()

# Stage master controls and live links back to SOPs.
stage = hou.node('/stage')
oldctl = stage.node('red_sphere_controls')
if oldctl:
    oldctl.destroy()
ctl = stage.createNode('null', 'red_sphere_controls')
make_controls(ctl)
for parm in ctl.parms():
    target = geo.parm(parm.name())
    if target is not None:
        target.setExpression('ch("%s")' % parm.path(), hou.exprLanguage.Hscript)

# MaterialX texture/tint material.
mat_parent = hou.node('/mat')
oldmat = hou.node(MAT_PATH)
if oldmat:
    oldmat.destroy()
voptoolutils._setupMtlXBuilderSubnet(destination_node=mat_parent, name='red_sphere_mtl',
    mask=voptoolutils.KARMAMTLX_TAB_MASK, folder_label='Karma Material Builder', render_context='kma')
mat = hou.node(MAT_PATH)
surf = mat.node('mtlxstandard_surface')
texcoord = mat.createNode('mtlxtexcoord', 'sphere_uv')
texcoord.parm('signature').set('vector2')
image = mat.createNode('mtlximage', 'persian_pattern')
image.parm('signature').set('color3')
image.parm('file').setExpression('chs("%s/red_texture")' % CTL_PATH, hou.exprLanguage.Hscript)
image.setNamedInput('texcoord', texcoord, 'out')
tint = mat.createNode('mtlxconstant', 'red_tint')
tint.parm('signature').set('color3')
for suffix in ('r','g','b'):
    tint.parm('value_color3'+suffix).setExpression('ch("%s/red_tint%s")' % (CTL_PATH, suffix), hou.exprLanguage.Hscript)
mix = mat.createNode('mtlxmix', 'texture_over_red', run_init_scripts=True)
mix.parm('signature').set('color3')
mix.setNamedInput('bg', tint, 'out')
mix.setNamedInput('fg', image, 'out')
mix.parm('mix').setExpression('ch("%s/red_texture_mix")' % CTL_PATH, hou.exprLanguage.Hscript)
surf.setNamedInput('base_color', mix, 'out')
surf.setNamedInput('emission_color', mix, 'out')
surf.parm('base').set(1.0)
surf.parm('specular').setExpression('ch("%s/red_specular")' % CTL_PATH, hou.exprLanguage.Hscript)
surf.parm('specular_roughness').setExpression('ch("%s/red_roughness")' % CTL_PATH, hou.exprLanguage.Hscript)
surf.parm('emission').setExpression('ch("%s/red_emission")' % CTL_PATH, hou.exprLanguage.Hscript)
mat.layoutChildren()

# Preserve the current Stage chain by inserting before the existing camera.
camera = stage.node('ink_drop_camera')
for name in ('red_sphere_materials', 'red_sphere_import'):
    n = stage.node(name)
    if n:
        n.destroy()
upstream = camera.input(0)
sopimport = stage.createNode('sopimport', 'red_sphere_import')
sopimport.setInput(0, upstream)
sopimport.parm('soppath').set(OBJ_PATH + '/OUT_RED_TEXTURED_SPHERE')
sopimport.parm('enable_pathprefix').set(True)
sopimport.parm('pathprefix').set('/red_sphere')
sopimport.parm('bindmaterials').set('nobind')
mlib = stage.createNode('materiallibrary', 'red_sphere_materials')
mlib.setInput(0, sopimport)
mlib.parm('matnet').set('/mat')
mlib.parm('materials').set(1)
mlib.parm('matflag1').set(True)
mlib.parm('matnode1').set(MAT_PATH)
mlib.parm('matpath1').set('/materials/red_sphere_mtl')
mlib.parm('assign1').set(True)
mlib.parm('geopath1').set('/red_sphere/**')
camera.setInput(0, mlib)
stage.layoutChildren()

hou.setFrame(24)
print('Red sphere points/prims:', len(out.geometry().points()), len(out.geometry().prims()))
print('Errors:', [(n.path(), n.errors()) for n in (animate, out, sopimport, mlib) if n.errors()])
hou.hipFile.save(HIP)
print('Saved additively:', HIP)
