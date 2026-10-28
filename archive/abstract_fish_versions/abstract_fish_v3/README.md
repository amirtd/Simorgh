# Version 3: Solaris Stage controls

Open `abstract_fish.hipnc`, go to **/stage**, and select the blue **FISH_CONTROLS** node. It is wired immediately before `fish_geometry` in the Solaris chain.

The Stage node is now the master for wind, flat/curl/thickness/twist, ribbon width/length/curvature, body proportions, fin/tail spread, palette variation, presentation mode, and each individual ribbon system’s overrides. The existing OBJ controls remain linked to it; they are not independent duplicate values.

This version was upgraded from the latest saved v2 scene instead of rebuilding the fish, preserving its saved values and geometry. It was checked for unchanged guide positions, live Stage wind updates, pinned roots, flat-surface updates, persistence after reload, and successful Solaris cooking. No new animation or material changes were made. Earlier previews are available in the sibling v2 folder.

## Add controls to an already open scene

If you prefer to keep working in an open v2 scene, use **Windows → Python Source Editor**, open `stage_controls.py`, and Run. The installer adds the Stage node in place without loading or saving a scene, so current unsaved edits remain in memory. Save manually afterward. It refuses to replace an unrelated existing FISH_CONTROLS node and safely returns an existing controller that it created previously.

## Rebuild a new version

`build_abstract_fish.py` includes the Stage installer and remains standalone. Run in a fresh Houdini 22 shell with `--output-dir` pointing to a new folder. Existing scenes and preview files are protected.

---

# Abstract ribbon fish v2 — wind, curl and flat-surface controls

A static, editable Houdini 22 scene inspired by the supplied Phoenix/Simorgh fish reference. It contains a continuous ivory body, 42 curved ribbon shells, paired eyes, eight MaterialX colors, side and three-quarter cameras, and three presentation modes. No textures, animation, displacement, or external assets are required.

## New control node

Inside `/obj/ABSTRACT_FISH`, select the blue **RIBBON_FORCE_CONTROLS** node. Its parameter pane exposes wind strength, XYZ direction, ripple amount/frequency/seed, root pin falloff, and the ribbon flat/curl/thickness/twist controls.

Wind is a static procedural deflection in scene units. Strength zero restores the original shape. Roots stay pinned while the tips deflect; no simulation or automatic animation is added. **Flat Ribbons** removes thickness, cross-section curl and authored twist while keeping flowing guide paths. A zero Thickness slider produces a single polygon surface instead of collapsed top/bottom faces. The continuous body and eyes remain solid.

Per-system overrides are on the HEAD_SURFACES, UPPER_RIBBONS, SIDE_RIBBONS and fin/tail Python SOP nodes under Surface Shape Overrides. Both the rendered surface and its matching guides follow these overrides.

The saved scene opens with wind strength zero and Flat Ribbons off. `previews/flat_wind_preview.png` is an actual rendered demonstration with Flat Ribbons on and wind deflection 0.35; these preview settings are not saved over the default scene. The original v1 scene remains untouched in the sibling `abstract_fish` folder.

Open **abstract_fish.hipnc** in Houdini 22. It was generated with Houdini **22.0.429 Apprentice**, so the native non-commercial format and rendered watermark are retained. There is no license conversion. The existing ink-drop project was not modified.

The final preview images are in `previews/`:

- `material_id.png`: unlit MaterialX palette, side view.
- `wireframe.png`: sparse actual mesh edges and original guide curves rendered as thin polygon tubes.
- `shaded.png`: the same geometry with moderate roughness and basic lighting.
- `three_quarter.png`: perspective depth and attachment review.

## Run the standalone builder

In Houdini 22 Command Line Tools:

```text
hython build_abstract_fish.py --render --output-dir /path/to/a/new/fish_version
```

On this Ubuntu workstation:

```bash
cd /opt/hfs22.0.429
source ./houdini_setup
hython /home/amir/Documents/ChatGPT/Phoenix/abstract_fish/build_abstract_fish.py --render --output-dir /home/amir/Documents/ChatGPT/Phoenix/abstract_fish_v2
```

Without `--render`, the script builds, validates, and saves the scene. Existing destination scene/preview files are protected; use a new output directory. The builder is self-contained: its ribbon runtime is embedded into Python SOPs, so a saved scene can be moved without this script, textures, or the original reference image. The validation helper imports the builder and should remain beside it.

Run in a fresh hython process. It does not clear an existing project or replace existing fish networks. The script intentionally refuses an existing output file. Edits to its control-point lists are your non-destructive source design; the original curves and cooked surfaces remain separately inspectable in the saved scene.

## Network

`/obj/ABSTRACT_FISH` contains the requested BODY_BASE, HEAD_SURFACES, UPPER_RIBBONS, SIDE_RIBBONS, PECTORAL_FIN, PELVIC_FIN, ANAL_FIN, TAIL_UPPER, TAIL_MIDDLE, TAIL_LOWER, EYES, and FINAL_MERGE nodes.

Each ribbon system has a `_GUIDES` node and a `_NORMALS` node. The guides are merged at ALL_GUIDE_CURVES. PRESENTATION_VIEW selects solids or wire tubes. OUT_FISH is the render/display output. Select the geometry object for the Ribbon Fish Controls and Presentation menus.

MaterialX builders are `/mat/fish_01` through `/mat/fish_08`. The Solaris chain under `/stage/fish_*` imports the geometry and assigns its materials. `/stage/fish_render` is the native USD Render ROP; its saved configuration renders the side Material ID preview. No remote queue is involved.

## Coordinates and cameras

Geometry uses X for length, Y for depth, and Z for up. The mouth is at X=-2.5; the tail extends to approximately X=3.5. The body depth is approximately 0.65. Decorative surfaces predominantly occupy the camera-facing positive-Y side. This is intentionally a side-view sculpture, not a symmetric realistic fish.

The side camera is at (0,12,0), looking toward the origin with world Z up. Its local X scale is mirrored for left-facing reference presentation while retaining the requested negative-X head and positive-Y camera. This is a presentation transform; object coordinates are unchanged. A small film offset centers the sculpture. The three-quarter camera is at (-9,17,5) with a conventional, unmirrored projection.

`/obj/FISH_SIDE` and `/obj/FISH_THREE_QUARTER` are viewport cameras. Matching Solaris cameras are under `/cameras/` in the USD stage. The saved default is the Material ID presentation. The side/three-quarter render camera can be selected on `/stage/fish_render_settings`.

## Geometry method

The reusable `create_ribbon(...)` function uses interpolated guide curves and a swept local frame, rather than flat rectangular strips. Each ribbon has 48 longitudinal stations, eight width segments, independently interpolated width and twist, a domed/curling cross-section, and variable physical thickness. Root and tip widths remain small and positive to avoid collapsed faces. With nonzero thickness, top/bottom grids and side/end caps form a closed polygon shell. At zero thickness only one smooth surface is generated; its boundary edges are intentional.

Body and eye meshes are separate. Meshes carry primitive groups and material IDs. Guide and mesh attributes include attachment position, serialized control points, rest positions, ribbon coordinates, width, and guide twist/normal information. The roots blend into their body attachment regions before the fins/tail fan outward.

## Review scope

This is a first geometry version for visual approval, not a pixel match. The supplied screenshot was consulted for the left-facing silhouette, layered palette, flowing fins, and curled tail. Ribbon intersections and the balance of negative space should still receive artistic review, especially before bending or animation. Broad parameter changes can introduce overlap even though the default topology is valid.

The scene is static. Rest coordinates, separate systems, original guide curves, and attachment attributes prepare it for a later head/body/tail rig. No animation or detailed material work has been added.
