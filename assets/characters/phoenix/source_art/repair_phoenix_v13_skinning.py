"""Repair the OPEN v13 scene. No load, recapture, paint reset, or scene copy.
In Houdini Python Shell:
import runpy; runpy.run_path('/home/amir/Documents/ChatGPT/Phoenix/assets/characters/phoenix/source_art/repair_phoenix_v13_skinning.py', run_name='__main__')
"""
from pathlib import Path
import hashlib
import hou
import numpy as np


def repair(save=True):
    expected = Path(__file__).resolve().parent / 'phoenix_rig_v13_unbound_clean_01.hipnc'
    current = Path(hou.hipFile.path()).resolve()
    if current != expected.resolve():
        raise hou.Error('Open the existing v13 scene first; nothing changed: ' + str(current))
    skin = hou.node('/obj/PHOENIX_SKINNING')
    deform = skin.node('jointdeform1') if skin else None
    paint = skin.node('PAINT_WEIGHTS') if skin else None
    if not deform or not paint:
        raise hou.Error('Expected PAINT_WEIGHTS and jointdeform1 are missing; nothing changed.')
    rest, pose = skin.node('REST'), skin.node('POSE')
    if not rest or not pose:
        raise hou.Error('REST or POSE is missing; nothing changed.')
    # Use the live painted cache. Never press Copy Input or change capture nodes.
    mesh = paint.geometryAtFrame(hou.frame(), 0)
    capture = mesh.findPointAttrib('boneCapture')
    if not capture:
        raise hou.Error('Paint output 0 has no boneCapture. Stopped without recapturing or resetting weights.')
    weights = mesh.pointFloatAttribValuesAsString('boneCapture')
    weight_hash = hashlib.sha256(weights).hexdigest()
    table = capture.indexPairPropertyTables()[0]
    names = [table.stringPropertyValueAtIndex('pCaptPath', i) for i in range(table.numIndices())]
    rest_names = set(rest.geometry().pointStringAttribValues('name'))
    pose_names = set(pose.geometry().pointStringAttribValues('name'))
    pairs = np.frombuffer(weights, dtype=np.float32).reshape(-1, 2)
    valid = (pairs[:, 0] >= 0) & (pairs[:, 1] > 0)
    totals = np.bincount(pairs[valid, 0].astype(np.int64), weights=pairs[valid, 1], minlength=len(names))
    active = [i for i, n in enumerate(names) if totals[i] > 0]
    if not active or any(names[i] not in rest_names or names[i] not in pose_names for i in active):
        raise hou.Error('Weighted capture paths do not match both skeletons; nothing changed.')
    nonroot = [i for i in active if names[i] != 'root']
    joint_index = max(nonroot or active, key=lambda i: totals[i])
    joint_name = names[joint_index]
    old = [(c.inputIndex(), c.inputNode(), c.outputIndex()) for c in deform.inputConnections()]
    test = None
    try:
        with hou.undos.group('Repair Phoenix v13 Joint Deform wiring'):
            # Joint Capture Paint: 0=weighted mesh, 1=capture pose, 2=animated pose.
            deform.setInput(0, paint, 0)
            deform.setInput(1, rest, 0)
            deform.setInput(2, pose, 0)
            base = deform.geometry().pointFloatAttribValuesAsString('P')
            if deform.errors():
                raise hou.Error(str(deform.errors()))
            test = skin.createNode('kinefx::rigpose', '__PHOENIX_REPAIR_ROTATION_TEST')
            test.setInput(0, pose)
            test.parm('transformations').set(1)
            test.parm('group0').set('@name=' + joint_name)
            test.parmTuple('r0').set((0, 0, 12))
            deform.setInput(2, test)
            rotated = deform.geometry().pointFloatAttribValuesAsString('P')
            if deform.errors():
                raise hou.Error(str(deform.errors()))
            delta = np.linalg.norm(np.frombuffer(rotated, np.float32).reshape(-1, 3) -
                                   np.frombuffer(base, np.float32).reshape(-1, 3), axis=1)
            per_point = pairs.reshape(len(delta), -1, 2)
            influenced = ((per_point[:, :, 0] == joint_index) & (per_point[:, :, 1] > 0)).any(axis=1)
            moved = int(np.count_nonzero((delta > 1e-6) & influenced))
            if moved == 0:
                raise hou.Error('Rotation test failed: no vertices weighted to ' + joint_name + ' moved.')
            deform.setInput(2, pose, 0)
            test.destroy()
            test = None
            if deform.geometry().pointFloatAttribValuesAsString('P') != base:
                raise hou.Error('Restoring the original pose did not restore the mesh.')
            after = paint.geometryAtFrame(hou.frame(), 0).pointFloatAttribValuesAsString('boneCapture')
            if hashlib.sha256(after).hexdigest() != weight_hash:
                raise hou.Error('Painted-weight checksum changed; refusing to save.')
    except Exception:
        for i in range(3):
            deform.setInput(i, None)
        for i, n, output in old:
            deform.setInput(i, n, output)
        if test is not None:
            test.destroy()
        raise
    # Save the current session, including its existing unsaved edits, to v13.
    # No disk scene is loaded and no alternate .hip file is created.
    if save:
        hou.hipFile.save(str(current))
    result = {'saved': save, 'file': str(current), 'tested_joint': joint_name,
              'rotation_degrees': 12, 'weighted_vertices_moved': moved,
              'max_displacement': float(delta.max()), 'weights_sha256': weight_hash,
              'original_pose_restored': True, 'deform_errors': deform.errors()}
    print('Phoenix v13 repair verified:', result, flush=True)
    return result


if __name__ == '__main__':
    if not hou.isUIAvailable():
        raise hou.Error('Execute this script inside the open Houdini session to preserve unsaved edits.')
    repair()
