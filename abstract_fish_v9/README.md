# OBJ orientation transfer to Stage — v9

Solaris now imports OUT_STAGE_FISH, a dedicated output that includes ABSTRACT_FISH's live OBJ world transform. The OBJ viewport still uses the local OUT_FISH output, preventing double transforms there. Translation, rotation, scale and parent transforms carry into Stage.

The saved v8 source had zero OBJ rotation. If your rotation correction is currently unsaved in the open Houdini scene, preserve it by running install_obj_stage_transform.py in Windows → Python Source Editor, then saving. This installer does not load or save a scene and keeps existing edits. The v9 scene includes the fix with the saved v8 orientation.

Validated with -90 degrees X plus translation: Stage USD world bounds match the transformed OBJ fish. Previous scenes are preserved.
