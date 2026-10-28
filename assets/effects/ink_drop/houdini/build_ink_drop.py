"""Build a lightweight procedural 2.5D ink-drop effect for Houdini 22.

Run from Houdini's Python Source Editor, Python Shell, or with hython.  The
builder is deliberately self-contained and safe to rerun: it replaces only
the nodes that it owns (INK_DROP_EFFECT, ink_drop_* and ink_* materials).
"""

from __future__ import annotations

import os
import sys

try:
    hou  # type: ignore[name-defined]
except NameError:
    import hou  # type: ignore


OWNER = "ink_drop_builder_v1"
GEO_PATH = "/obj/INK_DROP_EFFECT"
MAT_PATH = "/mat/ink_drop_mtl"
BUBBLE_MAT_PATH = "/mat/ink_bubble_mtl"
STAGE_MAT_NODE = "/stage/ink_drop_materials"
HERO_CTL_NODE = "/stage/ink_drop_hero_bubble_controls"
DEFAULT_TEXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "textures", "persian_pattern.png").replace("\\", "/")
LAYER_COUNT = 6
OWNED_STAGE = (
    "ink_drop_sopimport", "ink_drop_bubble_controls", "ink_drop_hero_bubble_controls", "ink_drop_materials", "ink_drop_camera",
    "ink_drop_dome", "ink_drop_key", "ink_drop_karma", "ink_drop_render",
)


# Houdini displays ParmTemplate help as the hover tooltip and in the F1 help
# popup. Keep the copy here so Stage and SOP controls stay consistent.
CONTROL_HELP = {
    "hero_start_frame": "Frame when the hero bubble begins growing from the pinned top point.",
    "hero_end_frame": "Frame when the hero bubble reaches its final size.",
    "hero_radius": "Target radius of the hero bubble after growth finishes.",
    "hero_overshoot": "Adds a brief elastic size overshoot near the end of growth.",
    "hero_pos_x": "Horizontal position of the hero bubble's pinned top point.",
    "hero_pos_y": "Vertical position of the hero bubble's pinned top point.",
    "hero_pos_z": "Depth position of the hero bubble's pinned top point.",
    "hero_rise": "Upward speed of the hero bubble after growth begins, in scene units per second.",
    "hero_skid": "Maximum side-to-side travel of the hero bubble.",
    "hero_skid_frequency": "Number of hero-bubble side-to-side cycles per second.",
    "hero_wobble": "Strength of the animated deformation across the hero bubble surface.",
    "hero_wobble_scale": "Spatial scale of the hero surface deformation; higher values make smaller ripples.",
    "hero_wobble_speed": "Playback speed of the hero surface deformation.",
    "hero_pin_length": "Distance below the apex over which motion and wobble fade in, keeping the top fixed.",
    "hero_top_widen_start": "Frame when the upper neck begins widening.",
    "hero_top_widen_end": "Frame when the upper neck reaches its final width.",
    "hero_top_width": "Additional final width applied to the upper neck.",
    "hero_top_widen_falloff": "Distance down the neck affected by the widening deformation.",
    "hero_scale_x": "Horizontal scale of the hero bubble around its pinned top point.",
    "hero_scale_y": "Vertical scale of the hero bubble around its pinned top point.",
    "hero_scale_z": "Depth scale of the hero bubble around its pinned top point.",
    "satellite_count": "Number of small bubbles generated around the hero bubble.",
    "satellite_radius": "Final average radius of the surrounding bubbles.",
    "satellite_radius_variation": "Random size variation around Final Radius; 0 makes every bubble the same size.",
    "satellite_spread": "Minimum empty space between a surrounding bubble and the current hero-bubble surface.",
    "satellite_birth_spread": "Randomizes births across this many frames after the hero growth starts.",
    "satellite_rise_speed": "Initial upward speed of each surrounding bubble, in scene units per second.",
    "satellite_up_force": "Adds upward acceleration after each surrounding bubble is born.",
    "satellite_wobble": "Maximum independent left/right drift. This does not rotate bubbles around the hero.",
    "satellite_wobble_frequency": "Number of left/right wobble cycles per second.",
    "satellite_orbit": "Maximum randomized front/back placement offset. It is static and does not create orbiting motion.",
    "satellite_split_frame": "Frame when the first surrounding bubble divides into two children.",
    "satellite_split_separation": "Final distance between the two children created by the split.",
    "satellite_turbulence": "Strength of small organic, non-orbiting positional noise.",
    "satellite_seed": "Changes randomized placement, size, birth time, phase and depth without changing the other settings.",
    "hero_reflection": "Strength of reflections on the air-bubble shell.",
    "hero_roughness": "Blurs reflections; lower values produce sharper highlights.",
    "hero_transmission": "Amount of light passing through the air-bubble shell.",
    "hero_ior": "Index of refraction used to bend light through the bubble shell.",
    "hero_refraction_roughness": "Blurs objects seen through the bubble shell.",
    "hero_coat": "Strength of the clear outer reflective coating.",
    "hero_coat_roughness": "Blurs reflections from the clear coat layer.",
    "hero_thin_walled": "Treats the shell as having no solid interior; faster and appropriate for a thin air-bubble film.",
}


def _set(node, parm, value):
    """Set a parameter if this Houdini build exposes it."""
    p = node.parm(parm)
    if p is not None:
        try:
            p.set(value)
        except hou.PermissionError:
            # Some HDAs expose computed/read-only companion parameters (for example
            # resolution Y when it is derived from camera aspect ratio).
            pass
    return p


def _set_tuple(node, parm, value):
    p = node.parmTuple(parm)
    if p is not None:
        try:
            p.set(value)
        except hou.PermissionError:
            pass
    return p


def _node(parent, type_name, name):
    n = parent.createNode(type_name, name)
    n.setUserData("ink_drop_owner", OWNER)
    return n


def _wrangle(parent, name, code, input_node=None, run_over="points"):
    n = _node(parent, "attribwrangle", name)
    if input_node is not None:
        n.setInput(0, input_node)
    _set(n, "class", {"points": 2, "prims": 1, "detail": 0}[run_over])
    _set(n, "snippet", code)
    return n


def _null(parent, name, input_node):
    n = _node(parent, "null", name)
    n.setInput(0, input_node)
    return n


def _separator(label):
    return hou.SeparatorParmTemplate("sep_" + label.lower().replace(" ", "_"), label)


def _float(name, label, default, lo, hi, folder, help_text=""):
    help_text = help_text or CONTROL_HELP.get(name, "")
    p = hou.FloatParmTemplate(name, label, 1, default_value=(default,), min=lo, max=hi,
                              min_is_strict=False, max_is_strict=False, help=help_text)
    folder.addParmTemplate(p)


def _int(name, label, default, lo, hi, folder, help_text=""):
    help_text = help_text or CONTROL_HELP.get(name, "")
    p = hou.IntParmTemplate(name, label, 1, default_value=(default,), min=lo, max=hi,
                            min_is_strict=False, max_is_strict=False, help=help_text)
    folder.addParmTemplate(p)


def _toggle(name, label, default, folder, help_text=""):
    help_text = help_text or CONTROL_HELP.get(name, "")
    folder.addParmTemplate(hou.ToggleParmTemplate(name, label, default_value=default, help=help_text))


def add_interface(geo):
    group = geo.parmTemplateGroup()
    old = group.find("ink_drop_controls")
    if old is not None:
        group.remove("ink_drop_controls")

    root = hou.FolderParmTemplate("ink_drop_controls", "Ink Drop Controls",
                                  folder_type=hou.folderType.Tabs)

    anim = hou.FolderParmTemplate("ink_anim", "Animation")
    _int("start_frame", "Start Frame", 1, -1000, 1000, anim)
    _int("form_end", "Form End", 6, 1, 200, anim)
    _int("stretch_end", "Stretch End", 12, 2, 300, anim)
    _int("cloud_end", "Cloud End", 24, 3, 500, anim)
    _int("end_frame", "End Frame", 48, 4, 1000, anim)
    _float("motion_speed", "Motion Speed", 1.0, 0.0, 4.0, anim)
    _float("impact_x", "Impact X", 0.0, -20.0, 20.0, anim)
    _float("impact_y", "Impact Y", 1.65, -20.0, 20.0, anim)
    root.addParmTemplate(anim)

    shape = hou.FolderParmTemplate("ink_shape", "Cloud Shape")
    _float("cloud_width", "Cloud Width", 2.6, 0.1, 10.0, shape)
    _float("cloud_height", "Cloud Height", 3.8, 0.1, 12.0, shape)
    _float("top_neck_width", "Top Neck Width", 0.16, 0.02, 1.0, shape,
           "Keeps the attachment side narrow while the body opens below it.")
    _float("top_neck_length", "Top Neck Length", 0.34, 0.02, 0.9, shape,
           "Fraction of the drop height used for the gradual neck-to-cloud transition.")
    _float("edge_noise", "Edge Noise", 0.24, 0.0, 1.0, shape)
    _float("noise_scale", "Noise Scale", 1.7, 0.05, 10.0, shape)
    _float("turbulence", "Turbulence", 0.32, 0.0, 2.0, shape)
    _float("curl_amount", "Curl Amount", 0.36, 0.0, 2.0, shape)
    _float("tendril_amount", "Tendril Amount", 0.42, 0.0, 2.0, shape)
    _int("radial_segments", "Radial Segments", 28, 6, 96, shape)
    _int("angular_segments", "Angular Segments", 96, 12, 256, shape)
    root.addParmTemplate(shape)

    depth = hou.FolderParmTemplate("ink_depth", "Layer Depth")
    _int("layer_count", "Visible Layers", 6, 1, LAYER_COUNT, depth)
    _float("depth_spacing", "Depth Spacing", 0.035, 0.002, 0.5, depth)
    _float("depth_drift", "Depth Drift", 0.018, 0.0, 0.25, depth)
    _float("parallax", "Parallax", 0.08, 0.0, 1.0, depth)
    root.addParmTemplate(depth)

    tex = hou.FolderParmTemplate("ink_texture", "Persian Texture")
    tex.addParmTemplate(hou.StringParmTemplate(
        "persian_texture", "Persian Pattern Texture", 1,
        default_value=(DEFAULT_TEXTURE,),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Image,
        help="RGBA PNG. Its RGB and alpha are both used by the MaterialX shader."))
    _toggle("use_texture", "Use Texture", True, tex)
    _float("texture_repeat", "Texture Repetition", 1.0, 0.1, 12.0, tex)
    _float("texture_rotation", "Pattern Rotation", 0.0, -180.0, 180.0, tex)
    _float("texture_growth", "Texture Growth", 0.35, -2.0, 2.0, tex)
    _float("uv_distortion", "UV Distortion", 0.035, 0.0, 0.5, tex)
    _float("uv_animation", "UV Animation Speed", 0.18, -3.0, 3.0, tex)
    root.addParmTemplate(tex)

    dissolve = hou.FolderParmTemplate("ink_dissolve", "Dissolve")
    _int("dissolve_start", "Dissolve Start Frame", 25, -1000, 1000, dissolve)
    _int("dissolve_duration", "Dissolve Duration", 24, 1, 500, dissolve)
    _float("dissolve_scale", "Dissolve Noise Scale", 3.5, 0.05, 30.0, dissolve)
    _float("dissolve_softness", "Dissolve Softness", 0.22, 0.001, 1.0, dissolve)
    _float("dissolve_turbulence", "Dissolve Turbulence", 0.55, 0.0, 3.0, dissolve)
    _float("final_opacity", "Final Opacity", 0.0, 0.0, 1.0, dissolve)
    _float("fragment_drift", "Fragment Drift", 0.30, 0.0, 3.0, dissolve)
    root.addParmTemplate(dissolve)

    bubbles = hou.FolderParmTemplate("ink_bubbles", "Bubbles")
    _toggle("enable_bubbles", "Enable Bubbles", True, bubbles)
    _int("bubble_count", "Bubble Count", 34, 0, 500, bubbles)
    _float("bubble_radius", "Bubble Radius", 0.055, 0.002, 0.5, bubbles)
    _float("bubble_rise", "Bubble Rise Speed", 0.62, 0.0, 5.0, bubbles)
    _float("bubble_spread", "Bubble Spread", 0.85, 0.0, 5.0, bubbles)
    _float("bubble_lifetime", "Bubble Lifetime", 30.0, 1.0, 240.0, bubbles)
    _float("bubble_radius_variation", "Radius Variation", 0.60, 0.0, 1.0, bubbles)
    _float("bubble_birth_frame", "Birth Frame", 7.0, -1000.0, 1000.0, bubbles)
    _float("bubble_birth_duration", "Birth Duration", 10.0, 0.0, 240.0, bubbles)
    _float("bubble_start_x", "Start X", 0.0, -20.0, 20.0, bubbles)
    _float("bubble_start_y", "Start Y", -0.25, -20.0, 20.0, bubbles)
    _float("bubble_start_depth", "Start Depth", 0.0, -10.0, 10.0, bubbles)
    _float("bubble_skid", "Left / Right Skid", 0.18, 0.0, 5.0, bubbles)
    _float("bubble_skid_frequency", "Skid Frequency", 1.35, 0.0, 10.0, bubbles)
    _float("bubble_ripple", "Ripple Orbit Amount", 0.07, 0.0, 2.0, bubbles)
    _float("bubble_ripple_frequency", "Ripple Frequency", 1.8, 0.0, 12.0, bubbles)
    _float("bubble_turbulence", "Bubble Turbulence", 0.05, 0.0, 2.0, bubbles)
    _float("bubble_fade_in", "Fade In Frames", 3.0, 0.1, 60.0, bubbles)
    _float("bubble_fade_out", "Fade Out Frames", 8.0, 0.1, 120.0, bubbles)
    _int("bubble_seed", "Bubble Seed", 17, 0, 100000, bubbles)
    _separator_hero = hou.SeparatorParmTemplate("hero_bubble_separator", "Single Hero Air Bubble")
    bubbles.addParmTemplate(_separator_hero)
    _float("hero_start_frame", "Hero Growth Start", 1.0, -1000.0, 1000.0, bubbles)
    _float("hero_end_frame", "Hero Growth End", 24.0, -999.0, 2000.0, bubbles)
    _float("hero_radius", "Hero Final Radius", 1.35, 0.01, 20.0, bubbles)
    _float("hero_overshoot", "Growth Overshoot", 0.12, 0.0, 1.0, bubbles)
    _float("hero_pos_x", "Hero Position X", 0.0, -20.0, 20.0, bubbles)
    _float("hero_pos_y", "Hero Position Y", 0.9, -20.0, 20.0, bubbles)
    _float("hero_pos_z", "Hero Position Z", 0.0, -20.0, 20.0, bubbles)
    _float("hero_rise", "Hero Rise Speed", 0.45, -5.0, 5.0, bubbles)
    _float("hero_skid", "Hero Left / Right Skid", 0.16, 0.0, 5.0, bubbles)
    _float("hero_skid_frequency", "Hero Skid Frequency", 0.7, 0.0, 10.0, bubbles)
    _float("hero_wobble", "Surface Wobble", 0.045, 0.0, 1.0, bubbles)
    _float("hero_wobble_scale", "Wobble Scale", 2.4, 0.1, 20.0, bubbles)
    _float("hero_wobble_speed", "Wobble Speed", 0.65, 0.0, 10.0, bubbles)
    _float("hero_pin_length", "Top Pin Falloff", 0.38, 0.01, 2.0, bubbles,
           "Profile distance below the apex over which motion and wobble fade in.")
    _float("hero_top_widen_start", "Top Widen Start", 24.0, -1000.0, 2000.0, bubbles)
    _float("hero_top_widen_end", "Top Widen End", 48.0, -999.0, 4000.0, bubbles)
    _float("hero_top_width", "Final Top Width", 0.32, 0.0, 3.0, bubbles)
    _float("hero_top_widen_falloff", "Top Widen Falloff", 0.58, 0.01, 2.28, bubbles,
           "Distance down the profile affected by widening.")
    _float("hero_scale_x", "Scale X", 1.0, 0.01, 5.0, bubbles)
    _float("hero_scale_y", "Scale Y", 1.08, 0.01, 5.0, bubbles)
    _float("hero_scale_z", "Scale Z", 1.0, 0.01, 5.0, bubbles)
    _int("satellite_count", "Satellite Bubble Count", 8, 0, 40, bubbles)
    _float("satellite_radius", "Satellite Radius", 0.19, 0.01, 2.0, bubbles)
    _float("satellite_radius_variation", "Satellite Radius Variation", 0.45, 0.0, 1.0, bubbles)
    _float("satellite_spread", "Outside Surface Gap", 0.32, 0.0, 5.0, bubbles)
    _float("satellite_birth_spread", "Satellite Birth Spread", 6.0, 0.0, 48.0, bubbles)
    _float("satellite_rise_speed", "Satellite Rise Speed", 0.65, -5.0, 10.0, bubbles)
    _float("satellite_up_force", "Upward Acceleration", 0.45, -5.0, 10.0, bubbles)
    _float("satellite_wobble", "Satellite Wobble", 0.16, 0.0, 3.0, bubbles)
    _float("satellite_wobble_frequency", "Satellite Wobble Frequency", 1.3, 0.0, 12.0, bubbles)
    _float("satellite_orbit", "Depth Offset", 0.08, 0.0, 2.0, bubbles)
    _float("satellite_split_frame", "Split Frame", 22.0, -1000.0, 2000.0, bubbles)
    _float("satellite_split_separation", "Split Separation", 0.24, 0.0, 3.0, bubbles)
    _float("satellite_turbulence", "Satellite Turbulence", 0.06, 0.0, 2.0, bubbles)
    _int("satellite_seed", "Satellite Seed", 41, 0, 100000, bubbles)
    root.addParmTemplate(bubbles)

    mats = hou.FolderParmTemplate("ink_materials", "Materials")
    mats.addParmTemplate(hou.FloatParmTemplate("ink_color", "Ink Tint", 4,
        default_value=(0.12, 0.36, 0.82, 1.0), min=0.0, max=1.0,
        look=hou.parmLook.ColorSquare, naming_scheme=hou.parmNamingScheme.RGBA))
    _float("base_opacity", "Base Opacity", 0.68, 0.0, 1.0, mats)
    _float("glass_thickness", "Glass Geometry Thickness", 0.018, 0.001, 0.25, mats,
           "Small physical depth for true refraction when Thin Walled is disabled.")
    _float("roughness", "Roughness", 0.22, 0.0, 1.0, mats)
    _float("transmission", "Transmission", 0.34, 0.0, 1.0, mats)
    _float("ior", "Index of Refraction", 1.18, 1.0, 2.5, mats)
    _float("fresnel", "Fresnel / Coat", 0.24, 0.0, 1.0, mats)
    _float("emission", "Emission", 0.0, 0.0, 10.0, mats)
    root.addParmTemplate(mats)

    water = hou.FolderParmTemplate("ink_water", "Water Integration")
    _toggle("sync_water", "Sync With /obj/WATER_RIPPLE", False, water)
    _toggle("create_stage", "Build Optional Solaris Setup", True, water)
    water.addParmTemplate(hou.LabelParmTemplate("water_status", "Status",
        column_labels=("When enabled, Impact X and Start Frame reference WATER_RIPPLE if compatible parameters exist.",)))
    root.addParmTemplate(water)

    group.append(root)
    geo.setParmTemplateGroup(group)


MESH_VEX = r'''
int nr = max(2, chi("../radial_segments"));
int ns = max(12, chi("../angular_segments"));
int center = addpoint(0, set(0, -1, 0));
setpointattrib(0, "restuv", center, set(0.5, 0.5, 0), "set");
for (int ring = 1; ring <= nr; ring++) {
    float rr = float(ring) / nr;
    for (int j = 0; j < ns; j++) {
        float a = 2 * PI * float(j) / ns;
        vector uvw = set(0.5 + 0.5 * rr * cos(a), 0.5 + 0.5 * rr * sin(a), 0);
        int p = addpoint(0, set(rr * cos(a), -1 + rr * sin(a), 0));
        setpointattrib(0, "restuv", p, uvw, "set");
        setpointattrib(0, "ring", p, rr, "set");
        setpointattrib(0, "angle", p, a, "set");
    }
}
for (int j = 0; j < ns; j++) {
    int p1 = 1 + j;
    int p2 = 1 + (j + 1) % ns;
    addprim(0, "poly", center, p1, p2);
}
for (int ring = 2; ring <= nr; ring++) {
    int a0 = 1 + (ring - 2) * ns;
    int b0 = 1 + (ring - 1) * ns;
    for (int j = 0; j < ns; j++) {
        int jn = (j + 1) % ns;
        addprim(0, "poly", a0+j, b0+j, b0+jn, a0+jn);
    }
}
'''


def layer_vex(layer):
    return r'''
int L = %d;
float seed = 17.31 + L * 91.7;
float f = @Frame;
float start = chf("../start_frame");
float a = smooth(start, chf("../form_end"), f);
float b = smooth(chf("../form_end"), chf("../stretch_end"), f);
float c = smooth(chf("../stretch_end"), chf("../cloud_end"), f);
float age = max(0, f - start) / 24.0 * chf("../motion_speed");
float lag = L * 0.035;
float grow = clamp(a * (1.0-lag) + b * 0.18 + c * 0.14, 0, 1.25);
float rr = f@ring;
float ang = f@angle;
float edge = smooth(0.65, 1.0, rr);

// Stable animated vector turbulence; top-center remains pinned by multiplying with rr.
vector q = set(v@restuv.x * chf("../noise_scale") + L*2.1,
               v@restuv.y * chf("../noise_scale") - age*0.22, seed);
vector nv = curlnoise(q + set(0, age*0.15, age*0.07));
float rim = snoise(set(cos(ang), sin(ang), seed + age*0.32) * 1.7);
float tendril = pow(max(0, -sin(ang)), 4.0) * (0.35 + 0.65*smooth(0.25, 1, c));
tendril *= (0.5 + 0.5*sin(ang*5 + seed));
float radial = 1 + edge * chf("../edge_noise") * rim + edge * chf("../tendril_amount") * tendril;

vector lp = set((v@restuv.x*2-1) * radial, (v@restuv.y*2-1) * radial - 1, 0);
// A persistent narrow inlet at the top.  `down` is zero at the top-center
// attachment and one at the bottom; the smooth profile lets the ink widen
// gradually below the inlet instead of forming a broad mushroom cap.
float down = clamp(-lp.y * 0.5, 0, 1);
float neck_len = max(0.02, chf("../top_neck_length"));
float neck_profile = lerp(chf("../top_neck_width"), 1.0,
                          smooth(0.0, neck_len, down));
// Hold the inlet even tighter during early formation, then allow only the
// lower body to gain the full cloud width during the bloom stage.
float lower_open = lerp(0.72, 1.0, smooth(neck_len*0.35, neck_len*1.8, down) * c);
lp.x *= neck_profile * lower_open;
float width = chf("../cloud_width") * (0.18*a + 0.82*grow) * (0.90 + L*0.027);
float height = chf("../cloud_height") * (0.10*a + 0.35*b + 0.55*grow) * (0.92 + L*0.018);
// Stretch stage is narrow and long; cloud stage broadens later.
width *= lerp(0.38, 1.0, c);
height *= lerp(0.50, 1.0, b);
@P.x = chf("../impact_x") + lp.x * width * 0.5;
@P.y = chf("../impact_y") + lp.y * height * 0.5;
@P += nv * rr * chf("../turbulence") * smooth(0.05, 0.7, grow);
@P.x += sin(@P.y*2.2 + age*1.7 + L) * chf("../curl_amount") * rr * c * 0.18;
@P.z = (L - 2.5) * chf("../depth_spacing") + nv.z * chf("../depth_drift");
@P.x += @P.z * chf("../parallax");

float layer_delay = L * 0.7;
float dp = clamp((f - chf("../dissolve_start") - layer_delay) / max(1, chf("../dissolve_duration")), 0, 1);
float dn = snoise(set(@P.x, @P.y, seed) * chf("../dissolve_scale") +
                   set(age*0.11, -age*chf("../dissolve_turbulence"), 0));
float cut = smooth(dp - chf("../dissolve_softness"), dp + chf("../dissolve_softness"), dn*0.5+0.5);
float edge_soft = 1 - smooth(0.78, 1.03, rr + rim*0.08);
float final_alpha = chf("../final_opacity");
f@ink_alpha = chf("../base_opacity") * edge_soft * lerp(1.0, final_alpha, dp) * cut;
f@ink_alpha *= (L < chi("../layer_count"));
@P += normalize(set(lp.x, lp.y+0.6, nv.z+0.01)) * dp * (1-cut) * chf("../fragment_drift") * rr;

float rot = radians(chf("../texture_rotation")) + L*0.035;
float cs=cos(rot), sn=sin(rot);
vector2 tuv = set(v@restuv.x-0.5, v@restuv.y-0.5);
tuv *= chf("../texture_repeat") / max(0.1, 1 + chf("../texture_growth")*c);
tuv = set(tuv.x*cs-tuv.y*sn, tuv.x*sn+tuv.y*cs);
tuv += set(nv.x, nv.y) * chf("../uv_distortion") + set(age*chf("../uv_animation")*0.02, -age*0.01);
v@uv = set(tuv.x+0.5, tuv.y+0.5, 0);
vector tint = chv("../ink_color");
float var = fit(snoise(set(@P.x*0.8, @P.y*0.8, seed)), -1, 1, 0.72, 1.18);
@Cd = clamp(tint * var * lerp(0.82, 1.15, float(L)/5.0), 0, 1);
i@layer_id = L;
''' % layer


BUBBLE_VEX = r'''
int count = chi("../bubble_count");
float start = chf("../bubble_birth_frame");
float birth_duration = chf("../bubble_birth_duration");
float life = max(1, chf("../bubble_lifetime"));
float seed = chi("../bubble_seed");
for (int i=0; i<count; i++) {
    float sid = i + seed * 101.37;
    float birth = start + rand(sid*31.71)*birth_duration;
    float agef = @Frame - birth;
    if (agef < 0 || agef > life || !chi("../enable_bubbles")) continue;
    float age = agef / life;
    float seconds = agef / 24.0;
    float side = fit01(rand(sid*19.3+2), -1, 1);
    float phase = rand(sid*7.11+8) * 2*PI;
    float skid_phase = seconds * chf("../bubble_skid_frequency") * 2*PI + phase;
    float ripple_phase = seconds * chf("../bubble_ripple_frequency") * 2*PI + phase*1.73;
    float outward = chf("../bubble_spread") * (0.18 + age*0.82);
    vector p = set(chf("../impact_x") + chf("../bubble_start_x") + side*outward,
                   chf("../impact_y") + chf("../bubble_start_y") + seconds*chf("../bubble_rise"),
                   chf("../bubble_start_depth") + fit01(rand(sid*7.7+4), -1, 1)*chf("../depth_spacing")*3);
    // Independent sideways skid plus a small circular ripple/orbit as bubbles rise.
    p.x += sin(skid_phase) * chf("../bubble_skid") * smooth(0, 0.12, age);
    p.x += sin(ripple_phase) * chf("../bubble_ripple");
    p.y += sin(ripple_phase*0.5) * chf("../bubble_ripple") * 0.25;
    p.z += cos(ripple_phase) * chf("../bubble_ripple");
    vector turb = curlnoise(set(p.x*1.7, p.y*1.7, sid + seconds*0.35));
    p += turb * chf("../bubble_turbulence") * smooth(0, 0.2, age);
    int pt = addpoint(0, p);
    float rv = chf("../bubble_radius_variation");
    float r = chf("../bubble_radius") * fit01(rand(sid*11.9), 1.0-rv, 1.0+rv);
    setpointattrib(0, "pscale", pt, r, "set");
    float fadein = smooth(0, max(0.1,chf("../bubble_fade_in")), agef);
    float fadeout = 1-smooth(life-max(0.1,chf("../bubble_fade_out")), life, agef);
    setpointattrib(0, "ink_alpha", pt, fadein*fadeout*0.58, "set");
    setpointattrib(0, "Cd", pt, set(0.72,0.90,1.0), "set");
}
'''


HERO_BUBBLE_VEX = r'''
float start = chf("../hero_start_frame");
float end = max(start + 1e-3, chf("../hero_end_frame"));
float u = clamp((@Frame-start)/(end-start), 0, 1);
float grow = u*u*(3-2*u);
grow += sin(PI*u) * chf("../hero_overshoot");
float radius = chf("../hero_radius") * max(grow, 0.0001);

vector restp = v@rest;
vector n = normalize(set(restp.x, restp.y+1.1, restp.z) + set(0,-0.001,0));
float seconds = max(0, @Frame-start)/24.0;
float wobble = snoise(n*chf("../hero_wobble_scale") +
                      set(0, seconds*chf("../hero_wobble_speed"), seconds*0.37));
vector axes = set(chf("../hero_scale_x"), chf("../hero_scale_y"), chf("../hero_scale_z"));
vector anchor = set(chf("../hero_pos_x"), chf("../hero_pos_y"), chf("../hero_pos_z"));
vector motion = set(
    sin(seconds*chf("../hero_skid_frequency")*2*PI) * chf("../hero_skid"),
    seconds*chf("../hero_rise"), 0);
// The revolved profile's apex is rest Y=0. It remains exactly at anchor;
// all translation and surface deformation fade in progressively below it.
float below_apex = max(0, -restp.y);
float pinmask = smooth(0, max(0.001, chf("../hero_pin_length")), below_apex);
float widen_start = chf("../hero_top_widen_start");
float widen_end = max(widen_start+0.001, chf("../hero_top_widen_end"));
float widen_u = smooth(widen_start, widen_end, @Frame);
float widen_envelope = 1-smooth(0, max(0.001, chf("../hero_top_widen_falloff")), below_apex);
vector radial = set(restp.x, 0, restp.z);
if (length2(radial) < 1e-10) {
    float a = 2*PI*float(@ptnum%64)/64.0;
    radial = set(cos(a), 0, -sin(a));
} else radial = normalize(radial);
vector top_widen = radial * chf("../hero_top_width") * widen_u * grow * widen_envelope;
@P = anchor + restp * axes * radius + top_widen + motion*pinmask
     + n*wobble*chf("../hero_wobble")*grow*pinmask;
f@ink_alpha = grow;
@Cd = set(0.72,0.92,1.0);
v@uv = set(atan2(n.z,n.x)/(2*PI)+0.5, asin(clamp(n.y,-1,1))/PI+0.5, 0);
'''


TEAR_PROFILE_VEX = r'''
// Half-profile, top apex to bottom pole. Revolve around Y to make one closed tear.
vector profile[] = array(
    set(0.000,  0.000, 0), set(0.035, -0.12, 0), set(0.120, -0.30, 0),
    set(0.290, -0.55, 0), set(0.520, -0.88, 0), set(0.720, -1.23, 0),
    set(0.790, -1.52, 0), set(0.720, -1.78, 0), set(0.540, -2.00, 0),
    set(0.300, -2.16, 0), set(0.100, -2.25, 0), set(0.000, -2.28, 0)
);
int pts[];
foreach (vector p; profile) append(pts, addpoint(0,p));
addprim(0,"polyline",pts);
'''


SATELLITE_POINTS_VEX = r'''
int count = chi("../satellite_count");
float start = chf("../hero_start_frame");
float end = max(start+1, chf("../hero_end_frame"));
float hero_u = clamp((@Frame-start)/(end-start),0,1);
float hero_grow = hero_u*hero_u*(3-2*hero_u);
float hero_r = chf("../hero_radius") * hero_grow;
float seconds = max(0,@Frame-start)/24.0;
float seed = chi("../satellite_seed");
vector hero_center = set(chf("../hero_pos_x"),
    chf("../hero_pos_y") + seconds*chf("../hero_rise") - hero_r*1.12,
    chf("../hero_pos_z"));
hero_center.x += sin(seconds*chf("../hero_skid_frequency")*2*PI)*chf("../hero_skid");

function void emitbubble(int id; int child; vector center; float r; float alpha) {
    int pt=addpoint(0,center);
    setpointattrib(0,"pscale",pt,max(0.0001,r),"set");
    setpointattrib(0,"ink_alpha",pt,alpha,"set");
    setpointattrib(0,"Cd",pt,set(0.72,0.92,1.0),"set");
    setpointattrib(0,"satellite_id",pt,id,"set");
    setpointattrib(0,"split_child",pt,child,"set");
}

for(int i=0;i<count;i++) {
    float sid=i+seed*31.71;
    float birth=start+rand(sid*2.17)*chf("../satellite_birth_spread");
    float agef=@Frame-birth;
    if(agef<0) continue;
    float age=max(0,agef/24.0);
    float local_u=clamp((@Frame-birth)/max(1,end-birth),0,1);
    float local_g=local_u*local_u*(3-2*local_u);
    float rv=chf("../satellite_radius_variation");
    float sr=chf("../satellite_radius")*fit01(rand(sid*5.3),1-rv,1+rv)*local_g;
    float a=2*PI*(float(i)/max(1,count))+fit01(rand(sid*7.9),-0.22,0.22);
    float yband=fit01(rand(sid*11.2),-0.70,0.55)*hero_r;
    float shell=max(hero_r*0.82,0.03)+chf("../satellite_spread")+sr;
    vector radial=set(cos(a),0,sin(a));
    vector p=hero_center+radial*shell+set(0,yband,0);
    // Faster upward force: velocity plus acceleration after birth.
    p.y += age*chf("../satellite_rise_speed") + 0.5*age*age*chf("../satellite_up_force");
    float phase=rand(sid*13.4)*2*PI;
    float w=age*chf("../satellite_wobble_frequency")*2*PI+phase;
    p.x += sin(w)*chf("../satellite_wobble");
    // Keep depth independent of the lateral wobble. Pairing cos(w) with the
    // X sine produces an ellipse, which reads as bubbles orbiting the hero.
    p.z += fit01(rand(sid*17.8),-1,1)*chf("../satellite_orbit");
    p += curlnoise(p*1.8+set(0,age,sid))*chf("../satellite_turbulence");

    // Bubble zero divides into two children; parent shrinks while children separate.
    float split=chf("../satellite_split_frame");
    if(i==0 && @Frame>=split) {
        float su=clamp((@Frame-split)/6.0,0,1);
        vector sep=normalize(set(-radial.z,0.35,radial.x))*chf("../satellite_split_separation")*su;
        float cr=sr*lerp(0.72,0.58,su);
        emitbubble(i,1,p+sep,cr,su);
        emitbubble(i,2,p-sep,cr,su);
    } else {
        // Every third satellite pulses subtly; the others remain smooth.
        float pulse=(i%3==1)?1+0.10*sin(w*1.7):1;
        emitbubble(i,0,p,sr*pulse,local_g);
    }
}
'''


def build_hero_air_bubble(geo):
    """One revolved tear plus satellite spheres that stay beyond its surface."""
    profile = _wrangle(geo, "hero_tear_profile", TEAR_PROFILE_VEX, run_over="detail")
    revolve = _node(geo, "revolve::2.0", "hero_tear_revolve")
    revolve.setInput(0, profile)
    _set(revolve, "diry", 1.0)
    _set(revolve, "divs", 64)
    _set(revolve, "surftype", 5)
    _set(revolve, "primtype", 1)
    _set(revolve, "cap", True)
    _set(revolve, "computeuvs", True)
    rest = _wrangle(geo, "hero_air_bubble_rest", "v@rest=@P;", revolve)
    animate = _wrangle(geo, "hero_air_bubble_animate", HERO_BUBBLE_VEX, rest)
    animate.setComment("Single closed 3D bubble: growth, rise, skid, ellipsoid scale and surface wobble.")
    nrm = _node(geo, "normal", "hero_air_bubble_normals")
    nrm.setInput(0, animate)
    tag = _wrangle(geo, "hero_air_bubble_material",
                   's@name="hero_air_bubble"; s@shop_materialpath="%s";' % BUBBLE_MAT_PATH,
                   nrm, run_over="prims")
    sat_points = _wrangle(geo, "satellite_bubble_points", SATELLITE_POINTS_VEX, run_over="detail")
    sat_sphere = _node(geo, "sphere", "satellite_bubble_source")
    _set(sat_sphere, "type", 2)
    _set(sat_sphere, "freq", 4)
    copy = _node(geo, "copytopoints", "copy_satellite_bubbles")
    copy.setInput(0, sat_sphere)
    copy.setInput(1, sat_points)
    sat_tag = _wrangle(geo, "satellite_bubble_material",
                       's@name="surrounding_bubbles"; s@shop_materialpath="%s";' % BUBBLE_MAT_PATH,
                       copy, run_over="prims")
    merge = _node(geo, "merge", "MERGE_HERO_AND_SATELLITES")
    merge.setInput(0, tag)
    merge.setInput(1, sat_tag)
    return merge


def build_layers(geo):
    layers = []
    for i in range(LAYER_COUNT):
        make = _wrangle(geo, "layer_%02d_mesh" % (i + 1), MESH_VEX, run_over="detail")
        make.setComment("Stable polar mesh: no animated topology or rectangular card silhouette.")
        deform = _wrangle(geo, "layer_%02d_animate" % (i + 1), layer_vex(i), make)
        deform.setComment("Anchored growth, curl deformation, UV motion and per-layer dissolution.")
        nrm = _node(geo, "normal", "layer_%02d_normals" % (i + 1))
        nrm.setInput(0, deform)
        _set(nrm, "type", 0)
        tag = _wrangle(geo, "layer_%02d_material" % (i + 1),
                       's@name="ink_layer_%02d"; s@shop_materialpath="%s";' %
                       (i + 1, MAT_PATH), nrm, run_over="prims")
        tag.setComment("Primitive name creates a distinct USD mesh; material path is preserved for OBJ workflows.")
        solid = _node(geo, "polyextrude", "layer_%02d_glass_thickness" % (i + 1))
        solid.setInput(0, tag)
        _set(solid, "dist", 0.018)
        if solid.parm("dist") is not None:
            solid.parm("dist").setExpression('ch("../glass_thickness")', hou.exprLanguage.Hscript)
        _set(solid, "outputfront", True)
        _set(solid, "outputback", True)
        _set(solid, "outputside", True)
        solid.setComment("Tiny physical thickness enables Karma refraction instead of a purely transparent card.")
        glass_nrm = _node(geo, "normal", "layer_%02d_glass_normals" % (i + 1))
        glass_nrm.setInput(0, solid)
        layers.append(glass_nrm)
    merge = _node(geo, "merge", "MERGE_INK_LAYERS")
    for i, n in enumerate(layers):
        merge.setInput(i, n)
    return merge


def build_bubbles(geo):
    points = _wrangle(geo, "bubble_points", BUBBLE_VEX, run_over="detail")
    sphere = _node(geo, "sphere", "bubble_prototype")
    _set(sphere, "type", 2)
    _set(sphere, "freq", 2)
    _set_tuple(sphere, "rad", (1.0, 1.0, 1.0))
    copy = _node(geo, "copytopoints", "copy_bubbles")
    copy.setInput(0, sphere)
    copy.setInput(1, points)
    attrib = _wrangle(geo, "bubble_attributes", 's@name="ink_bubbles"; s@shop_materialpath="%s";' % BUBBLE_MAT_PATH,
                      copy, run_over="prims")
    return attrib


def _material_builder(path, comment):
    import voptoolutils
    parent_path, name = path.rsplit("/", 1)
    parent = hou.node(parent_path)
    old = parent.node(name)
    if old is not None:
        old.destroy()
    voptoolutils._setupMtlXBuilderSubnet(destination_node=parent, name=name,
        mask=voptoolutils.KARMAMTLX_TAB_MASK, folder_label="Karma Material Builder", render_context="kma")
    net = parent.node(name)
    net.setUserData("ink_drop_owner", OWNER)
    net.setComment(comment)
    return net


def _mtlx(parent, type_name, name, signature=None, **parms):
    n = parent.createNode(type_name, name)
    if signature and n.parm("signature"):
        n.parm("signature").set(signature)
    for k, v in parms.items():
        _set(n, k, v)
    return n


def build_ink_material():
    net = _material_builder(MAT_PATH, "RGBA Persian pattern + procedural ink alpha; Karma CPU/XPU MaterialX")
    uv = _mtlx(net, "mtlxtexcoord", "deforming_uv", "vector2")
    cd = _mtlx(net, "mtlxgeompropvalue", "ink_tint", "color3", geomprop="Cd")
    alpha = _mtlx(net, "mtlxgeompropvalue", "procedural_alpha", "float", geomprop="ink_alpha")
    image = _mtlx(net, "mtlximage", "persian_pattern", "color3")
    image.setNamedInput("texcoord", uv, "out")
    _set(image, "file", '`chs("%s/persian_texture")`' % GEO_PATH)
    img_a = _mtlx(net, "mtlximage", "persian_alpha", "float")
    img_a.setNamedInput("texcoord", uv, "out")
    _set(img_a, "file", '`chs("%s/persian_texture")`' % GEO_PATH)
    _set(img_a, "default", 1.0)
    use = _mtlx(net, "mtlxconstant", "use_texture", "float", value=1.0)
    use.parm("value").setExpression('ch("%s/use_texture")' % GEO_PATH, hou.exprLanguage.Hscript)
    color_mix = _mtlx(net, "mtlxmix", "pattern_or_tint", "color3")
    color_mix.setNamedInput("bg", cd, "out")
    color_mix.setNamedInput("fg", image, "out")
    color_mix.setNamedInput("mix", use, "out")
    alpha_mix = _mtlx(net, "mtlxmix", "texture_alpha_enable", "float")
    _set(alpha_mix, "bg", 1.0)
    alpha_mix.setNamedInput("fg", img_a, "out")
    alpha_mix.setNamedInput("mix", use, "out")
    opacity = _mtlx(net, "mtlxmultiply", "combined_opacity", "float")
    opacity.setNamedInput("in1", alpha, "out")
    opacity.setNamedInput("in2", alpha_mix, "out")
    surface = net.node("mtlxstandard_surface")
    surface.setNamedInput("base_color", color_mix, "out")
    surface.setNamedInput("transmission_color", color_mix, "out")
    surface.setNamedInput("opacity", opacity, "out")
    surface.setNamedInput("emission_color", color_mix, "out")
    for parm, source, default in (
        ("base", "glass_base", 0.08), ("specular", "glass_reflection", 1.0),
        ("specular_roughness", "glass_roughness", 0.08),
        ("transmission", "glass_transmission", 0.94), ("specular_IOR", "glass_ior", 1.45),
        ("transmission_extra_roughness", "glass_refraction_roughness", 0.025),
        ("transmission_depth", "glass_depth", 0.8),
        ("transmission_dispersion", "glass_dispersion", 0.0),
        ("coat", "glass_coat", 0.28), ("coat_roughness", "glass_coat_roughness", 0.06),
        ("emission", "glass_emission", 0.0), ("thin_walled", "glass_thin_walled", 0),
    ):
        p = surface.parm(parm)
        if p is not None:
            try:
                p.setExpression('ch("%s/%s")' % (STAGE_MAT_NODE, source), hou.exprLanguage.Hscript)
            except hou.Error:
                p.set(default)
    _set(surface, "coat_IOR", 1.5)
    net.layoutChildren()


def add_stage_glass_controls(node):
    """Expose render-facing MaterialX controls directly on the Stage Material Library."""
    group = node.parmTemplateGroup()
    if group.find("ink_glass_controls") is not None:
        group.remove("ink_glass_controls")
    folder = hou.FolderParmTemplate("ink_glass_controls", "Ink Glass Controls")
    _float("glass_base", "Diffuse Weight", 0.08, 0.0, 1.0, folder,
           "Keep low for glass; pattern color primarily enters through transmission.")
    _float("glass_reflection", "Reflection", 1.0, 0.0, 1.0, folder)
    _float("glass_roughness", "Reflection Roughness", 0.08, 0.0, 1.0, folder)
    _float("glass_transmission", "Transparency / Transmission", 0.94, 0.0, 1.0, folder)
    _float("glass_ior", "Refraction IOR", 1.45, 1.0, 2.5, folder)
    _float("glass_refraction_roughness", "Refraction Roughness", 0.025, 0.0, 1.0, folder)
    _float("glass_depth", "Transmission Depth", 0.8, 0.001, 20.0, folder,
           "Absorption distance for the Persian transmission color.")
    _float("glass_dispersion", "Spectral Dispersion", 0.0, 0.0, 1.0, folder,
           "CPU/XPU support may differ; use subtly.")
    _float("glass_coat", "Clear Coat", 0.28, 0.0, 1.0, folder)
    _float("glass_coat_roughness", "Coat Roughness", 0.06, 0.0, 1.0, folder)
    _float("glass_emission", "Pattern Emission", 0.0, 0.0, 10.0, folder)
    _toggle("glass_thin_walled", "Thin Walled", False, folder,
            "Off uses the extruded SOP thickness for actual refraction; on is faster.")
    folder.addParmTemplate(hou.LabelParmTemplate(
        "glass_help", "Usage",
        column_labels=("Reflection, transparency and refraction are connected live to /mat/ink_drop_mtl.",)))
    group.append(folder)
    node.setParmTemplateGroup(group)


def add_stage_bubble_controls(node):
    """Create a Solaris-visible master panel for all procedural bubble motion."""
    group = node.parmTemplateGroup()
    folder = hou.FolderParmTemplate("bubble_animation_controls", "Bubble Animation Controls")
    _toggle("enable_bubbles", "Enable Bubbles", True, folder)
    _int("bubble_count", "Bubble Count", 34, 0, 500, folder)
    _float("bubble_radius", "Bubble Radius", 0.075, 0.001, 1.0, folder)
    _float("bubble_radius_variation", "Radius Variation", 0.60, 0.0, 1.0, folder)
    _float("bubble_birth_frame", "Birth Frame", 7.0, -1000.0, 1000.0, folder)
    _float("bubble_birth_duration", "Birth Duration", 10.0, 0.0, 240.0, folder)
    _float("bubble_lifetime", "Lifetime", 30.0, 1.0, 240.0, folder)
    folder.addParmTemplate(_separator("Location"))
    _float("bubble_start_x", "Start X", 0.0, -20.0, 20.0, folder)
    _float("bubble_start_y", "Start Y", -0.25, -20.0, 20.0, folder)
    _float("bubble_start_depth", "Start Depth", 0.0, -10.0, 10.0, folder)
    folder.addParmTemplate(_separator("Motion"))
    _float("bubble_rise", "Rise Speed", 0.62, -5.0, 5.0, folder)
    _float("bubble_spread", "Outward Spread", 0.85, 0.0, 8.0, folder)
    _float("bubble_skid", "Left / Right Skid", 0.18, 0.0, 5.0, folder)
    _float("bubble_skid_frequency", "Skid Frequency", 1.35, 0.0, 10.0, folder)
    _float("bubble_ripple", "Ripple Orbit Amount", 0.07, 0.0, 2.0, folder)
    _float("bubble_ripple_frequency", "Ripple Frequency", 1.8, 0.0, 12.0, folder)
    _float("bubble_turbulence", "Turbulence", 0.05, 0.0, 2.0, folder)
    folder.addParmTemplate(_separator("Life And Variation"))
    _float("bubble_fade_in", "Fade In Frames", 3.0, 0.1, 60.0, folder)
    _float("bubble_fade_out", "Fade Out Frames", 8.0, 0.1, 120.0, folder)
    _int("bubble_seed", "Random Seed", 17, 0, 100000, folder)
    folder.addParmTemplate(hou.LabelParmTemplate(
        "bubble_help", "Animation Tip",
        column_labels=("Keyframe any control here. Skid and ripple are continuous and independently phased per bubble.",)))
    group.append(folder)
    node.setParmTemplateGroup(group)


def link_stage_bubbles_to_sops(stage_control):
    """Make the Stage panel the live master while keeping SOP parameters visible."""
    geo = hou.node(GEO_PATH)
    names = (
        "enable_bubbles", "bubble_count", "bubble_radius", "bubble_radius_variation",
        "bubble_birth_frame", "bubble_birth_duration", "bubble_lifetime",
        "bubble_start_x", "bubble_start_y", "bubble_start_depth", "bubble_rise",
        "bubble_spread", "bubble_skid", "bubble_skid_frequency", "bubble_ripple",
        "bubble_ripple_frequency", "bubble_turbulence", "bubble_fade_in",
        "bubble_fade_out", "bubble_seed",
    )
    for name in names:
        target = geo.parm(name)
        source = stage_control.parm(name)
        if target is not None and source is not None:
            target.setExpression('ch("%s")' % source.path(), hou.exprLanguage.Hscript)


def add_stage_hero_bubble_controls(node):
    """Solaris master panel for the single 3D bubble and its MaterialX shell."""
    group = node.parmTemplateGroup()
    anim = hou.FolderParmTemplate("hero_animation", "Hero Bubble Animation")
    _float("hero_start_frame", "Growth Start Frame", 1.0, -1000.0, 1000.0, anim)
    _float("hero_end_frame", "Growth End Frame", 24.0, -999.0, 2000.0, anim)
    _float("hero_radius", "Final Radius", 1.35, 0.01, 20.0, anim)
    _float("hero_overshoot", "Growth Overshoot", 0.12, 0.0, 1.0, anim)
    _float("hero_pos_x", "Position X", 0.0, -20.0, 20.0, anim)
    _float("hero_pos_y", "Position Y", 0.9, -20.0, 20.0, anim)
    _float("hero_pos_z", "Position Z", 0.0, -20.0, 20.0, anim)
    _float("hero_rise", "Rise Speed", 0.45, -5.0, 5.0, anim)
    _float("hero_skid", "Left / Right Skid", 0.16, 0.0, 5.0, anim)
    _float("hero_skid_frequency", "Skid Frequency", 0.7, 0.0, 10.0, anim)
    _float("hero_wobble", "Surface Wobble", 0.045, 0.0, 1.0, anim)
    _float("hero_wobble_scale", "Wobble Scale", 2.4, 0.1, 20.0, anim)
    _float("hero_wobble_speed", "Wobble Speed", 0.65, 0.0, 10.0, anim)
    _float("hero_pin_length", "Top Pin Falloff", 0.38, 0.01, 2.0, anim,
           "Keeps the apex fixed and fades motion/wobble into the body below it.")
    _float("hero_top_widen_start", "Top Widen Start Frame", 24.0, -1000.0, 2000.0, anim)
    _float("hero_top_widen_end", "Top Widen End Frame", 48.0, -999.0, 4000.0, anim)
    _float("hero_top_width", "Final Top Width", 0.32, 0.0, 3.0, anim)
    _float("hero_top_widen_falloff", "Top Widen Falloff", 0.58, 0.01, 2.28, anim,
           "Controls how far down the neck the widening deformation reaches.")
    _float("hero_scale_x", "Scale X", 1.0, 0.01, 5.0, anim)
    _float("hero_scale_y", "Scale Y", 1.08, 0.01, 5.0, anim)
    _float("hero_scale_z", "Scale Z", 1.0, 0.01, 5.0, anim)
    satellites = hou.FolderParmTemplate("satellite_animation", "Surrounding Bubbles")
    _int("satellite_count", "Bubble Count", 8, 0, 40, satellites)
    _float("satellite_radius", "Final Radius", 0.19, 0.01, 2.0, satellites)
    _float("satellite_radius_variation", "Radius Variation", 0.45, 0.0, 1.0, satellites)
    _float("satellite_spread", "Outside Surface Gap", 0.32, 0.0, 5.0, satellites,
           "Minimum gap beyond the current main-bubble surface.")
    _float("satellite_birth_spread", "Birth Spread Frames", 6.0, 0.0, 48.0, satellites)
    _float("satellite_rise_speed", "Rise Speed", 0.65, -5.0, 10.0, satellites)
    _float("satellite_up_force", "Upward Acceleration", 0.45, -5.0, 10.0, satellites)
    _float("satellite_wobble", "Left / Right Wobble", 0.16, 0.0, 3.0, satellites)
    _float("satellite_wobble_frequency", "Wobble Frequency", 1.3, 0.0, 12.0, satellites)
    _float("satellite_orbit", "Depth Offset", 0.08, 0.0, 2.0, satellites)
    _float("satellite_split_frame", "Split Frame", 22.0, -1000.0, 2000.0, satellites)
    _float("satellite_split_separation", "Split Separation", 0.24, 0.0, 3.0, satellites)
    _float("satellite_turbulence", "Turbulence", 0.06, 0.0, 2.0, satellites)
    _int("satellite_seed", "Random Seed", 41, 0, 100000, satellites)
    material = hou.FolderParmTemplate("hero_material", "Air Bubble Material")
    _float("hero_reflection", "Reflection", 1.0, 0.0, 1.0, material)
    _float("hero_roughness", "Reflection Roughness", 0.035, 0.0, 1.0, material)
    _float("hero_transmission", "Transparency / Transmission", 0.98, 0.0, 1.0, material)
    _float("hero_ior", "Refraction IOR", 1.06, 1.0, 2.5, material)
    _float("hero_refraction_roughness", "Refraction Roughness", 0.01, 0.0, 1.0, material)
    _float("hero_coat", "Clear Coat", 0.35, 0.0, 1.0, material)
    _float("hero_coat_roughness", "Coat Roughness", 0.025, 0.0, 1.0, material)
    _toggle("hero_thin_walled", "Thin Walled Shell", True, material)
    group.append(anim)
    group.append(satellites)
    group.append(material)
    node.setParmTemplateGroup(group)


def link_stage_hero_to_sops(stage_control):
    geo = hou.node(GEO_PATH)
    names = (
        "hero_start_frame", "hero_end_frame", "hero_radius", "hero_overshoot",
        "hero_pos_x", "hero_pos_y", "hero_pos_z", "hero_rise", "hero_skid",
        "hero_skid_frequency", "hero_wobble", "hero_wobble_scale",
        "hero_wobble_speed", "hero_pin_length", "hero_top_widen_start",
        "hero_top_widen_end", "hero_top_width", "hero_top_widen_falloff",
        "hero_scale_x", "hero_scale_y", "hero_scale_z",
        "satellite_count", "satellite_radius", "satellite_radius_variation",
        "satellite_spread", "satellite_birth_spread", "satellite_rise_speed",
        "satellite_up_force", "satellite_wobble", "satellite_wobble_frequency",
        "satellite_orbit", "satellite_split_frame", "satellite_split_separation",
        "satellite_turbulence", "satellite_seed",
    )
    for name in names:
        geo.parm(name).setExpression('ch("%s")' % stage_control.parm(name).path(), hou.exprLanguage.Hscript)


def build_bubble_material():
    net = _material_builder(BUBBLE_MAT_PATH, "Reflective and refractive MaterialX air-bubble shell")
    alpha = _mtlx(net, "mtlxgeompropvalue", "bubble_alpha", "float", geomprop="ink_alpha")
    surf = net.node("mtlxstandard_surface")
    _set(surf, "base", 0.0)
    _set(surf, "base_color", (0.55, 0.82, 1.0))
    for parm, source, default in (
        ("specular", "hero_reflection", 1.0),
        ("specular_roughness", "hero_roughness", 0.035),
        ("specular_IOR", "hero_ior", 1.06),
        ("transmission", "hero_transmission", 0.98),
        ("transmission_extra_roughness", "hero_refraction_roughness", 0.01),
        ("coat", "hero_coat", 0.35),
        ("coat_roughness", "hero_coat_roughness", 0.025),
        ("thin_walled", "hero_thin_walled", 1),
    ):
        p = surf.parm(parm)
        if p is not None:
            try:
                p.setExpression('ch("%s/%s")' % (HERO_CTL_NODE, source), hou.exprLanguage.Hscript)
            except hou.Error:
                p.set(default)
    _set(surf, "transmission_color", (0.72, 0.93, 1.0))
    surf.setNamedInput("opacity", alpha, "out")
    net.layoutChildren()


def _sync_water(geo):
    water = hou.node("/obj/WATER_RIPPLE")
    if water is None:
        return
    # Accommodate common snake_case and label-derived parameter names without altering water.
    for ours, candidates in (("impact_x", ("impactx", "impact_x")),
                             ("start_frame", ("impactstartframe", "impact_start_frame"))):
        source = next((water.parm(n) for n in candidates if water.parm(n) is not None), None)
        if source is not None:
            geo.parm(ours).setExpression('if(ch("sync_water"), ch("%s"), %s)' %
                (source.path(), geo.parm(ours).eval()), hou.exprLanguage.Hscript)


def build_geo():
    obj = hou.node("/obj")
    old = hou.node(GEO_PATH)
    if old is not None:
        old.destroy()
    geo = _node(obj, "geo", "INK_DROP_EFFECT")
    geo.setComment("Procedural layered 2.5D ink drop. Controls are on this object.")
    for child in list(geo.children()):
        child.destroy()
    add_interface(geo)
    hero = build_hero_air_bubble(geo)
    out = _null(geo, "OUT_INK_EFFECT", hero)
    out.setComment("Single animated closed 3D air bubble; use this SOP for Solaris SOP Import.")
    out.setDisplayFlag(True)
    out.setRenderFlag(True)
    _sync_water(geo)
    geo.layoutChildren()
    return geo, out


def build_camera():
    obj = hou.node("/obj")
    old = obj.node("cam_ink_drop")
    if old is not None:
        old.destroy()
    cam = _node(obj, "cam", "cam_ink_drop")
    _set_tuple(cam, "t", (0.0, 0.0, 13.5))
    _set(cam, "focal", 50.0)
    _set(cam, "resx", 960)
    _set(cam, "resy", 960)
    return cam


def build_stage(out_sop):
    stage = hou.node("/stage")
    if stage is None:
        stage = hou.node("/").createNode("lopnet", "stage")
    for name in OWNED_STAGE:
        n = stage.node(name)
        if n is not None:
            n.destroy()
    sop = _node(stage, "sopimport", "ink_drop_sopimport")
    _set(sop, "soppath", out_sop.path())
    _set(sop, "enable_pathprefix", True)
    _set(sop, "pathprefix", "/ink_drop")
    _set(sop, "bindmaterials", "nobind")
    bubble_ctl = _node(stage, "null", "ink_drop_hero_bubble_controls")
    bubble_ctl.setInput(0, sop)
    bubble_ctl.setComment("Single 3D air bubble: animate growth, position, rise, skid, wobble, shape and glass here.")
    add_stage_hero_bubble_controls(bubble_ctl)
    link_stage_hero_to_sops(bubble_ctl)
    mats = _node(stage, "materiallibrary", "ink_drop_materials")
    mats.setInput(0, bubble_ctl)
    add_stage_glass_controls(mats)
    _set(mats, "matnet", "/mat")
    # SOP shop_materialpath imports cleanly; Material Library authors the MaterialX definitions.
    _set(mats, "materials", 2)
    for i, path in enumerate((MAT_PATH, BUBBLE_MAT_PATH), 1):
        _set(mats, "matflag%d" % i, True)
        _set(mats, "matnode%d" % i, path)
        _set(mats, "matpath%d" % i, "/materials/" + path.rsplit("/", 1)[-1])
        _set(mats, "assign%d" % i, True)
        _set(mats, "geopath%d" % i,
             "/ink_drop/ink_layer_*" if i == 1 else "/ink_drop/*bubble*")
    cam = _node(stage, "camera", "ink_drop_camera")
    cam.setInput(0, mats)
    _set(cam, "primpath", "/cameras/ink_drop")
    _set_tuple(cam, "t", (0.0, 0.0, 13.5))
    _set(cam, "focalLength", 50.0)
    dome = _node(stage, "domelight::3.0", "ink_drop_dome")
    dome.setInput(0, cam)
    _set(dome, "xn__inputsintensity_i0a", 0.35)
    key = _node(stage, "distantlight::2.0", "ink_drop_key")
    key.setInput(0, dome)
    _set_tuple(key, "r", (-28.0, 22.0, -18.0))
    _set(key, "xn__inputsintensity_i0a", 1.4)
    karma = _node(stage, "karmarenderproperties", "ink_drop_karma")
    karma.setInput(0, key)
    _set(karma, "camera", "/cameras/ink_drop")
    _set(karma, "engine", "cpu")
    _set(karma, "resolutionx", 960)
    _set(karma, "resolutiony", 960)
    _set(karma, "samplesperpixel", 16)
    _set(karma, "picture", "$HIP/render/ink_drop.$F4.png")
    rop = _node(stage, "usdrender_rop", "ink_drop_render")
    rop.setInput(0, karma)
    _set(rop, "renderer", "BRAY_HdKarma")
    # Make the post-material stage the default visible state.  Viewing the
    # upstream SOP Import intentionally shows unshaded blue proxy geometry.
    karma.setDisplayFlag(True)
    karma.setCurrent(True, clear_all_selected=True)
    stage.layoutChildren()
    return rop


def validate_scene():
    """Structural validation; this is not a claim of rendered visual validation."""
    geo = hou.node(GEO_PATH)
    out = hou.node(GEO_PATH + "/OUT_INK_EFFECT")
    assert geo is not None and out is not None
    hero_control = hou.node(HERO_CTL_NODE)
    assert hero_control is not None
    for name in CONTROL_HELP:
        parm = hero_control.parm(name)
        if parm is not None:
            assert parm.parmTemplate().help().strip(), "Missing tooltip: " + name
    reports = []
    for frame in (1, 6, 12, 24, 36, 48):
        hou.setFrame(frame)
        g = out.geometry()
        layers = sorted(set(g.pointIntAttribValues("layer_id"))) if g.findPointAttrib("layer_id") else []
        zvals = [p.position()[2] for p in g.points()]
        alpha = g.pointFloatAttribValues("ink_alpha") if g.findPointAttrib("ink_alpha") else []
        reports.append((frame, len(g.points()), len(g.prims()), layers,
                        min(zvals) if zvals else 0, max(zvals) if zvals else 0,
                        sum(alpha)/len(alpha) if alpha else 0))
    print("frame points prims layers zmin zmax avg_alpha")
    for row in reports:
        print(row)
    return reports


def build(save_path=None, make_stage=True):
    geo, out = build_geo()
    build_ink_material()
    build_bubble_material()
    build_camera()
    if make_stage and geo.parm("create_stage").eval():
        build_stage(out)
    hou.playbar.setFrameRange(1, 48)
    hou.playbar.setPlaybackRange(1, 48)
    hou.setFrame(1)
    if save_path:
        hou.hipFile.save(os.path.abspath(save_path))
        print("Saved:", os.path.abspath(save_path))
    print("Built", GEO_PATH)
    return geo


def rebuild_in_session():
    """Convenient entry point for Houdini's Python Shell; does not save the hip file."""
    return build()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "ink_drop_effect.hipnc")
    if "--no-save" in sys.argv:
        out_path = None
    build(out_path, make_stage="--no-stage" not in sys.argv)
    if "--validate" in sys.argv:
        validate_scene()
