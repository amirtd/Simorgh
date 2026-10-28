/*
    Creates a two-sided procedural fish that exits the main bubble,
    swims toward the camera, and passes close to the camera on the left.
    Run with: File > Scripts > Run Script File...
*/
(function () {
    app.beginUndoGroup("Create Fish Swim Scene");

    var project = app.project || app.newProject();
    var W = 1920, H = 1080, FPS = 24, DURATION = 6.0;
    var baseFolder = new File($.fileName).parent;
    var referenceFile = new File(baseFolder.fsName + "/houdini_frame_reference.png");

    // Remove only items created by an earlier run of this script, including a partial failed run.
    for (var cleanupIndex = project.numItems; cleanupIndex >= 1; cleanupIndex--) {
        var cleanupItem = project.item(cleanupIndex);
        if (cleanupItem.name === "FISH_PLANE_ART" ||
            cleanupItem.name === "FISH_SWIMS_OUT_SHOT" ||
            cleanupItem.name === "houdini_frame_reference.png") {
            cleanupItem.remove();
        }
    }

    function addFill(group, color, opacity) {
        var fill = group.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Fill");
        fill.property("ADBE Vector Fill Color").setValue(color);
        fill.property("ADBE Vector Fill Opacity").setValue(opacity === undefined ? 100 : opacity);
        return fill;
    }

    function addStroke(group, color, width, opacity) {
        var stroke = group.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Stroke");
        stroke.property("ADBE Vector Stroke Color").setValue(color);
        stroke.property("ADBE Vector Stroke Width").setValue(width);
        stroke.property("ADBE Vector Stroke Opacity").setValue(opacity === undefined ? 100 : opacity);
        return stroke;
    }

    function ellipseLayer(comp, name, size, position, color, strokeColor, strokeWidth) {
        var layer = comp.layers.addShape();
        layer.name = name;
        var group = layer.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
        group.name = name + " Shape";
        var ellipse = group.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Ellipse");
        ellipse.property("ADBE Vector Ellipse Size").setValue(size);
        addFill(group, color, 100);
        if (strokeWidth > 0) addStroke(group, strokeColor, strokeWidth, 100);
        layer.property("ADBE Transform Group").property("ADBE Position").setValue(position);
        return layer;
    }

    function pathLayer(comp, name, vertices, inTangents, outTangents, closed, color) {
        var layer = comp.layers.addShape();
        layer.name = name;
        var group = layer.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
        group.name = name + " Shape";
        var path = group.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Group");
        var shape = new Shape();
        shape.vertices = vertices;
        shape.inTangents = inTangents;
        shape.outTangents = outTangents;
        shape.closed = closed;
        path.property("ADBE Vector Shape").setValue(shape);
        addFill(group, color, 100);
        return layer;
    }

    // Procedural side-view fish artwork.
    var fishComp = project.items.addComp("FISH_PLANE_ART", 600, 300, 1, DURATION, FPS);
    fishComp.bgColor = [0, 0, 0];

    var tail = pathLayer(
        fishComp, "Tail_Wave",
        [[0,0],[-135,-100],[-105,0],[-135,100]],
        [[0,0],[0,0],[0,0],[0,0]], [[0,0],[0,0],[0,0],[0,0]],
        true, [0.72,0.06,0.035]
    );
    tail.property("ADBE Transform Group").property("ADBE Position").setValue([205,150]);
    tail.property("ADBE Transform Group").property("ADBE Rotate Z").expression =
        "Math.sin(time*2*Math.PI*2.25)*18";

    var body = ellipseLayer(fishComp, "Fish_Body", [350,155], [350,150],
                            [0.86,0.09,0.045], [1.0,0.63,0.17], 9);
    body.property("ADBE Transform Group").property("ADBE Scale").expression =
        "var w=Math.sin(time*2*Math.PI*2.25); [100-w*2.5,100+w*4.0]";

    var fin = ellipseLayer(fishComp, "Lower_Fin", [125,48], [340,205],
                           [0.92,0.24,0.06], [1.0,0.68,0.18], 5);
    fin.property("ADBE Transform Group").property("ADBE Rotate Z").expression =
        "-28+Math.sin(time*2*Math.PI*2.25+0.8)*13";

    var stripe1 = ellipseLayer(fishComp, "Persian_Gold_1", [40,115], [315,150],
                               [1.0,0.62,0.10], [0.62,0.02,0.02], 4);
    stripe1.property("ADBE Transform Group").property("ADBE Rotate Z").setValue(-18);
    var stripe2 = ellipseLayer(fishComp, "Persian_Gold_2", [30,95], [370,150],
                               [1.0,0.72,0.20], [0.62,0.02,0.02], 3);
    stripe2.property("ADBE Transform Group").property("ADBE Rotate Z").setValue(-18);

    ellipseLayer(fishComp, "Eye_White", [38,38], [465,120], [1,0.91,0.72], [0.4,0,0], 4);
    ellipseLayer(fishComp, "Eye_Pupil", [15,15], [471,120], [0.02,0.015,0.01], [1,0.55,0.1], 2);

    // Main shot composition and supplied frame.
    var comp = project.items.addComp("FISH_SWIMS_OUT_SHOT", W, H, 1, DURATION, FPS);
    comp.bgColor = [0.015, 0.035, 0.055];
    if (referenceFile.exists) {
        var footage = project.importFile(new ImportOptions(referenceFile));
        var bg = comp.layers.add(footage);
        bg.name = "Houdini_Frame_Reference";
        var sx = W / footage.width * 100;
        var sy = H / footage.height * 100;
        bg.property("ADBE Transform Group").property("ADBE Scale").setValue([sx, sy]);
        bg.locked = true;
    }

    var camera = comp.layers.addCamera("Fish Camera", [W/2, H/2]);
    camera.property("ADBE Transform Group").property("ADBE Position").setValue([W/2,H/2,-2200]);
    // A camera's Point of Interest uses the Anchor Point match-name in AE scripting.
    camera.property("ADBE Transform Group").property("ADBE Anchor Point").setValue([W/2,H/2,0]);

    var rig = comp.layers.addNull();
    rig.name = "FISH_RIG_AND_MOTION_CONTROLS";
    rig.threeDLayer = true;
    var pos = rig.property("ADBE Transform Group").property("ADBE Position");
    var times = [0.0, 0.8, 1.8, 3.0, 4.2, 5.25];
    var points = [
        [975,555,20],       // inside the main bubble
        [930,525,-180],     // clears the bubble surface
        [790,475,-520],
        [535,445,-980],
        [175,500,-1520],    // approaches left side of camera
        [-260,610,-2080]    // passes just left of camera
    ];
    for (var k=0; k<times.length; k++) {
        pos.setValueAtTime(times[k], points[k]);
        pos.setInterpolationTypeAtKey(k+1, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
        pos.setSpatialAutoBezierAtKey(k+1, true);
        pos.setTemporalAutoBezierAtKey(k+1, true);
    }
    pos.expression =
        "var a=ease(time,0,5.25,3,30);" +
        "var w=Math.sin(time*2*Math.PI*1.45);" +
        "value+[w*a,Math.sin(time*2*Math.PI*2.9+0.7)*a*0.35,0]";
    rig.property("ADBE Transform Group").property("ADBE Rotate Y").expression =
        "Math.sin(time*2*Math.PI*1.45)*9";
    rig.property("ADBE Transform Group").property("ADBE Rotate Z").expression =
        "-8+Math.sin(time*2*Math.PI*1.45+0.8)*5";

    // Two back-to-back copies make the artwork readable from either side.
    var front = comp.layers.add(fishComp);
    front.name = "Fish_Plane_FRONT";
    front.threeDLayer = true;
    front.parent = rig;
    front.property("ADBE Transform Group").property("ADBE Position").setValue([0,0,-0.5]);
    front.property("ADBE Transform Group").property("ADBE Scale").setValue([28,28,28]);

    var back = comp.layers.add(fishComp);
    back.name = "Fish_Plane_BACK_two_sided";
    back.threeDLayer = true;
    back.parent = rig;
    back.property("ADBE Transform Group").property("ADBE Position").setValue([0,0,0.5]);
    back.property("ADBE Transform Group").property("ADBE Rotate Y").setValue(180);
    back.property("ADBE Transform Group").property("ADBE Scale").setValue([28,28,28]);

    // Editable visual plan of the projected curve. Guide layers remain visible in AE but do not render.
    var guide = comp.layers.addShape();
    guide.name = "FISH_PATH_GUIDE_edit_this_curve";
    var gg = guide.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    gg.name = "Projected Swim Path";
    var gp = gg.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Group");
    var gs = new Shape();
    gs.vertices = [[975,555],[930,525],[790,475],[535,445],[175,500],[-260,610]];
    gs.inTangents = [[0,0],[-35,20],[-70,30],[-95,0],[-120,-35],[-80,-20]];
    gs.outTangents = [[30,-20],[45,-25],[75,-35],[110,0],[125,40],[0,0]];
    gs.closed = false;
    gp.property("ADBE Vector Shape").setValue(gs);
    addStroke(gg, [0.15,0.95,1.0], 5, 65);
    guide.guideLayer = true;
    guide.locked = false;

    var note = comp.layers.addText("EDIT FISH_RIG position keys for the 3D route. The cyan guide is a non-rendering 2D plan.");
    note.name = "INSTRUCTIONS_GUIDE_ONLY";
    note.guideLayer = true;
    note.property("ADBE Transform Group").property("ADBE Position").setValue([70,70]);

    comp.openInViewer();
    app.endUndoGroup();
    alert("Created FISH_SWIMS_OUT_SHOT. Save the project as an .aep when ready.");
})();
