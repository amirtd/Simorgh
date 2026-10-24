# Individual ribbon mesh offsets — v7

Open `abstract_fish.hipnc`, select `/stage/FISH_CONTROLS`, and open **Individual Ribbon Offsets**. Choose a ribbon system, then the named ribbon. **Ribbon Position Offset XYZ** moves only that ribbon mesh and its matching guide in local fish space.

X moves along the fish, Y adjusts depth, and Z adjusts height. Zero restores the original position. Large adjustments can detach a ribbon from the body because the complete ribbon, including its root, is translated. Offsets are applied before swimming and motion-path placement. Texture UVs remain unchanged and move with the mesh. No per-ribbon UV offset controls are added.

All 42 decorative ribbon meshes have individual controls. Body and eyes remain unchanged. Existing swimming, path and global texture controls are preserved. Keep the textures folder alongside the scene. Earlier scene versions remain unchanged.
