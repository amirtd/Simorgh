# Phoenix feather flows — Houdini

Guide curves traced from `ref/feather_flow_ref.png`, resampled into feather roots, randomized, and populated with procedural feathers.

## Native selectable-joint rig

`phoenix_kinefx_joint_rig.hipnc` is a separate native KineFX rig. Select
`/obj/phoenix_kinefx_rig/RIG_POSE_SELECT_AND_KEY`, press Enter in the viewport,
select any joint, and use the transform handle. Key the Rig Pose translate or
rotate channels normally. The captured body and feather geometry follows the
posed hierarchy. Procedural wind and automatic flapping are disabled in this file.

`Roots Only Preview` defaults on for responsive posing. Turn it off on
`/obj/phoenix_kinefx_rig` to cook and display the complete feathers.
Open the scene with `.\open_phoenix_kinefx_rig.ps1`.

## Phoenix character rig

`build_phoenix_character_rig.py` wraps the existing procedural wing in a non-destructive character scene. It creates:

- a named, KineFX-compatible body/wing/leg joint hierarchy in `/obj/phoenix_character_rig/REST_SKELETON`
- a lightweight 3D body proxy for proportion and pose blocking
- mirrored live-linked copies of `/obj/feather_flow_guides/OUT_FEATHER_SHAPES`
- shoulder, elbow, wrist, twist, feather-flex, body, neck, and head controls on `/obj/phoenix_character_rig`
- a **Feather Growth Completion** control (`0` = furled/not grown, `1` = fully grown), defaulting to `1`
- automatic flapping that can be disabled for hand-keyed animation

Build and open the derivative rig scene without changing `phoenix_birth.hipnc`:

```powershell
& "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin\hython.exe" build_phoenix_character_rig.py
.\open_phoenix_rig.ps1
```

Useful outputs are `OUT_SKELETON`, `OUT_BODY_PROXY`, `OUT_RIGGED_WINGS`, `OUT_WING_BOUNDARY`, and `OUT_PHOENIX_CHARACTER`. The body proxy is intentionally simple; replace it with the final body mesh and retain the named skeleton hierarchy. `OUT_WING_BOUNDARY` is a lightweight static mesh with shoulder, elbow, and wrist influence attributes; it follows the same rig controls as the feather wing and can be shown or hidden with **Show Wing Boundary**. **Wing Boundary Position Offset** moves both boundary meshes together in character-local space. **Wing Boundary Thickness** makes them closed solids, while **Wing Boundary Bevel Radius** rounds the silhouette and thickness edges.

`Show Body Proxy` defaults to off. `Wind Physics Strength` is an animatable 0–1 control on `/obj/phoenix_character_rig`: 1 applies the full procedural wind deformation, intermediate values blend it down, and 0 removes wind deformation entirely. It defaults to 0.

The rig opens in a neutral, unanimated pose: Auto Flap is off and the wing joint/flex controls default to zero. `Roots Only Preview` defaults on and avoids cooking the full feather meshes while posing. Turn it off for full-feather viewport display and final output.

The feather wing and roots are converted into character-local space before deformation. Moving or rotating `/obj/phoenix_character_rig` in the viewport carries the skeleton, roots, and full feather geometry together.

For flight and landing poses, **Body Center Position/Rotation** moves the complete character inside the rig. Independent **Left/Right Foot Position/Rotation** controls use a two-bone leg solve, so translating a foot bends its knee while retaining the leg lengths. The toe-curl controls rotate the toes around each ankle.

Each bird foot has a central, inner, outer, and rear hallux digit. **Toe Curl** bends the three forward digits together, **Toe Spread** fans the inner/outer digits, and **Hallux Curl** controls the rear gripping digit independently.

**Left/Right Leg World Pin** is a keyable 0–1 space switch for planted-foot animation. At 0 the leg follows the body normally; at 1 the ankle, foot, and toes remain fixed in rig/world space while the hip follows the body and the knee resolves between them. Intermediate values blend between those behaviors, which is useful for easing into and out of a landing pose.

`Shoulder Open/Sweep Y` rotates around Houdini's Y axis, opening the mirrored wings outward in Z. `Flap Offset` remains the up/down rotation around X.

## Open in Houdini

```powershell
& "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin\houdini.exe" "E:\Hirling Worlds\HIRLING WORLDS\houdini\phoenix\phoenix_birth.hipnc"
```

The script updates whichever of `phoenix_birth.hipnc` / `phoenix_birth.hip` was saved most recently.

Look through `cam_flow_guides`.

## Rebuild from script

```powershell
$hy = "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin\hython.exe"
& $hy build_phoenix.py          # rebuilds only /obj/feather_flow_guides inside the existing hip
& $hy build_phoenix.py --full   # fresh hip with only the feather flow system
```

The default mode keeps any manual edits outside `feather_flow_guides`. The original radial-birth wires (`/obj/phoenix_birth`) were removed and are not rebuilt.

## Feather flow guides

`/obj/feather_flow_guides` holds 9 guide curves drawn over a dimmed copy of the painting.

- Reshape flows in `FEATHER_FLOWS` in `build_phoenix.py` (pixel coordinates, root → tip)
- `OUT_FLOW_GUIDES`: `flow_id`, `flow_name`, `Cd`, `curveu`, `tangentu`, `N`, `band_profile`
- `hython preview_flow_guides.py` redraws `ref/feather_flow_guides_preview.png` and `ref/feather_copies_preview.png`

## Feathers along the guides

Four overlapping feather systems, each in its own subnet (`layer_primaries`, `layer_secondaries`, `layer_coverts`, `layer_down`), merged in `MERGE_LAYERS`, then shared `apply_bend` → `organic_noise` → `feather_color`.

Inside each layer subnet: `guide_resample` → `feather_roots` → Attribute Randomize chain → `apply_randomize` → `copy_feathers`.

| Layer | Length | Coverage (flow root → tip) | Depth | Look |
|---|---|---|---|---|
| primaries | 1.7 | whole flow, sparse | back | long, narrow, darker |
| secondaries | 1.1 | whole flow | 2nd | the main body |
| coverts | 0.55 | first half | 3rd | shorter, wider, lighter |
| down | 0.28 | first 30% | front | tiny, pale, very splayed |

Per-layer controls live on each subnet's `feather_roots` (spacing via `guide_resample`, rows, length, splay, band spread, Flow Start/End/Fade, Layer Depth, Color Ramp Shift, Color Tint), `apply_randomize` (Layer Width) and `feather_prototypes` (Segments). Defaults come from `FEATHER_LAYERS` in `build_phoenix.py`; add a fifth entry there for another layer.

| Attribute Randomize node | Attribute | Default range | Applied as |
|---|---|---|---|
| `rand_length` | `len_mult` | 0.8 – 1.2 | multiplies `pscale` |
| `rand_width` | `width_mult` | 0.75 – 1.3 | `scale.x` (mirrored per side) |
| `rand_bend` | `bend` | -0.08 – 0.15 | sideways tip offset × feather length, after copy |
| `rand_overlap` | `overlap` | 0 – 1 | tucks root back (`overlap_tuck`) and shuffles depth (`overlap_depth`) |
| `rand_rotation` | `rot_jitter` | -6° – 6° | rotates `N` around the view axis |

`organic_noise` (VEX noise, after bend):

| Parameters | Effect |
|---|---|
| Edge Frequency / Edge Wobble | slow swelling and pinching of the vane outline |
| Barb Frequency / Barb Raggedness | fine ragged cuts along the edge |
| Split Threshold / Split Depth | occasional deep splits that pull back toward the root |
| Shaft Wander Frequency / Shaft Wander | per-feather shaft curvature (root stays planted) |
| Flow Wave Frequency / Flow Wave | shared sway so neighbouring feathers bend together |
| Seed | re-rolls all noise |

`feather_color` samples **Color Ramp** (teal → green → peach → red) with a lookup built from:

| Parameter | Driver |
|---|---|
| Position Weight + Gradient Direction | canvas position (default: bottom → top, slightly toward +X) |
| Flow (curveu) Weight | shoulder (flow root) vs flow tip; tips move toward teal |
| Feather Root→Tip Weight | position inside each feather; tips warm up |
| Noise Amount / Frequency / Seed | painterly breakup of the bands |
| Per-Feather Jitter | small per-feather shift so neighbours differ |
| Contrast / Ramp Offset | spread and slide the lookup across the ramp |
| Ramp vs Painting Color | 1 = ramp only, 0 = colors sampled from the reference painting |
| Layer Tint Color | what positive per-layer Color Tint blends toward (cream by default) |

The lookup is stored as `color_lookup` for debugging (visualize it to see the raw 0–1 driver).

To rebuild inside an open Houdini session (keeps unsaved edits elsewhere), run in Windows → Python Shell:

```python
import sys, importlib; sys.path.insert(0, r"E:\Hirling Worlds\HIRLING WORLDS\houdini\phoenix")
import build_phoenix as bp; importlib.reload(bp); bp.rebuild_in_session()
```

- `feather_roots`: feathers per sample, base length, splay, painting vs guide color mix
- `feather_prototypes`: 4 variants; each has a vane (quad strips shaft → edge, with `uv`), shaft strip, outline curve and shaft curve
- `OUT_FEATHER_SHAPES`: vanes + shafts (displayed), with `uv`, `fcolor`, `fseed` and `shop_materialpath`
- `OUT_FEATHER_CURVES`: outline + shaft curves with `curveu` (for draw-on growth)
- `show_ref` / `show_guides` switches toggle the painting and the guide tubes

## Oil-run growth

`oil_growth` (right after `MERGE_LAYERS`) animates the feathers as if poured at the root and running toward the tip like thinned oil: paint reaches the flow shoulders first and runs out along the flows, back layers first. Frames 1 – 200 by default (**Progress** is an expression; keyframe it to retime).

| Parameters | Effect |
|---|---|
| Start / End Frame, Progress | global timing (0 = nothing poured, 1 = all settled) |
| Run Time | how long one feather takes to run out |
| Flow Delay / Layer Delay / Birth Jitter | order: shoulder → tip, back layer → front, randomness |
| Viscosity | fast start, slowing finish (higher = more sluggish ending) |
| Surges / Surge Strength | stop-and-go pulses of the running front |
| Front Lobe Frequency / Front Lobes | uneven, lobed leading edge |
| Sideways Spread Lag | vane opens this far behind the front (narrow tongue at the head) |
| Head Swell | bulbous pooled paint at the running head |
| Wet Length | how far behind the front the paint reads wet (`wet` attribute) |

It re-folds each feather from its rest shape (`lp`, `lxc` from the prototype), so bend, organic noise and color downstream still apply. Outline/shaft curves grow with it.

## Wing beat and wind

Settings live on the orange `WING_CONTROLS` null; two wrangles read them:

- `wing_wind` (after `apply_bend`, before `organic_noise`): external wind — gusts plus turbulence drifting downwind — and the air the beating wing moves through (rising pushes feathers down, falling pushes them up). Each feather bends with the air component across it, tips most, sampled at the root so it bends as one piece; still-growing feathers are softer. Adds a small per-feather flutter. Stores `wind` (air speed across the feather).
- `wing_flap` (after `paint_attribs`, so painted bands ride with the wing): rotation about the shoulder pivot. The angle grows toward the tip (Tip Flex) and lags behind the shoulder (Tip Lag), so the wing flexes like a slow wave. The beat starts at Beat While Small and builds to full strength as `oil_growth` progresses, then keeps beating after the wing has settled.

| Wing Beat | Default | Wind | Default |
|---|---|---|---|
| Shoulder Pivot | reference px (1010, 230) | Wind Direction | (-1, -0.5, 0): along the flows, slightly down |
| Wing Span | 5.5 | Wind Speed / Gusts / Gust Frequency | 0.8 / 0.6 / 0.35 Hz |
| Beat Angle | 4° | Turbulence Scale / Turbulence | 0.4 / 0.5 |
| Beat Period | 4 s | Wing-Beat Airflow | 1 (0 = only external wind) |
| Tip Flex / Tip Lag | 0.5 / 1.1 rad | Feather Flex / Growing Softness | 0.12 / 1.5 |
| Beat While Small | 0.25 | Flutter / Flutter Frequency | 0.02 / 3 Hz |

## Oil-paint shader

Feather uvs: `u` runs across the vane (left edge 0, shaft 0.5, right edge 1), `v` runs root → tip. Every row of vane quads joins a shaft point to the edge point at the same `v`, so lines of constant `v` follow the swept barbs.

`/mat/feather_paint` (Karma MaterialX builder):

| Node | Role |
|---|---|
| `feather_uv` → `streak_scale` (4, 90) | stretches noise across `u`, squeezes it along `v` → strokes along the barbs |
| `feather_seed` (`fseed`) | third noise axis, so neighbouring feathers get different strokes |
| `barb_streaks` / `barb_contrast` | fine strokes (remap out 0.62 – 1.22 = stroke strength) |
| `brush_bands` / `brush_contrast`, `hue_drift` | broad strokes, ± small hue shifts between them |
| `bristles` | very fine bristle grooves (impasto only) |
| `paint_saturation` | saturation × 1.55 |
| `dry_brush` / `dry_strength` | vane edges break up over the dark `ground_color` |
| `wet_paint` (`wet`) → `wet_darken`, `wet_roughness`, `wet_specular` | fresh paint at the running front is darker and glossier |
| `impasto_height` → `impasto` (bump 0.04) | raised strokes; also drives the coat normal (coat 0.12) |

`/mat/canvas_paint`: dark umber/oxblood ground with loose horizontal strokes and canvas grain, on `OUT_CANVAS` (render only; the viewport keeps the reference image).

`fcolor` is a copy of `Cd` (Cd becomes `displayColor` in USD). Stroke direction/density: `streak_scale`; paint thickness: `impasto` scale.

Render in `/stage`: `paint_feathers` + `paint_canvas` (SOP Import) → `paint_materials` (binds `feather_paint` to `/feathers`, `canvas_paint` to `/canvas`) → `paint_camera` → `paint_dome` / `paint_key` → `paint_karma` (1070×720, CPU, 12 spp) → `paint_render`. Render `paint_render` (current frame; set its frame range for the animation) or open a Karma viewport on `paint_camera`; output is `$HIP/render/feather_paint.$F4.png`, roughly 30–40 s per frame. SOP Import ignores the object's `tx = 7`, so `paint_camera` sits at the origin.
