# Paper ribbon fish — v8

Open `abstract_fish.hipnc`. Select `/stage/FISH_CONTROLS` → **Paper Ribbons**.

All 42 decorative ribbons are now zero-thickness polygon sheets with no cross-section curl. They retain a gentle twist along their length and use the colorful eight-color paper palette. The fish body retains the supplied texture; disable Use Colorful Paper Palette to use the image on ribbons again.

Paper Length defaults to 1.45 times the previous length. Wind Flexibility defaults to 3 for a stronger response to the Wind Force settings. Paper Flutter Amount and Flutter Speed add animated, tip-weighted flutter when wind strength is nonzero. Roots remain pinned within the ribbon generator; individual mesh offsets can still move a complete ribbon. Wind strength defaults to 0.14.

This is procedural wind deformation for lightweight-looking motion, not a mass-based cloth simulation. It needs no simulation cache. Set wind strength to 0 to remove wind and flutter. Existing body swimming and motion-path controls remain independent.

All previous per-ribbon mesh offset controls are preserved. Longer ribbons may overlap; use Individual Ribbon Offsets to adjust placement. Keep textures alongside the scene. Earlier scene versions remain unchanged.
