import hou

HIP = r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini\ink_drop_effect.hipnc"
hou.hipFile.load(HIP)

geo = hou.node('/obj/INK_DROP_EFFECT')
normal = geo.node('hero_air_bubble_normals')
if normal is None or normal.input(0) is None:
    raise RuntimeError('Could not locate the existing main-bubble normal branch safely.')

# Only replace this script's own node on a rerun. All user-created nodes remain intact.
old = geo.node('hero_mesh_subdivide')
if old is not None:
    if normal.input(0) == old and old.input(0) is not None:
        normal.setInput(0, old.input(0))
    old.destroy()

upstream = normal.input(0)
before = upstream.geometry()
before_counts = (len(before.points()), len(before.prims()))

subdivide = geo.createNode('subdivide', 'hero_mesh_subdivide')
subdivide.setComment('Adds render-smoothing faces to the main bubble only; inserted additively.')
subdivide.setInput(0, upstream)
subdivide.parm('algorithm').set('osdcc')
subdivide.parm('iterations').set(2)
subdivide.parm('updatenmls').set(True)
subdivide.parm('smoothvertex').set(True)
normal.setInput(0, subdivide)

# Expose subdivision depth without replacing the existing Stage control interface.
ctl = hou.node('/stage/ink_drop_hero_bubble_controls')
if ctl is not None:
    ptg = ctl.parmTemplateGroup()
    if ptg.find('hero_mesh_subdivision') is None:
        parm = hou.IntParmTemplate('hero_mesh_subdivision', 'Mesh Subdivision', 1,
                                   default_value=(2,), min=0, max=3,
                                   min_is_strict=True, max_is_strict=True)
        parm.setHelp('Catmull-Clark subdivision depth for the main bubble only. 2 is smooth; 3 is heavier.')
        folder = ptg.find('hero_animation')
        if folder is not None:
            folder.addParmTemplate(parm)
            ptg.replace('hero_animation', folder)
        else:
            ptg.append(parm)
        ctl.setParmTemplateGroup(ptg)
    subdivide.parm('iterations').setExpression(
        'ch("%s/hero_mesh_subdivision")' % ctl.path(), hou.exprLanguage.Hscript)

geo.layoutChildren()
hou.setFrame(24)
after = subdivide.geometry()
after_counts = (len(after.points()), len(after.prims()))
errors = subdivide.errors() + normal.errors()
print('Main bubble before points/prims:', before_counts)
print('Main bubble after points/prims:', after_counts)
print('Errors:', errors)
hou.hipFile.save(HIP)
print('Saved additively:', HIP)
