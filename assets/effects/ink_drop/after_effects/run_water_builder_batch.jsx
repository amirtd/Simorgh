(function(){
    var log=new File("E:/Wirling Worlds/Simorgh/assets/effects/ink_drop/after_effects/water_build_log.txt");
    try {
        app.open(new File("E:/Wirling Worlds/Simorgh/assets/effects/ink_drop/after_effects/persian_ink_drop.aep"));
        $.evalFile(new File("E:/Wirling Worlds/Simorgh/assets/effects/ink_drop/after_effects/add_animated_water_background.jsx"));
        app.project.save(new File("E:/Wirling Worlds/Simorgh/assets/effects/ink_drop/after_effects/persian_ink_drop_water.aep"));
        log.open("w"); log.write("BUILD_OK\n"); log.close();
    } catch(e) {
        log.open("w"); log.write("BUILD_ERROR\n"+e+"\nLine: "+e.line+"\nFile: "+e.fileName+"\n"); log.close();
    }
    try { app.quit(); } catch(ignore) {}
})();
