import hou

hou.hipFile.load(r"E:\Wirling Worlds\Houdini Ink Drop\ink_drop_effect.hipnc")
node = hou.node('/obj/INK_DROP_EFFECT/hero_air_bubble_animate')
for frame in (1, 6, 12, 24, 36, 48):
    hou.setFrame(frame)
    geo = node.geometry()
    apex = [p for p in geo.points() if sum(v*v for v in p.attribValue('rest')) < 1e-12]
    center = sum((p.position() for p in apex), hou.Vector3()) / len(apex)
    radius = max((p.position()-center).length() for p in apex)
    print(frame, len(apex), 'center', tuple(round(v, 6) for v in center),
          'top_radius', round(radius, 6))
