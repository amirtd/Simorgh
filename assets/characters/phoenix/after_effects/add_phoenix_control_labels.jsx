/*
 * Adds non-rendering on-screen labels to the simplified Phoenix controls.
 * Safe to run more than once: existing UI_LABEL_ layers are replaced.
 */
(function addPhoenixControlLabels() {
    app.beginUndoGroup("Add Phoenix Control Labels");

    var projectFile = new File("E:/Wirling Worlds/Simorgh/assets/characters/phoenix/after_effects/phoenix_main_body_rig.aep");
    var outputFile = new File("E:/Wirling Worlds/Simorgh/assets/characters/phoenix/after_effects/phoenix_main_body_rig_labeled.aep");
    var compName = "PHOENIX_MAIN_BODY_RIG_1080P";

    function findComp(name) {
        if (!app.project) return null;
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    var comp = findComp(compName);
    if (!comp) {
        if (!projectFile.exists) {
            alert("Phoenix rig project was not found:\n" + projectFile.fsName);
            app.endUndoGroup();
            return;
        }
        app.open(projectFile);
        comp = findComp(compName);
    }

    if (!comp) {
        alert("Composition was not found: " + compName);
        app.endUndoGroup();
        return;
    }

    function findLayer(name) {
        for (var i = 1; i <= comp.numLayers; i++) {
            if (comp.layer(i).name === name) return comp.layer(i);
        }
        return null;
    }

    // Remove labels made by an earlier run, while leaving all rig layers intact.
    for (var i = comp.numLayers; i >= 1; i--) {
        if (comp.layer(i).name.indexOf("UI_LABEL_") === 0) comp.layer(i).remove();
    }

    var master = findLayer("CTRL_MASTER");
    if (!master) {
        alert("CTRL_MASTER was not found in " + compName);
        app.endUndoGroup();
        return;
    }

    var effects = master.property("ADBE Effect Parade");
    var showLabels = effects.property("Show Control Labels");
    if (!showLabels) {
        showLabels = effects.addProperty("ADBE Checkbox Control");
        showLabels.name = "Show Control Labels";
    }
    showLabels.property(1).setValue(1);

    var specs = [
        { control:"CTRL_MASTER",    text:"MASTER",      offset:[0, 120],   color:[1.00, 0.78, 0.15] },
        { control:"CTRL_BODY_NECK", text:"BODY / NECK", offset:[0, 105],   color:[0.30, 1.00, 0.48] },
        { control:"CTRL_HEAD",      text:"HEAD",        offset:[0, -75],   color:[1.00, 0.30, 0.78] },
        { control:"CTRL_WING_L_UPPER", text:"L WING UPPER", offset:[-95,-55], color:[0.20, 0.85, 1.00] },
        { control:"CTRL_WING_L_LOWER", text:"L WING LOWER", offset:[-75,-48], color:[0.35, 0.72, 1.00] },
        { control:"CTRL_WING_R_UPPER", text:"R WING UPPER", offset:[95,-55],  color:[1.00, 0.70, 0.18] },
        { control:"CTRL_WING_R_LOWER", text:"R WING LOWER", offset:[75,-48],  color:[1.00, 0.45, 0.12] },
        { control:"CTRL_TAIL",      text:"TAIL",        offset:[105, 60],  color:[0.82, 0.30, 1.00] },
        { control:"CTRL_FEET",      text:"FEET",        offset:[0, 78],    color:[1.00, 0.55, 0.12] }
    ];

    function addLabel(spec) {
        var control = findLayer(spec.control);
        if (!control) return false;

        var label = comp.layers.addText("●  " + spec.text);
        label.name = "UI_LABEL_" + spec.control.substring(5);
        label.guideLayer = true;
        label.shy = true;
        label.motionBlur = false;
        label.parent = control;

        var sourceText = label.property("ADBE Text Properties").property("ADBE Text Document");
        var doc = sourceText.value;
        doc.fontSize = spec.control === "CTRL_MASTER" ? 30 : 25;
        doc.fillColor = spec.color;
        doc.applyFill = true;
        doc.applyStroke = true;
        doc.strokeColor = [0.015, 0.015, 0.025];
        doc.strokeWidth = 3;
        doc.strokeOverFill = false;
        doc.justification = ParagraphJustification.CENTER_JUSTIFY;
        sourceText.setValue(doc);

        var transform = label.property("ADBE Transform Group");
        transform.property("ADBE Anchor Point").setValue([0, 0]);
        transform.property("ADBE Position").setValue(spec.offset);
        transform.property("ADBE Scale").setValue([100, 100]);
        transform.property("ADBE Rotate Z").expression = "-parent.transform.rotation;";
        transform.property("ADBE Opacity").expression =
            "thisComp.layer('CTRL_MASTER').effect('Show Control Labels')('Checkbox') ? 100 : 0;";

        label.moveBefore(control);
        return true;
    }

    var made = 0;
    for (var s = 0; s < specs.length; s++) {
        if (addLabel(specs[s])) made++;
    }

    comp.hideShyLayers = false;
    comp.openInViewer();
    app.project.save(outputFile);
    app.endUndoGroup();
    alert(
        "Added " + made + " non-rendering control labels.\n\n" +
        "Toggle them with CTRL_MASTER > Show Control Labels.\n\n" +
        "Saved as:\n" + outputFile.fsName
    );
})();

