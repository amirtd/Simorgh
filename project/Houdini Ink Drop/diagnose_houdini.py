import hou

hou.hipFile.load(r"E:\Wirling Worlds\Houdini Ink Drop\ink_drop_effect.hipnc")
obj = hou.node('/obj/INK_DROP_EFFECT')
for frame in (1, 6, 12, 24, 30, 36, 48):
    hou.setFrame(frame)
    pts = obj.node('satellite_bubble_points').geometry().points()
    ids = [p.intAttribValue('satellite_id') for p in pts]
    children = [p.intAttribValue('split_child') for p in pts]
    print('frame', frame, 'satellites', len(pts), 'ids', ids, 'children', children,
          'pscale', [round(p.floatAttribValue('pscale'), 3) for p in pts])

bad = []
for n in obj.allSubChildren():
    try:
        if n.errors():
            bad.append((n.path(), n.errors()))
    except hou.OperationFailed:
        pass
print('node_errors', bad)

stage = hou.node('/stage/ink_drop_materials').stage()
for prim in stage.Traverse():
    path = str(prim.GetPath())
    if 'bubble' in path or path == '/ink_drop':
        rel = prim.GetRelationship('material:binding')
        print('usd', path, prim.GetTypeName(), [str(t) for t in rel.GetTargets()] if rel else [])
