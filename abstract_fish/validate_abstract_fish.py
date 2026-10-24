"""Read-only scene verification; writes only validation.json, never the HIP."""
from pathlib import Path
import hou
import build_abstract_fish as fish
root=Path(__file__).resolve().parent
scene=root/'abstract_fish.hipnc'
if not scene.exists():scene=root/'abstract_fish.hip'
hou.hipFile.load(str(scene),ignore_load_warnings=True,suppress_save_prompt=True)
fish.validate(hou.node('/obj/ABSTRACT_FISH'),hou.node('/obj/ABSTRACT_FISH/FINAL_MERGE'),root)
print('VALIDATION_PASSED',flush=True)
