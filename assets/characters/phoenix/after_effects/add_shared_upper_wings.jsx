/*
 * Adds the same shared upper-wing cutout to both sides of the Phoenix rig.
 * Existing wing artwork stays in the composition and becomes the lower piece.
 * The right-side shared upper wing is mirrored horizontally.
 */
(function addSharedUpperWings() {
    app.beginUndoGroup("Add Shared Upper Wings");

    var sourceProject = new File("E:/Wirling Worlds/Simorgh/assets/characters/phoenix/after_effects/phoenix_main_body_rig.aep");
    var outputProject = new File("E:/Wirling Worlds/Simorgh/assets/characters/phoenix/after_effects/phoenix_main_body_rig_upper_lower.aep");
    var upperWingFile = new File("E:/Wirling Worlds/Simorgh/assets/characters/phoenix/source_art/body_rig_current/wing_upper_shared.png");
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
        if (!sourceProject.exists) {
            alert("Phoenix project was not found:\n" + sourceProject.fsName);
            app.endUndoGroup();
            return;
        }
        app.open(sourceProject);
        comp = findComp(compName);
    }
    if (!comp || !upperWingFile.exists) {
        alert("The rig composition or shared upper-wing PNG is missing.");
        app.endUndoGroup();
        return;
    }

    function findLayer(name) {
        for (var i = 1; i <= comp.numLayers; i++) {
            if (comp.layer(i).name === name) return comp.layer(i);
        }
        return null;
    }

    function findFootageByFile(file) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof FootageItem && item.file && item.file.fsName === file.fsName) return item;
        }
        return null;
    }

    var sharedFootage = findFootageByFile(upperWingFile);
    if (!sharedFootage) sharedFootage = app.project.importFile(new ImportOptions(upperWingFile));
    sharedFootage.name = "wing_upper_shared.png";

    function removeIfPresent(name) {
        var layer = findLayer(name);
        if (layer) layer.remove();
    }

    function addSide(side, mirror, colorLabel) {
        removeIfPresent("ART_WING_" + side + "_UPPER");
        removeIfPresent("CTRL_WING_" + side + "_UPPER");

        var lowerCtrl = findLayer("CTRL_WING_" + side + "_LOWER") || findLayer("CTRL_WING_" + side);
        var lowerArt = findLayer("ART_WING_" + side + "_LOWER") || findLayer("ART_WING_" + side);
        if (!lowerCtrl || !lowerArt) throw new Error("Existing wing was not found for side " + side);

        lowerCtrl.name = "CTRL_WING_" + side + "_LOWER";
        lowerArt.name = "ART_WING_" + side + "_LOWER";

        // Duplicate the established root control so its position and master parenting stay exact.
        var upperCtrl = lowerCtrl.duplicate();
        upperCtrl.name = "CTRL_WING_" + side + "_UPPER";
        upperCtrl.guideLayer = true;
        upperCtrl.label = colorLabel;

        // Upper drives lower, while AE preserves the existing lower-wing world transform.
        lowerCtrl.parent = upperCtrl;

        var upperArt = comp.layers.add(sharedFootage);
        upperArt.name = "ART_WING_" + side + "_UPPER";
        upperArt.guideLayer = false;
        upperArt.motionBlur = true;
        upperArt.label = colorLabel;
        upperArt.parent = upperCtrl;

        var tr = upperArt.property("ADBE Transform Group");
        tr.property("ADBE Anchor Point").setValue([
            sharedFootage.width * 0.90,
            sharedFootage.height * 0.80
        ]);
        // A child position matching the null anchor aligns both root pivots.
        tr.property("ADBE Position").setValue([50,50]);
        tr.property("ADBE Scale").setValue(mirror ? [-43,43] : [43,43]);

        // Keep the original wing visible above the shared upper piece.
        upperArt.moveAfter(lowerArt);
        upperCtrl.moveBefore(upperArt);
    }

    try {
        addSide("L", false, 12);
        addSide("R", true, 2);
    } catch (err) {
        alert("Upper-wing setup failed:\n" + err.toString());
        app.endUndoGroup();
        return;
    }

    comp.openInViewer();
    app.project.save(outputProject);
    app.endUndoGroup();
    alert(
        "Added the shared upper-wing piece to both sides.\n" +
        "The original wings remain as the lower pieces.\n\n" +
        "Saved as:\n" + outputProject.fsName + "\n\n" +
        "Run add_phoenix_control_labels.jsx to refresh the labels."
    );
})();

