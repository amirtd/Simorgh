"""Add selectable KineFX sphere controls to the OPEN Phoenix v13 scene.
Run with runpy.run_path(..., run_name='__main__') inside Houdini.
Never loads a scene, recaptures weights, or changes animation parameters.
"""
from pathlib import Path
import hashlib
import hou


def install(save=True):
    expected = Path(__file__).resolve().with_name('phoenix_rig_v13_unbound_clean_01.hipnc')
    if Path(hou.hipFile.path()).resolve() != expected:
        raise hou.Error('Open the existing Phoenix v13 scene first; nothing changed.')
    rig = hou.node('/obj/PHOENIX_RIG')
    pose = hou.node('/obj/PHOENIX_RIG/POSE_JOINTS')
    paint = hou.node('/obj/PHOENIX_SKINNING/PAINT_WEIGHTS')
    deform = hou.node('/obj/PHOENIX_SKINNING/jointdeform1')
    if not all((rig, pose, paint, deform)):
        raise hou.Error('Required Phoenix rig/skinning nodes are missing.')
    names_to_create = ['CONTROL_SPHERE', 'NAME_CONTROL_SPHERE', 'SPHERE_CONTROLS']
    if any(rig.node(n) for n in names_to_create):
        raise hou.Error('Sphere control nodes already exist. Nothing reset. Use POSE_JOINTS to animate.')
    connections = pose.inputConnections()
    if not connections or connections[0].inputIndex() != 0:
        raise hou.Error('POSE_JOINTS has no skeleton input; nothing changed.')
    source, output = connections[0].inputNode(), connections[0].outputIndex()
    skeleton = source.geometryAtFrame(hou.frame(), output)
    names = skeleton.pointStringAttribValues('name')
    before_p = skeleton.pointFloatAttribValuesAsString('P')
    before_t = skeleton.pointFloatAttribValuesAsString('transform')
    hierarchy = [tuple(v.point().number() for v in p.vertices()) for p in skeleton.prims()]
    mesh_before = deform.geometry().pointFloatAttribValuesAsString('P')
    if deform.errors():
        raise hou.Error('Resolve Joint Deform errors before installing controls.')
    weight_hash = hashlib.sha256(paint.geometry().pointFloatAttribValuesAsString('boneCapture')).hexdigest()
    radius = max(skeleton.boundingBox().sizevec()) * 0.012
    if radius <= 0:
        raise hou.Error('Invalid skeleton bounds; nothing changed.')
    created = []
    try:
        with hou.undos.group('Add Phoenix sphere animation controls'):
            sphere = rig.createNode('sphere', names_to_create[0]); created.append(sphere)
            sphere.parm('type').set('prim')
            sphere.parmTuple('rad').set((radius,) * 3)
            sphere.setComment('Shared sphere shape. Adjust Radius to resize the joint handles.')
            named = rig.createNode('attribwrangle', names_to_create[1]); created.append(named)
            named.setInput(0, sphere)
            named.parm('class').set(1)
            named.parm('snippet').set('s@name="phoenix_sphere"; v@Cd=set(1,0.8,0.1);')
            controls = rig.createNode('kinefx::attachjointgeo', names_to_create[2]); created.append(controls)
            controls.setInput(0, source, output)
            controls.setInput(1, named)
            controls.setParms({'role': 0, 'userestposeattrib': 0, 'shapes': 1,
                               'group1': '*', 'shapename1': 'phoenix_sphere',
                               'shape_worldtrans1': 0, 'uselighting': 0, 'tweak': len(names)})
            for i, name in enumerate(names, 1):
                color = (0.1, 0.75, 1.0) if name.endswith('_L') else ((1.0, 0.2, 0.15) if name.endswith('_R') else (1.0, 0.8, 0.1))
                controls.parm('tweak_group%d' % i).set('@name=' + name)
                controls.parm('usecolor%d' % i).set(1)
                controls.parmTuple('color%d' % i).set(color)
                scale = 1.5 if name == 'root' else 1.0
                controls.parmTuple('s%d' % i).set((scale,) * 3)
            controls.setComment('Selectable Rig Pose handles: left cyan, right red, center yellow. Multiply Shape Scale resizes all controls.')
            result = controls.geometry()
            if controls.errors():
                raise hou.Error(str(controls.errors()))
            assert result.pointStringAttribValues('name') == names, 'Joint names changed'
            assert result.pointFloatAttribValuesAsString('P') == before_p, 'Joint positions changed'
            assert result.pointFloatAttribValuesAsString('transform') == before_t, 'Joint transforms changed'
            assert [tuple(v.point().number() for v in p.vertices()) for p in result.prims()[:len(hierarchy)]] == hierarchy, 'Joint hierarchy changed'
            group = result.findPrimGroup('kinefx_controls')
            assert group and len(group.prims()) == len(names), 'Not every joint received a sphere'
            pose.setInput(0, controls)
            assert deform.geometry().pointFloatAttribValuesAsString('P') == mesh_before, 'Mesh pose changed'
            assert not deform.errors(), str(deform.errors())
            assert hashlib.sha256(paint.geometry().pointFloatAttribValuesAsString('boneCapture')).hexdigest() == weight_hash, 'Painted weights changed'
            origin = source.position()
            sphere.setPosition(origin + hou.Vector2(-5, -1))
            named.setPosition(origin + hou.Vector2(-5, -2))
            controls.setPosition(origin + hou.Vector2(0, -1))
    except Exception:
        pose.setInput(0, source, output)
        for n in reversed(created):
            n.destroy()
        raise
    if hou.isUIAvailable():
        for viewer in hou.ui.paneTabs():
            if viewer.type() == hou.paneTabType.SceneViewer:
                viewer.setCurrentState('select')
        rig.setDisplayFlag(True)
        pose.setDisplayFlag(True)
        # Skeleton and controls remain viewport geometry, excluded from rendering.
        pose.setRenderFlag(False)
        deform.setDisplayFlag(True)
        pose.setCurrent(True, clear_all_selected=True)
        for viewer in hou.ui.paneTabs():
            if viewer.type() == hou.paneTabType.SceneViewer:
                viewer.setPwd(rig)
                viewer.enterCurrentNodeState()
    if save:
        hou.hipFile.save(str(expected))
    print('Phoenix sphere controls installed: %d selectable spheres. Weights, joint transforms, hierarchy, mesh pose, and existing animation preserved. Saved=%s. Select POSE_JOINTS and press Enter in the viewport. Resize at SPHERE_CONTROLS > Multiply Shape Scale.' % (len(names), save), flush=True)
    return controls


if __name__ == '__main__':
    if not hou.isUIAvailable():
        raise hou.Error('Run inside the open Houdini session to retain unsaved changes.')
    install()
