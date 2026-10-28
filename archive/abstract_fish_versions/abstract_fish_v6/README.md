# Fish v6 — image texture and planar UVs

Open `abstract_fish.hipnc`. Select `/stage/FISH_CONTROLS` → **Texture and Color**.

The supplied image is bundled in `textures/fish_pattern.png`. Body uses the original image with a white color multiplier. Fins, head surfaces and decorative ribbons use the same image with a dark blue multiplier. Eyes retain their original materials for readability.

Planar UVs default to the XZ side plane, fitted individually to each named part. Projection is generated before swimming/path movement so the texture stays attached to the fish. Choose XZ, XY or YZ; adjust tiling, offsets and rotation as desired. This is planar projection, so surfaces perpendicular to the plane can stretch.

Network-visible Stage controls include Texture Image, Enable Image Texture, Planar UV Plane, UV Tile U/V, UV Offset U/V, UV Rotation, Body Color, Other Parts Dark Blue Tint, independent tint strengths and brightness. Tint Strength 0 restores the source image colors; 1 applies the selected color fully. Disable Image Texture to return to the original eight-color materials. Use Shaded presentation to view the texture with lighting.

Swimming controls and the visual motion-path rig are preserved. Previous versions are unchanged. Keep the textures folder alongside the scene when moving the project.
