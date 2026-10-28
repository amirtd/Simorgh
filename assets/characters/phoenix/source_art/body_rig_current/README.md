# Simplified Phoenix card rig

`phoenix_simple.hipnc` contains a deliberately basic six-card Phoenix:

- one combined body and neck (`body.png`)
- one head (`head_01.png`)
- one left wing and one right wing
- one tail
- one feet card (`foot_R.png`)

Select `/obj/PHOENIX_SIMPLE_RIG`. Each body-part tab exposes Offset X/Y, Rotation Offset, Scale, Layer Depth, and Pivot controls while the assembled character remains visible. Global card height, layer spacing, and alpha clipping controls are under **Simple Phoenix**.

Viewport controls are available at `/obj`:

- `PHX_BODY_CTRL` moves, rotates, or scales the whole character.
- `PHX_HEAD_CTRL`, `PHX_WING_L_CTRL`, `PHX_WING_R_CTRL`, `PHX_TAIL_CTRL`, and `PHX_FEET_CTRL` control individual cards.
- `PHX_BODY_NECK_CTRL` provides a local control for the combined body/neck card.
- Toggle all control shapes with `PHOENIX_SIMPLE_RIG > Simple Phoenix > Show Visual Rig Controls`.

Transparent pixels use masked alpha with a low cutoff so they do not occlude neighboring planes in Houdini's viewport.

To rebuild:

```powershell
& "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin\hython.exe" "E:\Wirling Worlds\Simorgh\assets\characters\phoenix\source_art\body_rig_current\build_simple_phoenix.py"
```
