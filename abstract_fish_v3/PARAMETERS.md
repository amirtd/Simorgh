# Stage master controls

Select **/stage/FISH_CONTROLS** to edit all fish controls in Solaris. The OBJ parameters documented below are linked to this master and update the same values. Wind uses static procedural deflection; zero restores the unforced shape. Flat Ribbons creates actual zero-thickness single surfaces. Per-system controls cover each head/body/fin/tail system.

# New in v2: network-visible wind and surface controls

Dive into `/obj/ABSTRACT_FISH` and select **RIBBON_FORCE_CONTROLS**. Press **P** if the parameter pane is hidden.

- **Wind Force / Deflection**: static tip displacement in scene units, default 0. Increase gradually, for example 0.2–0.5.
- **Wind Direction XYZ**: normalized direction; default (0,1,0) pushes toward the side camera. Use (0,0,1) to lift tips or (1,0,0) to sweep them toward the tail.
- **Ripple Amount**: extra sinusoidal bending along each guide, default 0.2.
- **Ripple Frequency** and **Ripple Seed**: control the number and phase of the ripples.
- **Root Pin Falloff**: default 2. Higher values keep more of the root region still.
- **Flat Ribbons**: switches every decorative ribbon to a single zero-thickness surface with curl and twist removed. Guide paths remain curved.
- **Ribbon Thickness**: global multiplier; 0 is a genuine single surface, 1 is the approved original thickness.
- **Ribbon Curl**: scales cross-section arch and edge curl; 0 removes both.
- **Ribbon Twist Strength**: scales authored twist and the Additional Ribbon Twist control; 0 removes twist.

The surface controls shown on the geometry object are linked to the same controls on the blue force node. Select an individual system node for its local Thickness/Curl/Twist multipliers or Flatten This System toggle. A global Flat Ribbons toggle overrides all local thickness/curl/twist values until turned off.

These are artistic procedural bending controls, not Newton-based dynamic forces. They update without running a solver. They can be keyframed later, but the scene contains no keyframes or automatic motion.

# Fish parameters and editing

Select `/obj/ABSTRACT_FISH` and open **Ribbon Fish Controls**.

- **Ribbon Width Multiplier** (`width`, default 1, range 0.25–2): scales ribbon cross-sections while retaining finite tapered ends.
- **Ribbon Length Multiplier** (`length`, 1, 0.5–1.5): stretches ribbon guide displacements from their attachment roots. It does not extend the underlying body.
- **Ribbon Curvature** (`curvature`, 1, 0.2–1.8): scales departure from each guide's root-to-tip chord.
- **Additional Ribbon Twist** (`twist`, 0 degrees, -60–60): adds a smooth twist envelope to each ribbon's authored profile.
- **Tail Spread** (`tailspread`, 1, 0.4–1.5): changes vertical fan spread around tail roots.
- **Fin Spread** (`finspread`, 1, 0.4–1.5): changes vertical extension of the three lower-fin systems.
- **Body Length Multiplier** (`bodylength`, 1, 0.7–1.3): scales body/ribbon X coordinates around the mouth. Eye placement follows the same mouth-anchored length scale.
- **Body Thickness Multiplier** (`bodythickness`, 1, 0.5–1.8): scales body depth and ribbon depth placement. Eye depth placement follows the same scale.
- **Color Variation** (`colorvariation`, 0, 0–1): gently varies palette brightness; exact base palette at zero. Vertex display colors and rendered MaterialX palette brightness respond independently.
- **Presentation**: Material ID (unlit solid colors), Wireframe + Guides, or Shaded (diffuse/specular, roughness 0.48).

The body is ivory. Material IDs are: 01 crimson #C72D38; 02 coral #EF745F; 03 gold #E9A64B; 04 ivory #F1E3C8; 05 turquoise #3E9FAD; 06 pale blue #A5CBD4; 07 deep teal #236A76; 08 muted orange #D66B39. Hex palette values are converted from sRGB to linear shader colors. Output color management can alter their displayed appearance slightly.

## Individual ribbons

The standalone builder's `SYSTEMS` lists define each ribbon's control points and defaults. H01–H06 are the head, U01–U08 the upper body, S01–S06 the side, F01_01–04 the pectoral fin, F02_01–03 the pelvic fin, F03_01–03 the anal fin, and T01–T12 the tail.

The public function is:

```python
create_ribbon(name, control_points, width_profile, thickness, twist,
              material_id, depth_offset, geo=None, system='ribbon',
              controls=None, guides=False, edge_curl=0.05,
              conform=False, surface_normal=(0, 1, 0))
```

`control_points` are world-space XYZ tuples. `width_profile` is an interpolated sequence of full widths. `twist` is a sequence of degrees. `conform` places the centerline near the visible body surface; it is useful for cheek and side plates. `edge_curl` controls cross-sectional curl. The guide normal defines the initial sweep frame.

For a local Houdini edit, open a system Python SOP's code and edit the final `execute(...)` specification list. Both surfaces and matching guides have their own copies; edit both to keep them synchronized. For coordinated changes, edit the builder and create a new version. Primitive `control_points` is descriptive JSON metadata; editing that attribute alone does not recook the guide.

Every ribbon has a primitive group, `material_id`, `system`, `shop_materialpath`, and actual cooked-root `attachment`. `rest` and `ribbon_uv` are point attributes. Original guide points also contain `width`, `twist`, and `guide_normal`. These provide the data needed for later controlled deformation; no rig or animation channels are currently installed.
