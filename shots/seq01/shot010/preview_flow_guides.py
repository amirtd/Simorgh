"""Draw the feather flow guides and the copied feathers over the reference painting.

Run with:
  hython preview_flow_guides.py
"""

import os

from PySide6 import QtCore, QtGui

import build_phoenix as bp

try:
    hou  # type: ignore[name-defined]
except NameError:
    import hou  # type: ignore

GUIDES_OUT = os.path.join(bp.ROOT, "review", "feather_flow_guides_preview.png")
FEATHERS_OUT = os.path.join(bp.ROOT, "review", "feather_copies_preview.png")


def world_to_px(x: float, y: float) -> QtCore.QPointF:
    return QtCore.QPointF(x / bp.REF_SCALE + bp.REF_W * 0.5, bp.REF_H * 0.5 - y / bp.REF_SCALE)


def point_px(point) -> QtCore.QPointF:
    p = point.position()
    return world_to_px(p[0], p[1])


def _qcolor(rgb, gain=1.0) -> QtGui.QColor:
    return QtGui.QColor.fromRgbF(*(max(0.0, min(c * gain, 1.0)) for c in rgb))


def _canvas(dim_alpha: int) -> tuple[QtGui.QImage, QtGui.QPainter]:
    img = QtGui.QImage(bp.REF_IMAGE).convertToFormat(QtGui.QImage.Format_ARGB32)
    painter = QtGui.QPainter(img)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.fillRect(img.rect(), QtGui.QColor(0, 0, 0, dim_alpha))
    return img, painter


def draw_guides() -> None:
    geo = hou.node("/obj/feather_flow_guides/OUT_FLOW_GUIDES").geometry()
    img, painter = _canvas(110)

    for prim in geo.prims():
        pts = [point_px(v.point()) for v in prim.vertices()]
        color = _qcolor(prim.attribValue("Cd"), 1.15)
        path = QtGui.QPainterPath(pts[0])
        for p in pts[1:]:
            path.lineTo(p)

        for pen_color, width in ((QtGui.QColor(0, 0, 0, 200), 9), (color, 5)):
            pen = QtGui.QPen(pen_color, width)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawPath(path)

        painter.setBrush(color)
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 2))
        painter.drawEllipse(pts[0], 9, 9)

        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold))
        painter.drawText(pts[len(pts) // 2] + QtCore.QPointF(6, -10), prim.attribValue("flow_name"))

    painter.end()
    img.save(GUIDES_OUT)
    print("Saved:", GUIDES_OUT)


def draw_feathers() -> None:
    geo = hou.node("/obj/feather_flow_guides/OUT_FEATHER_SHAPES").geometry()
    img, painter = _canvas(235)

    # Vanes are many small quads: read attributes in bulk and flat-fill each quad with its
    # average Cd. Antialiasing off so neighbouring quads don't leave hairline seams.
    pos = geo.pointFloatAttribValues("P")
    cd = geo.pointFloatAttribValues("Cd")
    faces = [[v.point().number() for v in prim.vertices()] for prim in geo.prims()]
    faces.sort(key=lambda f: min(pos[i * 3 + 2] for i in f))

    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
    painter.setPen(QtCore.Qt.NoPen)
    for face in faces:
        poly = QtGui.QPolygonF([world_to_px(pos[i * 3], pos[i * 3 + 1]) for i in face])
        avg = [sum(cd[i * 3 + c] for i in face) / len(face) for c in range(3)]
        painter.setBrush(_qcolor(avg))
        painter.drawPolygon(poly)

    painter.end()
    img.save(FEATHERS_OUT)
    print("Saved:", FEATHERS_OUT)


def main() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])  # noqa: F841 (fonts need an app)
    hou.hipFile.load(bp.HIP_OUT, suppress_save_prompt=True)
    draw_guides()
    draw_feathers()


if __name__ == "__main__":
    main()
