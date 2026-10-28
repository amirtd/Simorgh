"""Reorganize the Stage master without changing parameter names or animation."""
import hou

def install():
 c=hou.node('/stage/FISH_CONTROLS')
 if c is None:raise RuntimeError('Open the fish scene first')
 old=c.parmTemplateGroup()
 if [f.label() for f in old.entries()]==['Preview','Motion','Ribbons','Color','Individual Ribbons']:return c
 labels={'preview_performance':'Preview Performance','presentation_controls':'Presentation','fish_transform':'Fish Location and Rotation','motion_path':'Motion Path Rig','swimming':'Swimming Motion','paper_controls':'Paper Ribbons','wind_controls':'Wind Force','surface_controls':'Ribbon Surface','body_fin_controls':'Body and Fin Shape','texture_controls':'Texture and Color','ribbon_offsets':'Individual Ribbon Offsets'}
 groups=[('compact_preview','Preview',['preview_performance','presentation_controls']),('compact_motion','Motion',['fish_transform','motion_path','swimming']),('compact_ribbons','Ribbons',['paper_controls','wind_controls','surface_controls','body_fin_controls']),('compact_color','Color',['texture_controls']),('compact_individual','Individual Ribbons',['ribbon_offsets'])]
 assigned=set();new=hou.ParmTemplateGroup()
 for name,label,folders in groups:
  tab=hou.FolderParmTemplate(name,label)
  for source in folders:
   f=next((p for p in old.entries() if p.label()==labels[source]),None)
   if f is None:continue
   f=f.clone();f.setFolderType(hou.folderType.Collapsible);tab.addParmTemplate(f);assigned.add(f.name())
  # Keep per-system surface controls next to individual ribbon placement.
  if name=='compact_individual':
   for f in old.entries():
    if isinstance(f,hou.FolderParmTemplate) and f.label() in ('Head Surfaces','Upper Ribbons','Side Ribbons','Pectoral Fin','Pelvic Fin','Anal Fin','Tail Upper','Tail Middle','Tail Lower'):
     sub=f.clone();sub.setFolderType(hou.folderType.Collapsible);tab.addParmTemplate(sub);assigned.add(f.name())
  new.append(tab)
 # Retain any future/custom controls rather than dropping them.
 extras=[f for f in old.entries() if f.name() not in assigned]
 if extras:
  extra=hou.FolderParmTemplate('compact_extra','Other Controls')
  for f in extras:extra.addParmTemplate(f)
  new.append(extra)
 c.setParmTemplateGroup(new);c.setCurrent(True,clear_all_selected=True)
 return c
if __name__=='__main__':install()
