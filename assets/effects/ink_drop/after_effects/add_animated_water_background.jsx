/*
 * Animated underwater background for PERSIAN_INK_DROP_2_5D.
 * Run after opening persian_ink_drop.aep. Safe to rerun: WATER_* layers are replaced.
 */
(function addAnimatedWaterBackground() {
    app.beginUndoGroup("Add Animated Water Background");

    var COMP_NAME = "PERSIAN_INK_DROP_2_5D";
    var comp = null;
    var i;

    if (app.project && app.project.activeItem instanceof CompItem) {
        comp = app.project.activeItem;
    }
    if (!comp || comp.name !== COMP_NAME) {
        for (i = 1; i <= app.project.numItems; i++) {
            if (app.project.item(i) instanceof CompItem && app.project.item(i).name === COMP_NAME) {
                comp = app.project.item(i);
                break;
            }
        }
    }
    if (!comp) {
        alert("Open the ink-drop project first. Composition not found: " + COMP_NAME);
        app.endUndoGroup();
        return;
    }

    function removeOldLayers() {
        for (var n = comp.numLayers; n >= 1; n--) {
            if (comp.layer(n).name.indexOf("WATER_") === 0) comp.layer(n).remove();
        }
    }

    function fx(layer, matchName, label) {
        try {
            var e = layer.property("ADBE Effect Parade").addProperty(matchName);
            if (label) e.name = label;
            return e;
        } catch (ignore) { return null; }
    }

    function findProp(group, names) {
        if (!group) return null;
        for (var p = 0; p < names.length; p++) {
            try {
                var result = group.property(names[p]);
                if (result) return result;
            } catch (ignore) {}
        }
        return null;
    }

    function set(p, value) {
        if (!p) return;
        try { p.setValue(value); } catch (ignore) {}
    }

    function keys(p, values) {
        if (!p) return;
        for (var k = 0; k < values.length; k++) {
            try { p.setValueAtTime(values[k][0], values[k][1]); } catch (ignore) {}
        }
        for (var q = 1; q <= p.numKeys; q++) {
            try {
                p.setInterpolationTypeAtKey(q, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
            } catch (ignoreEase) {}
        }
    }

    function slider(control, name, value) {
        var e = fx(control, "ADBE Slider Control", name);
        if (e) set(e.property(1), value);
        return e;
    }

    function addEllipseMask(layer, center, radius, feather, opacity) {
        var mask = layer.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
        var shape = new Shape();
        var c = 0.5522848;
        shape.vertices = [
            [center[0], center[1]-radius[1]], [center[0]+radius[0], center[1]],
            [center[0], center[1]+radius[1]], [center[0]-radius[0], center[1]]
        ];
        shape.inTangents = [[-c*radius[0],0],[0,-c*radius[1]],[c*radius[0],0],[0,c*radius[1]]];
        shape.outTangents = [[c*radius[0],0],[0,c*radius[1]],[-c*radius[0],0],[0,-c*radius[1]]];
        shape.closed = true;
        mask.property("ADBE Mask Shape").setValue(shape);
        set(mask.property("ADBE Mask Feather"), [feather,feather]);
        set(mask.property("ADBE Mask Opacity"), opacity);
        return mask;
    }

    function moveToBack(layer) { try { layer.moveToEnd(); } catch (ignore) {} }

    removeOldLayers();

    // The original ink rig includes a static 3D dark card. Disable it so it
    // cannot occlude the new full-frame animated water layers.
    try {
        var legacyBackground = comp.layer("BACKGROUND_WATER_DARK");
        if (legacyBackground) legacyBackground.enabled = false;
    } catch (ignoreLegacyBackground) {}

    // Artist-facing controls. The generated animation works without expressions,
    // while these values provide a clear place for later retiming and art direction.
    var control = comp.layers.addNull();
    control.name = "WATER_CTRL";
    control.guideLayer = true;
    control.label = 14;
    set(control.property("ADBE Transform Group").property("ADBE Position"), [155,105]);
    slider(control, "Current Speed", 35);
    slider(control, "Caustic Scale", 145);
    slider(control, "Caustic Contrast", 165);
    slider(control, "Ripple Strength", 55);
    slider(control, "Light Ray Opacity", 18);
    slider(control, "Water Darkness", 82);

    // Deep base. This replaces the earlier static background visually but leaves it
    // in the project so the water add-on remains independently removable.
    var base = comp.layers.addSolid([0.008,0.025,0.052], "WATER_01_DEEP_BASE", comp.width, comp.height, 1, comp.duration);
    base.label = 4;
    moveToBack(base);

    // Broad turquoise pool creates a photographic underwater gradient without plugins.
    var pool = comp.layers.addSolid([0.015,0.20,0.27], "WATER_02_TURQUOISE_POOL", comp.width, comp.height, 1, comp.duration);
    pool.label = 5;
    pool.blendingMode = BlendingMode.SCREEN;
    addEllipseMask(pool, [comp.width*0.53, comp.height*0.44], [comp.width*0.58, comp.height*0.56], 420, 52);
    set(pool.property("ADBE Transform Group").property("ADBE Opacity"), 54);
    moveToBack(pool);
    pool.moveBefore(base);

    // Animated caustics: two differently scaled noise fields sliding in opposing directions.
    function makeCaustic(name, color, scale, opacity, speed, zRotation) {
        var layer = comp.layers.addSolid(color, name, comp.width, comp.height, 1, comp.duration);
        layer.label = 10;
        layer.blendingMode = BlendingMode.SCREEN;
        var noise = fx(layer, "ADBE Fractal Noise", "Animated Water Caustics");
        set(findProp(noise, ["Fractal Type"]), 7);
        set(findProp(noise, ["Noise Type"]), 1);
        set(findProp(noise, ["Contrast"]), 210);
        set(findProp(noise, ["Brightness"]), -52);
        set(findProp(noise, ["Complexity"]), 4.2);
        var evolution = findProp(noise, ["Evolution"]);
        if (evolution) evolution.expression = "time*" + speed;
        var offset = findProp(noise, ["Offset Turbulence"]);
        if (offset) offset.expression = "value + [time*" + (speed*0.85) + ",time*" + (-speed*0.42) + "]";
        var transform = findProp(noise, ["Transform"]);
        if (transform) {
            set(findProp(transform, ["Scale"]), scale);
            set(findProp(transform, ["Scale Width"]), scale*2.8);
            set(findProp(transform, ["Scale Height"]), scale*0.72);
        }
        var td = fx(layer, "ADBE Turbulent Displace", "Liquid Refraction");
        set(findProp(td, ["Amount"]), 34);
        set(findProp(td, ["Size"]), 185);
        set(findProp(td, ["Complexity"]), 2.2);
        var evo = findProp(td, ["Evolution"]);
        if (evo) evo.expression = "time*" + (speed*1.3);
        var soften = fx(layer, "ADBE Gaussian Blur 2", "Caustic Diffusion");
        set(findProp(soften, ["Blurriness"]), 28);
        set(layer.property("ADBE Transform Group").property("ADBE Rotate Z"), zRotation);
        set(layer.property("ADBE Transform Group").property("ADBE Opacity"), opacity);
        moveToBack(layer);
        layer.moveBefore(pool);
        return layer;
    }

    makeCaustic("WATER_03_CAUSTICS_LARGE", [0.12,0.72,0.82], 165, 11, 32, -7);
    makeCaustic("WATER_04_CAUSTICS_FINE", [0.20,0.55,0.78], 76, 7, -46, 11);

    // Soft volumetric shafts from the surface.
    for (i = 0; i < 7; i++) {
        var ray = comp.layers.addSolid([0.20,0.68,0.78], "WATER_05_LIGHT_RAY_" + (i+1), 155, comp.height*1.5, 1, comp.duration);
        ray.blendingMode = BlendingMode.ADD;
        ray.label = 2;
        var rt = ray.property("ADBE Transform Group");
        set(rt.property("ADBE Anchor Point"), [77,0]);
        set(rt.property("ADBE Position"), [260+i*245, -80, 0]);
        set(rt.property("ADBE Rotate Z"), -13 + i*3.5);
        set(rt.property("ADBE Opacity"), 6 + (i%3)*2);
        addEllipseMask(ray, [77,comp.height*0.55], [100,comp.height*0.7], 160, 70);
        var blur = fx(ray, "ADBE Gaussian Blur 2", "Soft Ray");
        set(findProp(blur, ["Blurriness"]), 95);
        keys(rt.property("ADBE Position"), [[0,[260+i*245,-80,0]],[comp.duration,[330+i*245,-25,0]]]);
        moveToBack(ray);
        ray.moveBefore(pool);
    }

    // Surface shimmer line near the top.
    var surface = comp.layers.addSolid([0.18,0.78,0.88], "WATER_06_SURFACE_SHIMMER", comp.width, 110, 1, comp.duration);
    surface.blendingMode = BlendingMode.ADD;
    surface.label = 6;
    set(surface.property("ADBE Transform Group").property("ADBE Position"), [comp.width/2,75]);
    set(surface.property("ADBE Transform Group").property("ADBE Opacity"), 23);
    var wave = fx(surface, "ADBE Wave Warp", "Surface Ripples");
    set(findProp(wave, ["Wave Height"]), 18);
    set(findProp(wave, ["Wave Width"]), 155);
    set(findProp(wave, ["Wave Speed"]), 0.35);
    var sblur = fx(surface, "ADBE Gaussian Blur 2", "Surface Bloom");
    set(findProp(sblur, ["Blurriness"]), 34);
    moveToBack(surface);
    surface.moveBefore(pool);

    // Concentric impact ripples centered under the ink inlet.
    for (i = 0; i < 5; i++) {
        var ring = comp.layers.addShape();
        ring.name = "WATER_07_IMPACT_RIPPLE_" + (i+1);
        ring.label = 8;
        var contents = ring.property("ADBE Root Vectors Group");
        var ellipse = contents.addProperty("ADBE Vector Shape - Ellipse");
        set(ellipse.property("ADBE Vector Ellipse Size"), [290,62]);
        var stroke = contents.addProperty("ADBE Vector Graphic - Stroke");
        set(stroke.property("ADBE Vector Stroke Color"), [0.32,0.88,0.96,1]);
        set(stroke.property("ADBE Vector Stroke Width"), 2.2);
        set(stroke.property("ADBE Vector Stroke Opacity"), 52);
        var tr = ring.property("ADBE Transform Group");
        set(tr.property("ADBE Position"), [comp.width/2,205]);
        var begin = (5+i*2.5)/comp.frameRate;
        keys(tr.property("ADBE Scale"), [[begin,[8,8]],[begin+0.75,[150+i*22,150+i*22]]]);
        keys(tr.property("ADBE Opacity"), [[begin,0],[begin+0.08,48],[begin+0.75,0]]);
        var rblur = fx(ring, "ADBE Gaussian Blur 2", "Ripple Softness");
        set(findProp(rblur, ["Blurriness"]), 5);
        moveToBack(ring);
        ring.moveBefore(pool);
    }

    // Ensure all generated water sits behind the ink, bubbles, and camera.
    control.moveToEnd();
    base.moveToEnd();

    comp.openInViewer();
    app.project.save();
    app.endUndoGroup();
})();
