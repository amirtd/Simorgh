"""
Phoenix feather flow system.

Guide curves traced from ref/feather_flow_ref.png are resampled into feather roots,
varied with Attribute Randomize, populated with procedural feathers, then roughened
with VEX noise so edges and curvature read as organic. oil_growth animates each feather
running out from its root like oil on canvas; /mat/feather_paint is an oil-paint shader
(strokes along the feather uvs, impasto, dry-brush edges, wet front) and /stage renders it
over a painted ground with Karma.

Run with:
  hython build_phoenix.py          # rebuild /obj/feather_flow_guides inside the existing hip
  hython build_phoenix.py --full   # fresh hip containing only the feather flow system
"""

from __future__ import annotations

import os
import sys

# hython provides `hou` automatically; allow editors/linters that import this file.
try:
    hou  # type: ignore[name-defined]
except NameError:
    import hou  # type: ignore


ROOT = os.path.dirname(os.path.abspath(__file__))

def _latest_hip() -> str:
    """Apprentice saves .hipnc; update whichever scene file was saved most recently."""
    candidates = [os.path.join(ROOT, "phoenix_birth" + ext) for ext in (".hipnc", ".hip")]
    existing = [path for path in candidates if os.path.exists(path)]
    return max(existing, key=os.path.getmtime) if existing else candidates[1]


HIP_OUT = _latest_hip()
REF_IMAGE = os.path.join(ROOT, "ref", "feather_flow_ref.png")
REF_W, REF_H = 1024, 689
REF_SCALE = 1.0 / 200.0  # pixels → Houdini units
FLOW_OFFSET_X = 7.0

# Removed by hand from the scene; never rebuild them.
LEGACY_NODES = ("/obj/phoenix_birth", "/obj/cam_phoenix")

SHOULDER_PX = (1010, 230)  # wing-beat pivot, where the flows start (reference pixels)
GROW_FRAMES = (1, 200)  # oil_growth runs over these frames; playbar is 1-240
PAINT_MATERIAL = "/mat/feather_paint"
CANVAS_MATERIAL = "/mat/canvas_paint"
PAINT_RENDER_RES = (1070, 720)  # reference aspect, within the Apprentice 1280x720 cap
# Solaris nodes owned by this script (rebuilt every run; anything else in /stage is left alone).
PAINT_STAGE_NODES = ("paint_feathers", "paint_canvas", "paint_materials", "paint_camera", "paint_dome",
                     "paint_key", "paint_karma", "paint_render")

# Control points in reference-image pixels, ordered root → tip.
# Colors are the dominant band color; band_px is the approximate band width.
FEATHER_FLOWS = [
    ("crest_red", (0.85, 0.10, 0.08), 60,
     [(1024, 110), (880, 95), (720, 110), (560, 125), (400, 110), (260, 95), (130, 60), (40, 20)]),
    ("wisp_curl", (0.95, 0.75, 0.55), 8,
     [(820, 40), (660, 55), (560, 40), (470, 30), (380, 22), (310, 30), (290, 45), (305, 57), (322, 46)]),
    ("violet_blue", (0.55, 0.50, 0.85), 45,
     [(700, 165), (560, 185), (420, 200), (280, 215), (140, 215), (20, 200)]),
    ("scarlet_mid", (0.80, 0.12, 0.15), 50,
     [(1000, 180), (860, 190), (700, 215), (540, 240), (400, 255), (280, 265)]),
    ("coral_orange", (0.98, 0.55, 0.40), 55,
     [(820, 260), (680, 300), (560, 350), (440, 410), (320, 450), (230, 480)]),
    ("olive_green", (0.55, 0.68, 0.30), 55,
     [(560, 272), (420, 292), (280, 320), (140, 350), (0, 382)]),
    ("teal_blue", (0.25, 0.62, 0.72), 60,
     [(760, 420), (620, 480), (480, 530), (340, 570), (200, 590), (40, 600)]),
    ("amber_lower", (0.97, 0.62, 0.20), 60,
     [(820, 400), (740, 480), (680, 570), (640, 689)]),
    ("gold_cream", (0.98, 0.86, 0.58), 80,
     [(1024, 180), (930, 270), (860, 370), (810, 470), (780, 580), (760, 689)]),
]

# Target point attributes carried from roots onto every copied feather point.
COPIED_ATTRIBS = (
    "fcol flow_id flow_u band_edge feather_id side fside fdir froot flen width_mult bend overlap "
    "layer_id layer_shift layer_tint"
)

# Overlapping feather systems, back (large) → front (small). Each becomes a subnet.
#   spacing   resample length along the guides        rows      roots per resample point
#   length    base feather length                     splay     max fan angle at band edges (deg)
#   spread    root scatter as a fraction of band      u_range   portion of the flow (root=0, tip=1)
#   width     width multiplier on top of rand_width   z         depth offset (keeps layers stacked)
#   len_range / rot_range   Attribute Randomize ranges for len_mult / rot_jitter
#   shift     color ramp offset
#   tint      > 0 lightens toward cream (small coverts), < 0 darkens (deep primaries)
FEATHER_LAYERS = [
    dict(name="primaries", spacing=0.09, rows=1, length=1.7, splay=12, spread=0.7, u_range=(0.0, 1.0),
         width=0.85, z=0.00, segments=72, len_range=(0.85, 1.15), rot_range=(-4, 4), shift=-0.08, tint=-0.18),
    dict(name="secondaries", spacing=0.05, rows=2, length=1.1, splay=22, spread=1.0, u_range=(0.0, 1.0),
         width=1.0, z=0.08, segments=60, len_range=(0.8, 1.2), rot_range=(-6, 6), shift=0.0, tint=0.0),
    dict(name="coverts", spacing=0.045, rows=2, length=0.55, splay=30, spread=1.1, u_range=(0.0, 0.5),
         width=1.15, z=0.16, segments=40, len_range=(0.75, 1.25), rot_range=(-9, 9), shift=0.0, tint=0.14),
    dict(name="down", spacing=0.05, rows=2, length=0.28, splay=40, spread=1.2, u_range=(0.0, 0.3),
         width=1.3, z=0.24, segments=24, len_range=(0.7, 1.3), rot_range=(-14, 14), shift=0.0, tint=0.28),
]


# ---------------------------------------------------------------------------
# VEX
# ---------------------------------------------------------------------------
FLOW_ATTRS_VEX = r'''
// Tangent points root → tip; band profile swells mid-flow and tapers at the tip.
vector prev = @P, next = @P;
foreach (int nb; neighbours(0, @ptnum)) {
    if (point(0, "curveu", nb) < @curveu) prev = point(0, "P", nb);
    else next = point(0, "P", nb);
}
v@tangentu = normalize(next - prev);
v@N = normalize(cross({0, 0, 1}, v@tangentu));
float bw = prim(0, "band_width", pointprims(0, @ptnum)[0]);
f@band_profile = bw * (0.55 + 0.45 * sin(@curveu * PI * 0.8)) * (1.0 - 0.6 * @curveu * @curveu);
f@pscale = 0.035 * (1.0 - 0.75 * @curveu);
'''

FEATHER_PROTOTYPE_VEX = r'''
// Unit feather prototypes: shaft along +Z (0 → 1), vane width along X, flat in XZ.
// Each variant emits a vane (quad strips shaft → edge), a thin shaft strip, and matching
// open curves (outline + shaft) that carry curveu for later growth.
// uv: u across the vane (left edge 0, shaft 0.5, right edge 1), v root → tip. Each quad row
// joins shaft and edge points at the same t, so constant-v lines follow the swept barbs.
// edge_side (+1 right, -1 left, 0 shaft) and half_w let the noise stage push edges outward.
// lp (rest position) and lxc (shaft x at this t) let oil_growth re-fold the feather after copy.
int add_rest_point(vector p; float xc) {
    int pt = addpoint(0, p);
    setpointattrib(0, "lp", pt, p, "set");
    setpointattrib(0, "lxc", pt, xc, "set");
    return pt;
}

int nseg = chi("segments");
float curls[]  = {0.06, -0.05, 0.14, 0.02};
float widths[] = {0.20, 0.15, 0.26, 0.12};
float serrs[]  = {0.18, 0.28, 0.12, 0.35};
float barbs[]  = {8, 12, 6, 15};
float sweeps[] = {0.6, 0.8, 0.45, 1.0};

for (int v = 0; v < len(curls); v++) {
    int right[], left[], left_full[], shaft[], shaft_l[], shaft_r[];
    for (int i = 0; i <= nseg; i++) {
        float t = float(i) / float(nseg);
        float xc = curls[v] * t * t;
        float prof = pow(sin(PI * pow(t, 0.65)), 0.9);
        float saw = 1.0 - serrs[v] * pow(frac(t * barbs[v]), 1.5) * smooth(0.1, 0.3, t);
        float w = widths[v] * prof * saw;
        // Barbs sweep toward the tip, so outer edge points sit further along the shaft.
        float sweep = w * sweeps[v];

        int pr = add_rest_point(set(xc + w, 0, t + sweep), xc);
        setpointattrib(0, "fshade", pr, t, "set");
        setpointattrib(0, "side_light", pr, 1.0, "set");
        setpointattrib(0, "curveu", pr, t * 0.5, "set");
        setpointattrib(0, "edge_side", pr, 1.0, "set");
        setpointattrib(0, "half_w", pr, w, "set");
        setpointattrib(0, "uv", pr, set(1.0, t, 0), "set");
        append(right, pr);

        int pc = add_rest_point(set(xc, 0, t), xc);
        setpointattrib(0, "curveu", pc, t, "set");
        setpointattrib(0, "fshade", pc, t, "set");
        setpointattrib(0, "side_light", pc, 0.9, "set");
        setpointattrib(0, "uv", pc, set(0.5, t, 0), "set");
        append(shaft, pc);

        // The left edge closes onto the shaft at root and tip.
        if (i > 0 && i < nseg) {
            int pl = add_rest_point(set(xc - 0.75 * w, 0, t + 0.75 * sweep), xc);
            setpointattrib(0, "fshade", pl, t, "set");
            setpointattrib(0, "side_light", pl, 0.78, "set");
            setpointattrib(0, "curveu", pl, 1.0 - t * 0.5, "set");
            setpointattrib(0, "edge_side", pl, -1.0, "set");
            setpointattrib(0, "half_w", pl, 0.75 * w, "set");
            setpointattrib(0, "uv", pl, set(0.0, t, 0), "set");
            append(left, pl);
            append(left_full, pl);
        } else {
            append(left_full, pc);
        }

        if (t <= 0.95) {
            float sw = 0.008 * (1.0 - t);
            int sr = add_rest_point(set(xc + sw, 0.002, t), xc);
            int sl = add_rest_point(set(xc - sw, 0.002, t), xc);
            int strip_pts[] = {};
            append(strip_pts, sr);
            append(strip_pts, sl);
            foreach (int sp; strip_pts) {
                setpointattrib(0, "fshade", sp, t, "set");
                setpointattrib(0, "curveu", sp, t, "set");
                setpointattrib(0, "is_shaft", sp, 1, "set");
            }
            setpointattrib(0, "uv", sr, set(0.52, t, 0), "set");
            setpointattrib(0, "uv", sl, set(0.48, t, 0), "set");
            append(shaft_r, sr);
            append(shaft_l, sl);
        }
    }

    int made[] = {};
    for (int i = 0; i < nseg; i++) {
        int quad_r[] = {};
        append(quad_r, shaft[i]);
        append(quad_r, shaft[i + 1]);
        append(quad_r, right[i + 1]);
        append(quad_r, right[i]);

        // Mirrored winding so both halves face the same way; triangles where the left edge
        // meets the shaft.
        int quad_l[] = {};
        append(quad_l, shaft[i]);
        if (left_full[i] != shaft[i]) append(quad_l, left_full[i]);
        if (left_full[i + 1] != shaft[i + 1]) append(quad_l, left_full[i + 1]);
        append(quad_l, shaft[i + 1]);

        int qr = addprim(0, "poly", quad_r);
        int ql = addprim(0, "poly", quad_l);
        setprimattrib(0, "kind", qr, "vane", "set");
        setprimattrib(0, "kind", ql, "vane", "set");
        append(made, qr);
        append(made, ql);
    }

    int outline[] = right;
    for (int i = len(left) - 1; i >= 0; i--) append(outline, left[i]);

    int strip[] = shaft_r;
    for (int i = len(shaft_l) - 1; i >= 0; i--) append(strip, shaft_l[i]);
    int strip_prim = addprim(0, "poly", strip);
    setprimattrib(0, "kind", strip_prim, "shaft_strip", "set");

    int outline_curve[] = outline;
    append(outline_curve, outline[0]);
    int oc = addprim(0, "polyline", outline_curve);
    setprimattrib(0, "kind", oc, "outline_curve", "set");

    int sc = addprim(0, "polyline", shaft);
    setprimattrib(0, "kind", sc, "shaft_curve", "set");

    append(made, strip_prim);
    append(made, oc);
    append(made, sc);
    foreach (int mp; made)
        setprimattrib(0, "variant", mp, v, "set");
}
'''

FEATHER_ROOTS_VEX = r'''
// Turn each resampled guide point into several feather roots spread across the band.
// Per-feather variation (length, width, bend, overlap, rotation) comes from the
// Attribute Randomize chain downstream.
int rows = chi("rows_per_sample");
float spacing = chf("spacing");
float splay = radians(chf("splay"));
float base_len = chf("feather_length");
float ref_mix = chf("ref_color_mix");
int nvariants = chi("variants");
float u_min = chf("u_min"), u_max = chf("u_max"), u_fade = chf("u_fade");
int layer = chi("layer_id");

int pr = pointprims(0, @ptnum)[0];
int fid = prim(0, "flow_id", pr);
float bw = prim(0, "band_width", pr);
vector guide_cd = prim(0, "Cd", pr);
vector T = normalize(v@tangentu);
vector S = normalize(cross({0, 0, 1}, T));
float half_band = 0.5 * f@band_profile * chf("band_spread") + 1e-5;

// Soft window along the flow: density fades out past u_min / u_max instead of cutting hard.
float coverage = smooth(u_min - u_fade, u_min, @curveu) * (1.0 - smooth(u_max, u_max + u_fade, @curveu));

for (int r = 0; r < rows; r++) {
    float seed = @ptnum * 13.37 + r * 7.1 + fid * 101.3 + layer * 7919.0;
    if (rand(seed + 9) > coverage) continue;
    float off = fit01(rand(seed), -1.0, 1.0) * half_band;
    float edge = abs(off) / half_band;
    float side = off < 0 ? -1.0 : 1.0;

    // Feathers fan outward from the flow centerline.
    float ang = side * splay * edge;
    vector dir = normalize(T * cos(ang) + S * sin(ang));

    float len = base_len
              * fit(@curveu, 0, 1, 1.0, 0.45)
              * sqrt(bw / 0.3)
              * (1.0 - 0.35 * edge);

    vector root = @P + S * off + T * fit01(rand(seed + 1), -0.5, 0.5) * spacing;
    float base_z = chf("layer_z") + @curveu * 0.03 + fid * 0.002;
    root.z = base_z;

    vector mid = root + dir * len * 0.5;
    vector ref_cd = point(1, "Cd", nearpoint(1, set(mid.x, mid.y, -0.02)));
    vector col = lerp(guide_cd, ref_cd, ref_mix) * fit01(rand(seed + 5), 0.85, 1.1);

    int pt = addpoint(0, root);
    setpointattrib(0, "N", pt, dir, "set");
    setpointattrib(0, "up", pt, {0, 0, 1}, "set");
    setpointattrib(0, "pscale", pt, len, "set");
    setpointattrib(0, "side", pt, side, "set");
    setpointattrib(0, "base_z", pt, base_z, "set");
    setpointattrib(0, "variant", pt, int(rand(seed + 6) * nvariants), "set");
    setpointattrib(0, "fcol", pt, col, "set");
    setpointattrib(0, "flow_id", pt, fid, "set");
    setpointattrib(0, "flow_u", pt, @curveu, "set");
    setpointattrib(0, "band_edge", pt, edge, "set");
    setpointattrib(0, "layer_id", pt, layer, "set");
    setpointattrib(0, "layer_shift", pt, chf("color_shift"), "set");
    setpointattrib(0, "layer_tint", pt, chf("color_tint"), "set");
}
removepoint(0, @ptnum);
'''

APPLY_RANDOMIZE_VEX = r'''
// rot_jitter: degrees around the view axis.
float a = radians(f@rot_jitter);
v@N = normalize(set(v@N.x * cos(a) - v@N.y * sin(a), v@N.x * sin(a) + v@N.y * cos(a), 0));

// len_mult / width_mult: prototype length is uniform pscale, width is local X (mirrored by side).
// width_mult is folded with the layer width so the noise stage sees the final width.
f@pscale *= f@len_mult;
f@width_mult *= chf("width_scale");
v@scale = set(f@side * f@width_mult, 1, 1);

// overlap: tuck the root back under its neighbours and shuffle stacking depth.
@P -= v@N * f@overlap * chf("overlap_tuck") * f@pscale;
@P.z = f@base_z + f@overlap * chf("overlap_depth");

// Copy to Points maps prototype +X to cross(up, N); post-copy deformers work in that frame.
v@fside = normalize(cross(v@up, v@N)) * f@side;
v@fdir = v@N;
v@froot = @P;
f@flen = f@pscale;
// Unique across layers so noise never repeats between overlapping systems.
i@feather_id = @ptnum + i@layer_id * 100000;
'''

OIL_GROWTH_VEX = r'''
// Oil-run growth. Each feather is poured at its root and runs toward the tip like thinned
// oil on a tilted canvas: quick at first then slowing (viscosity), in surges, with a lobed
// front and a swollen head. The vane only spreads sideways once the front has passed.
// Paint reaches the flow shoulders first and runs out along the flows, back layers first.
float progress = chf("progress");
float run = chf("run_time");
float id = i@feather_id;

float w_flow = chf("flow_delay"), w_layer = chf("layer_delay"), w_jit = chf("birth_jitter");
float order = f@flow_u * w_flow + i@layer_id * w_layer + rand(id + 0.13) * w_jit;
float order_max = w_flow + (chi("layer_count") - 1) * w_layer + w_jit;
float birth = order / max(order_max, 1e-5) * (1.0 - run);
float p = clamp((progress - birth) / max(run, 1e-5), 0, 1);

// Surges: monotonic warp (strength <= 1); an integer count keeps p = 0 and 1 fixed.
float k = max(1, chi("surges"));
float ph = rand(id + 0.57) * 2 * PI;
p = clamp(p + chf("surge_strength") * (sin(2 * PI * k * p + ph) - sin(ph)) / (2 * PI * k), 0, 1);
float front = 1.0 - pow(1.0 - p, chf("viscosity"));

// Lobed front: strongest mid-run, gone once the feather has settled.
float lobe = noise(set(v@uv.x * chf("lobe_freq"), id * 0.37, 5.1)) * 2 - 1;
front = clamp(front + lobe * chf("lobe_amp") * 4 * front * (1 - front), 0, 1);

float t = f@fshade;
float tg = min(t, front);
float behind = front - tg;
float lag = chf("spread_lag") * sqrt(1 - front) + 1e-4;
float open = sqrt(smooth(0, lag, behind));
open *= 1 + chf("head_swell") * (1 - front) * exp(-pow((behind - 0.6 * lag) / (0.5 * lag), 2));

// Re-fold from the rest shape: unreached points pile up at the front, the vane (and the
// barb sweep) closes toward the shaft where the paint hasn't spread yet.
vector lp = v@lp;
float x = f@lxc + (lp.x - f@lxc) * open;
float z = tg + (lp.z - t) * open;
@P = v@froot + (v@fside * x * f@width_mult + set(0, 0, lp.y) + v@fdir * z) * f@flen;

f@fshade = tg;
f@half_w *= open;
f@grow = p;
// Fresh paint at and just behind the running front; dries once the feather settles.
f@wet = exp(-behind / chf("wet_length")) * (1 - smooth(0.85, 1.0, p)) * (p > 0);
'''

WING_ENVELOPE_VEX = r'''
// Wing beat shared by wing_wind and wing_flap (settings on WING_CONTROLS).
// Angle about the shoulder grows toward the tip and lags behind the shoulder, so the wing
// flexes like a slow wave; the beat starts small and builds up while the wing grows.
// Negative angles lift the tips of a wing that reaches toward -X.
float span_pos(vector p) {
    vector r = p - chv("../WING_CONTROLS/pivot");
    return clamp(length(set(r.x, r.y, 0)) / chf("../WING_CONTROLS/span"), 0, 1.5);
}

string ctl = "../WING_CONTROLS/";
vector pivot = chv(ctl + "pivot");
float beat_w = 2 * PI / chf(ctl + "flap_period");
float envelope = lerp(chf(ctl + "start_amount"), 1.0, smooth(0, 0.7, chf("../oil_growth/progress")));
'''

WING_WIND_VEX = r'''
// Wind on the feathers: external wind (gusts + turbulence drifting downwind) plus the air the
// beating wing moves through (rising pushes feathers down, falling pushes them up). Feathers
// bend with the air across them, tips most; still-growing feathers are softer.
// Sampled at the feather root so each feather bends as one piece.
float time = @Time;
vector wdir = normalize(chv(ctl + "wind_dir"));
float speed = chf(ctl + "wind_speed");
float gust = 1 + chf(ctl + "gust_amp") * (noise(time * chf(ctl + "gust_freq") + 3.7) * 2 - 1);
float tf = chf(ctl + "turb_freq");
vector turb = (vector(noise(v@froot * tf - wdir * time * speed * tf)) - 0.5) * 2 * chf(ctl + "turb_amp");
vector air = (wdir * gust + set(turb.x, turb.y, 0)) * speed;

vector r = v@froot - pivot;
float d = span_pos(v@froot);
float ang_vel = -radians(chf(ctl + "flap_amp")) * envelope * (1 + chf(ctl + "tip_flex") * d)
              * beat_w * cos(beat_w * time - chf(ctl + "tip_lag") * d);
air -= ang_vel * set(-r.y, r.x, 0) * chf(ctl + "beat_drag");

vector across = air - v@fdir * dot(air, v@fdir);
float soft = 1 + chf(ctl + "growing_softness") * (1 - f@grow) * (f@grow > 0);
vector sway = across * chf(ctl + "wind_flex") * soft;
if (length(sway) > 0.5) sway = normalize(sway) * 0.5;  // fraction of feather length
float flutter = sin(2 * PI * chf(ctl + "flutter_freq") * time + rand(i@feather_id + 0.9) * 2 * PI)
              * chf(ctl + "flutter_amp") * length(air) * soft;
float physics_strength = clamp(chf(ctl + "physics_strength"), 0, 1);
@P += (sway + v@fside * flutter) * f@flen * f@fshade * f@fshade * physics_strength;
f@wind = length(across) * physics_strength;
'''

WING_FLAP_VEX = r'''
// Rotate about the shoulder (view axis). Runs after color so the painted bands ride with
// the wing instead of sliding through it.
vector r = @P - pivot;
float d = span_pos(@P);
float ang = -radians(chf(ctl + "flap_amp")) * envelope * (1 + chf(ctl + "tip_flex") * d)
          * sin(beat_w * @Time - chf(ctl + "tip_lag") * d);
@P = pivot + set(r.x * cos(ang) - r.y * sin(ang), r.x * sin(ang) + r.y * cos(ang), r.z);
'''

APPLY_BEND_VEX = r'''
// fshade runs 0 (root) → 1 (tip); quadratic falloff keeps the root planted.
@P += v@fside * f@bend * f@flen * f@fshade * f@fshade;
'''

ORGANIC_NOISE_VEX = r'''
// Organic imperfection: noisy vane edges, ragged/split barbs, and wandering shafts.
// Every term depends only on (fshade, feather_id, froot), so shaft, vane and outline
// points at the same position along a feather move together.
float t = f@fshade;
float id = i@feather_id;
float seed = chf("seed");
float halfw = f@half_w * f@flen * f@width_mult;

// Vane edges: low-frequency swelling, fine ragged barbs, and occasional deep splits
// that also pull back toward the root like separated barbs.
if (f@edge_side != 0) {
    float es = f@edge_side;
    float wobble = noise(set(t * chf("edge_freq"), id * 0.618 + es * 3.1, seed)) * 2 - 1;
    float ragged = pow(abs(onoise(set(t * chf("barb_freq"), id * 1.37 + es * 7.7, seed + 11))), 0.7);
    float split = smooth(chf("split_threshold"), 1.0,
                         noise(set(t * chf("barb_freq") * 0.35, id * 2.3 + es * 5.0, seed + 23)));
    float taper = smooth(0.0, 0.15, t);

    float disp = chf("edge_amp") * wobble - chf("barb_amp") * ragged - chf("split_depth") * split;
    @P += v@fside * es * disp * halfw * taper;
    @P -= v@fdir * split * chf("split_depth") * halfw * 0.6 * taper;
}

// Shaft curvature: per-feather wander plus a spatial wave shared by neighbouring
// feathers (unmirrored side axis, so both sides of a flow sway together).
float wander = noise(set(t * chf("curve_freq"), id * 0.73, seed + 31)) * 2 - 1;
float wave = noise(v@froot * chf("spatial_freq") + set(seed, seed * 0.5, 0)) * 2 - 1;
vector side_axis = v@fside * f@side;
@P += v@fside * wander * chf("curve_amp") * f@flen * t;
@P += side_axis * wave * chf("spatial_amp") * f@flen * t * t;
'''

FEATHER_COLOR_VEX = r'''
// Ramp lookup blended from four drivers:
//   position  - where the point sits on the canvas along gradient_dir (teal low → red high)
//   flow_u    - shoulder (root of the flow) vs flow tip; tips drift toward the start of the ramp
//   curveu    - root → tip inside each feather (fshade), so tips warm up
//   noise     - painterly breakup so bands don't read as clean stripes
vector rel = relbbox(0, @P) - {0.5, 0.5, 0.5};
float pos = dot(rel, normalize(chv("gradient_dir"))) + 0.5;
float flow = 1.0 - f@flow_u;
float along = f@fshade;

float freq = chf("noise_freq");
vector np = @P * freq + chf("noise_seed");
float n = (noise(np) * 2 - 1) + 0.5 * (noise(np * 2.7 + 13.1) * 2 - 1);

float w_pos = chf("w_position"), w_flow = chf("w_flow"), w_along = chf("w_curveu");
float lookup = (pos * w_pos + flow * w_flow + along * w_along) / max(w_pos + w_flow + w_along, 1e-5);
lookup += n * chf("noise_amount");
lookup += (rand(i@feather_id + 0.37) - 0.5) * chf("feather_jitter");
// Weighted averages bunch up mid-ramp; contrast spreads them back over the full range.
lookup = clamp((lookup - 0.5) * chf("contrast") + 0.5 + chf("ramp_offset") + f@layer_shift, 0, 1);

vector ramp_cd = chramp("color_ramp", lookup);
vector base = lerp(v@fcol, ramp_cd, chf("ramp_mix"));
float tint = f@layer_tint;
base = tint >= 0 ? lerp(base, chv("tint_color"), tint) : base * (1.0 + tint);

v@Cd = base * (0.75 + 0.35 * f@fshade) * f@side_light;
if (i@is_shaft)
    v@Cd = lerp(base, {1.0, 0.95, 0.85}, chf("shaft_brightness"));
f@color_lookup = lookup;
'''

PAINT_ATTRIBS_VEX = r'''
// Inputs for the /mat/feather_paint shader. fcolor duplicates Cd because Cd is exported to
// USD as displayColor; fseed offsets the streak texture so neighbouring feathers differ.
v@fcolor = v@Cd;
setattribtypeinfo(0, "point", "fcolor", "color");
f@fseed = rand(i@feather_id + 0.71) * 100.0;
'''


def color_ramp() -> hou.Ramp:
    """Teal → green → peach → red."""
    keys = (0.0, 0.3, 0.62, 1.0)
    colors = (
        (0.10, 0.42, 0.48),
        (0.40, 0.58, 0.26),
        (0.98, 0.62, 0.42),
        (0.80, 0.10, 0.08),
    )
    return hou.Ramp((hou.rampBasis.CatmullRom,) * len(keys), keys, colors)


# ---------------------------------------------------------------------------
# Node helpers
# ---------------------------------------------------------------------------
_RUN_OVER = {"detail": 0, "prims": 1, "points": 2}


def _geo(name: str) -> hou.ObjNode:
    obj = hou.node("/obj")
    existing = obj.node(name)
    if existing is not None:
        existing.destroy()
    geo = obj.createNode("geo", name)
    for child in list(geo.children()):
        child.destroy()
    return geo


def _wrangle(parent: hou.Node, name: str, code: str, inputs=(), run_over: str = "points") -> hou.Node:
    node = parent.createNode("attribwrangle", name)
    node.parm("snippet").set(code)
    node.parm("class").set(_RUN_OVER[run_over])
    for i, src in enumerate(inputs):
        node.setInput(i, src)
    return node


def _null(parent: hou.Node, name: str, inp: hou.Node | None = None) -> hou.Node:
    node = parent.createNode("null", name)
    if inp is not None:
        node.setInput(0, inp)
    return node


def _fparm(name: str, label: str, default: float, lo: float, hi: float) -> hou.FloatParmTemplate:
    return hou.FloatParmTemplate(name, label, 1, default_value=(default,), min=lo, max=hi)


def _iparm(name: str, label: str, default: int, lo: int, hi: int) -> hou.IntParmTemplate:
    return hou.IntParmTemplate(name, label, 1, default_value=(default,), min=lo, max=hi)


def _add_parms(node: hou.Node, *templates: hou.ParmTemplate) -> None:
    ptg = node.parmTemplateGroup()
    for template in templates:
        ptg.append(template)
    node.setParmTemplateGroup(ptg)


def _randomize(parent: hou.Node, name: str, attr: str, lo: float, hi: float, seed: int, inp: hou.Node) -> hou.Node:
    """Uniform 1D point-attribute randomization."""
    node = parent.createNode("attribrandomize", name)
    node.setInput(0, inp)
    node.parm("class").set(2)
    node.parm("name").set(attr)
    node.parm("operation").set("set")
    node.parm("distribution").set("uniform")
    node.parm("dimensions").set(1)
    node.parm("minx").set(lo)
    node.parm("maxx").set(hi)
    node.parm("seed").set(seed)
    return node


def _switch(parent: hou.Node, name: str, off: hou.Node, on: hou.Node, enabled: bool) -> hou.Node:
    node = parent.createNode("switch", name)
    node.setInput(0, off)
    node.setInput(1, on)
    node.parm("input").set(int(enabled))
    return node


# ---------------------------------------------------------------------------
# Network stages
# ---------------------------------------------------------------------------
def _px_to_world(px: float, py: float) -> tuple[float, float]:
    return ((px - REF_W * 0.5) * REF_SCALE, (REF_H * 0.5 - py) * REF_SCALE)


def flow_guides_vex() -> str:
    lines = [
        "// Feather flow guides: root (curveu=0) → tip (curveu=1).",
        "// Edit the key arrays to reshape a flow; keys are Catmull-Rom control points.",
        "int samples = chi(\"samples\");",
        "vector keys[];",
        "int pts[];",
    ]
    for fid, (name, col, band_px, keys) in enumerate(FEATHER_FLOWS):
        world = [_px_to_world(x, y) for x, y in keys]
        # Duplicate endpoints so the catrom spline passes through every key.
        world = [world[0]] + world + [world[-1]]
        key_str = ", ".join(f"{{{x:.4f}, {y:.4f}, 0}}" for x, y in world)
        lines += [
            f"// --- {name} ---",
            f"keys = array({key_str});",
            "resize(pts, 0);",
            "for (int i = 0; i < samples; i++) {",
            "    float u = float(i) / float(samples - 1);",
            "    int pt = addpoint(0, spline(\"catrom\", u, keys));",
            "    setpointattrib(0, \"curveu\", pt, u, \"set\");",
            "    append(pts, pt);",
            "}",
            f"int pr_{name} = addprim(0, \"polyline\", pts);",
            f"setprimattrib(0, \"flow_id\", pr_{name}, {fid}, \"set\");",
            f"setprimattrib(0, \"flow_name\", pr_{name}, \"{name}\", \"set\");",
            f"setprimattrib(0, \"band_width\", pr_{name}, {band_px * REF_SCALE:.4f}, \"set\");",
            f"setprimattrib(0, \"Cd\", pr_{name}, set({col[0]}, {col[1]}, {col[2]}), \"set\");",
        ]
    return "\n".join(lines)


def build_reference(geo: hou.Node) -> tuple[hou.Node, hou.Node]:
    """Grid carrying the painting as point color. Returns (full-brightness map, dimmed display)."""
    half_w = REF_W * 0.5 * REF_SCALE
    half_h = REF_H * 0.5 * REF_SCALE
    grid = geo.createNode("grid", "ref_plane")
    grid.parm("orient").set("xy")
    grid.parm("sizex").set(REF_W * REF_SCALE)
    grid.parm("sizey").set(REF_H * REF_SCALE)
    grid.parm("rows").set(230)
    grid.parm("cols").set(340)
    grid_uv = _wrangle(
        geo,
        "ref_uv",
        f"v@uv = set(fit(@P.x, {-half_w}, {half_w}, 0, 1), fit(@P.y, {-half_h}, {half_h}, 0, 1), 0);\n"
        "@P.z = -0.02;",
        inputs=[grid],
    )
    ref_map = geo.createNode("attribfrommap", "ref_image")
    ref_map.setInput(0, grid_uv)
    ref_map.parm("filename").set(REF_IMAGE.replace("\\", "/"))
    ref_map.parm("uvattrib").set("uv")
    ref_dim = _wrangle(geo, "ref_dim", "v@Cd *= chf(\"ref_brightness\");", inputs=[ref_map])
    _add_parms(ref_dim, _fparm("ref_brightness", "Ref Brightness", 0.45, 0.0, 1.0))
    return ref_map, ref_dim


def build_guides(geo: hou.Node) -> tuple[hou.Node, hou.Node]:
    """Returns (OUT_FLOW_GUIDES, guide display tubes + root markers)."""
    empty = geo.createNode("null", "guides_empty")
    guides = _wrangle(geo, "flow_guide_curves", flow_guides_vex(), inputs=[empty], run_over="detail")
    _add_parms(guides, _iparm("samples", "Samples Per Flow", 96, 8, 512))
    guide_attrs = _wrangle(geo, "flow_attrs", FLOW_ATTRS_VEX, inputs=[guides])
    out_guides = _null(geo, "OUT_FLOW_GUIDES", guide_attrs)
    out_guides.setComment("Clean guide curves for feather scattering (flow_id, curveu, tangentu, band_profile)")

    wire = geo.createNode("polywire", "guide_wire")
    wire.setInput(0, out_guides)
    wire.parm("radius").set(1.0)
    wire.parm("usescaleattrib").set(True)
    wire.parm("div").set(6)

    root_marks = _wrangle(geo, "root_markers", "if (@curveu > 0.0) removepoint(0, @ptnum);", inputs=[out_guides])
    sphere = geo.createNode("sphere", "root_sphere")
    sphere.parm("type").set("polymesh")
    sphere.parm("scale").set(0.07)
    root_copies = geo.createNode("copytopoints::2.0", "root_copies")
    root_copies.setInput(0, sphere)
    root_copies.setInput(1, root_marks)

    display = geo.createNode("merge", "MERGE_GUIDE_DISPLAY")
    display.setInput(0, wire)
    display.setInput(1, root_copies)
    return out_guides, display


def build_feather_layer(geo: hou.Node, layer_id: int, cfg: dict, guides: hou.Node, ref_map: hou.Node) -> hou.Node:
    """One feather system as a subnet: resample → roots → Attribute Randomize → copy prototypes.

    Subnet inputs: 0 = flow guides, 1 = reference image map. Output: copied feathers (undeformed).
    """
    net = geo.createNode("subnet", f"layer_{cfg['name']}")
    net.setInput(0, guides)
    net.setInput(1, ref_map)
    net.setComment(f"{cfg['name']}: length {cfg['length']}, spacing {cfg['spacing']}, rows {cfg['rows']}")
    guides_in, ref_in = net.indirectInputs()[:2]

    resample = net.createNode("resample", "guide_resample")
    resample.setInput(0, guides_in)
    resample.parm("dolength").set(True)
    resample.parm("length").set(cfg["spacing"])
    resample.parm("docurveuattr").set(True)

    roots = _wrangle(net, "feather_roots", FEATHER_ROOTS_VEX, inputs=[resample, ref_in])
    _add_parms(
        roots,
        _iparm("layer_id", "Layer ID", layer_id, 0, 10),
        _fparm("spacing", "Spacing", 0.05, 0.005, 1.0),
        _iparm("rows_per_sample", "Feathers Per Sample", cfg["rows"], 1, 12),
        _fparm("feather_length", "Feather Length", cfg["length"], 0.05, 4.0),
        _fparm("splay", "Splay (deg)", cfg["splay"], 0.0, 90.0),
        _fparm("band_spread", "Band Spread", cfg["spread"], 0.0, 3.0),
        _fparm("u_min", "Flow Start", cfg["u_range"][0], 0.0, 1.0),
        _fparm("u_max", "Flow End", cfg["u_range"][1], 0.0, 1.0),
        _fparm("u_fade", "Flow Fade", 0.12, 0.0, 0.5),
        _fparm("layer_z", "Layer Depth", cfg["z"], 0.0, 1.0),
        _fparm("color_shift", "Color Ramp Shift", cfg["shift"], -0.5, 0.5),
        _fparm("color_tint", "Color Tint", cfg["tint"], -1.0, 1.0),
        _fparm("ref_color_mix", "Ref Color Mix", 0.6, 0.0, 1.0),
        _iparm("variants", "Variants", 4, 1, 4),
    )
    roots.parm("spacing").setExpression('ch("../guide_resample/length")')
    roots_only = _wrangle(net, "roots_points_only", "removeprim(0, @primnum, 0);", inputs=[roots], run_over="prims")

    seed = layer_id * 1000
    rnd = _randomize(net, "rand_length", "len_mult", *cfg["len_range"], seed + 11, roots_only)
    rnd = _randomize(net, "rand_width", "width_mult", 0.75, 1.3, seed + 23, rnd)
    rnd = _randomize(net, "rand_bend", "bend", -0.08, 0.15, seed + 37, rnd)
    rnd = _randomize(net, "rand_overlap", "overlap", 0.0, 1.0, seed + 53, rnd)
    rnd = _randomize(net, "rand_rotation", "rot_jitter", *cfg["rot_range"], seed + 71, rnd)

    apply_rand = _wrangle(net, "apply_randomize", APPLY_RANDOMIZE_VEX, inputs=[rnd])
    _add_parms(
        apply_rand,
        _fparm("width_scale", "Layer Width", cfg["width"], 0.1, 3.0),
        _fparm("overlap_tuck", "Overlap Tuck", 0.25, 0.0, 1.0),
        _fparm("overlap_depth", "Overlap Depth", 0.012, 0.0, 0.1),
    )
    out_roots = _null(net, "OUT_ROOTS", apply_rand)

    proto_empty = net.createNode("null", "proto_empty")
    proto = _wrangle(net, "feather_prototypes", FEATHER_PROTOTYPE_VEX, inputs=[proto_empty], run_over="detail")
    _add_parms(proto, _iparm("segments", "Segments", cfg["segments"], 8, 200))

    copy = net.createNode("copytopoints::2.0", "copy_feathers")
    copy.setInput(0, proto)
    copy.setInput(1, out_roots)
    copy.parm("useidattrib").set(True)
    copy.parm("idattrib").set("variant")
    copy.parm("targetattribs").set(1)
    copy.parm("applyto1").set(0)
    copy.parm("applymethod1").set(0)
    copy.parm("applyattribs1").set(COPIED_ATTRIBS)

    output = net.createNode("output", "output0")
    output.setInput(0, copy)
    for node in net.children():
        node.moveToGoodPosition()
    return net


def build_wing_controls(geo: hou.Node) -> hou.Node:
    """Null holding the wing-beat and wind settings read by wing_wind and wing_flap."""
    controls = geo.createNode("null", "WING_CONTROLS")
    pivot = _px_to_world(*SHOULDER_PX)
    _add_parms(
        controls,
        hou.FolderParmTemplate("beat", "Wing Beat", parm_templates=[
            hou.FloatParmTemplate("pivot", "Shoulder Pivot", 3, default_value=(pivot[0], pivot[1], 0.0)),
            _fparm("span", "Wing Span", 5.5, 0.5, 20.0),
            _fparm("flap_amp", "Beat Angle (deg)", 4.0, 0.0, 45.0),
            _fparm("flap_period", "Beat Period (s)", 4.0, 0.5, 20.0),
            _fparm("tip_flex", "Tip Flex", 0.5, 0.0, 3.0),
            _fparm("tip_lag", "Tip Lag (rad)", 1.1, 0.0, 6.3),
            _fparm("start_amount", "Beat While Small", 0.25, 0.0, 1.0),
        ]),
        hou.FolderParmTemplate("wind", "Wind", parm_templates=[
            _fparm("physics_strength", "Physics Strength", 0.0, 0.0, 1.0),
            hou.FloatParmTemplate("wind_dir", "Wind Direction", 3, default_value=(-1.0, -0.5, 0.0)),
            _fparm("wind_speed", "Wind Speed", 0.8, 0.0, 5.0),
            _fparm("gust_amp", "Gusts", 0.6, 0.0, 1.5),
            _fparm("gust_freq", "Gust Frequency (Hz)", 0.35, 0.0, 3.0),
            _fparm("turb_freq", "Turbulence Scale", 0.4, 0.0, 5.0),
            _fparm("turb_amp", "Turbulence", 0.5, 0.0, 2.0),
            _fparm("beat_drag", "Wing-Beat Airflow", 1.0, 0.0, 3.0),
            _fparm("wind_flex", "Feather Flex", 0.12, 0.0, 1.0),
            _fparm("growing_softness", "Growing Softness", 1.5, 0.0, 5.0),
            _fparm("flutter_amp", "Flutter", 0.02, 0.0, 0.2),
            _fparm("flutter_freq", "Flutter Frequency (Hz)", 3.0, 0.0, 12.0),
        ]),
    )
    controls.setComment("Wing beat + wind settings (read by wing_wind and wing_flap)")
    controls.setColor(hou.Color(0.9, 0.6, 0.2))
    return controls


def build_feathers(geo: hou.Node, guides: hou.Node, ref_map: hou.Node) -> tuple[hou.Node, hou.Node]:
    """Layered feather systems → deform → color. Returns (OUT_FEATHER_SHAPES, OUT_FEATHER_CURVES)."""
    layers = geo.createNode("merge", "MERGE_LAYERS")
    for i, cfg in enumerate(FEATHER_LAYERS):
        layers.setInput(i, build_feather_layer(geo, i, cfg, guides, ref_map))

    growth = _wrangle(geo, "oil_growth", OIL_GROWTH_VEX, inputs=[layers])
    _add_parms(
        growth,
        _fparm("start_frame", "Start Frame", GROW_FRAMES[0], 1, 480),
        _fparm("end_frame", "End Frame", GROW_FRAMES[1], 1, 480),
        _fparm("progress", "Progress", 1.0, 0.0, 1.0),
        _fparm("run_time", "Run Time (per feather)", 0.35, 0.02, 1.0),
        _fparm("flow_delay", "Flow Delay (shoulder → tip)", 0.6, 0.0, 1.0),
        _fparm("layer_delay", "Layer Delay (back → front)", 0.12, 0.0, 1.0),
        _fparm("birth_jitter", "Birth Jitter", 0.2, 0.0, 1.0),
        _fparm("viscosity", "Viscosity (slow-down)", 2.2, 1.0, 5.0),
        _iparm("surges", "Surges", 3, 1, 8),
        _fparm("surge_strength", "Surge Strength", 0.7, 0.0, 1.0),
        _fparm("lobe_freq", "Front Lobe Frequency", 3.0, 0.0, 12.0),
        _fparm("lobe_amp", "Front Lobes", 0.12, 0.0, 0.5),
        _fparm("spread_lag", "Sideways Spread Lag", 0.25, 0.0, 1.0),
        _fparm("head_swell", "Head Swell", 0.6, 0.0, 2.0),
        _fparm("wet_length", "Wet Length", 0.2, 0.01, 1.0),
        _iparm("layer_count", "Layer Count", len(FEATHER_LAYERS), 1, 10),
    )
    growth.parm("progress").setExpression(
        'clamp(($F - ch("start_frame")) / max(ch("end_frame") - ch("start_frame"), 1), 0, 1)')

    bend = _wrangle(geo, "apply_bend", APPLY_BEND_VEX, inputs=[growth])

    build_wing_controls(geo)
    wind = _wrangle(geo, "wing_wind", WING_ENVELOPE_VEX + WING_WIND_VEX, inputs=[bend])
    wind.setComment("Wind + wing-beat airflow bend the feathers (settings on WING_CONTROLS)")

    organic = _wrangle(geo, "organic_noise", ORGANIC_NOISE_VEX, inputs=[wind])
    _add_parms(
        organic,
        _fparm("seed", "Seed", 0.0, 0.0, 100.0),
        _fparm("edge_freq", "Edge Frequency", 3.0, 0.0, 20.0),
        _fparm("edge_amp", "Edge Wobble", 0.35, 0.0, 1.5),
        _fparm("barb_freq", "Barb Frequency", 12.0, 0.0, 60.0),
        _fparm("barb_amp", "Barb Raggedness", 0.35, 0.0, 1.5),
        _fparm("split_threshold", "Split Threshold", 0.6, 0.0, 1.0),
        _fparm("split_depth", "Split Depth", 0.6, 0.0, 1.5),
        _fparm("curve_freq", "Shaft Wander Frequency", 1.2, 0.0, 10.0),
        _fparm("curve_amp", "Shaft Wander", 0.08, 0.0, 0.5),
        _fparm("spatial_freq", "Flow Wave Frequency", 0.6, 0.0, 5.0),
        _fparm("spatial_amp", "Flow Wave", 0.12, 0.0, 0.5),
    )

    color = _wrangle(geo, "feather_color", FEATHER_COLOR_VEX, inputs=[organic])
    _add_parms(
        color,
        hou.RampParmTemplate("color_ramp", "Color Ramp", hou.rampParmType.Color, default_value=4),
        hou.FloatParmTemplate("gradient_dir", "Gradient Direction", 3, default_value=(0.25, 1.0, 0.0)),
        _fparm("w_position", "Position Weight", 0.6, 0.0, 1.0),
        _fparm("w_flow", "Flow (curveu) Weight", 0.25, 0.0, 1.0),
        _fparm("w_curveu", "Feather Root→Tip Weight", 0.15, 0.0, 1.0),
        _fparm("noise_amount", "Noise Amount", 0.25, 0.0, 1.0),
        _fparm("noise_freq", "Noise Frequency", 0.6, 0.0, 10.0),
        _fparm("noise_seed", "Noise Seed", 0.0, 0.0, 100.0),
        _fparm("feather_jitter", "Per-Feather Jitter", 0.08, 0.0, 0.5),
        _fparm("contrast", "Contrast", 1.8, 0.1, 4.0),
        _fparm("ramp_offset", "Ramp Offset", 0.0, -0.5, 0.5),
        _fparm("ramp_mix", "Ramp vs Painting Color", 1.0, 0.0, 1.0),
        hou.FloatParmTemplate("tint_color", "Layer Tint Color", 3, default_value=(1.0, 0.9, 0.72),
                              naming_scheme=hou.parmNamingScheme.RGBA, look=hou.parmLook.ColorSquare),
        _fparm("shaft_brightness", "Shaft Brightness", 0.3, 0.0, 1.0),
    )
    color.parm("color_ramp").set(color_ramp())

    paint_attribs = _wrangle(geo, "paint_attribs", PAINT_ATTRIBS_VEX, inputs=[color])
    flap = _wrangle(geo, "wing_flap", WING_ENVELOPE_VEX + WING_FLAP_VEX, inputs=[paint_attribs])
    flap.setComment("Gentle wing beat about the shoulder (settings on WING_CONTROLS)")

    shapes = _wrangle(
        geo,
        "keep_shapes",
        'if (s@kind != "vane" && s@kind != "shaft_strip") removeprim(0, @primnum, 1);',
        inputs=[flap],
        run_over="prims",
    )
    assign = _wrangle(geo, "assign_paint_material", f's@shop_materialpath = "{PAINT_MATERIAL}";',
                      inputs=[shapes], run_over="prims")
    out_shapes = _null(geo, "OUT_FEATHER_SHAPES", assign)
    out_shapes.setComment("Feather vanes + shaft strips with uv, fcolor, fseed for the painted shader")

    curves = _wrangle(
        geo,
        "keep_curves",
        'if (s@kind != "outline_curve" && s@kind != "shaft_curve") removeprim(0, @primnum, 1);',
        inputs=[flap],
        run_over="prims",
    )
    out_curves = _null(geo, "OUT_FEATHER_CURVES", curves)
    out_curves.setComment("Copied feather curves (outline + shaft) with curveu for growth")
    return out_shapes, out_curves


def _mtlx(parent: hou.Node, type_name: str, name: str, signature: str | None = None,
          inputs: dict | None = None, **parms) -> hou.Node:
    """MaterialX VOP. inputs maps input name → node or (node, output name)."""
    node = parent.createNode(type_name, name)
    if signature:
        node.parm("signature").set(signature)
    for parm_name, value in parms.items():
        node.parm(parm_name).set(value)
    for input_name, src in (inputs or {}).items():
        src_node, out_name = src if isinstance(src, tuple) else (src, "out")
        node.setNamedInput(input_name, src_node, out_name)
    return node


def _mtlx_material(path: str, comment: str) -> hou.Node:
    """Fresh Karma MaterialX builder subnet at path (replaces an existing one)."""
    import voptoolutils

    parent_path, name = path.rsplit("/", 1)
    parent = hou.node(parent_path)
    old = parent.node(name)
    if old is not None:
        old.destroy()
    voptoolutils._setupMtlXBuilderSubnet(destination_node=parent, name=name, mask=voptoolutils.KARMAMTLX_TAB_MASK,
                                         folder_label="Karma Material Builder", render_context="kma")
    net = parent.node(name)
    net.setComment(comment)
    return net


def _mtlx_weighted_sum(net: hou.Node, name: str, terms) -> hou.Node:
    """Float sum of (node, weight) pairs."""
    total = None
    for i, (src, weight) in enumerate(terms):
        term = _mtlx(net, "mtlxmultiply", f"{name}_w{i}", "float", inputs={"in1": src}, in2=weight)
        total = term if total is None else _mtlx(net, "mtlxadd", f"{name}_add{i}", "float",
                                                 inputs={"in1": total, "in2": term})
    return total


def build_paint_material() -> hou.Node:
    """Karma MaterialX oil-paint material for the feathers.

    uv.v runs root → tip and each row of vane quads follows one barb, so noise stretched
    across u and squeezed along v gives strokes along the barbs:
      barb_streaks   fine strokes              brush_bands   broad strokes (+ slight hue drift)
      bristles       very fine bristle grooves (impasto only)
    The same noises drive an impasto bump, the vane edges break up like dry brush over a dark
    ground, and fresh paint at the oil_growth front (wet) is darker and glossier.
    """
    net = _mtlx_material(PAINT_MATERIAL, "Oil-painted feathers: strokes along feather uvs, impasto, dry-brush edges, wet front")

    uv = _mtlx(net, "mtlxtexcoord", "feather_uv", "vector2")
    seed = _mtlx(net, "mtlxgeompropvalue", "feather_seed", "float", geomprop="fseed")
    feather_color = _mtlx(net, "mtlxgeompropvalue", "feather_color", "color3", geomprop="fcolor")
    wet = _mtlx(net, "mtlxgeompropvalue", "wet_paint", "float", geomprop="wet")

    # Stroke space: (u across vane, v along shaft, per-feather seed).
    streak_scale = _mtlx(net, "mtlxmultiply", "streak_scale", "vector2", inputs={"in1": uv},
                         in2_vector2x=4.0, in2_vector2y=90.0)
    split = _mtlx(net, "mtlxseparate2", "split_uv", inputs={"in": streak_scale})
    streak_space = _mtlx(net, "mtlxcombine3", "streak_space",
                         inputs={"in1": (split, "outx"), "in2": (split, "outy"), "in3": seed})

    def stroke_noise(name, scale, octaves):
        space = _mtlx(net, "mtlxmultiply", f"{name}_scale", "vector3", inputs={"in1": streak_space},
                      in2_vector3x=scale[0], in2_vector3y=scale[1], in2_vector3z=1.0)
        return _mtlx(net, "mtlxfractal3d", name, "float", inputs={"position": space},
                     octaves=octaves, lacunarity=2.1, diminish=0.55)

    barbs = stroke_noise("barb_streaks", (1.0, 1.0), 3)
    brush = stroke_noise("brush_bands", (0.35, 0.13), 2)
    bristles = stroke_noise("bristles", (0.4, 3.0), 2)

    # Color: strokes modulate the SOP color, broad strokes drift the hue a little.
    barbs_gain = _mtlx(net, "mtlxremap", "barb_contrast", "float", inputs={"in": barbs},
                       inlow=-0.45, inhigh=0.45, outlow=0.62, outhigh=1.22)
    brush_gain = _mtlx(net, "mtlxremap", "brush_contrast", "float", inputs={"in": brush},
                       inlow=-0.5, inhigh=0.5, outlow=0.8, outhigh=1.15)
    streaks = _mtlx(net, "mtlxmultiply", "streaks", "float", inputs={"in1": barbs_gain, "in2": brush_gain})
    painted = _mtlx(net, "mtlxmultiply", "painted_color", "color3FA",
                    inputs={"in1": feather_color, "in2": streaks})
    hue_drift = _mtlx(net, "mtlxremap", "hue_drift", "float", inputs={"in": brush},
                      inlow=-0.5, inhigh=0.5, outlow=-0.03, outhigh=0.03)
    # hsvadjust amount = (hue shift, saturation, value).
    hsv_amount = _mtlx(net, "mtlxcombine3", "hsv_amount", inputs={"in1": hue_drift}, in2=1.55, in3=1.05)
    saturated = _mtlx(net, "mtlxhsvadjust", "paint_saturation", "color3",
                      inputs={"in": painted, "amount": hsv_amount})

    # Dry brush: toward the vane edges the paint thins and breaks up over the dark ground.
    raw_uv = _mtlx(net, "mtlxseparate2", "raw_uv", inputs={"in": uv})
    centered = _mtlx(net, "mtlxsubtract", "u_from_shaft", "float", inputs={"in1": (raw_uv, "outx")}, in2=0.5)
    edge = _mtlx(net, "mtlxabsval", "u_edge", "float", inputs={"in": centered})
    dry_in = _mtlx_weighted_sum(net, "dry_in", [(edge, 2.0), (barbs, 0.5)])
    dry = _mtlx(net, "mtlxsmoothstep", "dry_brush", "float", inputs={"in": dry_in}, low=0.8, high=1.25)
    dry_mix = _mtlx(net, "mtlxmultiply", "dry_strength", "float", inputs={"in1": dry}, in2=0.55)
    ground = _mtlx(net, "mtlxconstant", "ground_color", "color3",
                   value_color3r=0.05, value_color3g=0.03, value_color3b=0.025)
    dried = _mtlx(net, "mtlxmix", "dry_over_ground", "color3",
                  inputs={"fg": ground, "bg": saturated, "mix": dry_mix})

    # Wet paint at the running front: darker, glossier.
    wet_dark = _mtlx(net, "mtlxremap", "wet_darken", "float", inputs={"in": wet},
                     inlow=0.0, inhigh=1.0, outlow=1.0, outhigh=0.72)
    base_color = _mtlx(net, "mtlxmultiply", "oil_color", "color3FA", inputs={"in1": dried, "in2": wet_dark})
    roughness = _mtlx(net, "mtlxremap", "wet_roughness", "float", inputs={"in": wet},
                      inlow=0.0, inhigh=1.0, outlow=0.5, outhigh=0.15)
    specular = _mtlx(net, "mtlxremap", "wet_specular", "float", inputs={"in": wet},
                     inlow=0.0, inhigh=1.0, outlow=0.25, outhigh=0.7)

    # Impasto: thick ridges along the strokes, bristle grooves inside them.
    height = _mtlx_weighted_sum(net, "impasto_height", [(brush, 0.8), (barbs, 0.5), (bristles, 0.3)])
    impasto = _mtlx(net, "mtlxbump", "impasto", inputs={"height": height}, scale=0.04)

    surface = net.node("mtlxstandard_surface")
    surface.setNamedInput("base_color", base_color, "out")
    surface.setNamedInput("specular_roughness", roughness, "out")
    surface.setNamedInput("specular", specular, "out")
    surface.setNamedInput("normal", impasto, "out")
    surface.setNamedInput("coat_normal", impasto, "out")
    for parm_name, value in (("base", 1.0), ("diffuse_roughness", 0.4), ("coat", 0.12),
                             ("coat_roughness", 0.3)):
        surface.parm(parm_name).set(value)

    net.layoutChildren()
    return net


def build_canvas_material() -> hou.Node:
    """Dark oil ground behind the feathers: loose horizontal strokes of umber and deep red."""
    net = _mtlx_material(CANVAS_MATERIAL, "Dark painted ground with loose strokes and impasto")

    uv = _mtlx(net, "mtlxtexcoord", "canvas_uv", "vector2")
    split = _mtlx(net, "mtlxseparate2", "split_uv", inputs={"in": uv})
    space = _mtlx(net, "mtlxcombine3", "stroke_space", inputs={"in1": (split, "outx"), "in2": (split, "outy")},
                  in3=0.0)
    stroke_space = _mtlx(net, "mtlxmultiply", "stroke_scale", "vector3", inputs={"in1": space},
                         in2_vector3x=3.0, in2_vector3y=9.0, in2_vector3z=1.0)
    strokes = _mtlx(net, "mtlxfractal3d", "ground_strokes", "float", inputs={"position": stroke_space},
                    octaves=4, lacunarity=2.2, diminish=0.55)
    grain_space = _mtlx(net, "mtlxmultiply", "grain_scale", "vector3", inputs={"in1": space},
                        in2_vector3x=260.0, in2_vector3y=260.0, in2_vector3z=1.0)
    grain = _mtlx(net, "mtlxfractal3d", "canvas_grain", "float", inputs={"position": grain_space}, octaves=2)

    umber = _mtlx(net, "mtlxconstant", "umber", "color3",
                  value_color3r=0.03, value_color3g=0.02, value_color3b=0.018)
    oxblood = _mtlx(net, "mtlxconstant", "oxblood", "color3",
                    value_color3r=0.09, value_color3g=0.025, value_color3b=0.018)
    warm = _mtlx(net, "mtlxsmoothstep", "warm_strokes", "float", inputs={"in": strokes}, low=0.15, high=0.7)
    color = _mtlx(net, "mtlxmix", "ground_color", "color3", inputs={"fg": oxblood, "bg": umber, "mix": warm})

    height = _mtlx_weighted_sum(net, "ground_height", [(strokes, 1.0), (grain, 0.15)])
    bump = _mtlx(net, "mtlxbump", "ground_impasto", inputs={"height": height}, scale=0.03)

    surface = net.node("mtlxstandard_surface")
    surface.setNamedInput("base_color", color, "out")
    surface.setNamedInput("normal", bump, "out")
    for parm_name, value in (("base", 1.0), ("specular", 0.35), ("specular_roughness", 0.4)):
        surface.parm(parm_name).set(value)

    net.layoutChildren()
    return net


def build_canvas(geo: hou.Node) -> hou.Node:
    """Render-only canvas plane just behind the feathers (the viewport keeps the reference image)."""
    grid = geo.createNode("grid", "canvas_plane")
    grid.parm("orient").set("xy")
    grid.parm("sizex").set(12.0)
    grid.parm("sizey").set(8.0)
    grid.parm("rows").set(2)
    grid.parm("cols").set(2)
    canvas = _wrangle(
        geo,
        "canvas_attribs",
        "v@uv = set(fit(@P.x, -6, 6, 0, 1), fit(@P.y, -4, 4, 0, 1), 0);\n"
        "@P.z = -0.03;",
        inputs=[grid],
    )
    return _null(geo, "OUT_CANVAS", canvas)


def build_paint_render(shapes: hou.Node, canvas: hou.Node) -> hou.Node:
    """/stage chain: import feathers + canvas → bind materials → camera + lights → Karma → USD Render ROP."""
    stage = hou.node("/stage")
    for node_name in PAINT_STAGE_NODES:
        old = stage.node(node_name)
        if old is not None:
            old.destroy()

    feathers = stage.createNode("sopimport", "paint_feathers")
    feathers.parm("soppath").set(shapes.path())
    feathers.parm("enable_pathprefix").set(True)
    feathers.parm("pathprefix").set("/feathers")

    ground = stage.createNode("sopimport", "paint_canvas")
    ground.setInput(0, feathers)
    ground.parm("soppath").set(canvas.path())
    ground.parm("enable_pathprefix").set(True)
    ground.parm("pathprefix").set("/canvas")

    materials = stage.createNode("materiallibrary", "paint_materials")
    materials.setInput(0, ground)
    materials.parm("matnet").set("/mat")
    bindings = ((PAINT_MATERIAL, "/feathers"), (CANVAS_MATERIAL, "/canvas"))
    materials.parm("materials").set(len(bindings))
    for i, (mat_path, geo_path) in enumerate(bindings, start=1):
        materials.parm(f"matnode{i}").set(mat_path)
        materials.parm(f"matpath{i}").set("/materials/" + mat_path.rsplit("/", 1)[-1])
        materials.parm(f"assign{i}").set(True)
        materials.parm(f"geopath{i}").set(geo_path)

    # SOP Import drops the object transform, so frame the geometry at the origin.
    cam = stage.createNode("camera", "paint_camera")
    cam.setInput(0, materials)
    cam.parm("primpath").set("/cameras/cam_paint")
    cam.parmTuple("t").set((0.0, 0.0, 7.5))
    cam.parm("horizontalAperture").set(41.4214)
    cam.parm("aspectratiox").set(PAINT_RENDER_RES[0])
    cam.parm("aspectratioy").set(PAINT_RENDER_RES[1])
    cam.parm("focalLength").set(35.0)

    dome = stage.createNode("domelight::3.0", "paint_dome")
    dome.setInput(0, cam)
    dome.parm("xn__inputsintensity_i0a").set(0.45)

    key = stage.createNode("distantlight::2.0", "paint_key")
    key.setInput(0, dome)
    key.parmTuple("r").set((-25.0, 20.0, 0.0))
    key.parm("xn__inputsintensity_i0a").set(0.9)

    karma = stage.createNode("karmarenderproperties", "paint_karma")
    karma.setInput(0, key)
    karma.parm("camera").set("/cameras/cam_paint")
    karma.parm("resolutionx").set(PAINT_RENDER_RES[0])  # height follows the camera aperture
    karma.parm("engine").set("cpu")
    karma.parm("samplesperpixel").set(12)
    karma.parm("picture").set("$HIP/render/feather_paint.$F4.png")
    karma.setDisplayFlag(True)

    rop = stage.createNode("usdrender_rop", "paint_render")
    rop.setInput(0, karma)
    rop.parm("renderer").set("BRAY_HdKarma")
    rop.parm("trange").set(0)

    stage.layoutChildren()
    return rop


def build_flow_guides() -> hou.ObjNode:
    geo = _geo("feather_flow_guides")
    geo.parm("tx").set(FLOW_OFFSET_X)

    ref_map, ref_dim = build_reference(geo)
    guides, guide_display = build_guides(geo)
    shapes, _ = build_feathers(geo, guides, ref_map)
    canvas = build_canvas(geo)

    # Toggles so the feathers can be judged with or without the painting / guides.
    nothing = geo.createNode("null", "nothing")
    nothing.setInput(0, geo.node("guides_empty"))
    show_ref = _switch(geo, "show_ref", nothing, ref_dim, enabled=True)
    show_guides = _switch(geo, "show_guides", nothing, guide_display, enabled=False)

    merge = geo.createNode("merge", "MERGE_DISPLAY")
    merge.setInput(0, show_ref)
    merge.setInput(1, shapes)
    merge.setInput(2, show_guides)
    display = _null(geo, "OUT_DISPLAY", merge)
    display.setDisplayFlag(True)
    display.setRenderFlag(True)

    for node in geo.children():
        node.moveToGoodPosition()

    old_cam = hou.node("/obj/cam_flow_guides")
    if old_cam is not None:
        old_cam.destroy()
    cam = hou.node("/obj").createNode("cam", "cam_flow_guides")
    cam.parmTuple("t").set((FLOW_OFFSET_X, 0.0, 7.5))
    cam.parm("focal").set(35)

    build_paint_material()
    build_canvas_material()
    build_paint_render(shapes, canvas)
    hou.playbar.setFrameRange(1, 240)
    return geo


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def _remove_legacy_nodes() -> None:
    for path in LEGACY_NODES:
        node = hou.node(path)
        if node is not None:
            node.destroy()
            print("Removed legacy node:", path)


def rebuild_in_session() -> None:
    """Rebuild /obj/feather_flow_guides in the open Houdini session (run from the Python Shell)."""
    _remove_legacy_nodes()
    build_flow_guides()
    print("Rebuilt feather_flow_guides in the current session; save to keep it.")


def update_flow_guides() -> None:
    """Rebuild only /obj/feather_flow_guides inside the existing hip, keeping manual edits elsewhere."""
    hou.hipFile.load(HIP_OUT, suppress_save_prompt=True, ignore_load_warnings=True)
    _remove_legacy_nodes()
    build_flow_guides()
    hou.hipFile.save(HIP_OUT)
    print("Updated feather_flow_guides in:", HIP_OUT)


def build() -> None:
    """Fresh hip containing only the feather flow system."""
    hou.hipFile.clear(suppress_save_prompt=True)
    build_flow_guides()
    hou.hipFile.save(HIP_OUT)
    print("Saved:", HIP_OUT)


if __name__ == "__main__":
    if "--full" in sys.argv or not os.path.exists(HIP_OUT):
        build()
    else:
        update_flow_guides()
