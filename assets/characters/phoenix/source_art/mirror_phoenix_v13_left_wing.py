"""Fill missing right-wing weights from the live left-wing paint; save v13.
Run inside Houdini with runpy.run_path(..., run_name='__main__').
Original paint is retained upstream. Never loads a .hip or resets capture.
"""
from pathlib import Path
import hashlib
import hou
import numpy as np

WINGS = ('clavicle', 'wing_upper', 'wing_mid', 'wing_tip', 'primary_tip')


def pairs(geo):
    return np.frombuffer(geo.pointFloatAttribValuesAsString('boneCapture'), np.float32).reshape(geo.intrinsicValue('pointcount'), -1, 2)


def capture_names(geo):
    table = geo.findPointAttrib('boneCapture').indexPairPropertyTables()[0]
    return [table.stringPropertyValueAtIndex('pCaptPath', i) for i in range(table.numIndices())]


def install(save=True):
    expected = Path(__file__).resolve().with_name('phoenix_rig_v13_unbound_clean_01.hipnc')
    if Path(hou.hipFile.path()).resolve() != expected:
        raise hou.Error('Open the existing Phoenix v13 first; nothing changed.')
    skin = hou.node('/obj/PHOENIX_SKINNING')
    paint = skin.node('PAINT_WEIGHTS') if skin else None
    deform = skin.node('jointdeform1') if skin else None
    if not paint or not deform or not skin.node('REST') or not skin.node('POSE'):
        raise hou.Error('Expected Phoenix skinning nodes are missing.')
    if skin.node('MIRROR_LEFT_WING_TO_RIGHT'):
        raise hou.Error('Wing mirror already exists. Nothing replaced; animate POSE_JOINTS.')
    if deform.inputs()[0] != paint:
        raise hou.Error('Joint Deform has another skin-processing input. Stopped to preserve it.')
    if deform.errors():
        raise hou.Error('Resolve existing Joint Deform errors first.')
    original = paint.geometryAtFrame(hou.frame(), 0)
    original_hash = hashlib.sha256(original.pointFloatAttribValuesAsString('boneCapture')).hexdigest()
    names = capture_names(original)
    needed = [base + side for base in WINGS for side in ('_L', '_R')]
    if not all(name in names for name in needed):
        raise hou.Error('Expected wing capture names are missing.')
    rest = skin.node('REST').geometry()
    positions = {p.attribValue('name'): p.position() for p in rest.points()}
    plane = (positions['clavicle_L'][0] + positions['clavicle_R'][0]) * 0.5
    if positions['wing_upper_L'][0] <= plane or positions['wing_upper_R'][0] >= plane:
        raise hou.Error('Unexpected wing orientation. This script expects left +X, right -X.')
    old = [(c.inputIndex(), c.inputNode(), c.outputIndex()) for c in deform.inputConnections()]
    created, test = [], None
    try:
        with hou.undos.group('Mirror Phoenix left-wing paint to missing right-wing weights'):
            unpack = skin.createNode('captureattribunpack', 'READ_WING_PAINT_FOR_MIRROR'); created.append(unpack)
            unpack.setInput(0, paint, 0)
            mask = skin.createNode('attribwrangle', 'SELECT_UNWEIGHTED_RIGHT_WING'); created.append(mask)
            mask.setInput(0, paint, 0); mask.setInput(1, unpack)
            mask.parm('snippet').set('''vector q=@P; q.x=2.0*PLANE-@P.x;
int src=nearpoint(1,q);
string paths[]=detail(1,"boneCapture_pCaptPath");
int source_indices[]=point(1,"boneCapture_index",src);
float source_weights[]=point(1,"boneCapture_data",src);
int own_indices[]=point(1,"boneCapture_index",@ptnum);
float own_weights[]=point(1,"boneCapture_data",@ptnum);
string left[]=array("clavicle_L","wing_upper_L","wing_mid_L","wing_tip_L","primary_tip_L");
string right[]=array("clavicle_R","wing_upper_R","wing_mid_R","wing_tip_R","primary_tip_R");
int has_source=0, already_painted=0;
foreach(int i; int index; source_indices) {
 if(index>=0 && index<len(paths) && source_weights[i]>1e-7 && find(left,paths[index])>=0) has_source=1;
}
foreach(int i; int index; own_indices) {
 if(index>=0 && index<len(paths) && own_weights[i]>1e-7 && find(right,paths[index])>=0) already_painted=1;
}
i@__phoenix_right_wing_mirror=(@P.x<PLANE-1e-6 && has_source && !already_painted);
'''.replace('PLANE', repr(float(plane))))
            mirror = skin.createNode('capturemirror', 'MIRROR_LEFT_WING_TO_RIGHT'); created.append(mirror)
            mirror.setInput(0, mask)
            mirror.setParms({'group': '@__phoenix_right_wing_mirror=1', 'usegroupas': 1,
                             'mirrorop': 0, 'from': ' '.join(b+'_L' for b in WINGS),
                             'to': ' '.join(b+'_R' for b in WINGS), 'color': 0})
            mirror.parmTuple('origin').set((plane, 0, 0))
            mirror.parmTuple('dir').set((1, 0, 0))
            mirror.setComment('L-to-R wing weights across X=%g. Original PAINT_WEIGHTS is unchanged. Points already painted to right-wing joints are protected. Bypass to restore original weights.' % plane)
            result = mirror.geometry()
            if mirror.errors():
                raise hou.Error(str(mirror.errors()))
            target = np.frombuffer(result.pointIntAttribValuesAsString('__phoenix_right_wing_mirror'), np.int32).astype(bool)
            if not target.any():
                raise hou.Error('No unweighted right-wing points need mirroring; nothing saved.')
            assert capture_names(result) == names, 'Capture table changed unexpectedly'
            before, after = pairs(original), pairs(result)
            assert before.shape == after.shape, 'Capture storage changed unexpectedly'
            assert np.array_equal(before[~target], after[~target]), 'Weights outside the selected right-wing area changed'
            assert result.pointFloatAttribValuesAsString('P') == original.pointFloatAttribValuesAsString('P'), 'Mesh positions changed'
            right_index = names.index('wing_upper_R')
            assert np.any((after[:,:,0] == right_index) & (after[:,:,1] > 0)), 'No upper right-wing weights were produced'
            deform.setInput(0, mirror)
            baseline = deform.geometry().pointFloatAttribValuesAsString('P')
            assert not deform.errors(), str(deform.errors())
            test = skin.createNode('kinefx::rigpose', '__VERIFY_RIGHT_WING_ROTATION')
            pose_input = next(c for c in deform.inputConnections() if c.inputIndex() == 2)
            test.setInput(0, pose_input.inputNode(), pose_input.outputIndex())
            test.parm('transformations').set(1)
            test.parm('group0').set('@name=wing_upper_R')
            test.parmTuple('r0').set((0, 0, 12))
            deform.setInput(2, test)
            rotated = deform.geometry().pointFloatAttribValuesAsString('P')
            assert not deform.errors(), str(deform.errors())
            delta = np.linalg.norm(np.frombuffer(rotated,np.float32).reshape(-1,3)-np.frombuffer(baseline,np.float32).reshape(-1,3),axis=1)
            moved = int(np.count_nonzero(delta > 1e-6))
            assert moved > 0, 'Right-wing rotation did not deform the mesh'
            deform.setInput(2, pose_input.inputNode(), pose_input.outputIndex())
            test.destroy(); test = None
            assert deform.geometry().pointFloatAttribValuesAsString('P') == baseline, 'Original pose was not restored'
            assert hashlib.sha256(paint.geometry().pointFloatAttribValuesAsString('boneCapture')).hexdigest() == original_hash, 'Original painted cache changed'
            origin = paint.position()
            unpack.setPosition(origin+hou.Vector2(-4,-1)); mask.setPosition(origin+hou.Vector2(0,-1)); mirror.setPosition(origin+hou.Vector2(0,-2))
    except Exception:
        for i in range(3): deform.setInput(i,None)
        for i,n,out in old: deform.setInput(i,n,out)
        if test is not None: test.destroy()
        for node in reversed(created): node.destroy()
        raise
    if save:
        hou.hipFile.save(str(expected))
    print('Phoenix wing mirror verified: %d right-wing points selected; 12-degree wing_upper_R rotation moved %d vertices. Original paint and all weights outside the selection preserved. Pose restored. Saved=%s.' % (int(target.sum()),moved,save),flush=True)
    return mirror


if __name__ == '__main__':
    if not hou.isUIAvailable():
        raise hou.Error('Run inside the open Houdini session to preserve unsaved edits.')
    install()
