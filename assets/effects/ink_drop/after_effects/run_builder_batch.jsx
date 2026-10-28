/* Isolated command-line wrapper. Writes any ExtendScript exception to disk. */
(function () {
    var log = new File("E:/Wirling Worlds/Simorgh/assets/effects/ink_drop/after_effects/build_log.txt");
    try {
        $.evalFile(new File("E:/Wirling Worlds/Simorgh/assets/effects/ink_drop/after_effects/build_ink_drop_rig.jsx"));
        log.open("w");
        log.write("BUILD_OK\n");
        log.close();
    } catch (e) {
        log.open("w");
        log.write("BUILD_ERROR\n" + e.toString() + "\nLine: " + e.line + "\nFile: " + e.fileName + "\n");
        log.close();
        try { app.quit(); } catch (ignore) {}
    }
})();
