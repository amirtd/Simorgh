# Abstract ribbon fish — first geometry review

A static, editable Houdini 22 scene inspired by the supplied Phoenix/Simorgh fish reference. It contains a continuous ivory body, 42 curved ribbon shells, paired eyes, eight MaterialX colors, side and three-quarter cameras, and three presentation modes. No textures, animation, displacement, or external assets are required.

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

The reusable `create_ribbon(...)` function uses interpolated guide curves and a swept local frame, rather than flat rectangular strips. Each ribbon has 48 longitudinal stations, eight width segments, independently interpolated width and twist, a domed/curling cross-section, and variable physical thickness. Root and tip widths remain small and positive to avoid collapsed faces. Top/bottom grids and side/end caps form a closed polygon shell.

Body and eye meshes are separate. Meshes carry primitive groups and material IDs. Guide and mesh attributes include attachment position, serialized control points, rest positions, ribbon coordinates, width, and guide twist/normal information. The roots blend into their body attachment regions before the fins/tail fan outward.

## Review scope

This is a first geometry version for visual approval, not a pixel match. The supplied screenshot was consulted for the left-facing silhouette, layered palette, flowing fins, and curled tail. Ribbon intersections and the balance of negative space should still receive artistic review, especially before bending or animation. Broad parameter changes can introduce overlap even though the default topology is valid.

The scene is static. Rest coordinates, separate systems, original guide curves, and attachment attributes prepare it for a later head/body/tail rig. No animation or detailed material work has been added.
