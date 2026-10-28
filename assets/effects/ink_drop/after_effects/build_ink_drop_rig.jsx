/*
 * Whirling Worlds - Procedural 2.5D Persian Ink Drop for After Effects 2026.
 * Rerunnable: replaces only project items inside INK_DROP_AE_RIG.
 */
(function buildInkDropRig() {
    app.beginUndoGroup("Build Persian Ink Drop Rig");

    var OUT_DIR = new Folder("E:/Wirling Worlds/Simorgh/assets/effects/ink_drop/after_effects");
    var TEX_FILE = new File(OUT_DIR.fsName + "/textures/persian_pattern.png");
    var PROJECT_FILE = new File(OUT_DIR.fsName + "/persian_ink_drop.aep");
    var FPS = 24;
    var DURATION = 2.0;
    var W = 1920, H = 1080;
    var ROOT_NAME = "INK_DROP_AE_RIG";

    if (!OUT_DIR.exists) OUT_DIR.create();
    if (!TEX_FILE.exists) {
        alert("Missing Persian texture: " + TEX_FILE.fsName);
        app.endUndoGroup();
        return;
    }

    var project = app.project || app.newProject();

    function removeOwnedItems() {
        for (var i = project.numItems; i >= 1; i--) {
            var it = project.item(i);
            if (it.name === ROOT_NAME || it.comment === "INK_DROP_BUILDER_V1") {
                try { it.remove(); } catch (ignore) {}
            }
        }
    }

    function folder(name, parent) {
        var f = project.items.addFolder(name);
        f.parentFolder = parent;
        f.comment = "INK_DROP_BUILDER_V1";
        return f;
    }

    function tag(item) { item.comment = "INK_DROP_BUILDER_V1"; return item; }

    function effect(layer, matchName, displayName) {
        try {
            var e = layer.property("ADBE Effect Parade").addProperty(matchName);
            if (displayName) e.name = displayName;
            return e;
        } catch (ignore) { return null; }
    }

    function prop(group, names) {
        if (!group) return null;
        for (var i = 0; i < names.length; i++) {
            try {
                var p = group.property(names[i]);
                if (p) return p;
            } catch (ignore) {}
        }
        return null;
    }

    function setValue(p, v) {
        if (!p) return;
        try { p.setValue(v); } catch (ignore) {}
    }

    function setKeys(p, keys) {
        if (!p) return;
        for (var i = 0; i < keys.length; i++) {
            try { p.setValueAtTime(keys[i][0], keys[i][1]); } catch (ignoreValue) {}
        }
        for (var k = 1; k <= p.numKeys; k++) {
            try {
                p.setInterpolationTypeAtKey(k, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
                var dims = (p.value instanceof Array) ? p.value.length : 1;
                var easeIn = [], easeOut = [];
                for (var d = 0; d < dims; d++) {
                    easeIn.push(new KeyframeEase(0, 70));
                    easeOut.push(new KeyframeEase(0, 70));
                }
                p.setTemporalEaseAtKey(k, easeIn, easeOut);
            } catch (ignore) {}
        }
    }

    function slider(ctrl, name, value) {
        var e = effect(ctrl, "ADBE Slider Control", name);
        if (e) setValue(e.property(1), value);
        return e;
    }

    function checkbox(ctrl, name, value) {
        var e = effect(ctrl, "ADBE Checkbox Control", name);
        if (e) setValue(e.property(1), value ? 1 : 0);
        return e;
    }

    function color(ctrl, name, value) {
        var e = effect(ctrl, "ADBE Color Control", name);
        if (e) setValue(e.property(1), value);
        return e;
    }

    function smoothShape(vertices) {
        var s = new Shape();
        var ins = [], outs = [];
        for (var i = 0; i < vertices.length; i++) {
            var prev = vertices[(i - 1 + vertices.length) % vertices.length];
            var next = vertices[(i + 1) % vertices.length];
            ins.push([(prev[0] - next[0]) / 6, (prev[1] - next[1]) / 6]);
            outs.push([(next[0] - prev[0]) / 6, (next[1] - prev[1]) / 6]);
        }
        s.vertices = vertices;
        s.inTangents = ins;
        s.outTangents = outs;
        s.closed = true;
        return s;
    }

    // Coordinates are in the 1536x1024 source layer. Top remains narrow;
    // the body opens progressively below it. Layer offsets introduce variation.
    function silhouette(stage, layerId) {
        var j = (layerId - 2.5) * 5;
        if (stage === 0) return smoothShape([
            [768,112], [779,126], [785,151], [778,177], [768,188],
            [758,177], [751,151], [757,126]
        ]);
        if (stage === 1) return smoothShape([
            [768,104], [783,126], [796,174], [790,226], [768,265],
            [746,226], [740,174], [753,126]
        ]);
        if (stage === 2) return smoothShape([
            [768,102], [785,133], [808,222], [838+j,340], [827-j,470],
            [781,590], [734,570], [696+j,468], [701-j,340], [738,220], [751,133]
        ]);
        if (stage === 3) return smoothShape([
            [768,100], [786,137], [812,230], [890+j,315], [1010-j,402],
            [1075+j,535], [1002-j,635], [1085+j,748], [930-j,850],
            [800+j,820], [690-j,900], [570+j,810], [510-j,670],
            [555+j,530], [485-j,420], [620+j,315], [724,225], [749,137]
        ]);
        return smoothShape([
            [768,100], [786,137], [818,235], [930+j,320], [1085-j,405],
            [1125+j,550], [1030-j,665], [1160+j,790], [955-j,910],
            [812+j,850], [665-j,950], [500+j,835], [440-j,680],
            [520+j,520], [405-j,405], [600+j,300], [720,220], [748,137]
        ]);
    }

    function addMaskAnimation(layer, layerId) {
        var masks = layer.property("ADBE Mask Parade");
        var mask = masks.addProperty("ADBE Mask Atom");
        mask.name = "INK SILHOUETTE - NARROW TOP";
        mask.maskMode = MaskMode.ADD;
        var path = mask.property("ADBE Mask Shape");
        path.setValueAtTime(0 / FPS, silhouette(0, layerId));
        path.setValueAtTime(5 / FPS, silhouette(1, layerId));
        path.setValueAtTime(11 / FPS, silhouette(2, layerId));
        path.setValueAtTime(23 / FPS, silhouette(3, layerId));
        path.setValueAtTime(47 / FPS, silhouette(4, layerId));
        setValue(mask.property("ADBE Mask Feather"), [55 + layerId * 4, 55 + layerId * 4]);
        setValue(mask.property("ADBE Mask Opacity"), 100);
        setValue(mask.property("ADBE Mask Expansion"), -4 + layerId);

        // Intersect the silhouette with a soft wipe that begins at the narrow
        // upper inlet and flows downward. This makes the Persian paint itself
        // enter from the top instead of appearing across the whole body at once.
        function revealShape(bottomY) {
            var r = new Shape();
            r.vertices = [[250,70],[1286,70],[1286,bottomY],[250,bottomY]];
            r.inTangents = [[0,0],[0,0],[0,0],[0,0]];
            r.outTangents = [[0,0],[0,0],[0,0],[0,0]];
            r.closed = true;
            return r;
        }
        var reveal = masks.addProperty("ADBE Mask Atom");
        reveal.name = "TOP-DOWN PAINT FLOW";
        reveal.maskMode = MaskMode.INTERSECT;
        var revealPath = reveal.property("ADBE Mask Shape");
        var d = layerId * 0.35 / FPS;
        revealPath.setValueAtTime(0/FPS + d, revealShape(108));
        revealPath.setValueAtTime(5/FPS + d, revealShape(270));
        revealPath.setValueAtTime(11/FPS + d, revealShape(625));
        revealPath.setValueAtTime(23/FPS + d, revealShape(1010));
        revealPath.setValueAtTime(47/FPS, revealShape(1010));
        setValue(reveal.property("ADBE Mask Feather"), [18,70]);
        setValue(reveal.property("ADBE Mask Opacity"), 100);
    }

    function applyOrganicEffects(layer, id) {
        var td = effect(layer, "ADBE Turbulent Displace", "Organic Curl " + (id + 1));
        setValue(prop(td, ["Displacement", "ADBE Turbulent Displace-0001"]), 1);
        setValue(prop(td, ["Amount", "ADBE Turbulent Displace-0002"]), 24 + id * 5);
        setValue(prop(td, ["Size", "ADBE Turbulent Displace-0003"]), 92 + id * 17);
        setValue(prop(td, ["Complexity", "ADBE Turbulent Displace-0005"]), 2.2 + id * 0.15);
        var evo = prop(td, ["Evolution", "ADBE Turbulent Displace-0006"]);
        if (evo) evo.expression = "time*(55+" + id + "*13)";

        var rough = effect(layer, "ADBE Roughen Edges", "Dissolving Edge " + (id + 1));
        var border = prop(rough, ["Border"]);
        setKeys(border, [[0, 4], [24/FPS, 10 + id], [47/FPS, 85 + id * 8]]);
        setValue(prop(rough, ["Edge Sharpness"]), 0.22);
        setValue(prop(rough, ["Scale"]), 115 + id * 11);
        setValue(prop(rough, ["Fractal Influence"]), 0.75);
        var revo = prop(rough, ["Evolution"]);
        if (revo) revo.expression = "time*(90+" + id + "*9)";

        var transform = effect(layer, "ADBE Geometry2", "Independent Pattern Growth");
        var scaleH = prop(transform, ["Scale Height"]);
        var scaleW = prop(transform, ["Scale Width"]);
        setKeys(scaleH, [[0, 68 + id*2], [23/FPS, 94 + id*2], [47/FPS, 106 + id*2]]);
        setKeys(scaleW, [[0, 68 + id*2], [23/FPS, 94 + id*2], [47/FPS, 106 + id*2]]);
        var trot = prop(transform, ["Rotation"]);
        setKeys(trot, [[0, -7 + id*3], [47/FPS, 8 + id*5]]);

        var bevel = effect(layer, "ADBE Bevel Alpha", "Glass Edge Highlight");
        setValue(prop(bevel, ["Edge Thickness"]), 2.5 + id*0.3);
        setValue(prop(bevel, ["Light Intensity"]), 0.65);

        var glow = effect(layer, "ADBE Glo2", "Soft Internal Glow");
        setValue(prop(glow, ["Glow Threshold"]), 68);
        setValue(prop(glow, ["Glow Radius"]), 18 + id*2);
        setValue(prop(glow, ["Glow Intensity"]), 0.28);
    }

    function addCloudLayer(comp, footage, ctrl, id) {
        var layer = comp.layers.add(footage);
        layer.name = "INK_LAYER_" + (id + 1) + "_PERSIAN";
        layer.threeDLayer = true;
        layer.motionBlur = true;
        layer.blendingMode = (id === 0) ? BlendingMode.NORMAL : BlendingMode.SCREEN;
        layer.label = 9 + (id % 5);
        var tr = layer.property("ADBE Transform Group");
        setValue(tr.property("ADBE Anchor Point"), [768, 512, 0]);
        setValue(tr.property("ADBE Position"), [960 + (id-2.5)*7, 540 + id*3, (id-2.5)*34]);
        setValue(tr.property("ADBE Scale"), [72 + id*1.7, 72 + id*1.7, 100]);
        setValue(tr.property("ADBE Rotate Z"), -3.5 + id*1.4);
        addMaskAnimation(layer, id);
        applyOrganicEffects(layer, id);

        var opacity = tr.property("ADBE Opacity");
        var delay = id * 0.025;
        setKeys(opacity, [
            [0 + delay, 0], [2/FPS + delay, 52 + id*4], [12/FPS + delay, 44 + id*3],
            [24/FPS + delay, 36 + id*2], [35/FPS + delay, 23], [47/FPS, 0]
        ]);
        return layer;
    }

    function addBubble(comp, ctrl, id) {
        var shape = comp.layers.addShape();
        shape.name = "BUBBLE_" + (id + 1);
        shape.threeDLayer = true;
        shape.motionBlur = true;
        shape.label = 8;
        var contents = shape.property("ADBE Root Vectors Group");
        var radius = 18 + (id % 7) * 5.2;

        function spherePart(name, size, offset, fillColor, fillOpacity, strokeColor, strokeWidth, strokeOpacity) {
            var group = contents.addProperty("ADBE Vector Group");
            group.name = name;
            var gc = group.property("ADBE Vectors Group");
            var ellipse = gc.addProperty("ADBE Vector Shape - Ellipse");
            setValue(ellipse.property("ADBE Vector Ellipse Size"), [size,size]);
            var fill = gc.addProperty("ADBE Vector Graphic - Fill");
            setValue(fill.property("ADBE Vector Fill Color"), fillColor);
            setValue(fill.property("ADBE Vector Fill Opacity"), fillOpacity);
            if (strokeWidth > 0) {
                var stroke = gc.addProperty("ADBE Vector Graphic - Stroke");
                setValue(stroke.property("ADBE Vector Stroke Color"), strokeColor);
                setValue(stroke.property("ADBE Vector Stroke Width"), strokeWidth);
                setValue(stroke.property("ADBE Vector Stroke Opacity"), strokeOpacity);
            }
            setValue(group.property("ADBE Vector Transform Group").property("ADBE Vector Position"), offset);
            return group;
        }

        // Layered vector shading gives every bubble a spherical lens appearance.
        spherePart("SPHERE_BODY", radius*2, [0,0], [0.18,0.58,0.72,1], 15,
                   [0.64,0.94,1.0,1], Math.max(2.2,radius*0.095), 78);
        spherePart("SPHERE_INNER_GLOW", radius*1.48, [-radius*0.10,-radius*0.12],
                   [0.35,0.82,0.92,1], 8, [0.30,0.72,0.86,1], 1.2, 32);
        spherePart("SPHERE_SHADOW", radius*0.82, [radius*0.20,radius*0.22],
                   [0.015,0.10,0.19,1], 17, [0.03,0.20,0.28,1], 0.8, 20);
        spherePart("SPHERE_HIGHLIGHT", radius*0.38, [-radius*0.34,-radius*0.34],
                   [0.88,0.98,1.0,1], 72, [1,1,1,1], 0.7, 80);

        var bubbleGlow = effect(shape, "ADBE Glo2", "Bubble Specular Bloom");
        setValue(prop(bubbleGlow, ["Glow Threshold"]), 62);
        setValue(prop(bubbleGlow, ["Glow Radius"]), 7 + radius*0.16);
        setValue(prop(bubbleGlow, ["Glow Intensity"]), 0.35);

        var tr = shape.property("ADBE Transform Group");
        // Most bubbles erupt within six frames of impact for a sudden dive;
        // a smaller second wave follows immediately behind it.
        var birthFrame = (id < 18) ? (6 + (id % 6) * 0.75) : (10 + (id % 5) * 1.1);
        var birth = birthFrame / FPS;
        var life = (24 + (id % 6) * 4) / FPS;
        var sx = 960 + ((id*83)%180)-90;
        var sy = 205 + ((id*47)%70);
        var drift = ((id%2) ? 1 : -1) * (105 + (id%5)*34);
        setKeys(tr.property("ADBE Position"), [[birth,[sx,sy,(id%7-3)*24]], [birth+life,[sx+drift,sy-330-(id%5)*28,(id%7-3)*24]]]);
        setKeys(tr.property("ADBE Opacity"), [[birth,0],[birth+0.10,60],[birth+life*0.72,42],[Math.min(DURATION,birth+life),0]]);
        setKeys(tr.property("ADBE Scale"), [[birth,[8,8,100]],[birth+0.09,[128,128,100]],[birth+0.18,[100,100,100]],[Math.min(DURATION,birth+life),[72,72,100]]]);
        // Slider Control's visual track stops at 100, but typed values can be
        // much higher. The expression makes those values functional while
        // preserving the authored impact overshoot. 180 = the designed size.
        tr.property("ADBE Scale").expression =
            'r=Math.max(1,thisComp.layer("CTRL_INK_DROP").effect("Bubble Radius")("Slider"));' +
            'm=r/180;' +
            '[value[0]*m,value[1]*m,value.length>2?value[2]:100]';
        // Bubble Count now hides higher-index bubbles without removing them,
        // so the count remains animatable and nondestructive.
        tr.property("ADBE Opacity").expression =
            'count=Math.floor(thisComp.layer("CTRL_INK_DROP").effect("Bubble Count")("Slider"));' +
            ((id + 1) + '<=count?value:0');
        return shape;
    }

    removeOwnedItems();
    var root = folder(ROOT_NAME, project.rootFolder);
    root.name = ROOT_NAME;
    var footageFolder = folder("01_FOOTAGE", root);
    var compsFolder = folder("02_COMPS", root);
    var controlsFolder = folder("03_CONTROLS_AND_GUIDES", root);

    var io = new ImportOptions(TEX_FILE);
    var texture = tag(project.importFile(io));
    texture.name = "Persian_Pattern_RGBA";
    texture.parentFolder = footageFolder;

    var comp = tag(project.items.addComp("PERSIAN_INK_DROP_2_5D", W, H, 1, DURATION, FPS));
    comp.parentFolder = compsFolder;
    comp.bgColor = [0.015, 0.022, 0.035];
    comp.motionBlur = true;
    comp.shutterAngle = 180;
    comp.shutterPhase = -90;

    var background = comp.layers.addSolid([0.012,0.018,0.03], "BACKGROUND_WATER_DARK", W, H, 1, DURATION);
    background.threeDLayer = true;
    setValue(background.property("ADBE Transform Group").property("ADBE Position"), [960,540,420]);

    var ctrl = comp.layers.addNull();
    ctrl.name = "CTRL_INK_DROP";
    ctrl.guideLayer = true;
    ctrl.label = 14;
    setValue(ctrl.property("ADBE Transform Group").property("ADBE Position"), [960,150]);
    slider(ctrl, "Start Frame", 1);
    slider(ctrl, "Form End", 6);
    slider(ctrl, "Stretch End", 12);
    slider(ctrl, "Cloud End", 24);
    slider(ctrl, "Dissolve Start", 25);
    slider(ctrl, "Dissolve Duration", 24);
    slider(ctrl, "Top Neck Width", 16);
    slider(ctrl, "Top Neck Length", 34);
    slider(ctrl, "Top-Down Paint Flow", 100);
    slider(ctrl, "Cloud Width", 100);
    slider(ctrl, "Cloud Height", 100);
    slider(ctrl, "Turbulence", 100);
    slider(ctrl, "Pattern Scale", 100);
    slider(ctrl, "Pattern Rotation", 0);
    slider(ctrl, "Layer Depth", 34);
    slider(ctrl, "Bubble Count", 32);
    slider(ctrl, "Bubble Radius", 180); // type values above 100; 180 is designed size
    slider(ctrl, "Bubble Rise Speed", 165);
    slider(ctrl, "Bubble Burst Spread", 145);
    slider(ctrl, "Final Opacity", 0);
    checkbox(ctrl, "Enable Persian Pattern", true);
    checkbox(ctrl, "Enable Bubbles", true);
    color(ctrl, "Ink Tint", [0.06,0.53,0.72,1]);

    // Back-to-front cloud layers.
    var cloudLayers = [];
    for (var c = 0; c < 6; c++) cloudLayers.push(addCloudLayer(comp, texture, ctrl, c));
    for (var b = 0; b < 32; b++) addBubble(comp, ctrl, b);

    // Camera creates subtle parallax between the six shallow Z layers.
    var camera = comp.layers.addCamera("CAM_INK_DROP", [960,540]);
    camera.label = 11;
    setValue(camera.property("ADBE Transform Group").property("ADBE Position"), [960,540,-1900]);
    setValue(camera.property("ADBE Camera Options Group").property("ADBE Camera Zoom"), 1900);

    var guide = comp.layers.addText(
        "PERSIAN INK DROP\rFrames 1-6 form | 7-12 stretch | 13-24 bloom | 25-48 dissolve\rEdit CTRL_INK_DROP and individual INK_LAYER effects"
    );
    guide.name = "GUIDE_README";
    guide.guideLayer = true;
    guide.enabled = false;

    // Add informative composition markers.
    var marker = comp.markerProperty;
    marker.setValueAtTime(0, new MarkerValue("DROP FORMS"));
    marker.setValueAtTime(6/FPS, new MarkerValue("STRETCH"));
    marker.setValueAtTime(12/FPS, new MarkerValue("CLOUD BLOOM"));
    marker.setValueAtTime(24/FPS, new MarkerValue("DISSOLVE"));

    // Render Queue entry: PNG sequence with alpha if the installed template exists.
    var rq = project.renderQueue.items.add(comp);
    rq.timeSpanStart = 0;
    rq.timeSpanDuration = DURATION;
    var om = rq.outputModule(1);
    var pngTemplate = false;
    try { om.applyTemplate("PNG Sequence with Alpha"); pngTemplate = true; }
    catch (ignoreTemplate) {
        try { om.applyTemplate("PNG Sequence"); pngTemplate = true; } catch (ignore) {}
    }
    var renders = new Folder(OUT_DIR.fsName + "/render");
    if (!renders.exists) renders.create();
    om.file = pngTemplate
        ? new File(renders.fsName + "/persian_ink_drop_[#####].png")
        : new File(renders.fsName + "/persian_ink_drop.mp4");

    comp.openInViewer();
    project.save(PROJECT_FILE);
    app.endUndoGroup();

    // CODEX_AE_BATCH is set only by the automated builder invocation.
    // It prevents a background After Effects process from remaining open.
    if ($.getenv("CODEX_AE_BATCH") === "1") {
        try { app.quit(); } catch (ignoreQuit) {}
    } else {
        alert("Persian ink-drop rig created:\n" + PROJECT_FILE.fsName);
    }
})();
