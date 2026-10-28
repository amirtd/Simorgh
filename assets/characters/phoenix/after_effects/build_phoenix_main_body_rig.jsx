/*
 * Whirling Worlds - simplified Phoenix main-body rig for After Effects.
 * Uses only: body/neck, head, left wing, right wing, tail, and feet.
 * Intentionally excludes wing tips, crests, and individual feathers.
 */

(function buildPhoenixMainBodyRig() {
    app.beginUndoGroup("Build Phoenix Main Body Rig");

    var project = app.project || app.newProject();
    var outputFolder = new Folder("E:/Wirling Worlds/Simorgh/assets/characters/phoenix/after_effects");
    if (!outputFolder.exists) outputFolder.create();

    var sourceFolder = new Folder("E:/Wirling Worlds/Simorgh/assets/characters/phoenix/source_art/body_rig_current");
    if (!sourceFolder.exists) {
        alert("Source folder was not found: " + sourceFolder.fsName);
        app.endUndoGroup();
        return;
    }

    function findOrCreateFolder(name, parentFolder) {
        for (var i = 1; i <= project.numItems; i++) {
            var item = project.item(i);
            if (item instanceof FolderItem && item.name === name && item.parentFolder === parentFolder) {
                return item;
            }
        }
        var folder = project.items.addFolder(name);
        folder.parentFolder = parentFolder;
        return folder;
    }

    function removeExistingComp(name) {
        for (var i = project.numItems; i >= 1; i--) {
            var item = project.item(i);
            if (item instanceof CompItem && item.name === name) item.remove();
        }
    }

    function importPng(filename, parentFolder) {
        var file = new File(sourceFolder.fsName + "/" + filename);
        if (!file.exists) throw new Error("Missing source image: " + file.fsName);
        var options = new ImportOptions(file);
        var footage = project.importFile(options);
        footage.parentFolder = parentFolder;
        return footage;
    }

    function setLabel(layer, labelIndex) {
        try { layer.label = labelIndex; } catch (ignore) {}
    }

    function addController(comp, name, position, colorLabel, parent) {
        var controller = comp.layers.addNull();
        controller.name = name;
        controller.threeDLayer = false;
        controller.guideLayer = true;
        controller.property("ADBE Transform Group").property("ADBE Position").setValue(position);
        controller.property("ADBE Transform Group").property("ADBE Anchor Point").setValue([50, 50]);
        setLabel(controller, colorLabel);
        if (parent) controller.parent = parent;
        return controller;
    }

    function addPart(comp, footage, spec, master) {
        var control = addController(comp, "CTRL_" + spec.name, spec.position, spec.label, master);
        var layer = comp.layers.add(footage);
        layer.name = "ART_" + spec.name;
        layer.property("ADBE Transform Group").property("ADBE Anchor Point").setValue([
            footage.width * spec.pivot[0],
            footage.height * spec.pivot[1]
        ]);
        layer.property("ADBE Transform Group").property("ADBE Position").setValue(spec.position);
        layer.property("ADBE Transform Group").property("ADBE Rotate Z").setValue(spec.rotation);
        layer.property("ADBE Transform Group").property("ADBE Scale").setValue([spec.scale, spec.scale]);
        layer.parent = control;
        setLabel(layer, spec.label);
        layer.motionBlur = true;
        control.moveBefore(layer);
        return { control: control, art: layer };
    }

    var root = findOrCreateFolder("PHOENIX_MAIN_BODY_RIG", project.rootFolder);
    var footageFolder = findOrCreateFolder("01_FOOTAGE", root);
    var compsFolder = findOrCreateFolder("02_COMPS", root);
    var controlsFolder = findOrCreateFolder("03_CONTROLS_INFO", root);

    removeExistingComp("PHOENIX_MAIN_BODY_RIG_1080P");
    var comp = project.items.addComp("PHOENIX_MAIN_BODY_RIG_1080P", 1920, 1080, 1, 10, 24);
    comp.parentFolder = compsFolder;
    comp.bgColor = [0.035, 0.035, 0.05];
    comp.motionBlur = true;
    comp.shutterAngle = 180;

    var footage = {
        BODY_NECK: importPng("body.png", footageFolder),
        TAIL: importPng("tail.png", footageFolder),
        WING_L: importPng("wing_L.png", footageFolder),
        WING_R: importPng("wing_R.png", footageFolder),
        HEAD: importPng("head_01.png", footageFolder),
        FEET: importPng("foot_R.png", footageFolder)
    };

    var master = addController(comp, "CTRL_MASTER", [960, 540], 9, null);
    master.property("ADBE Transform Group").property("ADBE Scale").setValue([100, 100]);

    // Positions translate the established Houdini card layout into a 1920x1080 frame.
    // Layer creation order is back-to-front.
    var parts = [
        { name:"TAIL",      footage:footage.TAIL,      pivot:[0.88,0.08], position:[1261,743], rotation:-8, scale:78, label:10 },
        { name:"BODY_NECK", footage:footage.BODY_NECK, pivot:[0.50,0.50], position:[960,540],  rotation:0,  scale:100,label:9  },
        { name:"WING_L",    footage:footage.WING_L,    pivot:[0.91,0.82], position:[925,393],  rotation:0,  scale:92, label:12 },
        { name:"WING_R",    footage:footage.WING_R,    pivot:[0.10,0.80], position:[1023,400], rotation:0,  scale:92, label:2  },
        { name:"FEET",      footage:footage.FEET,      pivot:[0.50,0.92], position:[960,827],  rotation:0,  scale:62, label:11 },
        { name:"HEAD",      footage:footage.HEAD,      pivot:[0.52,0.08], position:[621,229],  rotation:4,  scale:72, label:13 }
    ];

    var built = {};
    for (var p = 0; p < parts.length; p++) {
        var spec = parts[p];
        built[spec.name] = addPart(comp, spec.footage, spec, master);
    }

    // Keep the visible art in a predictable back-to-front stack.
    built.TAIL.art.moveToEnd();
    built.BODY_NECK.art.moveBefore(built.TAIL.art);
    built.WING_L.art.moveBefore(built.BODY_NECK.art);
    built.WING_R.art.moveBefore(built.WING_L.art);
    built.FEET.art.moveBefore(built.WING_R.art);
    built.HEAD.art.moveToBeginning();

    // Marker guide for animators; does not render.
    var guide = comp.layers.addText("MAIN BODY RIG: master, body/neck, head, wings, tail, feet");
    guide.name = "GUIDE_MAIN_PARTS_ONLY";
    guide.guideLayer = true;
    guide.enabled = false;
    guide.property("ADBE Transform Group").property("ADBE Position").setValue([960, 60]);
    setLabel(guide, 14);

    var readme = project.items.addComp("RIG_NOTES_MAIN_PARTS_ONLY", 1280, 720, 1, 1, 24);
    readme.parentFolder = controlsFolder;
    var note = readme.layers.addText(
        "PHOENIX MAIN BODY RIG\\r\\r" +
        "Included: body/neck, head, left wing, right wing, tail, feet.\\r" +
        "Excluded: wing tips, crests, individual feathers.\\r\\r" +
        "Animate the CTRL_ layers. CTRL_MASTER moves the full character."
    );
    note.property("ADBE Transform Group").property("ADBE Position").setValue([640, 360]);

    comp.openInViewer();
    project.save(new File(outputFolder.fsName + "/phoenix_main_body_rig.aep"));

    app.endUndoGroup();
    alert("Phoenix main-body After Effects rig created and saved to:\n" + outputFolder.fsName + "/phoenix_main_body_rig.aep");
})();
