# Phoenix main-body After Effects rig

This build uses the simplified artwork in `../source_art/body_rig_current/`.

Included body parts:

- combined body and neck
- head
- left wing
- right wing
- tail
- feet

Intentionally excluded:

- wing tips
- crests
- individual feathers

## Files

- `build_phoenix_main_body_rig.jsx` — generates the editable After Effects project.
- `phoenix_main_body_rig.aep` — generated project after the script runs.

The main composition is `PHOENIX_MAIN_BODY_RIG_1080P` at 1920×1080, 24 fps, and 10 seconds. Animate the `CTRL_` null layers; `CTRL_MASTER` moves the complete Phoenix.

To rebuild manually in After Effects, use **File → Scripts → Run Script File** and choose `build_phoenix_main_body_rig.jsx`.
