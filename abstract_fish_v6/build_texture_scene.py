from pathlib import Path
import hou,json
from install_texture import install_texture
r=Path(__file__).resolve().parent;dest=r/'abstract_fish.hipnc'
if dest.exists():
 hou.hipFile.load(str(dest),ignore_load_warnings=True,suppress_save_prompt=True)
 c=hou.node('/stage/FISH_CONTROLS')
else:
 hou.hipFile.load(str(r.parent/'abstract_fish_v5/abstract_fish.hipnc'),ignore_load_warnings=True,suppress_save_prompt=True)
 c=install_texture('$HIP/textures/fish_pattern.png')
 hou.hipFile.save(str(dest))
g=hou.node('/obj/ABSTRACT_FISH/OUT_FISH').geometry();assert g.findPointAttrib('uv');assert not hou.node('/obj/ABSTRACT_FISH/PLANAR_TEXTURE_UV').errors()
from pxr import UsdGeom,UsdShade
stage=hou.node('/stage/fish_render_settings').stage();meshes=[p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh) and str(p.GetPath()).startswith('/fish/')]
assert meshes
bindings={}
for p in meshes:
 mat=UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0];assert mat,'Unbound '+str(p.GetPath());bindings[str(p.GetPath())]=str(mat.GetPath())
assert any('fish_texture_body' in v for v in bindings.values());assert any('fish_texture_parts' in v for v in bindings.values())
(r/'texture_validation.json').write_text(json.dumps({'planar_uv':True,'bindings':bindings},indent=2))
hou.node('/stage/fish_render_settings').parm('samplesperpixel').set(8)
rop=hou.node('/stage/fish_render');rop.parm('res_user1').set(720);rop.parm('res_user2').set(405);rop.parm('outputimage').set(str(r/'textured_preview.png'));rop.render()
print('TEXTURE_VALIDATED_RENDERED',flush=True)
