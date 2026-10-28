import hou

HIP = r"E:\Wirling Worlds\Houdini Ink Drop\ink_drop_effect.hipnc"
hou.hipFile.load(HIP)
obj = hou.node('/obj')
old = obj.node('GAS_INSIDE_BUBBLE_TEST')
if old:
    old.destroy()
geo = obj.createNode('geo', 'GAS_INSIDE_BUBBLE_TEST')
geo.setComment('Low-resolution sparse Pyro smoke test confined by an inverted hero-bubble SDF.')
for n in geo.children():
    n.destroy()

source = geo.createNode('sphere', 'gas_source')
source.parmTuple('t').set((0.0, -1.45, 0.0))
source.parmTuple('rad').set((0.24, 0.24, 0.24))
source.parm('type').set(2)
source.parm('freq').set(3)

pyro_source = geo.createNode('pyrosource', 'initialize_smoke_source')
pyro_source.setInput(0, source)
pyro_source.parm('initialize').set('source')
pyro_source.parm('particlesep').set(0.08)
pyro_source.parm('particlescale').set(2.0)

motion = geo.createNode('attribwrangle', 'source_density_temperature_velocity')
motion.setInput(0, pyro_source)
motion.parm('class').set(2)
motion.parm('snippet').set('''
f@density = 1.0;
f@temperature = 1.25;
float phase = @Time*2.3 + @ptnum*0.173;
v@v = set(sin(phase)*0.22, 0.48, cos(phase*1.17)*0.22);
''')

raster = geo.createNode('volumerasterizeattributes', 'rasterize_gas_source')
raster.setInput(0, motion)
raster.parm('attributes').set('density temperature v')
raster.parm('voxelsize').set(0.12)

hero = geo.createNode('object_merge', 'hero_container_geometry')
hero.parm('objpath1').set('/obj/INK_DROP_EFFECT/hero_air_bubble_animate')
hero.parm('xformtype').set(1)
freeze = geo.createNode('timeshift', 'freeze_container_shape')
freeze.setInput(0, hero)
freeze.parm('frame').deleteAllKeyframes()
freeze.parm('frame').set(24)

sdf = geo.createNode('vdbfrompolygons', 'hero_container_sdf')
sdf.setInput(0, freeze)
sdf.parm('voxelsize').set(0.12)
sdf.parm('distancename').set('collision')
sdf.parm('exteriorbandvoxels').set(12)
sdf.parm('interiorbandvoxels').set(12)
sdf.parm('fillinterior').set(True)

invert = geo.createNode('volumewrangle', 'invert_sdf_for_container')
invert.setInput(0, sdf)
invert.parm('group').set('collision')
invert.parm('snippet').set('f@collision = -f@collision;')

solver = geo.createNode('pyrosolver', 'gas_inside_bubble_solver')
solver.setInput(0, raster)
solver.setInput(1, invert)
solver.parm('startframe').set(1)
solver.parm('divsize').set(0.12)
solver.parm('col_inputtype').set('volume')
solver.parm('collisionsdf').set('collision')
solver.parm('enable_buoyancy').set(True)
solver.parm('buoyancylift').set(0.42)
solver.parm('enable_disturbance').set(True)
solver.parm('disturbance').set(0.35)
solver.parm('disturbance_blocksize').set(0.22)
solver.parm('enable_turbulence').set(True)
solver.parm('turbulence').set(0.28)
solver.parm('turbulence_swirlsize').set(0.55)

out = geo.createNode('null', 'OUT_GAS_INSIDE_BUBBLE')
out.setInput(0, solver)
out.setDisplayFlag(True)
out.setRenderFlag(True)
geo.layoutChildren()

hou.setFrame(24)
g = out.geometry()
print('Gas primitives:', [(p.stringAttribValue('name'), p.type().name()) for p in g.prims()])
print('Solver errors:', solver.errors())

# Karma volume material.
import voptoolutils
mat = hou.node('/mat')
oldmat = mat.node('gas_inside_bubble_mtl')
if oldmat:
    oldmat.destroy()
voptoolutils._setupMtlXBuilderSubnet(
    destination_node=mat, name='gas_inside_bubble_mtl',
    mask=voptoolutils.KARMAMTLX_TAB_MASK,
    folder_label='Karma Material Builder', render_context='kma')
matnet = mat.node('gas_inside_bubble_mtl')
standard = matnet.node('mtlxstandard_surface')
if standard:
    standard.destroy()
pyro = matnet.createNode('kma_pyroshader', 'gas_volume_shader')
pyro.parm('densityscale').set(2.2)
pyro.parmTuple('smokecolor').set((0.12, 0.42, 0.72))
pyro.parm('shadowint').set(0.7)
matnet.node('Material_Outputs_and_AOVs').setNextInput(pyro, 0)
matnet.layoutChildren()

# Insert the test volume into the existing Solaris chain.
stage = hou.node('/stage')
for name in ('gas_inside_bubble_import', 'gas_inside_bubble_materials'):
    n = stage.node(name)
    if n:
        n.destroy()
base = stage.node('ink_drop_materials')
camera = stage.node('ink_drop_camera')
gas_import = stage.createNode('sopimport', 'gas_inside_bubble_import')
gas_import.setInput(0, base)
gas_import.parm('soppath').set('/obj/GAS_INSIDE_BUBBLE_TEST/OUT_GAS_INSIDE_BUBBLE')
gas_import.parm('enable_pathprefix').set(True)
gas_import.parm('pathprefix').set('/gas_inside_bubble')
gas_import.parm('bindmaterials').set('nobind')
gas_mats = stage.createNode('materiallibrary', 'gas_inside_bubble_materials')
gas_mats.setInput(0, gas_import)
gas_mats.parm('matnet').set('/mat')
gas_mats.parm('materials').set(1)
gas_mats.parm('matflag1').set(True)
gas_mats.parm('matnode1').set('/mat/gas_inside_bubble_mtl')
gas_mats.parm('matpath1').set('/materials/gas_inside_bubble_mtl')
gas_mats.parm('assign1').set(True)
gas_mats.parm('geopath1').set('/gas_inside_bubble/**')
camera.setInput(0, gas_mats)
stage.layoutChildren()

hou.hipFile.save(HIP)
print('Saved', HIP)
