# Test Procedure

The builder includes structural checks, but artistic and render validation must be performed in Houdini.

## Automated structural check

Close any open copy of the generated hip, then run:

```powershell
& "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin\hython.exe" .\build_ink_drop.py --validate
```

Expected output lists frames 1, 6, 12, 24, 36, and 48 with nonzero point/primitive counts, layer IDs 0–5, a nonzero Z range, and changing average alpha. This verifies cooking and attributes, not appearance.

## Geometry and animation

1. Open `ink_drop_effect.hipnc` and look through `/obj/cam_ink_drop`.
2. Scrub frames 1–6: confirm a small drop forms at the top-center anchor.
3. Scrub 7–12: confirm the form stretches downward while the anchor stays stable.
4. Scrub 13–24: confirm the silhouette broadens, curls, and develops lower tendrils.
5. Scrub 25–48: confirm noisy regions soften, separate visually, drift, and fade.
6. Inspect `/obj/INK_DROP_EFFECT/OUT_INK_EFFECT` in the Geometry Spreadsheet. Confirm `uv`, `Cd`, `ink_alpha`, `layer_id`, and `shop_materialpath` exist.
7. Temporarily increase Depth Spacing. Confirm the six ink layers occupy distinct Z positions and do not flicker.

## PNG and material

1. Assign a known RGBA PNG containing saturated colors and transparent areas.
2. In Karma CPU, verify original PNG hues remain recognizable and PNG transparency cuts the ink.
   If the viewport shows flat blue proxy geometry, move the display flag to `/stage/ink_drop_materials` or later in the chain; `/stage/ink_drop_sopimport` intentionally displays the pre-material import.
3. Change Texture Repetition, Pattern Rotation, Texture Growth, and UV Distortion; confirm the pattern changes without changing the base silhouette dimensions.
4. Set Use Texture off; confirm Ink Tint replaces the image.
5. Test Base Opacity, Transmission, IOR, Fresnel/Coat, and Emission at modest values. Confirm soft transparent edges and highlights without an opaque plastic appearance.
6. Repeat a representative still in Karma XPU. Compare opacity and refraction to CPU; compensate artistically if the engines differ.

## Bubbles and dissolve

1. Set Bubble Count to 5 for easy inspection. Verify different radii, birth times, lateral motion, rise, and fade.
2. Move Dissolve Start Frame and shorten Dissolve Duration. Confirm all layers respond with staggered timing.
3. Raise Dissolve Noise Scale to confirm breakup into smaller islands; adjust Softness to confirm feathered boundaries.

## Solaris and integration

1. Inspect `/stage/ink_drop_sopimport`; confirm its source is `/obj/INK_DROP_EFFECT/OUT_INK_EFFECT` and the primitive prefix is `/ink_drop`.
2. Scrub the Stage at frames 1, 24, and 48 to confirm time-dependent SOP geometry updates.
3. Confirm the OBJ Geometry transform is identity and the Solaris composition has no unexpected scale or offset.
4. Import `OUT_INK_EFFECT` into an existing Stage with a separate SOP Import. Confirm existing Stage nodes remain intact.
5. If `/obj/WATER_RIPPLE` exists, enable Sync, change its compatible impact/start controls, and confirm the ink follows. Disable Sync and confirm independent controls work.
6. Render a short CPU sequence (frames 1–48 at low samples), then inspect for opacity sorting, intersections, flicker, texture swimming, and discontinuities.

## Validation status

Do not treat successful script execution as visual approval. Final color, transparency, alpha behavior, and CPU/XPU parity require actual Karma renders with the production PNG, camera, lighting, and water scene.
