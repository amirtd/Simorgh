# Persian 2.5D Ink Drop — After Effects

This is an editable After Effects counterpart to the Houdini ink-drop effect. It uses six Persian-pattern layers with independently animated masks, depth, opacity, edge turbulence, pattern transforms, glass highlights, staggered dissolution, and 32 animated spherical bubbles.

## Files

- `build_ink_drop_rig.jsx` — rerunnable After Effects project builder.
- `add_animated_water_background.jsx` — rerunnable animated underwater background add-on.
- `persian_ink_drop.aep` — generated After Effects 2026 project.
- `textures/persian_pattern.png` — embedded Persian RGBA artwork.
- `render/` — default PNG sequence destination.

## Main composition

`PERSIAN_INK_DROP_2_5D` is 1920×1080, 24 fps, and 48 frames long.

Animation stages:

- Frames 1–6: paint enters through the narrow top inlet and forms a small drop.
- Frames 7–12: a feathered top-down reveal carries the Persian pattern through the stretching body.
- Frames 13–24: body opens into a wide layered bloom.
- Frames 25–48: edges roughen, layers spread, and opacity dissolves.

Open `CTRL_INK_DROP` for the organized animator-facing values. The generated keyframes and effect controls on each `INK_LAYER_*` layer remain directly editable. Each layer contains `INK SILHOUETTE - NARROW TOP` plus an intersecting `TOP-DOWN PAINT FLOW` mask. `Top Neck Width`, `Top Neck Length`, and `Top-Down Paint Flow` document the intended proportions and direction; rebuild-time paths live in `silhouette()` and `revealShape()` in the JSX.

## Rebuild

In After Effects, choose **File → Scripts → Run Script File** and select `build_ink_drop_rig.jsx`. The script replaces only project items tagged as part of `INK_DROP_AE_RIG` and saves the generated project beside the script.

## Render

The builder adds the main composition to the Render Queue under `render/`. It uses a PNG-sequence template when one is installed and otherwise keeps the installed default H.264 module with an `.mp4` destination.

## Animated water background

Open `persian_ink_drop.aep`, then run `add_animated_water_background.jsx` through **File → Scripts → Run Script File**. It creates `WATER_CTRL`, a deep turquoise gradient, two animated caustic fields, seven drifting light rays, a surface shimmer, and five impact-ripple rings behind the ink. Rerunning the script replaces only layers whose names start with `WATER_`.

## Notes

The After Effects version uses native compositing effects rather than physically based MaterialX refraction. Turbulent Displace, Roughen Edges, Bevel Alpha, Glow, animated masks, 3D depth, and camera parallax approximate the translucent oil-in-water look while remaining lightweight and editable.

The bubble system is timed as a sudden impact burst: most bubbles appear within six frames of water entry, overshoot in scale, then rise and spread. Every bubble contains separate vector groups for the translucent body, inner glow, lower-right shadow, and upper-left specular highlight so it reads as a sphere rather than a flat ring.

`Bubble Radius` is expression-linked to every bubble's animated Scale. The Slider Control track visually ends at 100, but After Effects accepts typed values above 100: `180` is the designed size, `360` is 2×, and `500` is about 2.78×. `Bubble Count` is also live and hides bubbles above the chosen count without deleting them.
