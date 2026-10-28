"""Run in Houdini's Python shell or hython. Refuses to overwrite a scene.
Creates a Solaris USD Reference -> OUT scene using the supplied glass fixture.
"""
import argparse
from pathlib import Path
import hou
p = argparse.ArgumentParser()
p.add_argument('output')
a = p.parse_args()
out = Path(a.output).resolve()
if out.exists():
    raise SystemExit('Refusing to overwrite ' + str(out))
if 'apprentice' in str(hou.licenseCategory()).lower():
    raise SystemExit('Apprentice unsupported')
if hou.hipFile.hasUnsavedChanges():
    raise SystemExit('Save your current scene first; this generator is intended for a fresh hython process')
stage = hou.node('/stage') or hou.node('/').createNode('lopnet', 'stage')
reference = stage.createNode('sublayer', 'glass_fixture')
parm = reference.parm('filepath1')
if parm is None:
    raise SystemExit('Sublayer parameter differs in this Houdini build; use the UI to load tests/glass.usda')
parm.set(str(Path(__file__).with_name('glass.usda').resolve()).replace('\\', '/'))
output = stage.createNode('null', 'OUT')
output.setInput(0, reference)
output.setDisplayFlag(True)
stage.layoutChildren()
hou.hipFile.save(str(out))
print(out)
