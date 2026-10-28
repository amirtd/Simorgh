"""Build an animatable Phoenix body skeleton around the procedural feather wing.

The source feather system is left untouched.  This script loads the newest
phoenix_birth scene, adds /obj/phoenix_character_rig, and saves a new
phoenix_character_rig.hipnc scene.

Run with Houdini's Python:
    hython build_phoenix_character_rig.py
"""

from __future__ import annotations

import os

try:
    hou  # type: ignore[name-defined]
except NameError:
    import hou  # type: ignore


ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE_CANDIDATES = (
    os.path.join(ROOT, "phoenix_birth.hipnc"),
    os.path.join(ROOT, "phoenix_birth.hip"),
)
OUTPUT = os.path.join(ROOT, "phoenix_character_rig.hipnc")

# The existing wing's shoulder pivot in world space.  build_phoenix.py places
# the feather object at +7 X; its local pivot is (2.49, 0.5725, 0).
SHOULDER = (9.49, 0.5725, 0.0)
ELBOW = (7.80, 0.70, 0.0)
WRIST = (6.25, 0.54, 0.0)
WING_TIP = (4.10, 0.18, 0.0)


def latest_source() -> str:
    existing = [p for p in SOURCE_CANDIDATES if os.path.exists(p)]
    if not existing:
        raise FileNotFoundError("No phoenix_birth.hipnc or phoenix_birth.hip found")
    return max(existing, key=os.path.getmtime)


def float_parm(name: str, label: str, default: float, lo: float, hi: float) -> hou.FloatParmTemplate:
    parm = hou.FloatParmTemplate(name, label, 1, default_value=(default,))
    parm.setMinValue(lo)
    parm.setMaxValue(hi)
    parm.setMinIsStrict(False)
    parm.setMaxIsStrict(False)
    return parm


def toggle_parm(name: str, label: str, default: bool) -> hou.ToggleParmTemplate:
    return hou.ToggleParmTemplate(name, label, default_value=default)


def vector_parm(name: str, label: str, default=(0.0, 0.0, 0.0)) -> hou.FloatParmTemplate:
    return hou.FloatParmTemplate(
        name,
        label,
        3,
        default_value=default,
        naming_scheme=hou.parmNamingScheme.XYZW,
    )


def add_controls(geo: hou.Node) -> None:
    group = geo.parmTemplateGroup()
    folder = hou.FolderParmTemplate(
        "phoenix_rig_controls",
        "Phoenix Rig Controls",
        parm_templates=[
            float_parm("feather_growth", "Feather Growth Completion", 1.0, 0.0, 1.0),
            float_parm("wind_physics_strength", "Wind Physics Strength", 0.0, 0.0, 1.0),
            toggle_parm("roots_only_preview", "Roots Only Preview", True),
            toggle_parm("auto_flap", "Auto Flap", False),
            float_parm("flap_angle", "Flap Offset (deg)", 0.0, -90.0, 90.0),
            float_parm("flap_amplitude", "Flap Amplitude (deg)", 0.0, 0.0, 90.0),
            float_parm("flap_period", "Flap Period (sec)", 1.35, 0.15, 10.0),
            float_parm("shoulder_sweep", "Shoulder Open/Sweep Y (deg)", 0.0, -75.0, 75.0),
            float_parm("elbow_fold", "Elbow Fold (deg)", 0.0, -120.0, 120.0),
            float_parm("wrist_curl", "Wrist Curl (deg)", 0.0, -120.0, 120.0),
            float_parm("wing_twist", "Wing Twist (deg)", 0.0, -60.0, 60.0),
            float_parm("feather_flex", "Feather Flex", 0.0, 0.0, 1.0),
            float_parm("body_pitch", "Body Pitch (deg)", 0.0, -45.0, 45.0),
            float_parm("neck_pitch", "Neck Pitch (deg)", 0.0, -60.0, 60.0),
            float_parm("head_pitch", "Head Pitch (deg)", 0.0, -60.0, 60.0),
            vector_parm("body_center_t", "Body Center Position"),
            vector_parm("body_center_r", "Body Center Rotation"),
            vector_parm("foot_l_t", "Left Foot Position"),
            vector_parm("foot_l_r", "Left Foot Rotation"),
            float_parm("leg_pin_l", "Left Leg World Pin", 0.0, 0.0, 1.0),
            float_parm("toe_l_curl", "Left Toe Curl (deg)", 0.0, -90.0, 90.0),
            float_parm("toe_l_spread", "Left Toe Spread (deg)", 0.0, -45.0, 45.0),
            float_parm("hallux_l_curl", "Left Hallux Curl (deg)", 0.0, -90.0, 90.0),
            vector_parm("foot_r_t", "Right Foot Position"),
            vector_parm("foot_r_r", "Right Foot Rotation"),
            float_parm("leg_pin_r", "Right Leg World Pin", 0.0, 0.0, 1.0),
            float_parm("toe_r_curl", "Right Toe Curl (deg)", 0.0, -90.0, 90.0),
            float_parm("toe_r_spread", "Right Toe Spread (deg)", 0.0, -45.0, 45.0),
            float_parm("hallux_r_curl", "Right Hallux Curl (deg)", 0.0, -90.0, 90.0),
            toggle_parm("show_wing_boundary", "Show Wing Boundary", True),
            vector_parm("wing_boundary_offset", "Wing Boundary Position Offset"),
            float_parm("wing_boundary_thickness", "Wing Boundary Thickness", 0.08, 0.0, 0.4),
            float_parm("wing_boundary_bevel_radius", "Wing Boundary Bevel Radius", 0.03, 0.0, 0.2),
            toggle_parm("show_body_proxy", "Show Body Proxy", False),
            toggle_parm("show_skeleton", "Show Skeleton", True),
        ],
    )
    group.append(folder)
    geo.setParmTemplateGroup(group)


def wrangle(parent: hou.Node, name: str, code: str, input_node: hou.Node | None = None,
            run_over: int = 0) -> hou.Node:
    node = parent.createNode("attribwrangle", name)
    if input_node is not None:
        node.setInput(0, input_node)
    node.parm("class").set(run_over)
    node.parm("snippet").set(code)
    return node


REST_SKELETON_VEX = r'''
// KineFX-compatible points and parent-child polylines.  The name and transform
// attributes make this usable by downstream KineFX tools; the polylines make
// the hierarchy readable without a special viewer state.
string names[] = array(
    "root", "pelvis", "spine_01", "chest", "neck_01", "neck_02", "head", "beak",
    "tail_01", "tail_02", "tail_03",
    "clavicle_L", "shoulder_L", "elbow_L", "wrist_L", "wingtip_L",
    "clavicle_R", "shoulder_R", "elbow_R", "wrist_R", "wingtip_R",
    "hip_L", "knee_L", "ankle_L", "foot_L", "toe_L", "toe_inner_L", "toe_outer_L", "toe_hallux_L",
    "hip_R", "knee_R", "ankle_R", "foot_R", "toe_R", "toe_inner_R", "toe_outer_R", "toe_hallux_R"
);

vector pos[] = array(
    {10.15,0.18,0}, {10.10,0.28,0}, {10.12,0.55,0}, {10.05,0.82,0},
    {10.22,1.14,0}, {10.43,1.46,0}, {10.68,1.70,0}, {11.12,1.68,0},
    {9.82,-0.05,0}, {9.34,-0.38,0}, {8.76,-0.66,0},
    {9.83,0.75,0.15}, {9.49,0.5725,0.28}, {7.80,0.70,0.28}, {6.25,0.54,0.24}, {4.10,0.18,0.18},
    {9.83,0.75,-0.15}, {9.49,0.5725,-0.28}, {7.80,0.70,-0.28}, {6.25,0.54,-0.24}, {4.10,0.18,-0.18},
    {10.04,0.18,0.24}, {9.98,-0.25,0.28}, {10.06,-0.66,0.29}, {10.25,-0.82,0.30},
    {10.62,-0.84,0.30}, {10.55,-0.84,0.18}, {10.54,-0.84,0.43}, {10.00,-0.84,0.32},
    {10.04,0.18,-0.24}, {9.98,-0.25,-0.28}, {10.06,-0.66,-0.29}, {10.25,-0.82,-0.30},
    {10.62,-0.84,-0.30}, {10.55,-0.84,-0.18}, {10.54,-0.84,-0.43}, {10.00,-0.84,-0.32}
);

int parent[] = array(
    -1, 0, 1, 2, 3, 4, 5, 6,
    1, 8, 9,
    3, 11, 12, 13, 14,
    3, 16, 17, 18, 19,
    1, 21, 22, 23, 24, 24, 24, 24,
    1, 29, 30, 31, 32, 32, 32, 32
);

matrix3 ident3 = ident();
matrix ident4 = ident();
int pts[];
foreach (int i; string nm; names) {
    int p = addpoint(0, pos[i]);
    setpointattrib(0, "name", p, nm, "set");
    setpointattrib(0, "transform", p, ident3, "set");
    setpointattrib(0, "localtransform", p, ident4, "set");
    setpointattrib(0, "joint_id", p, i, "set");
    setpointattrib(0, "Cd", p, {1.0,0.45,0.08}, "set");
    append(pts, p);
}
foreach (int i; int par; parent) {
    if (par < 0) continue;
    int pr = addprim(0, "polyline");
    addvertex(0, pr, pts[par]);
    addvertex(0, pr, pts[i]);
    setprimattrib(0, "bone_name", pr, names[i], "set");
}
'''


POSE_SKELETON_VEX = r'''
function vector4 eulerq(vector degrees) {
    vector r = radians(degrees);
    return qmultiply(quaternion(r.z, {0,0,1}),
                     qmultiply(quaternion(r.y, {0,1,0}), quaternion(r.x, {1,0,0})));
}

float flap = ch("../flap_angle");
if (chi("../auto_flap"))
    flap += ch("../flap_amplitude") * sin(2*PI*@Time/max(ch("../flap_period"), 0.01));
float sweep = ch("../shoulder_sweep");
float elbow = ch("../elbow_fold");
float wrist = ch("../wrist_curl");
float twist = ch("../wing_twist");

vector S = {9.49,0.5725,0};
vector E = {7.80,0.70,0};
vector W = {6.25,0.54,0};
string nm = s@name;
int side = endswith(nm, "_R") ? -1 : 1;

if (find(nm, "shoulder_") >= 0 || find(nm, "elbow_") >= 0 ||
    find(nm, "wrist_") >= 0 || find(nm, "wingtip_") >= 0) {
    vector p = @P; p.z = 0;
    // Houdini is Y-up: shoulder sweep around Y opens the wings outward in Z.
    vector4 qs = qmultiply(quaternion(radians(sweep), {0,1,0}),
                           quaternion(radians(flap), {1,0,0}));
    vector4 qe = quaternion(radians(elbow), {0,0,1});
    vector4 qw = qmultiply(quaternion(radians(wrist), {0,0,1}),
                           quaternion(radians(twist), {-1,0,0}));
    vector pe = S + qrotate(qs, E-S);
    vector pw = pe + qrotate(qs, qrotate(qe, W-E));
    if (find(nm, "shoulder_") >= 0) p = S;
    else if (find(nm, "elbow_") >= 0) p = pe;
    else if (find(nm, "wrist_") >= 0) p = pw;
    else p = pw + qrotate(qs, qrotate(qe, qrotate(qw, p-W)));
    p.z *= side;
    p.z += side * 0.28;
    @P = p;
}

// Independent foot targets with a lightweight two-bone leg solve.  Moving a
// foot target bends the knee while preserving the upper/lower leg lengths.
if (find(nm, "knee_") >= 0 || find(nm, "ankle_") >= 0 ||
    find(nm, "foot_") >= 0 || find(nm, "toe_") >= 0) {
    int right = endswith(nm, "_R");
    float zsign = right ? -1.0 : 1.0;
    vector H = set(10.04, 0.18, 0.24*zsign);
    vector K = set(9.98, -0.25, 0.28*zsign);
    vector A = set(10.06, -0.66, 0.29*zsign);
    vector F = set(10.25, -0.82, 0.30*zsign);
    vector T = set(10.62, -0.84, 0.30*zsign);
    if (find(nm, "toe_inner_") >= 0) T = set(10.55, -0.84, 0.18*zsign);
    else if (find(nm, "toe_outer_") >= 0) T = set(10.54, -0.84, 0.43*zsign);
    else if (find(nm, "toe_hallux_") >= 0) T = set(10.00, -0.84, 0.32*zsign);
    vector offset = right ? chv("../foot_r_t") : chv("../foot_l_t");
    vector rotation = right ? chv("../foot_r_r") : chv("../foot_l_r");
    float toe_curl = right ? ch("../toe_r_curl") : ch("../toe_l_curl");
    float toe_spread = right ? ch("../toe_r_spread") : ch("../toe_l_spread");
    float hallux_curl = right ? ch("../hallux_r_curl") : ch("../hallux_l_curl");
    vector target = A + offset;
    float upper = length(K-H);
    float lower = length(A-K);
    vector delta = target-H;
    float rawdist = max(length(delta), 1e-4);
    float reach = clamp(rawdist, abs(upper-lower)+1e-4, upper+lower-1e-4);
    vector direction = normalize(delta);
    target = H + direction*reach;
    float along = (upper*upper - lower*lower + reach*reach)/(2*reach);
    float bend_height = sqrt(max(upper*upper - along*along, 0));
    // Project the rest knee away from the current hip-target line.  This acts
    // as a stable pole vector and reproduces the authored neutral pose at zero.
    vector line_point = H + direction*dot(K-H, direction);
    vector bend_dir = normalize(K-line_point);
    vector solved_knee = H + direction*along + bend_dir*bend_height;
    vector4 foot_q = eulerq(rotation);
    float spread = 0;
    if (find(nm, "toe_inner_") >= 0) spread = toe_spread*zsign;
    else if (find(nm, "toe_outer_") >= 0) spread = -toe_spread*zsign;
    float digit_curl = find(nm, "toe_hallux_") >= 0 ? hallux_curl : toe_curl;
    vector4 toe_q = qmultiply(foot_q,
        qmultiply(quaternion(radians(spread), {0,1,0}),
                  quaternion(radians(digit_curl), {0,0,1})));
    if (find(nm, "knee_") >= 0) @P = solved_knee;
    else if (find(nm, "ankle_") >= 0) @P = target;
    else if (find(nm, "foot_") >= 0) @P = target + qrotate(foot_q, F-A);
    else @P = target + qrotate(toe_q, T-A);
}

// Simple body posing keeps the proxy rig useful for blocking animation.
vector rootp = {10.15,0.18,0};
if (nm != "root")
    @P = rootp + qrotate(quaternion(radians(ch("../body_pitch")), {0,0,1}), @P-rootp);
if (find(nm, "neck_") >= 0 || nm == "head" || nm == "beak") {
    vector nbase = {10.05,0.82,0};
    @P = nbase + qrotate(quaternion(radians(ch("../neck_pitch")), {0,0,1}), @P-nbase);
}
if (nm == "head" || nm == "beak") {
    vector hbase = {10.68,1.70,0};
    @P = hbase + qrotate(quaternion(radians(ch("../head_pitch")), {0,0,1}), @P-hbase);
}

// Animator-facing center control: translate and rotate the complete character
// pose as one unit after all local body, wing, neck, and foot posing.
vector center = {10.15,0.18,0};
@P = center + qrotate(eulerq(chv("../body_center_r")), @P-center) + chv("../body_center_t");

// World-pin space switch for planted feet. The hip continues to follow the
// body, the foot target stays in rig space, and the knee resolves between them.
int leg_joint = find(nm, "hip_") >= 0 || find(nm, "knee_") >= 0 ||
                find(nm, "ankle_") >= 0 || find(nm, "foot_") >= 0 ||
                find(nm, "toe_") >= 0;
if (leg_joint) {
    int right = endswith(nm, "_R");
    float pin = clamp(right ? ch("../leg_pin_r") : ch("../leg_pin_l"), 0, 1);
    if (pin > 0) {
        float zsign = right ? -1.0 : 1.0;
        vector H = set(10.04, 0.18, 0.24*zsign);
        vector K = set(9.98, -0.25, 0.28*zsign);
        vector A = set(10.06, -0.66, 0.29*zsign);
        vector F = set(10.25, -0.82, 0.30*zsign);
        vector T = set(10.62, -0.84, 0.30*zsign);
        if (find(nm, "toe_inner_") >= 0) T = set(10.55, -0.84, 0.18*zsign);
        else if (find(nm, "toe_outer_") >= 0) T = set(10.54, -0.84, 0.43*zsign);
        else if (find(nm, "toe_hallux_") >= 0) T = set(10.00, -0.84, 0.32*zsign);

        vector offset = right ? chv("../foot_r_t") : chv("../foot_l_t");
        vector rotation = right ? chv("../foot_r_r") : chv("../foot_l_r");
        float toe_curl = right ? ch("../toe_r_curl") : ch("../toe_l_curl");
        float toe_spread = right ? ch("../toe_r_spread") : ch("../toe_l_spread");
        float hallux_curl = right ? ch("../hallux_r_curl") : ch("../hallux_l_curl");

        vector4 body_q = qmultiply(eulerq(chv("../body_center_r")),
                                   quaternion(radians(ch("../body_pitch")), {0,0,1}));
        vector center_t = chv("../body_center_t");
        vector hip_follow = center + qrotate(body_q, H-center) + center_t;
        vector knee_follow = center + qrotate(body_q, K-center) + center_t;
        vector target = A + offset;

        float upper = length(K-H);
        float lower = length(A-K);
        vector delta = target-hip_follow;
        float rawdist = max(length(delta), 1e-4);
        vector direction = normalize(delta);
        float reach = clamp(rawdist, abs(upper-lower)+1e-4, upper+lower-1e-4);
        float along = (upper*upper - lower*lower + reach*reach)/(2*reach);
        float bend_height = sqrt(max(upper*upper - along*along, 0));
        vector line_point = hip_follow + direction*dot(knee_follow-hip_follow, direction);
        vector bend_dir = normalize(knee_follow-line_point);
        if (length2(bend_dir) < 1e-6) bend_dir = set(0, 0, zsign);
        vector pinned_knee = hip_follow + direction*along + bend_dir*bend_height;

        vector4 foot_q = eulerq(rotation);
        float spread = 0;
        if (find(nm, "toe_inner_") >= 0) spread = toe_spread*zsign;
        else if (find(nm, "toe_outer_") >= 0) spread = -toe_spread*zsign;
        float digit_curl = find(nm, "toe_hallux_") >= 0 ? hallux_curl : toe_curl;
        vector4 toe_q = qmultiply(foot_q,
            qmultiply(quaternion(radians(spread), {0,1,0}),
                      quaternion(radians(digit_curl), {0,0,1})));

        vector pinned = @P;
        if (find(nm, "hip_") >= 0) pinned = hip_follow;
        else if (find(nm, "knee_") >= 0) pinned = pinned_knee;
        else if (find(nm, "ankle_") >= 0) pinned = target;
        else if (find(nm, "foot_") >= 0) pinned = target + qrotate(foot_q, F-A);
        else pinned = target + qrotate(toe_q, T-A);
        @P = lerp(@P, pinned, pin);
    }
}
'''


WING_DEFORM_VEX = r'''
vector S = {9.49,0.5725,0};
vector E = {7.80,0.70,0};
vector W = {6.25,0.54,0};
float flap = ch("../flap_angle");
if (chi("../auto_flap"))
    flap += ch("../flap_amplitude") * sin(2*PI*@Time/max(ch("../flap_period"), 0.01));
// Houdini is Y-up: shoulder sweep around Y opens the wings outward in Z.
vector4 qs = qmultiply(quaternion(radians(ch("../shoulder_sweep")), {0,1,0}),
                       quaternion(radians(flap), {1,0,0}));
vector4 qe = quaternion(radians(ch("../elbow_fold")), {0,0,1});
vector4 qw = qmultiply(quaternion(radians(ch("../wrist_curl")), {0,0,1}),
                       quaternion(radians(ch("../wing_twist")), {-1,0,0}));

// Span coordinate follows the existing wing from the shoulder toward -X.
float u = max(S.x - @P.x, 0.0);
vector pe = S + qrotate(qs, E-S);
vector pw = pe + qrotate(qs, qrotate(qe, W-E));
vector posed;
if (u < length(E-S))
    posed = S + qrotate(qs, @P-S);
else if (u < length(E-S) + length(W-E))
    posed = pe + qrotate(qs, qrotate(qe, @P-E));
else
    posed = pw + qrotate(qs, qrotate(qe, qrotate(qw, @P-W)));

// Preserve the organic feather motion and add a soft extra tip response.
float flex = smooth(0.35, 1.0, clamp(u/5.5, 0, 1)) * ch("../feather_flex");
posed.z += sin(4.0*clamp(u/5.5,0,1) - 2*PI*@Time) * flex;
vector rootp = {10.15,0.18,0};
@P = rootp + qrotate(quaternion(radians(ch("../body_pitch")), {0,0,1}), posed-rootp);
'''


WING_BOUNDARY_REST_VEX = r'''
// Low-resolution static wing surface for silhouette, blocking, and downstream
// proxy use. Five chord rows give the shoulder/elbow/wrist weight blends enough
// resolution to bend cleanly without adding viewport cost.
float xs[]    = array(9.49, 8.85, 8.10, 7.35, 6.60, 5.80, 5.00, 4.25);
float lower[] = array(0.20,-0.15,-0.45,-0.78,-1.05,-1.32,-1.52,-1.68);
float upper[] = array(0.82, 1.18, 1.48, 1.63, 1.55, 1.30, 0.92, 0.42);
int rows = 5;
int ids[];
for (int i = 0; i < len(xs); i++) {
    for (int row = 0; row < rows; row++) {
        float v = float(row) / float(rows-1);
        vector p = set(xs[i], lerp(lower[i], upper[i], v), 0);
        int pt = addpoint(0, p);
        setpointattrib(0, "uv", pt, set(float(i)/float(len(xs)-1), v, 0), "set");
        setpointattrib(0, "Cd", pt, {0.75,0.17,0.025}, "set");
        setpointattrib(0, "Alpha", pt, 0.28, "set");
        setpointattrib(0, "N", pt, {0,0,1}, "set");
        setpointattrib(0, "name", pt, "wing_boundary", "set");
        append(ids, pt);
    }
}
for (int i = 0; i < len(xs)-1; i++) {
    for (int row = 0; row < rows-1; row++) {
        int pr = addprim(0, "poly");
        addvertex(0, pr, ids[i*rows+row]);
        addvertex(0, pr, ids[(i+1)*rows+row]);
        addvertex(0, pr, ids[(i+1)*rows+row+1]);
        addvertex(0, pr, ids[i*rows+row+1]);
        setprimattrib(0, "name", pr, "wing_boundary", "set");
        setprimgroup(0, "wing_boundary", pr, 1, "set");
    }
}
'''


WING_BOUNDARY_DEFORM_VEX = r'''
vector S = {9.49,0.5725,0};
vector E = {7.80,0.70,0};
vector W = {6.25,0.54,0};
float flap = ch("../flap_angle");
if (chi("../auto_flap"))
    flap += ch("../flap_amplitude") * sin(2*PI*@Time/max(ch("../flap_period"), 0.01));
vector4 qs = qmultiply(quaternion(radians(ch("../shoulder_sweep")), {0,1,0}),
                       quaternion(radians(flap), {1,0,0}));
vector4 qe = quaternion(radians(ch("../elbow_fold")), {0,0,1});
vector4 qw = qmultiply(quaternion(radians(ch("../wrist_curl")), {0,0,1}),
                       quaternion(radians(ch("../wing_twist")), {-1,0,0}));

float u = max(S.x - @P.x, 0.0);
float elbow_u = length(E-S);
float wrist_u = elbow_u + length(W-E);
float blend_width = 0.38;

// Explicit, inspectable skin weights. They sum to one at every point.
f@wing_weight_shoulder = 1.0 - smooth(elbow_u-blend_width, elbow_u+blend_width, u);
f@wing_weight_wrist = smooth(wrist_u-blend_width, wrist_u+blend_width, u);
f@wing_weight_elbow = max(1.0 - f@wing_weight_shoulder - f@wing_weight_wrist, 0.0);
float total = max(f@wing_weight_shoulder + f@wing_weight_elbow + f@wing_weight_wrist, 1e-6);
f@wing_weight_shoulder /= total;
f@wing_weight_elbow /= total;
f@wing_weight_wrist /= total;

vector shoulder_p = S + qrotate(qs, @P-S);
vector pe = S + qrotate(qs, E-S);
vector elbow_p = pe + qrotate(qs, qrotate(qe, @P-E));
vector pw = pe + qrotate(qs, qrotate(qe, W-E));
vector wrist_p = pw + qrotate(qs, qrotate(qe, qrotate(qw, @P-W)));
vector posed = shoulder_p*f@wing_weight_shoulder +
               elbow_p*f@wing_weight_elbow + wrist_p*f@wing_weight_wrist;

vector rootp = {10.15,0.18,0};
@P = rootp + qrotate(quaternion(radians(ch("../body_pitch")), {0,0,1}), posed-rootp);
'''


BODY_POSE_VEX = r'''
function vector4 eulerq(vector degrees) {
    vector r = radians(degrees);
    return qmultiply(quaternion(r.z, {0,0,1}),
                     qmultiply(quaternion(r.y, {0,1,0}), quaternion(r.x, {1,0,0})));
}
vector rootp = {10.15,0.18,0};
@P = rootp + qrotate(quaternion(radians(ch("../body_pitch")), {0,0,1}), @P-rootp);
if (@P.y > 0.78) {
    vector nbase = {10.05,0.82,0};
    @P = nbase + qrotate(quaternion(radians(ch("../neck_pitch")), {0,0,1}), @P-nbase);
}
if (@P.y > 1.42) {
    vector hbase = {10.68,1.70,0};
    @P = hbase + qrotate(quaternion(radians(ch("../head_pitch")), {0,0,1}), @P-hbase);
}
@P = rootp + qrotate(eulerq(chv("../body_center_r")), @P-rootp) + chv("../body_center_t");
'''


CENTER_TRANSFORM_VEX = r'''
function vector4 eulerq(vector degrees) {
    vector r = radians(degrees);
    return qmultiply(quaternion(r.z, {0,0,1}),
                     qmultiply(quaternion(r.y, {0,1,0}), quaternion(r.x, {1,0,0})));
}
vector center = {10.15,0.18,0};
@P = center + qrotate(eulerq(chv("../body_center_r")), @P-center) + chv("../body_center_t");
'''


BODY_PROXY_VEX = r'''
// Low-resolution ellipsoids form a neutral body volume for rig blocking.
function void ellipsoid(vector c; vector r; int rows; int cols; vector col; string part) {
    int ids[];
    for (int y=0; y<=rows; y++) {
        float v = float(y)/rows;
        float phi = -PI/2 + v*PI;
        for (int x=0; x<cols; x++) {
            float u = float(x)/cols;
            float th = u*2*PI;
            vector p = c + set(cos(phi)*cos(th)*r.x, sin(phi)*r.y, cos(phi)*sin(th)*r.z);
            int pt = addpoint(0,p);
            setpointattrib(0,"Cd",pt,col,"set");
            append(ids,pt);
        }
    }
    for (int y=0; y<rows; y++) for (int x=0; x<cols; x++) {
        int nx=(x+1)%cols;
        int pr=addprim(0,"poly");
        addvertex(0,pr,ids[y*cols+x]); addvertex(0,pr,ids[y*cols+nx]);
        addvertex(0,pr,ids[(y+1)*cols+nx]); addvertex(0,pr,ids[(y+1)*cols+x]);
        setprimattrib(0,"body_part",pr,part,"set");
    }
}
ellipsoid({10.08,0.48,0}, {0.70,0.78,0.48}, 12, 20, {0.20,0.07,0.035}, "torso");
ellipsoid({10.35,1.18,0}, {0.38,0.62,0.32}, 10, 16, {0.28,0.08,0.025}, "neck");
ellipsoid({10.70,1.69,0}, {0.34,0.30,0.30}, 10, 16, {0.48,0.12,0.025}, "head");
ellipsoid({10.98,1.67,0}, {0.38,0.10,0.15}, 6, 12, {0.80,0.36,0.04}, "beak");
ellipsoid({9.60,-0.13,0}, {0.74,0.25,0.35}, 8, 16, {0.30,0.07,0.025}, "tail_base");
'''


def build_wing_boundary_network(geo: hou.Node, empty: hou.Node) -> tuple[hou.Node, hou.Node]:
    """Create the weighted static wing proxy and return (viewport switch, output)."""
    boundary_rest = wrangle(
        geo, "WING_BOUNDARY_REST", WING_BOUNDARY_REST_VEX, empty, run_over=0)
    boundary_rest.setComment(
        "Static low-resolution wing silhouette with UVs and inspectable influence weights")
    boundary_extrude = geo.createNode("polyextrude::2.0", "WING_BOUNDARY_EXTRUDE")
    boundary_extrude.setInput(0, boundary_rest)
    boundary_extrude.parm("dist").setExpression('ch("../wing_boundary_thickness")')
    boundary_extrude.parm("outputfront").set(1)
    boundary_extrude.parm("outputback").set(1)
    boundary_extrude.parm("outputside").set(1)
    boundary_extrude.setComment("Adds closed solid thickness to the static wing surface")

    boundary_center_thickness = geo.createNode("xform", "WING_BOUNDARY_CENTER_THICKNESS")
    boundary_center_thickness.setInput(0, boundary_extrude)
    boundary_center_thickness.parm("tz").setExpression(
        '-ch("../wing_boundary_thickness")/2')

    boundary_bevel = geo.createNode("polybevel::3.0", "WING_BOUNDARY_BEVEL")
    boundary_bevel.setInput(0, boundary_center_thickness)
    boundary_bevel.parm("grouptype").set(3)
    boundary_bevel.parm("offset").setExpression('ch("../wing_boundary_bevel_radius")')
    boundary_bevel.parm("divisions").set(3)
    boundary_bevel.parm("ignoreflatedges").set(1)
    boundary_bevel.parm("ignoreinlinepoints").set(1)
    boundary_bevel.setComment("Rounds the solid wing outline and thickness edges")

    boundary_deform = wrangle(
        geo, "WING_BOUNDARY_SKIN", WING_BOUNDARY_DEFORM_VEX, boundary_bevel, run_over=2)
    boundary_deform.setComment(
        "Smooth shoulder/elbow/wrist weighted deformation matching the wing rig controls")

    boundary_normals = geo.createNode("normal", "WING_BOUNDARY_NORMALS")
    boundary_normals.setInput(0, boundary_deform)

    boundary_left = geo.createNode("xform", "LEFT_WING_BOUNDARY_OFFSET")
    boundary_left.setInput(0, boundary_normals)
    boundary_left.parm("tz").set(0.28)
    boundary_right = geo.createNode("xform", "RIGHT_WING_BOUNDARY_MIRROR")
    boundary_right.setInput(0, boundary_deform)
    boundary_right.parm("sz").set(-1.0)
    boundary_right.parm("tz").set(-0.28)
    boundary_merge = geo.createNode("merge", "MERGE_WING_BOUNDARIES")
    boundary_merge.setInput(0, boundary_left)
    boundary_merge.setInput(1, boundary_right)

    boundary_offset = geo.createNode("xform", "WING_BOUNDARY_POSITION_OFFSET")
    boundary_offset.setInput(0, boundary_merge)
    for axis in "xyz":
        boundary_offset.parm("t" + axis).setExpression(
            f'ch("../wing_boundary_offset{axis}")', language=hou.exprLanguage.Hscript)
    boundary_offset.setComment(
        "Animator-facing local position offset shared by both wing boundary meshes")

    boundary_center = wrangle(
        geo, "BODY_CENTER_WING_BOUNDARY", CENTER_TRANSFORM_VEX, boundary_offset, run_over=2)
    boundary_out = geo.createNode("null", "OUT_WING_BOUNDARY")
    boundary_out.setInput(0, boundary_center)

    boundary_switch = geo.createNode("switch", "SHOW_WING_BOUNDARY")
    boundary_switch.setInput(0, empty)
    boundary_switch.setInput(1, boundary_out)
    boundary_switch.parm("input").setExpression('ch("../show_wing_boundary")')
    return boundary_switch, boundary_out


def build_character() -> hou.Node:
    obj = hou.node("/obj")
    old = obj.node("phoenix_character_rig")
    if old is not None:
        old.destroy()

    geo = obj.createNode("geo", "phoenix_character_rig")
    for child in geo.children():
        child.destroy()
    add_controls(geo)
    geo.setColor(hou.Color(0.72, 0.20, 0.06))
    geo.setComment("Phoenix body proxy + KineFX-style skeleton + articulated copies of the existing procedural wing")

    empty = geo.createNode("null", "EMPTY")
    rest = wrangle(geo, "REST_SKELETON", REST_SKELETON_VEX, empty, run_over=0)
    rest.setComment("Named rest joints and parent-child topology for KineFX workflows")
    pose = wrangle(geo, "POSE_SKELETON", POSE_SKELETON_VEX, rest, run_over=2)
    pose.setComment("Body and wing pose driven by Phoenix Rig Controls on the object")

    wire = geo.createNode("polywire", "SKELETON_BONES")
    wire.setInput(0, pose)
    if wire.parm("radius"):
        wire.parm("radius").set(0.025)
    skeleton_out = geo.createNode("null", "OUT_SKELETON")
    skeleton_out.setInput(0, wire)

    body = wrangle(geo, "BODY_PROXY", BODY_PROXY_VEX, empty, run_over=0)
    body.setComment("Lightweight proportion mesh; replace with final modeled body when available")
    body_pose = wrangle(geo, "BODY_PROXY_POSE", BODY_POSE_VEX, body, run_over=2)
    body_switch = geo.createNode("switch", "SHOW_BODY_PROXY")
    body_switch.setInput(0, empty)
    body_switch.setInput(1, body_pose)
    body_switch.parm("input").setExpression('ch("../show_body_proxy")')
    body_out = geo.createNode("null", "OUT_BODY_PROXY")
    body_out.setInput(0, body_switch)

    wing_import = geo.createNode("object_merge", "SOURCE_FEATHER_WING")
    wing_import.parm("objpath1").set("/obj/feather_flow_guides/OUT_FEATHER_SHAPES")
    if wing_import.parm("xformtype"):
        wing_import.parm("xformtype").set(0)
    wing_import.setComment("Live link to the existing procedural Phoenix feather wing in source-local space")

    wing_source_xform = geo.createNode("xform", "SOURCE_WING_TO_CHARACTER_SPACE")
    wing_source_xform.setInput(0, wing_import)
    for axis in "xyz":
        wing_source_xform.parm("t" + axis).setExpression(
            f'ch("/obj/feather_flow_guides/t{axis}")', language=hou.exprLanguage.Hscript)
        wing_source_xform.parm("r" + axis).setExpression(
            f'ch("/obj/feather_flow_guides/r{axis}")', language=hou.exprLanguage.Hscript)
        wing_source_xform.parm("s" + axis).setExpression(
            f'ch("/obj/feather_flow_guides/s{axis}")', language=hou.exprLanguage.Hscript)
    wing_source_xform.setComment(
        "Rebuild the source object transform in character-local space so object transforms carry the wing")

    root_sources = []
    source_geo = hou.node("/obj/feather_flow_guides")
    if source_geo is not None:
        for layer in source_geo.children():
            roots = layer.node("OUT_ROOTS")
            if roots is None:
                continue
            root_import = geo.createNode("object_merge", f"SOURCE_ROOTS_{layer.name().upper()}")
            root_import.parm("objpath1").set(roots.path())
            if root_import.parm("xformtype"):
                root_import.parm("xformtype").set(0)
            root_xform = geo.createNode("xform", f"{root_import.name()}_TO_CHARACTER_SPACE")
            root_xform.setInput(0, root_import)
            for axis in "xyz":
                root_xform.parm("t" + axis).setExpression(
                    f'ch("/obj/feather_flow_guides/t{axis}")', language=hou.exprLanguage.Hscript)
                root_xform.parm("r" + axis).setExpression(
                    f'ch("/obj/feather_flow_guides/r{axis}")', language=hou.exprLanguage.Hscript)
                root_xform.parm("s" + axis).setExpression(
                    f'ch("/obj/feather_flow_guides/s{axis}")', language=hou.exprLanguage.Hscript)
            root_sources.append(root_xform)

    roots_merge = geo.createNode("merge", "MERGE_SOURCE_ROOTS")
    for index, root_source in enumerate(root_sources):
        roots_merge.setInput(index, root_source)
    roots_merge.setComment("Lightweight feather-root points for fast rig previews")

    preview_switch = geo.createNode("switch", "FEATHERS_OR_ROOTS")
    preview_switch.setInput(0, wing_source_xform)
    preview_switch.setInput(1, roots_merge)
    preview_switch.parm("input").setExpression('ch("../roots_only_preview")')
    preview_switch.setComment("0 = full feathers, 1 = lightweight roots-only preview")

    wing_deform = wrangle(geo, "WING_SKELETAL_DEFORM", WING_DEFORM_VEX, preview_switch, run_over=2)

    left = geo.createNode("xform", "LEFT_WING_OFFSET")
    left.setInput(0, wing_deform)
    left.parm("tz").set(0.28)
    right = geo.createNode("xform", "RIGHT_WING_MIRROR")
    right.setInput(0, wing_deform)
    right.parm("sz").set(-1.0)
    right.parm("tz").set(-0.28)
    wings = geo.createNode("merge", "MERGE_WINGS")
    wings.setInput(0, left)
    wings.setInput(1, right)
    centered_wings = wrangle(geo, "BODY_CENTER_WINGS", CENTER_TRANSFORM_VEX, wings, run_over=2)
    wings_out = geo.createNode("null", "OUT_RIGGED_WINGS")
    wings_out.setInput(0, centered_wings)

    boundary_switch, boundary_out = build_wing_boundary_network(geo, empty)

    skeleton_switch = geo.createNode("switch", "SHOW_SKELETON")
    skeleton_switch.setInput(0, empty)
    skeleton_switch.setInput(1, skeleton_out)
    skeleton_switch.parm("input").setExpression('ch("../show_skeleton")')

    final = geo.createNode("merge", "MERGE_CHARACTER")
    final.setInput(0, body_out)
    final.setInput(1, wings_out)
    final.setInput(2, skeleton_switch)
    final.setInput(3, boundary_switch)
    out = geo.createNode("null", "OUT_PHOENIX_CHARACTER")
    out.setInput(0, final)
    out.setDisplayFlag(True)
    out.setRenderFlag(True)

    for node in geo.children():
        node.moveToGoodPosition()
    geo.layoutChildren()
    return geo


def configure_wind_physics(character: hou.Node) -> None:
    """Expose a keyframeable 0..1 multiplier for the source wing's wind deformation."""
    controls = hou.node("/obj/feather_flow_guides/WING_CONTROLS")
    wind = hou.node("/obj/feather_flow_guides/wing_wind")
    if controls is None or wind is None:
        return

    if controls.parm("physics_strength") is None:
        group = controls.parmTemplateGroup()
        group.append(float_parm("physics_strength", "Physics Strength", 1.0, 0.0, 1.0))
        controls.setParmTemplateGroup(group)

    controls.parm("physics_strength").setExpression(
        f'ch("{character.path()}/wind_physics_strength")',
        language=hou.exprLanguage.Hscript,
    )

    snippet = wind.parm("snippet").eval()
    old_displacement = '@P += (sway + v@fside * flutter) * f@flen * f@fshade * f@fshade;'
    new_displacement = (
        'float physics_strength = clamp(chf(ctl + "physics_strength"), 0, 1);\n'
        '@P += (sway + v@fside * flutter) * f@flen * f@fshade * f@fshade * physics_strength;'
    )
    if old_displacement in snippet:
        snippet = snippet.replace(old_displacement, new_displacement)
    snippet = snippet.replace(
        'f@wind = length(across);',
        'f@wind = length(across) * physics_strength;',
    )
    wind.parm("snippet").set(snippet)
    wind.setComment("Wind deformation scaled by the animatable Wind Physics Strength control")


def main() -> None:
    source = latest_source()
    hou.hipFile.load(source, suppress_save_prompt=True)
    character = build_character()

    # The older VEX flap remains useful in the source scene, but the character
    # rig owns the gross wing motion in this derivative scene.
    old_controls = hou.node("/obj/feather_flow_guides/WING_CONTROLS")
    if old_controls is not None and old_controls.parm("flap_amp") is not None:
        old_controls.parm("flap_amp").set(0.0)

    configure_wind_physics(character)

    # The character rig owns growth timing.  A value of 1 produces the fully
    # grown/rest wing at every frame; animators can keyframe 0..1 when needed.
    growth = hou.node("/obj/feather_flow_guides/oil_growth")
    if growth is not None and growth.parm("progress") is not None:
        growth.parm("progress").deleteAllKeyframes()
        growth.parm("progress").setExpression(
            'ch("/obj/phoenix_character_rig/feather_growth")',
            language=hou.exprLanguage.Hscript,
        )

    hou.playbar.setFrameRange(1, 240)
    hou.setFrame(1)
    hou.hipFile.save(OUTPUT)
    print("Built:", character.path())
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
