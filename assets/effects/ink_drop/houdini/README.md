# Procedural 2.5D Ink Drop — Houdini 22

`build_ink_drop.py` builds a closed 3D hero air bubble from a hand-shaped curve revolved around Y. Its tip stays anchored while the teardrop grows downward. Smaller bubbles begin outside the hero surface, scale up with it, accelerate upward with controllable left/right wobble, static depth variation and turbulence, and one splits into two on cue. They do not orbit or inherit a spin from the hero bubble. All bubbles use the reflective/refractive MaterialX shell. Camera, lights, and a Solaris/Karma chain are included.

## Build

From PowerShell:

```powershell
& "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin\hython.exe" .\build_ink_drop.py --validate
```

This writes `ink_drop_effect.hipnc` beside the script. Apprentice will keep its normal non-commercial restrictions.

From an open Houdini scene, use **Windows → Python Source Editor**, open the script, and press **Run**, or run this in the Python Shell:

```python
import sys, importlib
sys.path.insert(0, r"E:\Wirling Worlds\Simorgh\assets\effects\ink_drop\houdini")
import build_ink_drop
importlib.reload(build_ink_drop)
build_ink_drop.rebuild_in_session()
```

The in-session entry point does not save. Save manually after review. Rerunning replaces only `/obj/INK_DROP_EFFECT`, `/obj/cam_ink_drop`, `/mat/ink_drop_mtl`, `/mat/ink_bubble_mtl`, and `/stage/ink_drop_*`. Other scene and Stage nodes are preserved.

## Texture

The supplied `textures/persian_pattern.png` is assigned by default. Select `/obj/INK_DROP_EFFECT`, open **Persian Texture**, and choose another RGBA PNG for **Persian Pattern Texture** if needed. RGB remains the pattern color and PNG alpha multiplies the procedural cloud/dissolve alpha. Repetition, rotation, independent texture growth, distortion, and drift are exposed beside it.

If no PNG is assigned, disable **Use Texture** to use the **Ink Tint** procedural color.

## Render

- SOP output: `/obj/INK_DROP_EFFECT/OUT_INK_EFFECT`
- OBJ camera: `/obj/cam_ink_drop`
- Solaris camera: `/cameras/ink_drop`
- Karma settings: `/stage/ink_drop_karma`
- Render ROP: `/stage/ink_drop_render`
- Hero bubble panel: `/stage/ink_drop_hero_bubble_controls`
- Default output: `$HIP/render/ink_drop.$F4.png`

The supplied render settings default to Karma CPU. In Houdini, switch the Karma render settings engine to XPU for an XPU test. The ink layers have a small physical SOP thickness and use a MaterialX glass-oriented standard surface. Reflection, transmission and IOR refraction controls are exposed on `/stage/ink_drop_materials` under **Ink Glass Controls**. Exact transparent/refraction and dispersion results can differ between CPU and XPU, so verify both in the target Houdini production build.

Animate the single bubble's growth range, final radius, overshoot, XYZ location, rise, skid, wobble and XYZ scale directly on `/stage/ink_drop_hero_bubble_controls`. The same Stage node exposes Reflection, Roughness, Transmission, Refraction IOR, Refraction Roughness, Coat and Thin Walled controls for the air-bubble MaterialX shell.

## Water ripple integration

If `/obj/WATER_RIPPLE` exists when the builder runs, enabling **Sync With /obj/WATER_RIPPLE** lets the ink's start frame and horizontal impact position reference compatible ripple parameters. The builder only reads those parameters and never modifies the water network. If no compatible water node or parameters exist, the ink controls remain independent.

## Design notes

- No FLIP or volume simulation is used.
- Mesh topology remains stable across the animation to avoid popping.
- Growth is calculated from the top-center anchor instead of object-center scaling. A controllable neck profile keeps the upper inlet narrow while the lower cloud gradually opens.
- Layer delay, independent noise seeds, depth offsets, and per-layer dissolve delay create the 2.5D volume.
- Organic opacity and a polar boundary prevent the appearance of rectangular image cards.
- Geometry is authored directly at SOP scale; the Geometry object remains at identity to prevent SOP Import double transforms.

See [PARAMETERS.md](PARAMETERS.md) for controls and [TESTING.md](TESTING.md) for validation.
