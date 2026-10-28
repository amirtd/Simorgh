# Fish v5 — visual motion-path rig

Open `abstract_fish.hipnc`. Select `/stage/FISH_CONTROLS` → **Motion Path Rig**.

1. Click **Edit Visual Path Controls**. This switches the network to OBJ and selects the six cyan `FISH_PATH_POINT_01` through `06` controls. In the viewport, select an individual control and use the Translate handle to shape the visible curved path. Point 01 starts the path; point 06 ends it. Avoid overlapping consecutive points.
2. Return to `/stage/FISH_CONTROLS`. Keyframe **Path Progress**: 0 starts the path, 1 finishes it. Set keys at your desired start/end frames. Use linear interpolation for steady travel; ease the keys to accelerate or stop. Progress uses sampled curve distance for approximately uniform speed.
3. **Face Along Path** turns the fish toward its direction of travel, keeping its back upward. For custom banking, keyframe the rotation of `/obj/FISH_MOTION_CTRL`; its native transform handles also provide a local offset and scale. Turn off **Face Along Path** for entirely manual orientation.
4. Swimming Motion retains the body ripple and independent **Swim Speed**. Motion Path Rig controls where the whole fish travels; swim speed controls the body cycle.

**Follow Motion Path** can be disabled for free animation using `FISH_MOTION_CTRL`. **Show Visual Rig** toggles the cyan Stage guide curve and waypoint rings. These guides have USD `guide` purpose and stay out of normal Karma renders. The editable native OBJ null controls remain available when the Stage guide is hidden.

The new scene starts at progress 0 with no travel keys, ready for your animation. The existing cameras are fixed: reframe or animate a camera for longer paths. Earlier v4 files are unchanged. No bones or skin weights are required; placement is applied after the existing procedural swimming deformation, so all fish parts remain together.

To update an already open v4 scene while retaining unsaved edits, open `install_path_rig.py` in Houdini's Python Source Editor and Run, then save manually. It refuses to replace an existing path rig. The installer does not load or save a scene.
