# Validation and review

The scene is built and rendered in Houdini 22.0.429 with a native Apprentice license. Apprentice's normal watermark/non-commercial restrictions remain in force.

## Repeat structural checks

From Houdini Command Line Tools, with the files kept together:

```text
hython validate_abstract_fish.py
```

The helper loads the saved scene without changing it and writes `validation.json`. It checks:

1. Every required geometry system exists and cooks to polygons.
2. Exactly 42 named ribbon groups are present: 6 head, 8 upper, 6 side, 4 pectoral, 3 pelvic, 3 anal, and 12 tail.
3. Original guide curves exist for all ribbon systems and have at least 24 samples (the builder uses 48).
4. Width, twist, and guide-normal point attributes exist on the original guides.
5. Every face has positive measured area above the tolerance; shells have no open/non-manifold edges.
6. Shared-edge winding is consistent, each named shell has positive signed volume, and smooth normals are present.
7. Every primitive uses a valid palette ID from 1 through 8.
8. Imported USD meshes exist and have resolved MaterialX material bindings.

The validator inspects the default configuration. It does not prove the absence of self-intersection at every possible control setting, and signed volume does not replace a visual silhouette check.

## Actual render checks

The builder's `--render` option uses the scene's native USD Render ROP. It verifies the existence and nonzero size of each requested PNG after the ROP returns. Renders use Karma CPU at 960×540 and 32 samples, respecting Apprentice licensing. A background render is not counted as complete until that process returns and its image exists.

Inspect `previews/material_id.png`, `wireframe.png`, `shaded.png`, and `three_quarter.png`. These are rendered images, not illustrations. Development iterations and intermediate previews are kept separately under `development/`; they are not the final deliverable.

The side Material ID camera uses a mirrored local X scale so the image faces left like the reference while geometry retains negative-X-facing coordinates and the camera remains on positive Y. Check the actual camera transform if exporting to a renderer that does not support mirrored camera transforms.

## Artistic checklist before animation

- Mouth and eye remain clear; cheek ribbons do not cover the pupil.
- Upper ribbons emerge from the back and have deliberate negative spaces.
- Side plates lie close to the curved body instead of floating away.
- Pectoral, pelvic, and anal fins have recognizable roots and tapered tips.
- Tail ribbons converge at the rear body before fanning upward, backward, and downward.
- Three-quarter view shows real depth, nonuniform shell thickness, and curved sections.
- Palette is flat in Material ID mode; shaded mode adds only basic lighting and roughness.
- Final framing includes the entire tail and fins.

Review the relative width of the head, side ribbon layering, intersections, and tail curl against the supplied screenshot. This version is intended for user review before animation or detailed material development.

## Completed validation on 2026-10-22

The saved scene passed the structural checks: **42 ribbons, 49 USD meshes, 41,254 polygons**, closed manifold shells, consistent outward winding, and resolved USD material bindings. All four 960×540 Karma CPU previews completed and were visually inspected for colors, framing, silhouette, and depth. See `render_validation.json` for the actual output files. The user’s artistic approval is still pending.
